# FloatNote 🎙️

> **Real-time meeting intelligence** — transcription, speaker diarization, screen reading, AI summaries, and a chatbot that knows your meeting.

FloatNote is a desktop-first meeting assistant that quietly runs in the background while you work. It captures your microphone **and** your system audio (remote participants), tells speakers apart in real time, reads your screen during presentations, and turns everything into searchable, queryable meeting memory — powered by local Whisper transcription and HuggingFace LLMs.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎤 **Live Transcription** | Streams mic audio through OpenAI Whisper (`base` model) in real time, gated by Silero VAD so only real speech is transcribed |
| 🔊 **System Audio Capture** | Captures remote participants via WASAPI loopback (`soundcard`) — hear both sides of the meeting, with per-meeting consent |
| 🗣️ **Speaker Diarization** | Streaming, fully-offline speaker identification (Resemblyzer d-vectors) — consistent `SPEAKER_00 / SPEAKER_01` labels across a live meeting |
| ✏️ **Speaker Aliases & Titles** | Rename speakers to real names and edit the meeting title mid-recording, live-synced to all connected clients |
| ⏯️ **Meeting Controls** | Start, pause, resume, stop, and mute (mic/speaker independently) from the dashboard |
| 🖥️ **Screen OCR** | Captures slide content as it changes, extracting text and keywords automatically (opt-in) |
| 🧠 **AI Summarization** | Generates meeting summaries via the project's single LLM (Qwen2.5-7B), with a local fallback |
| 💬 **Meeting Chatbot** | Ask questions about any past meeting — answers grounded in a FAISS vector store via RAG |
| 🗃️ **Persistent Storage** | All transcripts, speaker labels, OCR captures, and action items saved to SQLite via async SQLAlchemy |
| ⚡ **Action Item Extraction** | NLP pipeline (spaCy) detects tasks and assignees from spoken text |
| 🖥️ **Electron Desktop App** | Optional Electron wrapper for a native windowed experience |

---

## 🏗️ Architecture

```
FloatNote/
├── run.ps1                            # Dev runner: launches backend + React + Electron
├── backend/
│   ├── main.py                        # Entry point (starts the server below)
│   ├── requirements.txt
│   ├── ai_modules/
│   │   ├── stt/
│   │   │   └── whisper_engine.py      # FastAPI app + WebSocket server, mic & loopback
│   │   │                              #   capture, Silero VAD, Whisper transcription
│   │   ├── diarization/
│   │   │   └── diarizer.py            # Streaming speaker diarization (Resemblyzer)
│   │   ├── ocr/
│   │   │   ├── ocr_processor.py       # Screen capture + Tesseract OCR
│   │   │   └── keyword_filter.py      # LLM keyword filtering (local fallback)
│   │   ├── summarizer/
│   │   │   └── summarizer.py          # LLM meeting summaries (local fallback)
│   │   ├── chatbot/
│   │   │   └── chatbot.py             # RAG chatbot (FAISS retrieval + LLM)
│   │   └── utils/
│   │       ├── llm_client.py          # THE single LLM client (Qwen2.5-7B via HF)
│   │       └── nlp_processor.py       # spaCy NLP pipeline
│   └── database/
│       ├── models.py                  # SQLAlchemy models (Meeting, Transcript, ActionItem)
│       ├── crud.py                    # Async database operations
│       └── view_db.py                 # Database viewer utility
├── frontend/
│   ├── react-app/                     # Vite + React 19 + Tailwind CSS UI
│   │   └── src/App.jsx                # Dashboard: live transcript, speaker labels,
│   │                                  #   meeting controls, summaries, chat
│   └── electron/
│       └── main.js                    # Electron wrapper (loads localhost:5173)
└── website/
    └── index.html                     # Landing page
```

---

## 🚀 Setup & Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- Windows (for system-audio loopback capture; mic-only works elsewhere)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (only if you enable screen reading)

### 1. Clone the repo

```bash
git clone https://github.com/Parth-Gupta-github/FloatNote.git
cd FloatNote
```

### 2. Install Python dependencies

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

> ⚠️ First run downloads the Whisper `base` model (~150MB), the Silero VAD model, the Resemblyzer voice encoder, and the spaCy `en_core_web_sm` model automatically.

