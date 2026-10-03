"""Standalone Streamlit entrypoint: streamlit run app.py."""

from pathlib import Path, PurePosixPath
from uuid import uuid4

import streamlit as st

from messages import SOLFEGE_EN, translate
from palette import MAX_PALETTE_BYTES, parse_palette, serialize_palette
from palette_storage import browser_palette
from score_coloring import (
    DEFAULT_COLORS, LETTERS, MAX_PAGES, MAX_UPLOAD_MB, SOLFEGE,
    ConversionError, convert_pdf,
)


def discard_result():
    st.session_state.pop("result", None)
    st.session_state.pop("output_stem", None)
    st.session_state.pop("conversion_error", None)


def reset_palette():
    palette_changed()
    for note, color in DEFAULT_COLORS.items():
        st.session_state[f"color_{note}"] = color


def palette_changed():
    discard_result()
    # A deliberate edit takes precedence over a late browser restore.
    st.session_state["palette_ready"] = True
    st.session_state.pop("palette_notice", None)


def apply_palette(colors):
    palette_changed()
    for note, color in colors.items():
        st.session_state[f"color_{note}"] = color


def restore_browser_palette():
    if st.session_state.get("palette_ready"):
        return
    loaded = st.session_state.get("palette_storage", {}).get("loaded")
    if not isinstance(loaded, dict):
        return
    st.session_state["palette_ready"] = True
    raw = loaded.get("raw")
    if raw is not None:
        try:
            apply_palette(parse_palette(raw))
        except ValueError:
            st.session_state["palette_notice"] = "palette_stored_invalid"


def import_palette():
    uploaded = st.session_state.get("palette_upload")
    st.session_state.pop("palette_notice", None)
    if uploaded is None:
        return
    try:
        # Bound the read as well as validating the decoded settings.
        uploaded.seek(0)
        colors = parse_palette(uploaded.read(MAX_PALETTE_BYTES + 1))
    except ValueError:
        st.session_state["palette_notice"] = "palette_invalid"
        return
    apply_palette(colors)
    st.session_state["palette_notice"] = "palette_imported"


def clear_upload():
    discard_result()
    st.session_state["upload_generation"] = st.session_state.get("upload_generation", 0) + 1


def download_stem(filename):
    # A browser-supplied filename is only used as a download label, never a path.
    name = PurePosixPath(filename.replace("\\", "/")).stem
    return "".join(char for char in name if char.isprintable())[:120] or "score"


def toggle_language():
    st.session_state["language"] = (
        "日本語" if st.session_state.get("language") == "English" else "English"
    )


