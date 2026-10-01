#!/usr/bin/env python3
"""Color noteheads in supported vector PDFs, preserving the original notation.

Coordinates in reports are PDF points measured from the media box's top left.
Pitch means written diatonic pitch: accidentals and octave signs are not applied.
"""

import copy
import csv
import re
from dataclasses import dataclass, field
from io import BytesIO, StringIO
from typing import List, Tuple, Optional, Mapping, Callable

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError
from pypdf.generic import ArrayObject, ByteStringObject, ContentStream, FloatObject

from messages import translate


# アプリ独自の初期配色。作成時のローカル版 colors.json を引き継ぐ。
DEFAULT_COLORS = {
    "C": "#000000",  # ド: 黒
    "D": "#FFEE74",  # レ: 黄色
    "E": "#33AC5F",  # ミ: 薄めの黄緑
    "F": "#996A3B",  # ファ: 薄めの茶色
    "G": "#57BBE3",  # ソ: 水色
    "A": "#E29C1C",  # ラ: オレンジ
    "B": "#E0C2EE",  # シ: 薄めのラベンダー
}
LETTERS = "CDEFGAB"
SOLFEGE = dict(zip(LETTERS, ["ド", "レ", "ミ", "ファ", "ソ", "ラ", "シ"]))
IDENTITY = (1., 0., 0., 1., 0., 0.)
LEGACY_SYMBOLS = {
    0xCF: "black", 0xFA: "half", 0x77: "whole",
    0x26: "treble", 0x3F: "bass", 0x42: "c_clef",
}
# Legacy Maestro CID fonts in some PDF exporters use a Symbol-font ToUnicode map.
MAESTRO_CID_SYMBOLS = {
    0x0153: "black", 0x02D9: "half", 0x0077: "whole",
    0x0026: "treble", 0x003F: "bass", 0x0042: "c_clef",
}
NOTE_KINDS = {"black", "half", "whole"}
REFERENCE_PITCH = {"treble": 4 * 7 + 4, "bass": 3 * 7 + 3, "c_clef": 4 * 7}


def object_value(value):
    return value.get_object() if hasattr(value, "get_object") else value


def raw_bytes(value):
    if isinstance(value, bytes):
        return value
    return bytes(value.original_bytes)


def transform(matrix, x, y):
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


def compose(outer, inner):
    """Return outer(inner(point)), using PDF's six-element matrix notation."""
    a, b, c, d, e, f = inner
    aa, bb, cc, dd, ee, ff = outer
    return (aa*a + cc*b, bb*a + dd*b, aa*c + cc*d, bb*c + dd*d,
            aa*e + cc*f + ee, bb*e + dd*f + ff)


def parse_cmap(data):
    """Read bfchar and bfrange entries without assuming CID equals Unicode."""
    source = re.sub(rb"%[^\r\n]*", b"", data).decode("latin1")
    result = {}
    for block in re.findall(r"beginbfchar(.*?)endbfchar", source, re.S):
        for key, value in re.findall(r"<([\da-fA-F]+)>\s*<([\da-fA-F]+)>", block):
            result[bytes.fromhex(key)] = bytes.fromhex(value).decode("utf-16-be")
    for block in re.findall(r"beginbfrange(.*?)endbfrange", source, re.S):
        entries = re.findall(
            r"<([\da-fA-F]+)>\s*<([\da-fA-F]+)>\s*(\[.*?\]|<[\da-fA-F]+>)",
            block, re.S,
        )
        for first, last, target in entries:
            start, end = int(first, 16), int(last, 16)
            width = len(first) // 2
            if end - start > 65535:
                raise ValueError("過大なフォント文字範囲です")
            if target.startswith("["):
                values = [bytes.fromhex(v) for v in re.findall(r"<([\da-fA-F]+)>", target)]
            else:
                base = bytes.fromhex(target[1:-1])
                values = [(int.from_bytes(base, "big") + offset).to_bytes(len(base), "big")
                          for offset in range(end - start + 1)]
            for offset, value in enumerate(values[:end - start + 1]):
                # Some exporters include invalid extra entries beyond codespace.
                if start + offset >= 1 << (width * 8):
                    break
                result[(start + offset).to_bytes(width, "big")] = value.decode("utf-16-be", errors="replace")
    return result


