"""AppTest drives real conversion with a synthetic upload (no private PDFs)."""

from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from test_conversion import make_score


APP = Path(__file__).resolve().parents[1] / "app.py"


def button(app, label):
    return next(item for item in app.button if item.label == label)


class AppTests(unittest.TestCase):
    def test_initial_page_and_reset(self):
        app = AppTest.from_file(str(APP)).run()
        self.assertFalse(app.exception)
        self.assertTrue(button(app, "色付けする").disabled)
        self.assertEqual(len(app.color_picker), 7)
        self.assertEqual(app.color_picker[1].value.upper(), "#FFEE74")
        app.color_picker[0].set_value("#112233").run()
        button(app, "配色を初期値に戻す").click().run()
        self.assertEqual(app.color_picker[0].value, "#000000")
        self.assertFalse(app.exception)

    def test_language_switch_keeps_upload_widget_identity(self):
        app = AppTest.from_file(str(APP)).run()
        upload_id = app.get("file_uploader")[0].proto.id
        button(app, "English").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.get("file_uploader")[0].proto.id, upload_id)
        self.assertEqual(app.title[0].value, "Score Palette")
        self.assertEqual(app.color_picker[1].label, "Re (D)")

    def test_language_switch_keeps_colors_and_results_and_translates_warnings(self):
        upload = BytesIO(make_score(blank_page=True))
        upload.name = "部分.pdf"
        with patch("streamlit.file_uploader", return_value=upload):
            app = AppTest.from_file(str(APP)).run()
            app.color_picker[1].set_value("#123456").run()
            app.checkbox[0].check().run()
            button(app, "色付けする").click().run()
            original_pdf = app.session_state["result"].pdf_bytes
            with patch("score_coloring.convert_pdf") as convert:
                button(app, "English").click().run()
                convert.assert_not_called()
            self.assertFalse(app.exception)
            self.assertEqual(app.color_picker[1].value, "#123456")
            self.assertTrue(app.checkbox[0].value)
            self.assertEqual(app.session_state["result"].pdf_bytes, original_pdf)
            self.assertIn("A partial PDF is ready", app.warning[0].value)
            self.assertIn("Page 2: No recognizable noteheads", app.text[0].value)
            self.assertEqual(app.get("download_button")[0].label, "Download colored PDF")
            button(app, "日本語").click().run()
            self.assertEqual(app.session_state["result"].pdf_bytes, original_pdf)
            self.assertIn("2ページ", app.text[0].value)
            button(app, "配色を初期値に戻す").click().run()
            self.assertEqual(app.color_picker[1].value.upper(), "#FFEE74")

    def test_error_is_translated_without_reprocessing(self):
        upload = BytesIO(b"not a pdf")
        upload.name = "invalid.pdf"
        with patch("streamlit.file_uploader", return_value=upload):
            app = AppTest.from_file(str(APP)).run()
            button(app, "色付けする").click().run()
            self.assertIn("PDF形式", app.error[0].value)
            button(app, "English").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.error[0].value, "Please choose a file in PDF format.")
            button(app, "Clear PDF and results").click().run()
            self.assertFalse(app.error)

    def test_conversion_download_and_stale_results(self):
        upload = BytesIO(make_score())
        upload.name = "テスト.pdf"
        # AppTest has no file_uploader setter; inject only the upload widget.
        with patch("streamlit.file_uploader", return_value=upload):
            app = AppTest.from_file(str(APP)).run()
            button(app, "色付けする").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.success), 1)
            self.assertEqual(len(app.get("download_button")), 2)
            self.assertTrue(app.session_state["result"].pdf_bytes.startswith(b"%PDF-"))
            app.color_picker[1].set_value("#ABCDEF").run()
            self.assertEqual(len(app.get("download_button")), 0)
            button(app, "色付けする").click().run()
            button(app, "PDFと結果をクリア").click().run()
            self.assertNotIn("result", app.session_state)
            self.assertEqual(app.session_state["upload_generation"], 1)

    def test_partial_mode_and_error_feedback(self):
        upload = BytesIO(make_score(blank_page=True))
        upload.name = "部分.pdf"
        with patch("streamlit.file_uploader", return_value=upload):
            app = AppTest.from_file(str(APP)).run()
            button(app, "色付けする").click().run()
            self.assertFalse(app.exception)
            self.assertIsNone(app.session_state["result"].pdf_bytes)
            self.assertEqual(len(app.get("download_button")), 1)
            app.checkbox[0].check().run()
            self.assertNotIn("result", app.session_state)
            button(app, "色付けする").click().run()
            self.assertEqual(len(app.get("download_button")), 2)
            self.assertTrue(app.warning)
        bad_upload = BytesIO(b"not a pdf")
        bad_upload.name = "invalid.pdf"
        with patch("streamlit.file_uploader", return_value=bad_upload):
            button(app, "色付けする").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            self.assertEqual(len(app.get("download_button")), 0)


if __name__ == "__main__":
    unittest.main()
