# Score Palette — Streamlit App

Upload a sheet music PDF, choose colors for the seven note names (C–B), and download a PDF with colored noteheads. A CSV recognition report is also available.

Open [Score Palette](https://score-pallete.streamlit.app/) to use the app in your browser.

## Run locally

Python 3.12 is recommended. Run the following commands from the app folder:

```sh
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