class Font:
    def __init__(self, pdf_font):
        pdf_font = object_value(pdf_font)
        self.name = str(pdf_font.get("/BaseFont", ""))
        self.cid = pdf_font.get("/Subtype") == "/Type0"
        self.unit = 2 if self.cid else 1
        self.supported_encoding = not self.cid or pdf_font.get("/Encoding") == "/Identity-H"
        self.maestro = "Maestro" in self.name and "FinaleMaestro" not in self.name
        self.cmap = parse_cmap(object_value(pdf_font["/ToUnicode"]).get_data()) if "/ToUnicode" in pdf_font else {}
        self.widths = {}
        self.default_width = 0.
        if self.cid:
            descendant = object_value(pdf_font["/DescendantFonts"][0])
            self.default_width = float(descendant.get("/DW", 1000))
            widths = list(object_value(descendant.get("/W", [])))
            i = 0
            while i < len(widths):
                first = int(widths[i])
                item = object_value(widths[i + 1])
                if isinstance(item, list):
                    self.widths.update((first + j, float(w)) for j, w in enumerate(item))
                    i += 2
                else:
                    last, width = int(item), float(widths[i + 2])
                    self.widths.update((code, width) for code in range(first, last + 1))
                    i += 3
        else:
            first = int(pdf_font.get("/FirstChar", 0))
            self.widths = {first + j: float(w) for j, w in enumerate(object_value(pdf_font.get("/Widths", [])))}

    def symbol(self, raw):
        if not self.supported_encoding:
            return None
        code = int.from_bytes(raw, "big")
        if self.maestro and not self.cid:
            return LEGACY_SYMBOLS.get(code)
        text = self.cmap.get(raw, "")
        if len(text) != 1:
            return None
        unicode_value = ord(text)
        if 0xF000 <= unicode_value <= 0xF0FF:
            return LEGACY_SYMBOLS.get(unicode_value - 0xF000)
        if self.maestro:
            return MAESTRO_CID_SYMBOLS.get(unicode_value)
        return None

    def width(self, raw):
        return self.widths.get(int.from_bytes(raw, "big"), self.default_width)


@dataclass
class State:
    ctm: Tuple = IDENTITY
    font_name: str = ""
    font_size: float = 0.
    char_space: float = 0.
    word_space: float = 0.
    horizontal_scale: float = 1.
    leading: float = 0.
    rise: float = 0.


@dataclass
class Glyph:
    operation: int
    ordinal: int
    kind: str
    x: float
    y: float
    font: str


@dataclass
class Staff:
    index: int
    left: float
    right: float
    lines: List[float]
    clefs: List[Glyph] = field(default_factory=list)

    @property
    def gap(self):
        return (self.lines[-1] - self.lines[0]) / 4

    @property
    def center(self):
        return (self.lines[0] + self.lines[-1]) / 2


