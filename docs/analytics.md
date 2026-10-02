# Score Palette analytics

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

## Cross-domain measurement (GA4 administrator setup)

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

## Verification

Run `node --test tests/analytics.test.cjs` for production-host, rerun, reload,
and incoming-link URL preservation checks, in addition to the Python app tests.
These checks do not contact Google and do not verify live GA4 delivery.

The Community Cloud outer page is `/`, while the app runs in an iframe at
`/~/+/`. `st.html` runs in the app document without creating another iframe.
Live inspection on 2026-10-02 confirmed that `page_view` is sent for `/~/+/`;
this implementation does not normalize it to `/`. Cross-domain continuity has
not yet been verified: check that `_gl` reaches the app document as well as the
outer page before assuming that users and sessions remain connected.

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
