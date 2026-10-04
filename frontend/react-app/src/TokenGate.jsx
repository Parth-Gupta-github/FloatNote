import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// First-run gate: requires a HuggingFace token before the app is usable.
// Works in BOTH dev (no Electron bridge) and production (Electron desktop)
// by talking directly to the backend API.
export default function TokenGate({ children }) {
  const [status, setStatus] = useState("loading"); // loading | need-token | ready
  const [token, setToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // Ask the backend whether a token is already configured.
    fetch(`${API_BASE}/settings/token/status`)
      .then((r) => r.json())
      .then((data) => setStatus(data && data.hasToken ? "ready" : "need-token"))
      .catch(() => {
        // Backend not reachable yet — fall back to Electron bridge if available.
        const bridge = window.floatnote;
        if (bridge && bridge.isDesktop) {
          bridge
            .getConfig()
            .then((cfg) =>
              setStatus(cfg && cfg.hasToken ? "ready" : "need-token")
            )
            .catch(() => setStatus("need-token"));
        } else {
          setStatus("need-token");
        }
      });
  }, []);

  async function handleSave(e) {
    e.preventDefault();
    const value = token.trim();
    if (!value.startsWith("hf_")) {
      setError(
        'That doesn\'t look like a HuggingFace token (it should start with "hf_").'
      );
      return;
    }
    setSaving(true);
    setError("");
    try {
      // 1. Save to backend (hot-updates in-memory — works immediately).
      const res = await fetch(`${API_BASE}/settings/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: value }),
      });
      if (!res.ok) {
        throw new Error(`Backend returned ${res.status}`);
      }

      // 2. Also save via Electron bridge for persistence across installs.
      const bridge = window.floatnote;
      if (bridge && bridge.saveToken) {
        await bridge.saveToken(value);
      }

      setStatus("ready");
    } catch (err) {
      console.error("Token save failed:", err);
      // If the backend is down, try Electron-only as a last resort.
      const bridge = window.floatnote;
      if (bridge && bridge.saveToken) {
        try {
          const cfg = await bridge.saveToken(value);
          if (cfg && cfg.hasToken) {
            setStatus("ready");
            return;
          }
        } catch { /* fall through */ }
      }
      setError(
        "Could not save the token. Make sure the backend is running and try again."
      );
    } finally {
      setSaving(false);
    }
  }

  if (status === "loading") {
    return (
      <div style={styles.screen}>
        <div style={styles.muted}>Loading…</div>
      </div>
    );
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
          <div style={styles.hint}>
            ⚠️ Make sure the token has the{" "}
            <strong>"Make calls to Inference Providers"</strong> permission
            enabled.
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
  hint: {
    color: "#fbbf24",
    fontSize: 13,
    lineHeight: 1.5,
    background: "rgba(251,191,36,0.1)",
    padding: "8px 10px",
    borderRadius: 8,
    border: "1px solid rgba(251,191,36,0.25)",
  },
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
  link: {
    color: "#38bdf8",
    fontSize: 13,
    textDecoration: "none",
    textAlign: "center",
  },
  error: { color: "#f87171", fontSize: 13 },
};
