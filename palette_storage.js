// Runs in the app page through Streamlit components v2; no third-party service.
export default function ({ data, parentElement, setStateValue }) {
    const status = parentElement.querySelector("[role=status]");
    const storageKey = "score-palette.colors.v1";
    const operation = JSON.stringify([data.session, data.ready, data.palette]);
    if (parentElement.paletteOperation !== operation) {
        parentElement.paletteOperation = operation;
        if (!data.ready) {
            parentElement.paletteStatus = "loading";
            let raw = null;
            let available = true;
            try {
                raw = window.localStorage.getItem(storageKey);
                // Never send an unexpectedly large stored value to the server.
                if (raw && raw.length > 4096) raw = "invalid";
            } catch (_) {
                available = false;
            }
            setStateValue("loaded", { raw, available });
        } else {
            try {
                window.localStorage.setItem(storageKey, data.palette);
                parentElement.paletteStatus = "saved";
            } catch (_) {
                parentElement.paletteStatus = "unavailable";
            }
        }
    }
    status.textContent = data.messages[parentElement.paletteStatus || "loading"];
}
