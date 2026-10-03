"""Small browser-storage bridge using Streamlit's built-in component API."""

from pathlib import Path

import streamlit.components.v2 as components

browser_palette = components.component(
    "palette_storage",
    html='<div role="status" aria-live="polite"></div>',
    css='div { font-size: 0.875rem; color: var(--st-text-color); opacity: .75; }',
    js=Path(__file__).with_suffix(".js").read_text(encoding="utf-8"),
)
