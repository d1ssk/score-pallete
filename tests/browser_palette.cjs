// Requires Playwright + Chromium and a running app. No private PDFs are used.
// NODE_PATH=/path/to/node_modules node tests/browser_palette.cjs [app URL]
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');

const url = process.argv[2] || 'http://127.0.0.1:8517';
const key = 'score-palette.colors.v1';
const savedText = 'このブラウザに配色を保存しました。次回も自動で復元します。';
const defaults = {C:'#000000', D:'#FFEE74', E:'#33AC5F', F:'#996A3B', G:'#57BBE3', A:'#E29C1C', B:'#E0C2EE'};
const imported = {...defaults, C:'#123456', D:'#ABCDEF'};
const payload = colors => Buffer.from(JSON.stringify({version:1, colors}));
const file = buffer => ({name:'colors.json', mimeType:'application/json', buffer});

async function expectStored(page, colors) {
    await page.waitForFunction(({key, colors}) => {
        const actual = JSON.parse(localStorage.getItem(key))?.colors;
        return actual && Object.keys(colors).every(note => actual[note].toUpperCase() === colors[note]);
    }, {key, colors});
}
async function expectColor(page, index, hex) {
    const rgb = hex.slice(1).match(/../g).map(n => parseInt(n, 16));
    await page.waitForFunction(({index, rgb}) => {
        const block = document.querySelectorAll('[data-testid="stColorPickerBlock"]')[index];
        return block && getComputedStyle(block).backgroundColor === `rgb(${rgb.join(', ')})`;
    }, {index, rgb});
}
async function openFiles(page) {
    await page.getByText('配色の保存・読み込み', {exact:true}).click();
}

(async () => {
    const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'palette-browser-'));
    let context;
    let browser;
    try {
        context = await chromium.launchPersistentContext(profile, {headless:true});
        let page = await context.newPage();
        await page.goto(url);
        await page.getByText(savedText).waitFor();
        await expectStored(page, defaults);
        await page.getByRole('button', {name:'ド (C) color picker', exact:true}).click();
        await page.getByLabel('hex', {exact:true}).fill('#654321');
        await page.getByRole('heading', {name:'2. 色を選ぶ'}).click();
        await expectStored(page, {...defaults, C:'#654321'});
        await page.reload();
        await page.getByText(savedText).waitFor();
        await expectColor(page, 0, '#654321');
        console.log('PASS: color change, automatic save, reload restoration');

        await openFiles(page);
        await page.locator('input[type=file]').nth(1).setInputFiles(file(payload(imported)));
        await page.getByText('色設定を読み込みました。', {exact:true}).waitFor();
        await expectColor(page, 0, imported.C);
        await expectColor(page, 1, imported.D);
        await expectStored(page, imported);
        const downloadEvent = page.waitForEvent('download');
        await page.getByRole('button', {name:'色設定を保存（JSON）'}).click();
        const download = await downloadEvent;
        assert.equal(download.suggestedFilename(), 'score-palette.json');
        assert.deepEqual(JSON.parse(await fs.readFile(await download.path(), 'utf8')).colors, imported);
        await page.locator('input[type=file]').nth(1).setInputFiles(file(Buffer.from('{}')));
        await page.getByText(/色設定を読み込めませんでした/).waitFor();
        await expectColor(page, 0, imported.C);
        await expectStored(page, imported);
        console.log('PASS: JSON import/export, invalid import preserves palette');

        await page.getByRole('button', {name:'English', exact:true}).click();
        await page.getByText('Colors saved in this browser. They will be restored next time.').waitFor();
        await expectColor(page, 0, imported.C);
        await context.close();
        context = await chromium.launchPersistentContext(profile, {headless:true});
        page = await context.newPage();
        await page.goto(url);
        await page.getByText(savedText).waitFor();
        await expectColor(page, 0, imported.C);
        await expectColor(page, 1, imported.D);
        console.log('PASS: language switch and browser shutdown/restart');

        browser = await chromium.launch();
        const isolated = await browser.newContext();
        const other = await isolated.newPage();
        await other.goto(url);
        await other.getByText(savedText).waitFor();
        await expectStored(other, defaults);
        await expectStored(page, imported);
        await isolated.close();
        await page.getByRole('button', {name:'配色を初期値に戻す'}).click();
        await expectStored(page, defaults);
        await page.reload();
        await page.getByText(savedText).waitFor();
        await expectColor(page, 0, defaults.C);
        console.log('PASS: browser isolation and persistent reset');

        await page.evaluate(key => localStorage.setItem(key, 'corrupt'), key);
        await page.reload();
        await page.getByText(/ブラウザに保存されていた配色を読み込めなかった/).waitFor();
        await expectColor(page, 0, defaults.C);
        const blocked = await browser.newContext();
        await blocked.addInitScript(() => {
            Object.defineProperty(window, 'localStorage', {get() {throw new Error('blocked');}});
        });
        const blockedPage = await blocked.newPage();
        await blockedPage.goto(url);
        await blockedPage.getByText(/ブラウザへの自動保存ができません/).waitFor();
        await openFiles(blockedPage);
        await blockedPage.locator('input[type=file]').nth(1).setInputFiles(file(payload(imported)));
        await blockedPage.getByText('色設定を読み込みました。', {exact:true}).waitFor();
        await expectColor(blockedPage, 0, imported.C);
        await blockedPage.getByText(/ブラウザへの自動保存ができません/).waitFor();
        assert.equal(await blockedPage.locator('[data-testid="stException"]').count(), 0);
        await blocked.close();
        console.log('PASS: corrupt storage recovery and file import with browser storage blocked');
    } finally {
        if (context) await context.close();
        if (browser) await browser.close();
        await fs.rm(profile, {recursive:true, force:true});
    }
})().catch(error => {console.error(error); process.exit(1);});
