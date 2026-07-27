# FloatNote — Build & Packaging Guide

How FloatNote is turned into a downloadable Windows installer, what each change
does, the problems hit along the way (and their fixes), and the exact steps to
rebuild the `.exe` / installer again.

FloatNote ships as **two programs in one installer**: an Electron desktop UI and
a Python FastAPI backend (with Whisper/PyTorch). The user's machine has no
Python, so the backend is compiled to a standalone `.exe` with PyInstaller, and
Electron launches it as a child process.

---

## Prerequisites (one-time)

- Windows, Python 3.10+ (venv at `.venv`), Node.js 18+.
- Backend deps installed: `pip install -r backend/requirements.txt` and `pip install pyinstaller`.
- Electron deps installed: `cd frontend/electron && npm install` (this includes `electron-builder`).
- React deps installed: `cd frontend/react-app && npm install`.

---

## What changed in each phase (and how to do it manually)

### Phase 1 — Make the Electron production build render
The packaged app showed a blank white screen.
- `frontend/react-app/vite.config.js`: add `base: './'`. **Why:** Vite defaults
  to absolute asset paths (`/assets/...`) which 404 under Electron's `file://`
  protocol; relative paths (`./assets/...`) resolve next to `index.html`.
- `frontend/electron/main.js`: add `app.on('window-all-closed', () => app.quit())`
  so the process actually exits on Windows.
- `frontend/react-app/index.html`: set `<title>FloatNote</title>`.
- Verify: `cd frontend/react-app && npm run build`, then confirm `dist/index.html`
  references `./assets/...`.

### Phase 6 — Security hardening (do this BEFORE bundling)
`backend/ai_modules/stt/whisper_engine.py` and `backend/main.py`:
- Bind to `127.0.0.1` instead of `0.0.0.0` (server default + `HOST` default).
  **Why:** `0.0.0.0` exposes the mic/screen-capture API to the whole network.
- CORS: replace `allow_origins=["*"] + allow_credentials=True` with a fixed list
  (`localhost:5173`, `127.0.0.1:5173`, `null` for `file://`) and
  `allow_credentials=False`. **Why:** the old combo let any website drive the API.
- Debug endpoints: gate all four behind `ENABLE_DEBUG_ENDPOINTS` (return 404 when
  off). **Why:** they dump full transcripts to disk.
- OCR default: change the forced `ENABLE_OCR=true` to `false`. **Why:** OCR reads
  the whole screen; it must be opt-in.

### Phase 4a — Token from config, not baked into the exe
- New `backend/ai_modules/utils/app_config.py`: resolves a per-user data dir
  (`FLOATNOTE_DATA_DIR` env, else `%APPDATA%/FloatNote`), reads/writes
  `config.json`, and resolves the HF token as **env var → config.json → empty**.
- `backend/ai_modules/utils/llm_client.py`: read the token via `get_hf_token()`.
  **Why:** a public app can't ship a real token; the user supplies their own.

### Phase 2 — Bundle the backend into a standalone `.exe` (the hard part)
- New `backend/floatnote_backend.spec`: uses `collect_all()` for every package
  that loads models/data/native libs dynamically (torch, whisper, silero_vad,
  resemblyzer, soundcard, sounddevice, spacy, en_core_web_sm, faiss, langchain*,
  sentence_transformers, transformers, huggingface_hub, tokenizers, **aiosqlite,
  sqlalchemy, greenlet, uvicorn**). Excludes `tkinter, matplotlib, PyQt5,
  PySide2, webrtcvad`. Builds **onedir** (folder of libs beside the exe).
  **Why collect_all:** PyInstaller traces `import` statements statically, but ML
  libs load their weights/DLLs by runtime path, so they must be gathered explicitly.
- New `backend/build_backend.py`: patches a Python 3.10.0 `dis` bug, then runs
  PyInstaller on the spec. Always build through this, not raw `pyinstaller`.
- `backend/main.py`: at the very top, force `sys.stdout/stderr` to UTF-8.
  **Why:** the emoji log lines crash on a cp1252 Windows console / redirected file.
- `backend/database/models.py`: when frozen, put the SQLite DB in the data dir.
  **Why:** the default path points inside the read-only bundle → "unable to open
  database file".

### Phase 3 — Electron spawns and owns the backend
`frontend/electron/main.js`:
- On app-ready, `spawn()` the bundled `backend.exe` (path under
  `process.resourcesPath/backend/floatnote-backend/`), passing
  `FLOATNOTE_DATA_DIR = userData` and `PYTHONIOENCODING/PYTHONUTF8`.
- Poll `http://127.0.0.1:8000` until ready; show `splash.html` meanwhile, then
  load the UI; show `backend-error.html` on failure.
- Kill the backend on `window-all-closed` / `before-quit`.
- **Add a `backendProcess.on('error', ...)` handler** — without it a spawn error
  crashes Electron's main process.
