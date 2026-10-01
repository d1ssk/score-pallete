"""Synthetic PDFs only: tests can be published without the local sheet music."""

import csv
from io import BytesIO, StringIO
import unittest

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject,
)

from score_coloring import (
    ConversionError, DEFAULT_COLORS, MAX_PAGES, MAX_UPLOAD_MB, convert_pdf, scan_page,
)


def make_score(*, no_clef=False, blank_page=False, rotated=False, encrypted=False):
    writer = PdfWriter()
    page = writer.add_blank_page(300, 300)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Maestro"),
        NameObject("/FirstChar"): NumberObject(0),
        NameObject("/LastChar"): NumberObject(255),
        NameObject("/Widths"): ArrayObject([NumberObject(500) for _ in range(256)]),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)}),
    })
    stream = DecodedStreamObject()
    lines = b"\n".join(f"20 {y} m 280 {y} l S".encode() for y in (160, 170, 180, 190, 200))
    clef = b"" if no_clef else b"BT /F1 20 Tf 1 0 0 1 30 170 Tm <26> Tj ET\n"
    stream.set_data(lines + b"\n" + clef +
                    b"BT /F1 20 Tf 1 0 0 1 60 160 Tm <CF> Tj "
                    b"1 0 0 1 90 150 Tm <FA> Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    if rotated:
        page.rotate(90)
    if blank_page:
        writer.add_blank_page(300, 300)
    if encrypted:
        writer.encrypt("secret")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class ConversionTests(unittest.TestCase):
    def test_colors_pitch_and_positions_survive(self):
        data = make_score()
        progress = []
        result = convert_pdf(data, {"E": "#123456"}, progress=lambda *x: progress.append(x))
        self.assertEqual((result.page_count, result.colored, result.skipped), (1, 2, 0))
        self.assertFalse(result.needs_review)
        self.assertEqual(progress, [(1, 1)])
        rows = list(csv.DictReader(StringIO(result.csv_bytes.decode("utf-8-sig"))))
        self.assertEqual([(r["note"], r["written_octave"]) for r in rows], [("E", "4"), ("C", "4")])
        self.assertEqual(rows[0]["color"], "#123456")
        before = PdfReader(BytesIO(data)).pages[0]
        after = PdfReader(BytesIO(result.pdf_bytes)).pages[0]
        self.assertEqual(before.mediabox, after.mediabox)
        self.assertEqual(before.extract_text(), after.extract_text())
        _, _, old_glyphs, old_staves, _ = scan_page(before)
        stream, _, new_glyphs, new_staves, _ = scan_page(after)
        self.assertEqual([(g.kind, g.x, g.y) for g in old_glyphs],
                         [(g.kind, g.x, g.y) for g in new_glyphs])
        self.assertEqual(old_staves, new_staves)
        rgb = next(args for args, op in stream.operations if op == b"rg")
        for actual, expected in zip(rgb, (0x12 / 255, 0x34 / 255, 0x56 / 255)):
            self.assertAlmostEqual(float(actual), expected, places=6)
        self.assertNotEqual(DEFAULT_COLORS["E"], "#123456")

    def test_partial_output_requires_explicit_choice(self):
        data = make_score(blank_page=True)
        blocked = convert_pdf(data)
        self.assertIsNone(blocked.pdf_bytes)
        self.assertEqual(blocked.colored, 2)
        self.assertIn("2ページ", blocked.issues[0].message("ja"))
        self.assertIn("Page 2: No recognizable noteheads", blocked.issues[0].message("en"))
        self.assertIn(b"colored", blocked.csv_bytes)
        allowed = convert_pdf(data, allow_partial=True)
        self.assertEqual(len(PdfReader(BytesIO(allowed.pdf_bytes)).pages), 2)
        self.assertTrue(allowed.needs_review)

    def test_unrecognized_notes_never_produce_a_pdf(self):
        result = convert_pdf(make_score(no_clef=True), allow_partial=True)
        self.assertIsNone(result.pdf_bytes)
        self.assertEqual((result.colored, result.skipped), (0, 2))
        self.assertIn(b"no_clef", result.csv_bytes)

    def test_blank_document_returns_report_and_warning(self):
        writer = PdfWriter()
        writer.add_blank_page(100, 100)
        data = BytesIO()
        writer.write(data)
        result = convert_pdf(data.getvalue(), allow_partial=True)
        self.assertIsNone(result.pdf_bytes)
        self.assertTrue(result.issues)
        self.assertEqual(len(result.csv_bytes.decode("utf-8-sig").splitlines()), 1)

    def test_invalid_encrypted_rotated_and_oversized_inputs(self):
        cases = [
            (b"", "空"), (b"not a pdf", "PDF形式"), (b"%PDF-broken", "読み取れません"),
            (make_score(encrypted=True), "暗号化"), (make_score(rotated=True), "回転"),
            (b"%PDF-" + b"x" * (MAX_UPLOAD_MB * 1024 * 1024), "MB以下"),
        ]
        for data, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ConversionError, message):
                convert_pdf(data)
        writer = PdfWriter()
        for _ in range(MAX_PAGES + 1):
            writer.add_blank_page(100, 100)
        data = BytesIO()
        writer.write(data)
        with self.assertRaisesRegex(ConversionError, "ページ以下"):
            convert_pdf(data.getvalue())

    def test_invalid_colors_are_rejected(self):
        for colors in ({"H": "#000000"}, {"C": "red"}, {"C": None}):
            with self.subTest(colors=colors), self.assertRaises(ConversionError):
                convert_pdf(make_score(), colors)


if __name__ == "__main__":
    unittest.main()
