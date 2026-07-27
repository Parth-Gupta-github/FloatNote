# FloatNote 1.0.0 🎙️

> Be present in the meeting — FloatNote remembers it for you.

FloatNote is a Windows desktop app that captures a meeting as it happens — every
word, who said it, and what's on screen — and turns it into a clean transcript,
an on-demand summary, and a chatbot you can actually ask about it. It's built
**local-first**: the recording, transcription, speaker separation, and screen
reading all run on your own machine, and only the final summary/chat step reaches
a language model.

---

## ⭐ At a glance

| Capability | Powered by | Runs |
|---|---|---|
| Live transcription (mic + system audio) | OpenAI Whisper | 🖥️ On your PC |
| Speech / silence gating | Silero VAD | 🖥️ On your PC |
| Speaker separation & labels | Resemblyzer voice embeddings | 🖥️ On your PC |
| Screen Reader (OCR) | OpenCV + Tesseract *(bundled)* | 🖥️ On your PC |
| Keywords & action items | spaCy | 🖥️ On your PC |
| Summaries · chat · keyword cleanup | Qwen2.5-7B-Instruct | ☁️ HuggingFace |
| Meeting history | SQLite | 🖥️ On your PC |

---

## 🧩 A closer look at the features

### 🎤 Two-way live transcription
Captures **your microphone and the meeting's system audio at the same time**, so
your side and the remote participants both land in a single transcript. You can
**mute either stream independently** mid-meeting without stopping the recording.

### 🗣️ Automatic speaker separation
Tells voices apart **as the meeting runs** — no need to process the whole
recording afterward — and tags each line (`Speaker 1`, `Speaker 2`, …). You can
rename a speaker to a real name and it sticks for that meeting.

### 🖥️ Screen Reader (OCR)
Watches your screen and, **only when the content actually changes**, reads the
text off it — slides, shared docs, whiteboards — and adds it to the meeting as
its own stream, separate from the spoken transcript. **Tesseract is bundled**, so
there's nothing extra to install.

### ✅ Keywords & action items
A lightweight language pipeline picks out the **key topics** and detects
**tasks and who they're for** in real time, so follow-ups don't slip through.

### 🧠 Summaries & chat — one model, zero fuss
A single language model (**Qwen2.5-7B** via HuggingFace) powers the on-demand
**summary**, the **chatbot**, and keyword cleanup — so there's just one setup and
one place your data goes. The chatbot answers **only from the saved meeting**, so
it stays grounded instead of guessing.

### 💾 Everything saved locally
Meetings, transcripts (tagged by mic / speaker / screen), speaker names, and
action items are stored in a local database you own — ready to summarize or
revisit any time.

---

## 🚀 Install & first run

1. **Download** `FloatNote Setup 1.0.0.exe` from the Assets below and run it.
2. **SmartScreen?** If Windows warns "unknown publisher," it's just because the
   build isn't code-signed yet — click **More info → Run anyway**.
3. **First launch** downloads the speech models once (~250 MB) — give it a minute.
4. **Add a token** when prompted: a free HuggingFace token powers the summary and
   chat. Create one at
   [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) with
   the **"Make calls to Inference Providers"** permission. It's stored only on
   your device.

---

## 🎬 Using it, step by step

1. Optionally name the session, then hit **▶ Start Meeting**.
2. The **transcript** streams in with speaker labels; **keywords** and **action
   items** appear live. Have a slide up? The **Screen Reader** grabs its text too.
3. **Mute** the mic or system audio whenever you need to go off the record.
4. Hit **⏹ Stop** to end the session.
5. Press **Generate Summary** for the recap, then **chat** with the meeting to
   pull out specifics.
6. Your next meeting starts on a clean slate.

---

## 🏗️ How it's built

FloatNote ships as **one installer that carries both the interface and the whole
AI engine** — no Python, no manual setup on the user's side.

- **Desktop shell** — Electron. On launch it starts the local engine, waits for
  it, then loads the interface; on exit it shuts the engine down.
- **Interface** — React + Vite + Tailwind CSS.
- **Engine** — a FastAPI (Python) service frozen into a standalone `.exe` with
  PyInstaller, streaming to the UI over a WebSocket.
- **On-device AI** — Whisper (transcription), Silero (voice detection),
  Resemblyzer (speaker matching), OpenCV + Tesseract (screen OCR), and spaCy
  (action items) all run offline.
- **Cloud AI** — only summaries and chat call out, to the **Qwen2.5-7B** model on
  HuggingFace.
- **Storage** — a local SQLite database via async SQLAlchemy.

```
 speak / share screen
        │
        ▼
 ┌──────────────── local engine (on your PC) ────────────────┐
 │  Whisper + Silero + Resemblyzer   →  transcript + speakers │
 │  OpenCV + Tesseract               →  on-screen text        │
 │  spaCy                            →  keywords + action items│
 └───────────────┬───────────────────────────┬───────────────┘
                 ▼                           ▼
          live to the app             saved to SQLite
                 │
                 ▼
   "summarize" / "ask a question"  →  Qwen2.5-7B (HuggingFace)  →  answer
```

---

## ✅ Requirements

- Windows 10 or 11, 64-bit
- ~2.5 GB free disk space (the app bundles its full AI runtime)
- Internet — for the one-time model download and for summaries/chat
- A microphone for your own voice (remote audio is captured automatically)

## 🔒 Privacy

- **Nothing is captured until you press Start.**
- Audio, speaker analysis, screen text, and meeting history all stay **on your
  device**. Only the text needed for a summary or chat reply is sent to the
  model, and your token never leaves your machine otherwise.
- The FloatNote window is **excluded from screen capture**, so the Screen Reader
  never reads its own interface and the app won't appear in recordings.

## ⚠️ Known limitations

- **Windows only** for now (system-audio capture is Windows-specific).
- **Not code-signed yet** — expect the one-time SmartScreen prompt.
- Summaries and chat need an internet connection and a HuggingFace token.