### 3. (Optional) Install Tesseract OCR

Only needed if you set `ENABLE_OCR=true`. On Windows:

```bash
winget install UB-Mannheim.TesseractOCR
```

Then verify the path in `backend/ai_modules/ocr/ocr_processor.py`:
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### 4. Configure environment variables

Create a `.env` file inside `backend/`:

```env
# Required — powers the chatbot, summaries, and keyword filtering (one model for everything)
HUGGINGFACEHUB_API_TOKEN=hf_...
HUGGINGFACE_PROVIDER=auto
```

> 💡 All LLM features run on a **single model** (`Qwen/Qwen2.5-7B-Instruct`) through the HuggingFace router. Create a token with the "Make calls to Inference Providers" permission at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens). Without a token, summaries, chat, and keyword filtering degrade to local fallbacks.

### 5. Run everything (recommended)

```powershell
.\run.ps1               # backend + React + Electron, each in its own window
.\run.ps1 -NoElectron   # backend + React only (open http://localhost:5173)
```

### Or start each part manually

```bash
# Backend — http://localhost:8000
.\.venv\Scripts\Activate.ps1
cd backend
python main.py

# Frontend — http://localhost:5173
cd frontend/react-app
npm install
npm run dev

# (Optional) Electron desktop app
cd frontend/electron
npm install
npm start
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `WS` | `/ws` | Real-time transcript / status / OCR stream |
| `POST` | `/meetings/start` | Start a new meeting (recording begins) |
| `POST` | `/meetings/pause` | Pause recording |
| `POST` | `/meetings/resume` | Resume recording |
| `POST` | `/meetings/stop` | Stop and finalize the meeting |
| `POST` | `/meetings/mute` | Mute/unmute mic and/or system audio |
| `POST` | `/meetings/title` | Set or edit the active meeting's title |
| `GET` | `/meetings/{id}/speakers` | List speaker aliases for a meeting |
| `POST` | `/meetings/{id}/speakers` | Rename a speaker (`speaker_key` → `display_name`) |
| `GET` | `/meetings/latest/summary` | Summarize the most recent meeting |
| `GET` | `/meetings/{id}/summary` | Summarize a specific meeting by ID |
| `POST` | `/meetings/latest/chat` | Ask a question about the latest meeting |
| `POST` | `/meetings/{id}/chat` | Ask a question about a specific meeting |
| `GET` | `/meetings/{id}/debug/export` | Export raw meeting data for debugging |

### Chat request body

```json
{
  "question": "What action items were assigned to me?"
}
```

### WebSocket status message

```json
{
  "type": "status",
  "recording": true,
  "paused": false,
  "meeting_id": 42,
  "title": "Q3 Roadmap Sync",
  "mic_muted": false,
  "speaker_muted": false,
  "speaker_enabled": true
}
```

### WebSocket transcript message

```json
{
  "text": "Let's align on the Q3 roadmap.",
  "keywords": ["roadmap", "Q3"],
  "actions": [{ "task": "Share roadmap draft", "assignee": "SPEAKER_00" }],
  "meeting_id": 42
}
```

---

## 🤖 AI Models

FloatNote uses exactly **one LLM** for every language task — chatbot answers, meeting summaries, and keyword filtering all go through `ai_modules/utils/llm_client.py`. The remaining models are small local pipeline models (audio/NLP), not LLM providers.

| Component | Default Model | Configurable |
|---|---|---|
| **The LLM** (chat + summaries + keywords) | `Qwen/Qwen2.5-7B-Instruct` (HuggingFace router) | `HUGGINGFACE_CHAT_MODEL` env var |
| Transcription | `openai/whisper-base` (local) | Change model size in `whisper_engine.py` |
| Voice Activity Detection | Silero VAD (local) | `VAD_THRESHOLD` env var |
| Speaker Diarization | Resemblyzer d-vector encoder (local) | `DIARIZATION_SIMILARITY` env var |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local) | Hardcoded in `chatbot.py` |
| NLP / Action Items | `en_core_web_sm` (spaCy, local) | — |

---

## 🗄️ Database Schema

FloatNote uses **SQLite** (`backend/database/meeting_assistant.db`) with async SQLAlchemy.

```
meetings
  id, title, start_time, summary

