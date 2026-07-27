import { useEffect, useState } from "react";
import { exportMeeting } from "./exportMeeting";

// Browse past meetings (from the local database) and reopen one to read its
// transcript and summary, or export it.
export default function HistoryPanel({ open, onClose, apiBase }) {
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null); // full meeting data
  const [loadingOne, setLoadingOne] = useState(false);

  useEffect(() => {
    if (!open) return;
    setSelected(null);
    setError("");
    setLoading(true);
    fetch(`${apiBase}/meetings`)
      .then((r) => r.json())
      .then((d) => setMeetings(d.meetings || []))
      .catch(() => setError("Couldn't load meetings."))
      .finally(() => setLoading(false));
  }, [open, apiBase]);

  if (!open) return null;

  async function openMeeting(id) {
    setLoadingOne(true);
    setError("");
    try {
      const res = await fetch(`${apiBase}/meetings/${id}/full`);
      if (!res.ok) throw new Error();
      setSelected(await res.json());
    } catch {
      setError("Couldn't open that meeting.");
    } finally {
      setLoadingOne(false);
    }
  }

  function fmtDate(iso) {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  }

  const detailTranscript = selected
    ? (selected.items || []).map((it) => ({ text: it.text, source: it.speaker || (it.source === "ocr" ? "OCR" : "MIC") }))
    : [];

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.card} onClick={(e) => e.stopPropagation()}>
        <div style={styles.header}>
          <span style={styles.title}>🕘 Meeting history</span>
          <button style={styles.close} onClick={onClose}>×</button>
        </div>

        {error ? <div style={styles.error}>{error}</div> : null}

        {!selected ? (
          <div style={styles.list}>
            {loading ? (
              <div style={styles.muted}>Loading…</div>
            ) : meetings.length === 0 ? (
              <div style={styles.muted}>No saved meetings yet.</div>
            ) : (
              meetings.map((m) => (
                <button key={m.id} style={styles.item} onClick={() => openMeeting(m.id)}>
                  <div style={styles.itemTitle}>{m.title}</div>
                  <div style={styles.itemMeta}>
                    {fmtDate(m.start_time)} {m.has_summary ? "· 📝 summary" : ""}
                  </div>
                </button>
              ))
            )}
          </div>
        ) : (
          <div style={styles.detail}>
            <button style={styles.back} onClick={() => setSelected(null)}>← All meetings</button>
            <div style={styles.detailTitle}>{selected.title || "Meeting"}</div>
            <div style={styles.detailActions}>
              <button style={styles.smallBtn} onClick={() => exportMeeting("md", { title: selected.title, transcript: detailTranscript, summary: selected.summary })}>⬇ Markdown</button>
              <button style={styles.smallBtn} onClick={() => exportMeeting("txt", { title: selected.title, transcript: detailTranscript, summary: selected.summary })}>⬇ Text</button>
            </div>
            {loadingOne ? (
              <div style={styles.muted}>Loading…</div>
            ) : (
              <>
                {selected.summary ? (
                  <div style={styles.block}>
                    <div style={styles.blockLabel}>Summary</div>
                    <div style={styles.summaryText}>{selected.summary}</div>
                  </div>
                ) : null}
                <div style={styles.block}>
                  <div style={styles.blockLabel}>Transcript</div>
                  {detailTranscript.length === 0 ? (
                    <div style={styles.muted}>No transcript saved.</div>
                  ) : (
                    detailTranscript.map((t, i) => (
                      <div key={i} style={styles.line}>
                        <span style={styles.who}>{t.source === "MIC" ? "You" : t.source}:</span> {t.text}
                      </div>
                    ))
                  )}
                </div>
              </>
            )}
          </div>
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
    width: 620, maxWidth: "92vw", maxHeight: "85vh", overflow: "hidden",
    background: "#fff", borderRadius: 16, padding: 24,
    boxShadow: "0 20px 60px rgba(0,0,0,0.25)", display: "flex", flexDirection: "column",
    fontFamily: "Segoe UI, system-ui, sans-serif", color: "#0f172a",
  },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  title: { fontSize: 20, fontWeight: 700 },
  close: { border: "none", background: "none", fontSize: 26, cursor: "pointer", color: "#64748b", lineHeight: 1 },
  list: { overflowY: "auto", display: "flex", flexDirection: "column", gap: 8 },
  item: {
    textAlign: "left", padding: "12px 14px", borderRadius: 10, border: "1px solid #e2e8f0",
    background: "#f8fafc", cursor: "pointer",
  },
  itemTitle: { fontWeight: 600, fontSize: 15 },
  itemMeta: { color: "#64748b", fontSize: 12, marginTop: 3 },
  detail: { overflowY: "auto" },
  back: { border: "none", background: "none", color: "#2563eb", cursor: "pointer", fontSize: 14, padding: 0, marginBottom: 8 },
  detailTitle: { fontSize: 18, fontWeight: 700, marginBottom: 8 },
  detailActions: { display: "flex", gap: 8, marginBottom: 14 },
  smallBtn: { padding: "6px 12px", borderRadius: 8, border: "1px solid #cbd5e1", background: "#fff", cursor: "pointer", fontSize: 13 },
  block: { marginBottom: 16 },
  blockLabel: { fontWeight: 600, fontSize: 13, textTransform: "uppercase", color: "#94a3b8", marginBottom: 6, letterSpacing: 0.5 },
  summaryText: { whiteSpace: "pre-wrap", fontSize: 14, lineHeight: 1.6 },
  line: { fontSize: 14, lineHeight: 1.6, marginBottom: 4 },
  who: { fontWeight: 600, color: "#2563eb" },
  muted: { color: "#64748b", fontSize: 14 },
  error: { color: "#dc2626", fontSize: 13, marginBottom: 8 },
};
