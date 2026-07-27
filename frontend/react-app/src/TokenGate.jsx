import { useEffect, useState } from "react";

// Gates the app behind a one-time HuggingFace token setup in the packaged
// desktop app. In the browser / dev (no window.floatnote bridge) it renders the
// app directly, since the dev backend reads the token from backend/.env.
export default function TokenGate({ children }) {
  const [status, setStatus] = useState("loading"); // loading | need-token | ready
  const [token, setToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const bridge = window.floatnote;
    if (!bridge || !bridge.isDesktop) {
      setStatus("ready"); // dev / browser: token comes from backend/.env
      return;
    }
    bridge
      .getConfig()
      .then((cfg) => setStatus(cfg && cfg.hasToken ? "ready" : "need-token"))
      .catch(() => setStatus("need-token"));
  }, []);

  async function handleSave(e) {
    e.preventDefault();
    const value = token.trim();
    if (!value.startsWith("hf_")) {
      setError('That doesn\'t look like a HuggingFace token (it should start with "hf_").');
      return;
    }
    setSaving(true);
    setError("");
    try {
      const cfg = await window.floatnote.saveToken(value);
      if (cfg && cfg.hasToken) {
        setStatus("ready");
      } else {
        setError("Could not save the token. Please try again.");
      }
    } catch {
      setError("Could not save the token. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  if (status === "loading") {
    return <div style={styles.screen}><div style={styles.muted}>Loading…</div></div>;
  }

  if (status === "need-token") {
    return (
      <div style={styles.screen}>
        <form style={styles.card} onSubmit={handleSave}>
          <div style={styles.title}>Welcome to FloatNote 🎙️</div>
          <div style={styles.muted}>
            FloatNote uses a HuggingFace model for summaries and chat. Paste a
            free access token to get started — it stays on this device.
          </div>
          <input
            style={styles.input}
            type="password"
            placeholder="hf_..."
            value={token}
            onChange={(e) => setToken(e.target.value)}
            autoFocus
          />
          {error ? <div style={styles.error}>{error}</div> : null}
          <button style={styles.button} type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save & Continue"}
          </button>
          <a
            style={styles.link}
            href="https://huggingface.co/settings/tokens"
            target="_blank"
            rel="noreferrer"
          >
            Get a free token →
          </a>
        </form>
      </div>
    );
  }

  return children;
}

const styles = {
  screen: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#0f172a",
    color: "#e2e8f0",
    fontFamily: "Segoe UI, system-ui, sans-serif",
  },
  card: {
    width: 380,
    padding: 32,
    background: "#1e293b",
    borderRadius: 14,
    display: "flex",
    flexDirection: "column",
    gap: 14,
    boxShadow: "0 10px 40px rgba(0,0,0,0.4)",
  },
  title: { fontSize: 22, fontWeight: 700 },
  muted: { color: "#94a3b8", fontSize: 14, lineHeight: 1.5 },
  input: {
    padding: "11px 12px",
    borderRadius: 8,
    border: "1px solid #334155",
    background: "#0f172a",
    color: "#e2e8f0",
    fontSize: 14,
    outline: "none",
  },
  button: {
    padding: "11px 12px",
    borderRadius: 8,
    border: "none",
    background: "#38bdf8",
    color: "#0f172a",
    fontWeight: 700,
    fontSize: 14,
    cursor: "pointer",
  },
  link: { color: "#38bdf8", fontSize: 13, textDecoration: "none", textAlign: "center" },
  error: { color: "#f87171", fontSize: 13 },
};
