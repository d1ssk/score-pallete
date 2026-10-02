const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const test = require("node:test");

const html = readFileSync(join(__dirname, "../analytics.html"), "utf8");
const source = html.match(/<script>([\s\S]*?)<\/script>/)[1];
function browser(hostname = "score-pallete.streamlit.app", search = "") {
  const scripts = [];
  const window = { location: { hostname, search } };
  const context = vm.createContext({
    window,
    document: {
      createElement: () => ({}),
      head: { appendChild: (script) => scripts.push(script) },
    },
  });
  return { window, scripts, run: () => vm.runInContext(source, context) };
}

test("production initializes the shared stream once across reruns", () => {
  const page = browser();
  for (let i = 0; i < 10; i++) page.run();
  assert.equal(page.scripts.length, 1);
  assert.equal(page.scripts[0].async, true);
  assert.equal(page.scripts[0].src,
    "https://www.googletagmanager.com/gtag/js?id=G-P4BVZ9ZZ0E");
  assert.equal(page.window.dataLayer.length, 2);
  assert.deepEqual(Array.from(page.window.dataLayer[1]), ["config", "G-P4BVZ9ZZ0E"]);
});

test("local and unrelated hosts never initialize tracking", () => {
  for (const host of ["localhost", "127.0.0.1", "other.streamlit.app",
    "score-pallete.streamlit.app.example.com"]) {
    const page = browser(host);
    page.run();
    assert.equal(page.scripts.length, 0);
    assert.equal(page.window.dataLayer, undefined);
  }
});

test("a new document can initialize tracking again", () => {
  for (let i = 0; i < 2; i++) {
    const page = browser();
    page.run();
    assert.equal(page.scripts.length, 1);
    assert.equal(page.window.dataLayer[1][0], "config");
  }
});

test("incoming linker and campaign parameters are preserved", () => {
  const query = "?_gl=example-linker-value&utm_source=portfolio";
  const page = browser("score-pallete.streamlit.app", query);
  page.run();
  assert.equal(page.window.location.search, query);
});