def main():
    st.session_state["language"] = st.session_state.get("language", "日本語")
    selected_language = st.session_state["language"]
    language = "en" if selected_language == "English" else "ja"

    def t(key, **values):
        return translate(language, key, **values)

    st.set_page_config(
        page_title=t("title"),
        page_icon=Path(__file__).with_name("favicon.png"),
        layout="centered",
    )
    # Trusted, static HTML only; browser state prevents duplicate tracking on reruns.
    st.html(Path(__file__).with_name("analytics.html"), unsafe_allow_javascript=True)
    # Streamlit scrolls its main panel rather than the document body.
    # Reserve scrollbar space even while the rules expander is closed.
    st.html("""
        <style>
            [data-testid="stMain"] {
                scrollbar-gutter: stable;
            }
            @supports not (scrollbar-gutter: stable) {
                [data-testid="stMain"] {
                    overflow-y: scroll;
                }
            }
        </style>
    """)
    with st.container(horizontal=True, horizontal_alignment="right"):
        st.button(
            "日本語" if language == "en" else "English",
            key="language_switch", type="tertiary", on_click=toggle_language,
        )
    st.title(t("title"))
    st.write(t("subtitle"))
    with st.expander(t("rules")):
        st.info(t("supported"))
        st.markdown(t("rules_body"))
        st.caption(t("privacy", mb=MAX_UPLOAD_MB, pages=MAX_PAGES))

    st.subheader(t("upload_step"))
    generation = st.session_state.get("upload_generation", 0)
    uploaded = st.file_uploader(
        t("upload"), type=["pdf"], accept_multiple_files=False,
        max_upload_size=MAX_UPLOAD_MB, key=f"upload_{generation}", on_change=discard_result,
        help=t("upload_help", mb=MAX_UPLOAD_MB, pages=MAX_PAGES),
    )
    st.subheader(t("color_step"))
    if "palette_session" not in st.session_state:
        st.session_state["palette_session"] = uuid4().hex
    colors = {}
    for column, note in zip(st.columns(7), LETTERS):
        color_key = f"color_{note}"
        if color_key not in st.session_state:
            st.session_state[color_key] = DEFAULT_COLORS[note]
        with column:
            colors[note] = st.color_picker(
                f"{(SOLFEGE_EN if language == 'en' else SOLFEGE)[note]} ({note})",
                key=color_key, on_change=palette_changed,
            )
    browser_palette(
        key="palette_storage",
        data={
            "session": st.session_state["palette_session"],
            "ready": st.session_state.get("palette_ready", False),
            "palette": serialize_palette(colors),
            "messages": {key: t(f"palette_{key}") for key in ("loading", "saved", "unavailable")},
        },
        on_loaded_change=restore_browser_palette,
    )
    st.button(t("reset"), key="reset", on_click=reset_palette)
    with st.expander(t("palette_files")):
        st.caption(t("palette_help"))
        st.download_button(
            t("palette_download"), serialize_palette(colors),
            file_name="score-palette.json", mime="application/json",
            key="palette_download", on_click="ignore",
        )
        st.file_uploader(
            t("palette_upload"), type=["json"], key="palette_upload",
            max_upload_size=1, on_change=import_palette,
            help=t("palette_upload_help"),
        )
    notice = st.session_state.get("palette_notice")
    if notice:
        (st.success if notice == "palette_imported" else st.warning)(t(notice))
    allow_partial = st.checkbox(
        t("partial"), key="allow_partial",
        on_change=discard_result,
        help=t("partial_help"),
    )
    if allow_partial:
        st.caption(t("partial_hint"))

    if st.button(t("convert"), key="convert", type="primary", disabled=uploaded is None):
        discard_result()
        progress_bar = st.progress(0, text=t("loading"))
        try:
            result = convert_pdf(
                uploaded.getvalue(), colors, allow_partial,
                progress=lambda done, total: progress_bar.progress(
                    done / total, text=t("progress", done=done, total=total),
                ),
            )
            st.session_state["result"] = result
            st.session_state["output_stem"] = download_stem(uploaded.name)
        except ConversionError as exc:
            st.session_state["conversion_error"] = exc
        except Exception:
            # Do not show PDF contents or server tracebacks to public users.
            st.session_state["conversion_error"] = ConversionError("unexpected")
        finally:
            progress_bar.empty()

    error = st.session_state.get("conversion_error")
    if error is not None:
        st.error(error.message(language))

    result = st.session_state.get("result")
    if uploaded is not None and result is not None:
        st.subheader(t("result_step"))
        if not result.colored:
            st.error(t("no_notes"))
        elif result.pdf_bytes is None:
            st.warning(t("blocked"))
        elif result.needs_review:
            st.warning(t("partial_done"))
        else:
            st.success(t("done"))
        columns = st.columns(3)
        columns[0].metric(t("pages"), result.page_count)
        columns[1].metric(t("colored" if result.pdf_bytes else "colorable"), result.colored)
        columns[2].metric(t("skipped"), result.skipped)
        st.caption(t("counts_hint"))
        if result.issues:
            with st.expander(t("issues", count=len(result.issues)), expanded=True):
                for issue in result.issues:
                    st.text(issue.message(language))
        stem = st.session_state["output_stem"]
        if result.pdf_bytes is not None:
            suffix = "_partial_colored.pdf" if result.needs_review else "_colored.pdf"
            st.download_button(
                t("download_pdf"), result.pdf_bytes, key="download_pdf", file_name=stem + suffix,
                mime="application/pdf", type="primary", on_click="ignore",
            )
        st.download_button(
            t("download_csv"), result.csv_bytes, key="download_csv",
            file_name=stem + "_notes.csv", mime="text/csv", on_click="ignore",
        )
    if uploaded is not None:
        st.button(t("clear"), key="clear", on_click=clear_upload)

    st.divider()
    st.caption("[Daichi Sasaki](https://d1ssk.github.io/)")


if __name__ == "__main__":
    main()