def scan_page(page):
    """Interpret text placement and straight lines, keeping glyph operation IDs."""
    stream = ContentStream(page.get_contents(), page.pdf)
    resources = object_value(page.get("/Resources", {}))
    fonts = {str(key): Font(value) for key, value in object_value(resources.get("/Font", {})).items()}
    state, stack = State(), []
    tm = tlm = IDENTITY
    start = current = None
    pending_lines, lines, glyphs = [], [], []
    issues = set()
    box = page.mediabox

    def point(x, y):
        xx, yy = transform(state.ctm, float(x), float(y))
        return xx - float(box.left), float(box.top) - yy

    def show(items, operation):
        nonlocal tm
        font = fonts.get(state.font_name)
        ordinal = 0
        for item in items:
            if not isinstance(item, (str, bytes)):
                tm = compose(tm, (1, 0, 0, 1, -float(item) / 1000 * state.font_size * state.horizontal_scale, 0))
                continue
            raw = raw_bytes(item)
            unit = font.unit if font else 1
            if len(raw) % unit:
                issues.add("invalid_text")
                continue
            for offset in range(0, len(raw), unit):
                char = raw[offset:offset + unit]
                symbol = font.symbol(char) if font else None
                if symbol:
                    xx, yy = transform(tm, 0, state.rise)
                    x, y = point(xx, yy)
                    # Pitch positions assume horizontal, unskewed music text.
                    matrix = compose(state.ctm, tm)
                    if abs(matrix[1]) > 0.001 or abs(matrix[2]) > 0.001:
                        issues.add("rotated_text")
                    else:
                        glyphs.append(Glyph(operation, ordinal, symbol, x, y, font.name))
                width = font.width(char) if font else 0
                extra = state.word_space if unit == 1 and char == b" " else 0
                advance = (width / 1000 * state.font_size + state.char_space + extra) * state.horizontal_scale
                tm = compose(tm, (1, 0, 0, 1, advance, 0))
                ordinal += 1

    for index, (args, op) in enumerate(stream.operations):
        if op == b"q":
            stack.append(copy.copy(state))
        elif op == b"Q":
            if stack:
                state = stack.pop()
        elif op == b"cm":
            state.ctm = compose(state.ctm, tuple(float(x) for x in args))
        elif op == b"BT":
            tm = tlm = IDENTITY
        elif op == b"Tf":
            state.font_name, state.font_size = str(args[0]), float(args[1])
        elif op in (b"Tc", b"Tw", b"Tz", b"TL", b"Ts"):
            attribute = {b"Tc": "char_space", b"Tw": "word_space", b"Tz": "horizontal_scale",
                         b"TL": "leading", b"Ts": "rise"}[op]
            setattr(state, attribute, float(args[0]) / (100 if op == b"Tz" else 1))
        elif op == b"Tm":
            tm = tlm = tuple(float(x) for x in args)
        elif op in (b"Td", b"TD"):
            if op == b"TD":
                state.leading = -float(args[1])
            tm = tlm = compose(tlm, (1, 0, 0, 1, float(args[0]), float(args[1])))
        elif op == b"T*":
            tm = tlm = compose(tlm, (1, 0, 0, 1, 0, -state.leading))
        elif op in (b"Tj", b"TJ", b"'", b'"'):
            if op == b'"':
                state.word_space, state.char_space = float(args[0]), float(args[1])
            if op in (b"'", b'"'):
                tm = tlm = compose(tlm, (1, 0, 0, 1, 0, -state.leading))
            show(args[0] if op == b"TJ" else [args[-1]], index)
        elif op == b"m":
            start = current = point(*args)
        elif op == b"l":
            end = point(*args)
            if current:
                pending_lines.append((current, end))
            current = end
        elif op == b"re":
            x, y, w, h = (float(v) for v in args)
            corners = [point(x, y), point(x + w, y), point(x + w, y + h), point(x, y + h)]
            pending_lines.extend(zip(corners, corners[1:] + corners[:1]))
            start = current = corners[0]
        elif op in (b"c", b"v", b"y"):
            current = point(args[-2], args[-1])
        elif op == b"h":
            if current and start:
                pending_lines.append((current, start))
            current = start
        elif op in (b"S", b"s", b"B", b"B*", b"b", b"b*", b"f", b"F", b"f*", b"n"):
            if op in (b"S", b"s", b"B", b"B*", b"b", b"b*"):
                lines.extend(pending_lines)
            elif op != b"n":
                # Very thin filled rectangles can also represent staff lines.
                for a, b in pending_lines:
                    if abs(a[1] - b[1]) < .15:
                        lines.append((a, b))
            pending_lines, start, current = [], None, None
        elif op == b"Do":
            obj = object_value(object_value(resources.get("/XObject", {})).get(args[0]))
            if obj and obj.get("/Subtype") == "/Form":
                issues.add("form_xobject")
    return stream, fonts, glyphs, find_staves(lines), sorted(issues)


def find_staves(lines):
    horizontal = sorted((min(a[0], b[0]), max(a[0], b[0]), (a[1] + b[1]) / 2)
                        for a, b in lines if abs(a[1] - b[1]) < .15 and abs(a[0] - b[0]) > 40)
    # Join segments on the same y, including staff lines split by barlines.
    merged = []
    for left, right, y in sorted(horizontal, key=lambda row: (row[2], row[0])):
        match = next((row for row in merged if abs(row[2] - y) < .25 and
                      left <= row[1] + 2 and right >= row[0] - 2), None)
        if match is None:
            merged.append([left, right, y])
        else:
            match[0], match[1] = min(match[0], left), max(match[1], right)
    merged.sort(key=lambda row: row[2])
    candidates = []
    for i, first in enumerate(merged):
        for j in range(i + 1, len(merged)):
            gap = merged[j][2] - first[2]
            if gap > 14:
                break
            if gap < 2:
                continue
            indices = [i, j]
            for step in range(2, 5):
                target = first[2] + step * gap
                candidate = next((k for k in range(j + 1, len(merged))
                                  if k not in indices and
                                  abs(merged[k][2] - target) < max(.28, gap * .06) and
                                  min(first[1], merged[k][1]) - max(first[0], merged[k][0]) > 40), None)
                if candidate is None:
                    break
                indices.append(candidate)
            if len(indices) == 5:
                left = max(merged[k][0] for k in indices)
                right = min(merged[k][1] for k in indices)
                if right - left < 40:
                    continue
                candidates.append((right - left, indices, left, right))
    # Long five-line groups take priority over clusters of short ledger lines.
    used, staves = set(), []
    for width, indices, left, right in sorted(candidates, key=lambda candidate: -candidate[0]):
        if not used.intersection(indices):
            staves.append(Staff(0, left, right, [merged[k][2] for k in indices]))
            used.update(indices)
    staves.sort(key=lambda staff: (staff.lines[0], staff.left))
    for i, staff in enumerate(staves, 1):
        staff.index = i
    return staves


