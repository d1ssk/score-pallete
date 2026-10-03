"""Portable, versioned color settings (also accepts a plain note/color mapping)."""

import json
import re

from score_coloring import LETTERS

MAX_PALETTE_BYTES = 4096


def parse_palette(raw):
    """Validate the entire document before returning any colors."""
    if len(raw) > MAX_PALETTE_BYTES:
        raise ValueError("Palette too large")
    try:
        value = json.loads(raw)
        if isinstance(value, dict) and "version" in value:
            if type(value["version"]) is not int or value["version"] != 1:
                raise ValueError("Unsupported version")
            if set(value) != {"version", "colors"}:
                raise ValueError("Unexpected fields")
            value = value["colors"]
        if not isinstance(value, dict) or set(value) != set(LETTERS):
            raise ValueError("Invalid notes")
        if any(not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color)
               for color in value.values()):
            raise ValueError("Invalid color")
    except (UnicodeError, TypeError, RecursionError) as exc:
        raise ValueError("Invalid settings") from exc
    return {note: value[note].upper() for note in LETTERS}


def serialize_palette(colors):
    return json.dumps({"version": 1, "colors": colors}, indent=2) + "\n"
