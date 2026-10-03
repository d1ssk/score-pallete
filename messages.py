"""Japanese and English text shared by the UI and conversion diagnostics."""

TEXT = {
    "title": ("Score Palette", "Score Palette"),
    "subtitle": (
        "楽譜PDFの音符を音名ごとに7色で着色し、PDFとしてダウンロードできます。",
        "Color the notes in your sheet music PDF with seven colors. Download your colored PDF.",
    ),
    "rules": ("対応する楽譜と色付けのルール", "Supported sheet music and coloring rules"),
    "supported": (
        "対応する楽譜フォントを使ったPDF専用です。スキャン・写真の楽譜には対応していません。",
        "For PDFs using supported music fonts only. Scanned or photographed sheet music is not supported.",
    ),
    "rules_body": (
        "従来型Maestroフォント、および対応する文字配置のCIDフォントを使ったPDFが対象です。"
        "五線・文字・レイアウトを保ち、音符の符頭を着色します。\n\n"
        "固定ドの記譜上の音名で分類します。♯・♭・オクターブ違いは同じ色になります。"
        "白い符頭は輪郭を着色します。\n\n"
        "画像、図形のみの音符、SMuFLなど未対応フォント、Form XObject内の楽譜、"
        "回転ページは対象外です。未対応の音符は検出自体ができないこともあるため、"
        "処理後の楽譜をご確認ください。",
        "Supports legacy Maestro fonts and CID fonts with supported character mappings. "
        "Colors noteheads while preserving staff lines, text, and layout.\n\n"
        "Colors follow written note names (fixed do). Sharps, flats, and different octaves "
        "share the same color. For hollow noteheads, only the outline is colored.\n\n"
        "Images, notes drawn only as shapes, unsupported fonts such as SMuFL, music inside "
        "Form XObjects, and rotated pages are not supported. Some unsupported notes may "
        "not be detected at all. Please check the resulting score.",
    ),
    "privacy": (
        "上限：{mb}MB・{pages}ページ。PDFは実行サーバーへ送信されます。"
        "アプリはファイルに保存せず、セッションのメモリ上で処理します。",
        "Limit: {mb} MB and {pages} pages. Your PDF is sent to the application server. "
        "The app processes it in session memory without saving it to disk.",
    ),
    "upload_step": ("1. 楽譜を選ぶ", "1. Choose your sheet music"),
    "upload": ("楽譜PDF", "Sheet music PDF"),
    "upload_help": ("1ファイル{mb}MB・{pages}ページまで。", "One PDF, up to {mb} MB and {pages} pages."),
    "color_step": ("2. 色を選ぶ", "2. Choose your colors"),
    "reset": ("配色を初期値に戻す", "Reset colors"),
    "palette_loading": ("前回の配色を確認しています…", "Checking your saved colors…"),
    "palette_saved": ("このブラウザに配色を保存しました。次回も自動で復元します。", "Colors saved in this browser. They will be restored next time."),
    "palette_unavailable": ("ブラウザへの自動保存ができません。設定ファイルを保存してご利用ください。", "Browser saving is unavailable. Download your color settings to keep them."),
    "palette_files": ("配色の保存・読み込み", "Save or load color settings"),
    "palette_help": (
        "自動保存は同じ端末・ブラウザ・サイトで有効です。サイトデータの削除やシークレットモードでは失われることがあります。別の端末への移行やバックアップには設定ファイルをご利用ください。",
        "Automatic saving works on the same device, browser, and site. Clearing site data or using private browsing may erase it. Use a settings file for backup or transfer to another device.",
    ),
    "palette_download": ("色設定を保存（JSON）", "Download color settings (JSON)"),
    "palette_upload": ("色設定を読み込む（JSON）", "Load color settings (JSON)"),
    "palette_upload_help": ("4KB以下の設定ファイル。読み込むと現在の7色を置き換えます。", "Settings file up to 4 KB. Loading replaces all seven current colors."),
    "palette_imported": ("色設定を読み込みました。", "Color settings loaded."),
    "palette_invalid": ("色設定を読み込めませんでした。4KB以下で、C〜Bの7色が #RRGGBB 形式のJSONを選んでください。現在の配色は変更していません。", "Could not load settings. Choose a JSON file up to 4 KB with all seven C–B colors in #RRGGBB format. Your current colors are unchanged."),
    "palette_stored_invalid": ("ブラウザに保存されていた配色を読み込めなかったため、初期配色を使用します。", "The saved browser settings could not be read. Using the default colors."),
    "partial": ("読めた音符だけ着色して出力する（部分出力）", "Allow partial output (color recognized notes only)"),
    "partial_help": (
        "通常は、未着色の音符や認識上の注意があるとPDFの出力を止めます。部分出力では未対応箇所をそのまま残します。",
        "By default, uncolored notes or recognition warnings block PDF output. "
        "Partial output leaves unsupported content unchanged.",
    ),
    "partial_hint": (
        "未着色の箇所が残ることがあります。出力後に楽譜と読み取り結果をご確認ください。",
        "Some notes may remain uncolored. Please review the score and recognition report.",
    ),
    "convert": ("色付けする", "Color my score"),
    "loading": ("PDFを読み込んでいます…", "Reading your PDF…"),
    "progress": ("{done} / {total}ページを処理しました", "Processed {done} / {total} pages"),
    "unexpected": (
        "処理を完了できませんでした。別のPDFか、ページ数を減らしたPDFでお試しください。",
        "Processing could not be completed. Try another PDF or a PDF with fewer pages.",
    ),
    "result_step": ("3. 結果をダウンロード", "3. Download your results"),
    "no_notes": (
        "着色できる音符がありません。画像PDFや未対応フォントの可能性があります。",
        "No notes could be colored. This may be an image-based PDF or use an unsupported font.",
    ),
    "blocked": (
        "読み取りに問題があるため、PDFの出力を止めました。下の注意とCSVを確認してください。"
        "部分出力が必要なら、上のチェックを入れて再実行できます。",
        "PDF output was blocked because of recognition issues. Review the warnings and CSV below. "
        "To create a partial PDF, enable partial output above and run again.",
    ),
    "partial_done": (
        "部分出力のPDFを作成しました。未着色箇所や認識上の注意をご確認ください。",
        "A partial PDF is ready. Please check uncolored notes and recognition warnings.",
    ),
    "done": ("色付けしたPDFを作成しました。", "Your colored PDF is ready."),
    "pages": ("ページ数", "Pages"),
    "colored": ("着色した音符", "Colored notes"),
    "colorable": ("着色可能な音符", "Colorable notes"),
    "skipped": ("検出した未着色の音符", "Detected uncolored notes"),
    "counts_hint": (
        "未対応の音符は検出できない場合があります。音符数は認識できた範囲の集計です。",
        "Unsupported notes may go undetected. These counts cover detected notes only.",
    ),
    "issues": ("認識上の注意（{count}件）", "Recognition warnings ({count})"),
    "download_pdf": ("着色済みPDFをダウンロード", "Download colored PDF"),
    "download_csv": ("読み取り結果CSVをダウンロード", "Download recognition CSV"),
    "clear": ("PDFと結果をクリア", "Clear PDF and results"),
    "invalid_color_keys": (
        "色設定には C, D, E, F, G, A, B を指定してください。",
        "Use C, D, E, F, G, A, B as color keys.",
    ),
    "invalid_color": ("色は #RRGGBB 形式で指定してください。", "Specify colors in #RRGGBB format."),
    "empty": ("ファイルが空です。PDFを選び直してください。", "The file is empty. Please choose a PDF."),
    "too_large": ("PDFは{mb}MB以下にしてください。", "The PDF must be {mb} MB or smaller."),
    "not_pdf": ("PDF形式のファイルを選んでください。", "Please choose a file in PDF format."),
    "unreadable": (
        "このPDFを読み取れませんでした。ファイルが破損しているか、未対応の構造を含んでいます。別のPDFでお試しください。",
        "This PDF could not be read. It may be damaged or contain an unsupported structure. Please try another PDF.",
    ),
    "encrypted": ("暗号化・パスワード付きPDFは対象外です。", "Encrypted or password-protected PDFs are not supported."),
    "no_pages": ("ページのないPDFは処理できません。", "PDFs with no pages cannot be processed."),
    "too_many_pages": ("PDFは{pages}ページ以下にしてください。", "The PDF must have {pages} pages or fewer."),
    "rotated_page": (
        "{page}ページ目は回転しています。PDF編集ソフトで回転を解除してください。",
        "Page {page} is rotated. Remove the page rotation in a PDF editor first.",
    ),
    "invalid_text": (
        "不正な長さの文字列があり、認識できない文字があります",
        "Some characters could not be recognized because of an invalid text string length",
    ),
    "rotated_text": ("回転・傾斜した楽譜文字は対象外です", "Rotated or skewed music text is not supported"),
    "form_xobject": ("Form XObject内の楽譜は対象外です", "Music inside Form XObjects is not supported"),
    "no_noteheads": (
        "認識できる符頭がありません（画像PDF・未対応フォント・空白ページ等）",
        "No recognizable noteheads (image-based PDF, unsupported font, blank page, etc.)",
    ),
    "page_issue": ("{page}ページ: {issue}", "Page {page}: {issue}"),
}

SOLFEGE_EN = dict(zip("CDEFGAB", ["Do", "Re", "Mi", "Fa", "Sol", "La", "Ti"]))


def translate(language, key, **values):
    return TEXT[key][1 if language == "en" else 0].format(**values)
