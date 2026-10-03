# Score Palette development

Run commands from the repository root. Python 3.12 and the pinned dependencies in `requirements.txt` are used for validation.

## Run locally

Python 3.12 is recommended. Run the following commands from the app folder:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Open `http://localhost:8501` in your browser. Press `Ctrl+C` in the terminal to stop the app. For subsequent runs, only the last command is needed.

## Development and validation

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Tests use only synthetic PDFs and can run independently from this folder. They cover note names, colors, coordinate preservation, partial output, unsupported inputs, input limits, palette validation, and restore/import behavior. Streamlit's AppTest also checks the interface, conversion flow, and removal of stale results after settings change. In AppTest, the PDF uploader's return value is replaced with a synthetic PDF and the browser-storage component is mocked because AppTest does not execute JavaScript.

For browser persistence and real settings-file upload/download checks, start the app and run the following with Playwright and its Chromium browser installed in your test environment:

```sh
node tests/browser_palette.cjs http://localhost:8501
```

If Playwright is installed outside this folder, set `NODE_PATH` to that environment's `node_modules` directory. This test uses a temporary browser profile and removes it afterward. It checks color edits, reloads, browser shutdown/restart, JSON import/export, invalid settings, reset, language switching, separate browser profiles, and unavailable browser storage.

Main files:

- `app.py`: Interface, session result management, and downloads.
- `score_coloring.py`: PDF recognition and coloring, exposing `convert_pdf(bytes, colors, allow_partial)`.
- `messages.py`: Japanese and English translations for the interface and conversion diagnostics.
- `palette.py`: Versioned JSON validation and serialization; also accepts plain note/color mappings.
- `palette_storage.py` / `palette_storage.js`: Browser persistence through Streamlit components v2, with no extra Python dependency or external service.
- `requirements.txt`: Pinned versions of the direct dependencies used for validation.

Analytics setup and live verification are documented in [analytics.md](analytics.md).

The conversion code is independent of any local command-line score converter; changes must be reviewed and applied to this app explicitly. Conversion runs in memory without shared result caching. For heavier hosting workloads, evaluate process-level timeouts, job queues, and rate limiting; the upload limits alone do not bound execution time.