- New files: `splash.html`, `backend-error.html`.

### Phase 4b — First-run token screen
- New `frontend/electron/preload.js`: `contextBridge` exposing
  `getConfig()` / `saveToken()` over IPC (renderer never touches the filesystem).
- `frontend/electron/main.js`: `ipcMain` handlers that read/write
  `userData/config.json`; attach the preload to the window.
- New `frontend/react-app/src/TokenGate.jsx`: shows a token-entry screen when no
  token is set (desktop only); `main.jsx` wraps `<App/>` in `<TokenGate>`.

### Phase 7 — Build the installer
- `frontend/electron/package.json` `build` block: `appId`, `productName`, NSIS
  Windows target, `asar: false`, and `extraResources` copying `react-app/dist` →
  `ui` and `backend/dist/floatnote-backend` → `backend/floatnote-backend`.
- `main.js` loads the UI from `process.resourcesPath/ui` when packaged.
- Run `electron-builder --win nsis` → `release/FloatNote Setup 1.0.0.exe`.

---

## Problems encountered & how they were fixed

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | `IndexError: tuple index out of range` in `dis.py` during PyInstaller analysis | **Python 3.10.0** stdlib bug (fixed in 3.10.1+) | `build_backend.py` monkey-patches `dis._get_const_info` before building |
| 2 | `ImportErrorWhenRunningHook ... webrtcvad` | Unused optional dep's hook fails | Add `webrtcvad` to spec `excludes` |
| 3 | Exe runs, then `ModuleNotFoundError: aiosqlite` | SQLAlchemy loads the driver by name; PyInstaller missed it | Add `aiosqlite/sqlalchemy/greenlet/uvicorn` to the spec |
| 4 | `UnicodeEncodeError: '\U0001f310'` at first print | cp1252 console can't encode emoji | Force UTF-8 stdout at top of `main.py` |
| 5 | `sqlite3.OperationalError: unable to open database file` | DB path pointed inside the read-only bundle | Route DB to the writable data dir when frozen |
| 6 | Rebuild fails: `PermissionError WinError 32` on `dist/` | A leftover `floatnote-backend.exe` locked the folder | Kill strays before rebuild; reboot clears stubborn locks |
| 7 | Packaged app exits instantly, `--version` shows Node version | **electron-builder 25 can't package Electron 40** | Upgrade `electron-builder` to 26+ |
| 8 | App crashes at `app.isPackaged` (app undefined) | **`ELECTRON_RUN_AS_NODE=1`** in the shell forces Node mode | Clear the env var before testing — it is a test-env artifact, not an app bug |
| 9 | False "it works" / "unable to bind" | A stale server was already on port 8000 | Always check the PID actually serving :8000 |

---

## HOW TO REBUILD THE EXE / INSTALLER AGAIN

Run from the repo root (`FloatNote_Resources`). Make sure no `floatnote-backend.exe`
is running first (`taskkill //IM floatnote-backend.exe //F`).

**1. Build the React UI**
```
cd frontend/react-app
npm run build
```

**2. Build the backend .exe** (uses the spec + the 3.10.0 patch)
```
cd ../../backend
PYTHONIOENCODING=utf-8 ../.venv/Scripts/python.exe build_backend.py
```
Output: `backend/dist/floatnote-backend/floatnote-backend.exe` (+ libs).

**3. (Optional) Smoke-test the backend exe**
```
cd dist/floatnote-backend
FLOATNOTE_DATA_DIR=<a temp dir> ./floatnote-backend.exe
# in another shell: curl http://127.0.0.1:8000/openapi.json  → expect 200, no traceback
```

**4. Build the installer**
```
cd ../../../frontend/electron
npm run dist          # electron-builder --win nsis
```
Output: `frontend/electron/release/FloatNote Setup <version>.exe`.

**5. Test the packaged app** (⚠️ clear the env var first)
```
# PowerShell:
Remove-Item Env:\ELECTRON_RUN_AS_NODE
Start-Process ".\release\win-unpacked\FloatNote.exe"
# It should open a window and, within ~15s, serve on http://127.0.0.1:8000
```

If you change any **backend** code, you must redo steps 2 and 4 (the exe is frozen
at build time). If you change only **React** code, redo steps 1 and 4. If you
change only **Electron** `main.js`/`preload.js`, redo step 4.

To bump the version, change `version` in `frontend/electron/package.json`.

---

## Known follow-ups
- **Size (~490 MB):** dominated by PyTorch. Switch Whisper to `faster-whisper`
  (CTranslate2, no full torch) to shrink significantly.
- **Unsigned:** Windows SmartScreen warns "unknown publisher". Needs a paid
  code-signing certificate to remove.
- **asar:** currently `false` (app files loose in `resources/app`). Can be set
  `true` for a tidier package once re-verified.
