"""Standalone Streamlit entrypoint: streamlit run app.py."""

from pathlib import PurePosixPath

import streamlit as st

from messages import SOLFEGE_EN, translate
from score_coloring import (
    DEFAULT_COLORS, LETTERS, MAX_PAGES, MAX_UPLOAD_MB, SOLFEGE,
    ConversionError, convert_pdf,
)


def discard_result():
    st.session_state.pop("result", None)
    st.session_state.pop("output_stem", None)
    st.session_state.pop("conversion_error", None)


def reset_palette():
    discard_result()
    for note, color in DEFAULT_COLORS.items():
        st.session_state[f"color_{note}"] = color


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

    st.set_page_config(page_title=t("title"), page_icon="🎼", layout="centered")
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
    colors = {}
    for column, note in zip(st.columns(7), LETTERS):
        color_key = f"color_{note}"
        if color_key not in st.session_state:
            st.session_state[color_key] = DEFAULT_COLORS[note]
        with column:
            colors[note] = st.color_picker(
                f"{(SOLFEGE_EN if language == 'en' else SOLFEGE)[note]} ({note})",
                key=color_key, on_change=discard_result,
            )
    st.button(t("reset"), key="reset", on_click=reset_palette)
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
