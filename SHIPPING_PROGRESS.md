# FloatNote — Shipping Progress (resume notes)

Goal: turn FloatNote into a downloadable Windows installer (Electron UI +
PyInstaller-bundled Python backend). ALL PHASES DONE except final installer
verification + distribution.

> All changes below are UNCOMMITTED by request — verify, then commit yourself.

## ⚠️ CRITICAL testing gotcha (cost hours to find)
When test-running the packaged Electron app, `ELECTRON_RUN_AS_NODE=1` was set in
the shell env, which makes Electron run as plain Node (no `app` object) so the
app crashes instantly at `app.isPackaged`. It is NOT an app bug. Before testing
the packaged exe, clear it: `Remove-Item Env:\ELECTRON_RUN_AS_NODE`. The user's
normal environment does not have this set, so the shipped app works for them.

## ✅ VERIFIED: the packaged app works end-to-end
With ELECTRON_RUN_AS_NODE cleared, running the packaged FloatNote.exe logs:
main.js loaded (isPackaged=true) → app ready → startBackend spawns the bundled
backend exe → createWindow → backend serves :8000 in ~14s. Phase 3 confirmed.
Also required: **electron-builder upgraded 25→26** (25 could not package Electron 40).

## Status by phase

| Phase | What | State |
|---|---|---|
| 1 | Electron production build (vite `base:'./'`, quit handler, title) | ✅ done & verified |
| 6 | Security: bind 127.0.0.1, CORS restricted, debug endpoints gated, OCR default off | ✅ done & verified |
| 4-backend | Token from injected env / `config.json` (`app_config.py`) | ✅ done & verified |
| 2 | Bundle backend into `.exe` with PyInstaller | ✅ DONE — exe runs clean, serves :8000, DB in data dir, all models load |
| 4-frontend | First-run token screen (`TokenGate.jsx` + `preload.js` + IPC in main.js) | ✅ done, compiles |
| 3 | Electron spawns/owns backend (`main.js`, `splash.html`, `backend-error.html`) | 🔧 code done; verified once installer runs |
| 7 | electron-builder installer (`electron/package.json` build config) | 🔧 IN PROGRESS — `npm run dist` building |
| 5 | Models on first run | ✅ covered — models auto-download on first use; splash tells the user |
| 8 | Distribution (sign, host, install/uninstall test) | ⏳ after installer builds |

### Phase 2 — DONE. The bundled exe fully works:
Verified startup log: `🗄️ Database initialized`, OCR off, DB/transcription workers up, serves :8000 (openapi/speakers = 200). Took ~34s to load models. Fixes that got it there, all in `floatnote_backend.spec` + code:
1. Python 3.10.0 dis bug → `build_backend.py` wrapper. 2. webrtcvad excluded. 3. aiosqlite/uvicorn/sqlalchemy/greenlet added. 4. `main.py` forces UTF-8 stdout (emoji crash). 5. `database/models.py` puts the DB in the data dir when frozen (was: unopenable path in the read-only bundle).

## Phase 2 — exactly where we are

The exe builds. Fixed so far:
1. **Python 3.10.0 `dis` bug** → patched by `backend/build_backend.py` (run builds through this, NOT raw pyinstaller).
2. **webrtcvad hook failure** → excluded in `floatnote_backend.spec` (unused; we use silero).
3. **`ModuleNotFoundError: aiosqlite`** at runtime → added aiosqlite/sqlalchemy/greenlet/uvicorn to the spec's `DYNAMIC_PACKAGES`.

LATEST (2026-07-18 end of session):
- The bundled exe loads the ENTIRE backend fine (db, whisper, silero, etc.). The
  only remaining crash was the emoji log line -> **FIXED in code**: `main.py` now
  forces UTF-8 stdout/stderr at the top (durable; PYTHONIOENCODING was unreliable
  in the frozen exe). Fix #4 in the spec: aiosqlite/uvicorn/sqlalchemy/greenlet
  are all bundled and working (no more aiosqlite crash).
- The rebuild to bake in the UTF-8 fix FAILED on a transient Windows file lock:
  `PermissionError WinError 32` — a leftover floatnote-backend.exe was holding
  `dist/floatnote-backend` open, so --clean couldn't wipe it. `dist/` is now in a
  partial/locked state. This is a build-artifact lock, NOT a code problem.

### RESUME HERE (next commands)
1. Make sure no exe is holding dist (reboot clears it if needed):
   `taskkill //IM floatnote-backend.exe //F`  (then confirm `tasklist | grep floatnote` is empty)
   If `dist/floatnote-backend` still won't delete, reboot, then delete `backend/dist` and `backend/build`.
2. Rebuild (bakes in the UTF-8 fix):  from `backend/`  `PYTHONIOENCODING=utf-8 ../.venv/Scripts/python.exe build_backend.py`
3. Run-test the exe (should now serve clean — emoji crash gone):
```
cd backend/dist/floatnote-backend
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 FLOATNOTE_DATA_DIR=<tempdir> ./floatnote-backend.exe
# poll http://127.0.0.1:8000/openapi.json ; expect 200 and NO traceback in stdout
```
If it crashes with another `ModuleNotFoundError: X`, add `X` to `DYNAMIC_PACKAGES`
in `floatnote_backend.spec` and rebuild. Repeat until it serves clean, then do a
summary+chat smoke test with a real HF token.

## Files changed (uncommitted)
- `frontend/react-app/vite.config.js`, `frontend/react-app/index.html`
- `frontend/electron/main.js` (+ new `splash.html`, `backend-error.html`)
- `backend/main.py`, `backend/ai_modules/stt/whisper_engine.py`
- new: `backend/ai_modules/utils/app_config.py`
- new: `backend/floatnote_backend.spec`, `backend/build_backend.py`
- `backend/.env` (local: ENABLE_OCR=false) — gitignored, not committed

## Gotchas / notes
- Python is **3.10.0** (buggy patch release). Consider upgrading to 3.10.11+/3.11 later.
- Always launch the backend with `PYTHONIOENCODING=utf-8` or the emoji logs crash the Windows console.
- Watch for stale servers on port 8000 giving false "it works" readings — check the serving PID.
- HF token (`Floatnotekey`) works; single model = `Qwen/Qwen2.5-7B-Instruct`.
