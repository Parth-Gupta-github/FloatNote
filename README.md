# FloatNote — Real-time Meeting Assistant (Local)

FloatNote captures live microphone audio and screen text (OCR), extracts keywords and action-items, persists meeting data in SQLite, and provides tools for summarization and grounded Q&A over recorded meeting content.

This README documents everything you need to install, configure, and run FloatNote locally on Windows/macOS/Linux and includes examples for development, debugging, and integrating the frontend UI.

Contents
- [Project summary](#project-summary)
- [Features](#features)
- [Architecture (mermaid)](#architecture-mermaid)
- [Quickstart — Windows (recommended)](#quickstart-windows-recommended)
- [Prerequisites](#prerequisites)
- [Backend: setup & run](#backend-setup--run)
- [Frontend: setup & run (React + Electron)](#frontend-setup--run-react--electron)
- [Environment variables](#environment-variables)
- [WebSocket API (realtime)](#websocket-api-realtime)
- [Database & data model](#database--data-model)
- [Common tasks & examples](#common-tasks--examples)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License & acknowledgements](#license--acknowledgements)

## Project summary

FloatNote is built as a local-first meeting assistant with these goals:
- Low-latency transcription from microphone using Whisper (or its faster variants).
- Screen capture-based OCR to capture slide content and extract keywords.
- Automatic extraction and persistence of transcripts, keywords, and action items.
- Tools to summarize meetings and provide a grounded chatbot powered by vector search (FAISS) + Hugging Face models.

## Features

- Real-time streaming WebSocket (`/ws`) that emits JSON analysis packages (transcript, keywords, OCR result, actions).
- Screen-monitor OCR with change-detection to avoid repeated OCR on static content.
- Lightweight SQLite storage (async SQLAlchemy) for meetings, transcripts, and action items.
- Summarizer and Chatbot helpers (Hugging Face + LangChain) configurable via env tokens.

## Architecture (mermaid)

```mermaid
flowchart LR
      subgraph Client
            UI[React UI / Electron]
      end

      subgraph Backend
            STT[Whisper STT WebSocket /ws]
            OCR[OCR Processor]
            DB[(SQLite: meeting_assistant.db)]
            Chat[Chatbot (LangChain + FAISS)]
            Summ[Summarizer (Hugging Face)]
      end

      Mic[Microphone] --> STT
      Screen[Screen Capture] --> OCR
      OCR --> STT
      STT --> DB
      STT --> UI
      DB --> Chat
      DB --> Summ
      UI --> Chat
      UI --> Summ
```

## Quickstart — Windows (recommended)

1. Clone the repository:

```powershell
git clone <repo-url> FloatNote
cd FloatNote
```

2. Create a Python virtual environment and activate it:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# On macOS/Linux: python -m venv .venv; source .venv/bin/activate
```

3. Install backend Python dependencies:

```powershell
pip install -r backend/requirements.txt
```

4. Install system dependencies:

- Tesseract OCR (for screen OCR) — Windows installer recommended: install and ensure `tesseract.exe` path is correct.
- ffmpeg (required by Whisper and some audio tooling) — ensure `ffmpeg` is on PATH.

5. Copy example envs and edit tokens:

```powershell
copy backend\.env.example backend\.env
copy frontend\react-app\.env.example frontend\react-app\.env
# Then edit backend\.env and add your HUGGINGFACEHUB_API_TOKEN
```

6. Start the backend (PowerShell helper provided):

```powershell
.\backend\start_backend.ps1
# or: python backend/main.py
```

7. Start the frontend (React dev server):

```powershell
cd frontend/react-app
npm install
npm run dev
```

8. (Optional) Start the Electron wrapper (loads the React dev URL):

```powershell
cd frontend/electron
npm install
npm start
```

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Tesseract OCR (Windows: install and make sure path matches the `ocr_processor.py` setting)
- ffmpeg (on PATH) for Whisper
- On Windows, install Visual C++ Build Tools if binary packages fail to install

Note: Some packages (torch, faiss) may have platform-specific wheels. If `pip install -r backend/requirements.txt` fails for these, follow the official install instructions for your platform (CPU vs GPU builds).

## Backend — setup & run

Main entry points:
- `backend/main.py` — primary entry which either imports and runs `ai_modules.stt.whisper_engine.run_server()` or falls back to a minimal FastAPI root.
- `backend/ai_modules/stt/whisper_engine.py` — WebSocket server and audio capture pipeline.

Environment-sensitive defaults
- `HOST` and `PORT` are read by `backend/main.py` (defaults: `0.0.0.0:8000`).

Recommended flow (cross-platform):

- Create and activate venv (see Quickstart).
- Install requirements: `pip install -r backend/requirements.txt`.
- Ensure `backend/.env` contains `HUGGINGFACEHUB_API_TOKEN` if you want summarizer/chat features.
- Start server: `python backend/main.py` (or use `backend/start_backend.ps1` on Windows).

Using dotenv CLI (if installed via requirements):

```bash
python -m dotenv run -- python backend/main.py
```

### Backend helper files added
- [backend/.env.example](backend/.env.example) — example environment variables (copy to `.env`).
- [backend/start_backend.ps1](backend/start_backend.ps1) — PowerShell helper to load `.env` and run the server.

## Frontend — setup & run (React + Electron)

React app:
- Folder: `frontend/react-app`
- Dev server: `npm run dev` (Vite)
- Example env: [frontend/react-app/.env.example](frontend/react-app/.env.example)

Electron shell:
- Folder: `frontend/electron`
- Start: `npm start` (this loads the React dev URL in a desktop window)

Notes
- The React UI expects a WebSocket at `ws://<HOST>:<PORT>/ws` and REST endpoints for summaries/chat if available.

## Environment variables

Copy `backend/.env.example` to `backend/.env` and add secrets/tokens.

Key variables (explained):
- `HOST`, `PORT` — server bind address and port.
- `HUGGINGFACEHUB_API_TOKEN` — required for Hugging Face model access used by summarizer/chat.
- `HUGGINGFACE_CHAT_MODEL` — repo id for chat model (optional override).
- `ENABLE_OCR` — enable screen OCR processing (`true`/`false`).
- `OCR_INTERVAL_SECONDS`, `OCR_CHANGE_THRESHOLD` — OCR tuning for change-detection.

See [backend/.env.example](backend/.env.example).

## WebSocket API (realtime)

The STT server exposes a WebSocket endpoint at:

```
ws://<HOST>:<PORT>/ws
```

Behavior:
- On connection, the server returns a handshake JSON: `{ "type": "connected", "meeting_id": <id> }`.
- While streaming, the server pushes JSON packets containing at least:

```json
{
      "text": "transcribed text",
      "keywords": ["keyword1","keyword2"],
      "ocr": { "text": "screen text", "keywords": ["slide","topic"] },
      "meeting_id": 1,
      "actions": ["action item 1", "action item 2"]
}
```

Example JavaScript client:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = () => console.log('connected');
ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      console.log('msg', msg);
};
```

Example Python client (websockets):

```python
import asyncio
import websockets
import json

async def run():
            async with websockets.connect('ws://localhost:8000/ws') as ws:
                        async for msg in ws:
                                    data = json.loads(msg)
                                    print(data)

asyncio.run(run())
```

## Database & data model

SQLite file: `backend/database/meeting_assistant.db`

Tables (core):
- `meetings` — id, title, start_time, summary
- `transcripts` — id, meeting_id, timestamp, text, keywords, source
- `action_items` — id, meeting_id, description, assignee, status

Quick DB viewer:

```bash
python backend/database/view_db.py
```

## Common tasks & examples

- View latest meeting data (from Python):

```python
from backend.database.crud import get_latest_meeting_data
import asyncio

print(asyncio.run(get_latest_meeting_data()))
```

- Generate a vector store for chatbot usage (example flow):

```python
from backend.ai_modules.chatbot.chatbot import convert_to_documents, create_vector_store, ask_question
data = asyncio.run(get_latest_meeting_data())
docs = convert_to_documents(data['items'])
db = create_vector_store(docs)
answer = ask_question('What are the action items?', db)
```

## Troubleshooting

- If `ai_modules.stt` fails to import in `backend/main.py`, ensure you installed the heavy dependencies (Whisper, torch, sounddevice). If you want a minimal startup without STT, the fallback FastAPI app will start.
- OCR empty results: install Tesseract and confirm `pytesseract.pytesseract.tesseract_cmd` in `backend/ai_modules/ocr/ocr_processor.py` points to the installed executable.
- Resource issues: large models (Whisper, HF chat) need CPU/RAM. Use smaller models or run on a machine with sufficient memory.

## Contributing

- PRs welcome. Keep changes focused and update this README with any new instructions.

## License & acknowledgements

Add a `LICENSE` file if you intend to open-source this project. FloatNote leverages open-source packages such as Whisper, Hugging Face, LangChain, spaCy, FAISS, Vite, and Electron.

---

Files I added to make the README actionable:
- [backend/.env.example](backend/.env.example)
- [backend/start_backend.ps1](backend/start_backend.ps1)
- [frontend/react-app/.env.example](frontend/react-app/.env.example)

If you'd like, I can also:
- Wire simple FastAPI REST routes for `/meetings/latest/summary` and `/meetings/latest/chat` and add curl/postman examples.
- Add a Dockerfile / docker-compose for local containerized development.

Tell me which of the above you'd like next and I will implement it.
