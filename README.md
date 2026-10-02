# Score Palette — Streamlit App

Upload a sheet music PDF, choose colors for the seven note names (C–B), and download a PDF with colored noteheads. A CSV recognition report is also available.

The app runs independently from this folder. It does not read or write the parent folder's `color_scores.py`, `colors.json`, `inputs/`, or `outputs/`. Its conversion code is separate from the local command-line version, so future changes are not automatically shared between them. The default palette is based on the local version's `colors.json` at the time the app was created, with D (Re) changed to `#FFEE74`.

## Run locally

Python 3.12 is recommended. Run the following commands from the app folder:

```sh
cd /Users/dsasaki/convert_scores/streamlit_app
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Open `http://localhost:8501` in your browser. Press `Ctrl+C` in the terminal to stop the app. For subsequent runs, only the last command is needed.

## How to use

Click the small **English** / **日本語** button in the upper-right corner to switch languages. Instructions, buttons, errors, and recognition warnings change language while your colors, uploaded file, and existing results are preserved. The CSV format, including column names and note data, remains the same in both languages. Text inside Streamlit's built-in widgets, such as “Browse files,” follows the framework's own display behavior.

Open **Supported sheet music and coloring rules** for supported formats, coloring rules, file size and page limits, and information about how uploads are handled.

1. Select one PDF, up to 20 MB and 50 pages.
2. Adjust the colors for C–B if needed.
3. Click **Color my score**.
4. Review the results and warnings, then download the PDF or CSV.

By default, uncolored notes or recognition warnings block PDF output, leaving only the CSV available. Enable **Allow partial output (color recognized notes only)** and run again to create a PDF with only the recognized notes colored. Partial output filenames end in `_partial_colored.pdf`. If no notes can be colored, no PDF is produced, even with partial output enabled.

Changing the file, colors, or partial-output setting clears the previous results and download buttons. Click **Clear PDF and results** to clear the upload and results held by the app.

## Supported formats and limitations

- Supports vector PDFs using legacy Maestro fonts or CID fonts with supported character mappings.
- Colors filled noteheads and the outlines of hollow and whole-note heads while preserving staff lines, text, flags, and layout.
- Colors follow written note names using fixed do. Sharps and flats are not distinguished, and notes in different octaves share the same color.
- Scans, photographs, noteheads drawn only as shapes, unsupported fonts such as SMuFL, music inside Form XObjects, and rotated pages are not supported. Encrypted PDFs are also rejected.
- Unsupported notes may go undetected. A count of zero uncolored notes does not guarantee that every note was recognized correctly. Always check the output.

In the CSV, a `status` of `colored` identifies a note selected for coloring. Other statuses indicate uncolored notes, including `no_staff` (staff not found), `no_clef` (clef not found), `ambiguous_staff` (uncertain staff assignment), and `off_staff_grid` (position does not align with the staff grid). When PDF output is blocked in normal mode, `colored` means the note could be colored if output were allowed. Coordinates are in PDF points measured from the top-left corner of the page's MediaBox. The CSV uses UTF-8 with a BOM to help applications display Japanese text correctly.

## Upload handling and operation

PDFs are sent to the application server and converted in memory. The app itself does not persist PDFs or CSVs to disk or external storage, and it does not use a shared cache for conversion results. Results are held separately for each Streamlit session. This does not guarantee how the hosting platform handles memory reclamation or access logs.

The 20 MB and 50-page limits help control resource use during normal operation. They do not impose strict memory or execution-time limits on highly compressed or complex PDFs, and the app does not include request rate limiting. For heavy use by the general public, consider adding process-level timeouts, a job queue, and rate limiting. This initial version is intended for small-scale shared use.

## Development and validation

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Tests use only synthetic PDFs and can run independently from this folder. They cover note names, colors, coordinate preservation, partial output, unsupported inputs, and input limits. Streamlit's AppTest also checks the interface, conversion flow, and removal of stale results after settings change. In AppTest, the file uploader's return value is replaced with a synthetic PDF. These tests do not automate file selection or saving downloads in a real browser.

Main files:

- `app.py`: Interface, session result management, and downloads.
- `score_coloring.py`: PDF recognition and coloring, exposing `convert_pdf(bytes, colors, allow_partial)`.
- `messages.py`: Japanese and English translations for the interface and conversion diagnostics.
- `requirements.txt`: Pinned versions of the direct dependencies used for validation.
- `.streamlit/config.toml`: Upload limit, usage statistics opt-out, and visual theme.

## Google Analytics

The production app uses the same GA4 web stream as the GitHub Pages sites:
`G-P4BVZ9ZZ0E`. `analytics.html` runs through Streamlit 1.64's non-iframe
`st.html(..., unsafe_allow_javascript=True)` API. It contains only trusted static
code; never interpolate uploaded content, filenames, or user input into it.

Tracking runs only on `score-pallete.streamlit.app`. A browser-window guard allows
one initialization per document load, so color changes, language switches,
conversion, and other Streamlit reruns do not send additional initial page views.
Reloading the page allows a new page view. Local development does not load GA4.
No custom upload, conversion, or download events are implemented here; automatic
measurement features follow the existing web stream's settings.

Use GA4's **Host name** dimension to distinguish `score-pallete.streamlit.app`
from `d1ssk.github.io`; use page paths to distinguish the GitHub Pages projects.
The Google tag derives the hostname from the actual page URL, so no custom
hostname parameter or new data stream is required.

### Cross-domain measurement (GA4 administrator setup)

This repository does not configure the GA4 account. To connect visits that follow
links between the sites, open the existing web stream for `G-P4BVZ9ZZ0E`:

1. Admin → Data streams → the existing web stream → Configure tag settings →
   Configure your domains.
2. Add **exactly matches** conditions for `d1ssk.github.io` and
   `score-pallete.streamlit.app`, then save. Do not match the shared hosting
   domains `github.io` or `streamlit.app` broadly.
3. Keep the same measurement ID on both sites. No additional tag is needed on
   GitHub Pages for this administrator-managed configuration.

Official documentation:
- https://support.google.com/analytics/answer/10071811
- https://docs.streamlit.io/develop/api-reference/text/st.html

### Verification

Run `node --test tests/analytics.test.cjs` for production-host, rerun, reload,
and incoming-link URL preservation checks, in addition to the Python app tests.
These checks do not contact Google and do not verify live GA4 delivery.

After deployment and administrator setup:

1. Open the app with browser developer tools. Check that Google tag requests use
   `G-P4BVZ9ZZ0E` and the page URL belongs to `score-pallete.streamlit.app`.
2. Change a color, switch language, and run a conversion. These reruns must not
   send another `page_view`. A full browser reload should send a new one.
3. Follow the Score Palette link from `https://d1ssk.github.io/`. Confirm that
   the destination URL receives `_gl` and that hosting redirects do not discard
   it before the Google tag reads it. The app does not clear query parameters.
4. Use Tag Assistant / GA4 DebugView to verify page views and continuity of the
   client and session IDs across that link, and check the Host name dimension
   in reporting. Seeing both sites in one property alone does not prove that
   cross-domain continuity works. Ad blockers and consent settings can suppress
   collection.