transcripts
  id, meeting_id → meetings.id, timestamp, text, keywords,
  source (MIC / SPEAKER_xx / OCR)

action_items
  id, meeting_id → meetings.id, description, assignee, status
```

Speaker aliases (`SPEAKER_00` → "Priya") are stored per meeting and applied live across the dashboard.

To inspect the database directly:
```bash
python backend/database/view_db.py
```

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `HUGGINGFACEHUB_API_TOKEN` | — | **Required.** HF token for the single LLM (chat + summaries + keywords) |
| `HUGGINGFACE_CHAT_MODEL` | `Qwen/Qwen2.5-7B-Instruct` | The one LLM used everywhere |
| `HUGGINGFACE_PROVIDER` | `auto` | Inference provider routing (`auto` recommended) |
| `ENABLE_SPEAKER` | `true` | Capture system (loopback) audio |
| `ENABLE_DIARIZATION` | `true` | Label speakers on the system-audio stream |
| `DIARIZATION_SIMILARITY` | `0.70` | Cosine similarity to match an existing speaker |
| `DIARIZATION_MIN_SAMPLES` | `16000` | Min samples (~1s) needed to embed an utterance |
| `VAD_THRESHOLD` | `0.5` | Silero VAD speech-probability threshold |
| `RMS_GATE` | `0.002` | Energy pre-gate; skips dead-silent chunks before VAD |
| `CHUNK_SECONDS` | `5` | Audio chunk length fed to Whisper |
| `AUDIO_BUFFER_SECONDS` | `30` | Rolling capture buffer size |
| `ENABLE_OCR` | `false` | Enable screen capture + OCR |
| `OCR_INTERVAL_SECONDS` | `1.0` | How often to poll for screen changes |
| `OCR_CHANGE_THRESHOLD` | `0.02` | Minimum pixel-change ratio to trigger OCR |
| `HOST` | `0.0.0.0` | Backend bind host |
| `PORT` | `8000` | Backend bind port |

---

## 🛠️ Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) — async web server + WebSockets
- [OpenAI Whisper](https://github.com/openai/whisper) — local speech-to-text
- [Silero VAD](https://github.com/snakers4/silero-vad) — local neural voice activity detection
- [Resemblyzer](https://github.com/resemble-ai/Resemblyzer) — speaker embeddings for streaming diarization
- [soundcard](https://github.com/bastibe/SoundCard) — WASAPI loopback (system audio) capture
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) + [pytesseract](https://github.com/madmaze/pytesseract) — screen reading
- [LangChain](https://www.langchain.com/) + [FAISS](https://faiss.ai/) — RAG chatbot
- [HuggingFace router](https://huggingface.co/docs/inference-providers) (`Qwen2.5-7B-Instruct`) — the single LLM behind chat, summaries, and keyword filtering
- [spaCy](https://spacy.io/) — action item extraction + NLP
- [SQLAlchemy (async)](https://docs.sqlalchemy.org/) + [SQLite](https://sqlite.org/) — database

**Frontend**
- [React 19](https://react.dev/) + [Vite](https://vitejs.dev/) — UI framework
- [Tailwind CSS](https://tailwindcss.com/) — styling
- [Electron](https://www.electronjs.org/) — optional desktop wrapper

---

## 🐛 Known Issues & Limitations

- **System-audio capture is Windows-only** — loopback recording uses WASAPI via `soundcard`. On other platforms FloatNote runs mic-only.
- **Windows-only OCR path** — the Tesseract path in `ocr_processor.py` defaults to a Windows path. Linux/macOS users must update it or ensure `tesseract` is on `PATH`.
- **Single monitor** — OCR captures monitor index `1` by default. Adjust `monitor_index` in `OCRProcessor` for multi-monitor setups.
- **Diarization needs ~1s of speech** — very short utterances keep the previous speaker's label (sticky fallback) rather than guessing.
- **HF API latency** — summarization and chat responses depend on HuggingFace Inference API availability and may be slow on free tier.

---

## 👥 Team

Built as a group project by:

- **Parth Gupta**
- **Parv Tiwari**
- **Vansh Agrawal**
- **Tashvi Gangrade**
- **Shaurya**