def nearest_staff(glyph, staves):
    eligible = [staff for staff in staves if staff.left - 5 <= glyph.x <= staff.right + 5]
    return sorted(eligible, key=lambda staff: abs(glyph.y - staff.center) / staff.gap)


def classify_notes(glyphs, staves, page_number, colors):
    for glyph in glyphs:
        if glyph.kind in REFERENCE_PITCH:
            candidates = nearest_staff(glyph, staves)
            if candidates and abs(glyph.y - candidates[0].center) < candidates[0].gap * 3:
                candidates[0].clefs.append(glyph)
    for staff in staves:
        staff.clefs.sort(key=lambda clef: clef.x)
    rows, selected = [], {}
    for glyph in glyphs:
        if glyph.kind not in NOTE_KINDS:
            continue
        row = {"page": page_number, "staff": "", "x_pt": round(glyph.x, 3),
               "y_pt": round(glyph.y, 3), "note": "", "solfege": "", "written_octave": "",
               "clef": "", "kind": glyph.kind, "color": "", "status": "", "font": glyph.font}
        candidates = nearest_staff(glyph, staves)
        reason = ""
        if not candidates:
            reason = "no_staff"
        else:
            staff = candidates[0]
            row["staff"] = staff.index
            if abs(glyph.y - staff.center) > staff.gap * 9:
                reason = "too_far_from_staff"
            elif len(candidates) > 1 and abs(
                abs(glyph.y - candidates[0].center) / candidates[0].gap -
                abs(glyph.y - candidates[1].center) / candidates[1].gap
            ) < .35:
                reason = "ambiguous_staff"
            active = [clef for clef in staff.clefs if clef.x <= glyph.x + .5]
            if not reason and not active:
                reason = "no_clef"
            if not reason:
                clef = active[-1]
                row["clef"] = clef.kind
                # Each clef origin is the position of its named reference note.
                bottom_step = (clef.y - staff.lines[-1]) / (staff.gap / 2)
                position = (staff.lines[-1] - glyph.y) / (staff.gap / 2)
                if abs(bottom_step - round(bottom_step)) > .22 or abs(position - round(position)) > .22:
                    reason = "off_staff_grid"
                else:
                    pitch = REFERENCE_PITCH[clef.kind] + round(bottom_step) + round(position)
                    note = LETTERS[pitch % 7]
                    row.update(note=note, solfege=SOLFEGE[note], written_octave=pitch // 7,
                               color=colors[note], status="colored")
                    selected[(glyph.operation, glyph.ordinal)] = colors[note]
        if reason:
            row["status"] = reason
        rows.append(row)
    return rows, selected


def color_operations(stream, fonts, selected):
    """Split only selected text operations, retaining all glyph advances and TJ offsets."""
    rewritten, font_name, stack = [], "", []
    fill = [([FloatObject(0)], b"g")]
    stroke = [([FloatObject(0)], b"G")]
    selected_operations = {index for index, _ in selected}
    for index, (args, op) in enumerate(stream.operations):
        if op == b"q":
            stack.append((font_name, fill[:], stroke[:]))
        elif op == b"Q" and stack:
            font_name, fill, stroke = stack.pop()
        elif op == b"Tf":
            font_name = str(args[0])
        elif op in (b"g", b"rg", b"k", b"cs"):
            fill = [(args, op)]
        elif op in (b"G", b"RG", b"K", b"CS"):
            stroke = [(args, op)]
        elif op in (b"sc", b"scn"):
            fill = [(a, o) for a, o in fill if o == b"cs"] + [(args, op)]
        elif op in (b"SC", b"SCN"):
            stroke = [(a, o) for a, o in stroke if o == b"CS"] + [(args, op)]
        if index not in selected_operations:
            rewritten.append((args, op))
            continue
        if op == b'"':
            rewritten.extend([([args[0]], b"Tw"), ([args[1]], b"Tc")])
        if op in (b"'", b'"'):
            rewritten.append(([], b"T*"))
        items = args[0] if op == b"TJ" else [args[-1]]
        unit, ordinal = fonts[font_name].unit, 0
        for item in items:
            if not isinstance(item, (str, bytes)):
                rewritten.append(([ArrayObject([item])], b"TJ"))
                continue
            raw = raw_bytes(item)
            for offset in range(0, len(raw), unit):
                color = selected.get((index, ordinal))
                if color:
                    rgb = [FloatObject(int(color[j:j + 2], 16) / 255) for j in (1, 3, 5)]
                    # q/Q inside a text object can break rendering. Restore the
                    # original colors explicitly without changing text state.
                    rewritten.extend([(rgb, b"rg"), (rgb, b"RG")])
                rewritten.append(([ByteStringObject(raw[offset:offset + unit])], b"Tj"))
                if color:
                    rewritten.extend(fill + stroke)
                ordinal += 1
    stream.operations = rewritten


