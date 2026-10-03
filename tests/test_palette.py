import json
from io import BytesIO
import unittest
from unittest.mock import patch

from palette import parse_palette, serialize_palette
from score_coloring import DEFAULT_COLORS


class PaletteTests(unittest.TestCase):
    def test_round_trip_and_legacy_mapping(self):
        expected = {note: color.upper() for note, color in DEFAULT_COLORS.items()}
        self.assertEqual(parse_palette(serialize_palette(DEFAULT_COLORS).encode()), expected)
        self.assertEqual(parse_palette(json.dumps(DEFAULT_COLORS)), expected)

    def test_invalid_documents(self):
        for raw in [
            b"\xff", "{", "[]", "null", "{}", " " * 4097,
            json.dumps({"version": 2, "colors": DEFAULT_COLORS}),
            json.dumps({"version": True, "colors": DEFAULT_COLORS}),
            json.dumps({**DEFAULT_COLORS, "C": "red"}),
            json.dumps({**DEFAULT_COLORS, "C": 123}),
            json.dumps({**DEFAULT_COLORS, "C": "#123456\n"}),
            json.dumps({**DEFAULT_COLORS, "X": "#123456"}),
            json.dumps({"version": 1, "colors": []}),
        ]:
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                parse_palette(raw)

    def test_import_applies_atomically_and_discards_stale_result(self):
        from app import import_palette
        state = {"color_C": "#ABCDEF", "result": "existing result",
                 "palette_upload": BytesIO(b"{}")}
        with patch("app.st.session_state", state):
            import_palette()
            self.assertEqual(state["color_C"], "#ABCDEF")
            self.assertEqual(state["result"], "existing result")
            self.assertEqual(state["palette_notice"], "palette_invalid")
            state["palette_upload"] = BytesIO(serialize_palette(DEFAULT_COLORS).encode())
            import_palette()
        self.assertEqual(state["color_C"], DEFAULT_COLORS["C"])
        self.assertNotIn("result", state)
        self.assertTrue(state["palette_ready"])

    def test_late_browser_restore_does_not_replace_user_edit(self):
        from app import restore_browser_palette
        state = {"color_C": "#ABCDEF", "palette_ready": True,
                 "palette_storage": {"loaded": {"raw": serialize_palette(DEFAULT_COLORS)}}}
        with patch("app.st.session_state", state):
            restore_browser_palette()
        self.assertEqual(state["color_C"], "#ABCDEF")

    def test_browser_restore_and_invalid_storage(self):
        from app import restore_browser_palette
        state = {"palette_storage": {"loaded": {"raw": serialize_palette(DEFAULT_COLORS)}}}
        with patch("app.st.session_state", state):
            restore_browser_palette()
        self.assertEqual(state["color_D"], DEFAULT_COLORS["D"])
        state = {"palette_storage": {"loaded": {"raw": "broken"}}}
        with patch("app.st.session_state", state):
            restore_browser_palette()
        self.assertEqual(state["palette_notice"], "palette_stored_invalid")
        self.assertTrue(state["palette_ready"])
