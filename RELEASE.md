# Releasing FloatNote (Windows installer → GitHub Releases)

FloatNote ships as an unsigned Windows NSIS installer (`FloatNote Setup <version>.exe`)
built locally and uploaded to [GitHub Releases](https://github.com/ParvTiwari/FloatNote/releases).

## Prerequisites (one-time)

- Root `.venv` with `backend/requirements.txt` + `pyinstaller` + `pyinstaller-hooks-contrib` installed.
- `npm install` run in both `frontend/react-app` and `frontend/electron`.
- Tesseract-OCR installed at `C:\Program Files\Tesseract-OCR` (source for the bundled copy).
- For publishing: a GitHub token in `$env:GH_TOKEN` — a classic PAT with the **`repo`** scope,
  or a fine-grained token with **Contents: read & write** on `ParvTiwari/FloatNote`.
  Create one at https://github.com/settings/tokens

## Cut a release

1. Bump the version in `frontend/electron/package.json` (`"version"`). The release is tagged `v<version>`.
2. From the repo root, in PowerShell:

   ```powershell
   $env:GH_TOKEN = "ghp_your_token_here"
   .\build-release.ps1 -Publish
   ```

   This builds the React UI, freezes the Python backend (PyInstaller), bundles Tesseract +
   the Whisper model, packages the NSIS installer, and uploads it to a **draft** GitHub release.

3. Go to https://github.com/ParvTiwari/FloatNote/releases, open the draft, add release notes,
   and click **Publish release**.

To build the installer **without** publishing (output lands in `release\`):

```powershell
.\build-release.ps1
```

## What users see (unsigned build)

The installer is **not code-signed**, so on first download Windows SmartScreen shows
*"Windows protected your PC."* Users click **More info → Run anyway**. This is expected for
indie apps. To remove the warning you'd need a code-signing certificate (OV or EV, ~$200–400/yr;
separate from a Microsoft Partner Center account) configured in the electron-builder `win` block.

## Notes

- The installer is large (~580 MB) because it bundles PyTorch, faiss, Whisper, and Tesseract.
- First launch shows a settings screen to collect the required API keys
  (`GROQ_API_KEY`, `HUGGINGFACEHUB_API_TOKEN`, `GEMINI_API_KEY`), stored per-user under
  the app's `userData` folder — not in the install directory.
- Windows Defender may false-positive on the frozen `FloatNoteBackend.exe` and silently delete
  it mid-build. If it goes missing from `backend\dist\FloatNoteBackend`, add a build-machine
  exclusion in an elevated PowerShell and re-run:
  `Add-MpPreference -ExclusionPath "<repo>\backend"`
- No app icon is set yet, so the default Electron icon is used. To brand it, add an `icon.ico`
  and point `build.win.icon` at it in `frontend/electron/package.json`.
