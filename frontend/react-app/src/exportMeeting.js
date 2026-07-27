// Build and download a meeting as Markdown or plain text — fully client-side,
// from the data the dashboard already has (no backend call needed).

function speakerLabel(source, speakerNames) {
  if (!source || source === "MIC") return "You";
  if (speakerNames && speakerNames[source]) return speakerNames[source];
  const m = /^SPEAKER_(\d+)$/.exec(source);
  if (m) return "Speaker " + (parseInt(m[1], 10) + 1);
  return source;
}

export function buildMarkdown({ title, transcript, keywords, actions, summary, speakerNames }) {
  const out = [];
  out.push(`# ${title || "FloatNote Meeting"}`, "");
  if (summary) out.push("## Summary", "", summary, "");
  if (actions && actions.length) {
    out.push("## Action items", "");
    actions.forEach((a) => out.push(`- ${a}`));
    out.push("");
  }
  if (keywords && keywords.length) {
    out.push("## Keywords", "", keywords.join(", "), "");
  }
  out.push("## Transcript", "");
  (transcript || []).forEach((t) =>
    out.push(`**${speakerLabel(t.source, speakerNames)}:** ${t.text}`)
  );
  return out.join("\n");
}

export function buildText({ title, transcript, keywords, actions, summary, speakerNames }) {
  const out = [];
  out.push(title || "FloatNote Meeting", "=".repeat((title || "FloatNote Meeting").length), "");
  if (summary) out.push("SUMMARY", summary, "");
  if (actions && actions.length) {
    out.push("ACTION ITEMS");
    actions.forEach((a) => out.push("  - " + a));
    out.push("");
  }
  if (keywords && keywords.length) out.push("KEYWORDS", "  " + keywords.join(", "), "");
  out.push("TRANSCRIPT", "");
  (transcript || []).forEach((t) =>
    out.push(`${speakerLabel(t.source, speakerNames)}: ${t.text}`)
  );
  return out.join("\n");
}

function download(filename, content, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

export function exportMeeting(format, data) {
  const base =
    (data.title || "floatnote-meeting")
      .replace(/[^a-z0-9]+/gi, "-")
      .replace(/^-+|-+$/g, "")
      .toLowerCase() || "floatnote-meeting";
  if (format === "md") {
    download(`${base}.md`, buildMarkdown(data), "text/markdown;charset=utf-8");
  } else {
    download(`${base}.txt`, buildText(data), "text/plain;charset=utf-8");
  }
}
