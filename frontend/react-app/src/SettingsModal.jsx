import { useEffect, useState } from "react";

// Settings for the desktop app: manage the HuggingFace token and toggle the
// Screen Reader (OCR). Talks to Electron via the window.floatnote bridge.
export default function SettingsModal({ open, onClose }) {
  const bridge = typeof window !== "undefined" ? window.floatnote : null;
  const [hasToken, setHasToken] = useState(false);
  const [ocrEnabled, setOcrEnabled] = useState(true);
  const [token, setToken] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    if (!open || !bridge) return;
    bridge.getConfig().then((cfg) => {
      setHasToken(Boolean(cfg?.hasToken));
      setOcrEnabled(cfg?.ocrEnabled !== false);
    });
  }, [open, bridge]);

  if (!open) return null;

  async function saveToken() {
    const value = token.trim();
    if (!value.startsWith("hf_")) {
      setStatus('That doesn\'t look like a token (should start with "hf_").');
      return;
    }
    const res = await bridge.saveToken(value);
    setHasToken(Boolean(res?.hasToken));
    setToken("");
    setStatus("Token saved.");
  }

  async function toggleOcr() {
    const next = !ocrEnabled;
    setOcrEnabled(next);
    await bridge.setOcrEnabled(next);
    setStatus("Screen Reader " + (next ? "enabled" : "disabled") + " — restart FloatNote to apply.");
  }

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.card} onClick={(e) => e.stopPropagation()}>
        <div style={styles.header}>
          <span style={styles.title}>⚙️ Settings</span>
          <button style={styles.close} onClick={onClose}>×</button>
        </div>

        {!bridge ? (
          <p style={styles.muted}>
            Settings are available in the installed desktop app.
          </p>
        ) : (
          <>
            <div style={styles.section}>
              <div style={styles.label}>HuggingFace token</div>
              <div style={styles.muted}>
                {hasToken ? "✅ A token is configured." : "⚠️ No token set — summaries and chat won't work."}
              </div>
              <input
                style={styles.input}
                type="password"
                placeholder="Paste a new token (hf_...)"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
              <button style={styles.btn} onClick={saveToken}>Save token</button>
            </div>

            <div style={styles.section}>
              <div style={styles.rowBetween}>
                <div>
                  <div style={styles.label}>Screen Reader (OCR)</div>
                  <div style={styles.muted}>Reads on-screen text (slides, docs) into the meeting.</div>
                </div>
                <button
                  style={{ ...styles.toggle, background: ocrEnabled ? "#22c55e" : "#cbd5e1" }}
                  onClick={toggleOcr}
                  aria-label="toggle screen reader"
                >
                  <span style={{ ...styles.knob, left: ocrEnabled ? 22 : 2 }} />
                </button>
              </div>
            </div>

            {status ? <div style={styles.statusMsg}>{status}</div> : null}
          </>
        )}
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: "fixed", inset: 0, background: "rgba(15,23,42,0.45)",
    display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
  },
  card: {
    width: 420, maxWidth: "90vw", background: "#fff", borderRadius: 16,
    padding: 24, boxShadow: "0 20px 60px rgba(0,0,0,0.25)",
    fontFamily: "Segoe UI, system-ui, sans-serif", color: "#0f172a",
  },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  title: { fontSize: 20, fontWeight: 700 },
  close: { border: "none", background: "none", fontSize: 26, cursor: "pointer", color: "#64748b", lineHeight: 1 },
  section: { padding: "16px 0", borderTop: "1px solid #e2e8f0" },
  label: { fontWeight: 600, fontSize: 15 },
  muted: { color: "#64748b", fontSize: 13, marginTop: 4, lineHeight: 1.5 },
  input: {
    width: "100%", marginTop: 10, padding: "10px 12px", borderRadius: 8,
    border: "1px solid #cbd5e1", fontSize: 14, boxSizing: "border-box",
  },
  btn: {
    marginTop: 10, padding: "9px 16px", borderRadius: 8, border: "none",
    background: "#2563eb", color: "#fff", fontWeight: 600, cursor: "pointer",
  },
  rowBetween: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 },
  toggle: {
    position: "relative", width: 44, height: 24, borderRadius: 999,
    border: "none", cursor: "pointer", flexShrink: 0, transition: "background 0.15s",
  },
  knob: {
    position: "absolute", top: 2, width: 20, height: 20, borderRadius: "50%",
    background: "#fff", transition: "left 0.15s",
  },
  statusMsg: { marginTop: 12, fontSize: 13, color: "#2563eb" },
};