MAX_UPLOAD_MB = 20
MAX_PAGES = 50
REPORT_FIELDS = [
    "page", "staff", "x_pt", "y_pt", "note", "solfege", "written_octave",
    "clef", "kind", "color", "status", "font",
]


class ConversionError(ValueError):
    """An input problem that can be safely explained to the user."""

    def __init__(self, code, **values):
        self.code = code
        self.values = values
        super().__init__(self.message("ja"))

    def message(self, language):
        return translate(language, self.code, **self.values)


@dataclass(frozen=True)
class RecognitionIssue:
    code: str
    page: int

    def message(self, language):
        return translate(language, "page_issue", page=self.page,
                         issue=translate(language, self.code))


@dataclass
class ConversionResult:
    pdf_bytes: Optional[bytes]
    csv_bytes: bytes
    page_count: int
    colored: int
    skipped: int
    issues: List[RecognitionIssue]

    @property
    def needs_review(self):
        return bool(self.skipped or self.issues)


def validate_colors(supplied: Optional[Mapping[str, str]] = None):
    colors = DEFAULT_COLORS.copy()
    if supplied is not None:
        if not isinstance(supplied, Mapping) or set(supplied) - set(LETTERS):
            raise ConversionError("invalid_color_keys")
        colors.update(supplied)
    if any(not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value)
           for value in colors.values()):
        raise ConversionError("invalid_color")
    return colors


def _report_bytes(rows):
    handle = StringIO(newline="")
    table = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
    table.writeheader()
    # Font names originate in the uploaded PDF. Avoid spreadsheet formulas.
    for row in rows:
        table.writerow({key: "'" + value if isinstance(value, str) and
                        value.startswith(("=", "+", "-", "@", "\t", "\r", "\n"))
                        else value for key, value in row.items()})
    return handle.getvalue().encode("utf-8-sig")


def convert_pdf(
    data: bytes,
    colors: Optional[Mapping[str, str]] = None,
    allow_partial: bool = False,
    progress: Optional[Callable[[int, int], None]] = None,
) -> ConversionResult:
    """Convert one upload in memory; never read or write local score files.

    Uncertain recognition returns a report but no PDF unless explicitly allowed.
    No PDF is returned when zero notes can be colored, even in partial mode.
    """
    palette = validate_colors(colors)
    if not data:
        raise ConversionError("empty")
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise ConversionError("too_large", mb=MAX_UPLOAD_MB)
    if not data.startswith(b"%PDF-"):
        raise ConversionError("not_pdf")
    try:
        return _convert_pdf(data, palette, allow_partial, progress)
    except ConversionError:
        raise
    except (PyPdfError, ValueError, TypeError, KeyError, IndexError, OSError,
            NotImplementedError, RecursionError, OverflowError) as exc:
        raise ConversionError("unreadable") from exc


def _convert_pdf(data, colors, allow_partial, progress):
    reader = PdfReader(BytesIO(data))
    if reader.is_encrypted:
        raise ConversionError("encrypted")
    page_count = len(reader.pages)
    if not page_count:
        raise ConversionError("no_pages")
    if page_count > MAX_PAGES:
        raise ConversionError("too_many_pages", pages=MAX_PAGES)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    all_rows, issues = [], []
    for page_number, page in enumerate(writer.pages, 1):
        if page.get("/Rotate", 0) % 360:
            raise ConversionError("rotated_page", page=page_number)
        stream, fonts, glyphs, staves, page_issues = scan_page(page)
        rows, selected = classify_notes(glyphs, staves, page_number, colors)
        if not rows:
            page_issues.append("no_noteheads")
        issues.extend(RecognitionIssue(issue, page_number) for issue in page_issues)
        all_rows.extend(rows)
        color_operations(stream, fonts, selected)
        page.replace_contents(stream)
        if progress is not None:
            progress(page_number, page_count)
    colored = sum(row["status"] == "colored" for row in all_rows)
    skipped = len(all_rows) - colored
    pdf_bytes = None
    if colored and (allow_partial or not (issues or skipped)):
        output = BytesIO()
        writer.write(output)
        pdf_bytes = output.getvalue()
    return ConversionResult(
        pdf_bytes, _report_bytes(all_rows), page_count, colored, skipped, issues,
    )
