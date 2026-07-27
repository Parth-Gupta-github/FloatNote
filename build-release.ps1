# FloatNote - production build
# Builds the React UI, freezes the Python backend with PyInstaller, bundles
# a portable Tesseract-OCR + the cached Whisper model into that build, then
# packages everything into a Windows installer (release\FloatNote Setup *.exe).
#
# Usage:
#   .\build-release.ps1            # build the installer only (release\FloatNote Setup *.exe)
#   .\build-release.ps1 -Publish   # build AND upload it to a GitHub draft release
#
# -Publish requires a GitHub token in $env:GH_TOKEN (a classic PAT with the
# "repo" scope, or a fine-grained token with Contents: read/write on
# ParvTiwari/FloatNote). The release is created as a DRAFT for the version in
# frontend\electron\package.json - review it on GitHub, then click Publish.
#
# Requires: root .venv (with pyinstaller + pyinstaller-hooks-contrib installed),
# npm deps installed in frontend\react-app and frontend\electron, and a local
# Tesseract-OCR install at "C:\Program Files\Tesseract-OCR" (used as the
# source for the bundled portable copy).
#
# NOTE: Windows Defender's real-time/cloud protection has been observed
# silently deleting the frozen FloatNoteBackend.exe right after PyInstaller
# writes it (a false positive on large PyInstaller bundles with torch/numba/
# faiss - no quarantine entry, no event log record, the file just vanishes
# from build\ and dist\). A trivial PyInstaller "hello world" build in the
# same environment was unaffected, isolating this to Defender's heuristics
# on this specific bundle rather than a build bug. If `FloatNoteBackend.exe`
# is missing from backend\dist\FloatNoteBackend after this script runs, add
# a build-machine-only exclusion (elevated PowerShell) and re-run:
#   Add-MpPreference -ExclusionPath "<repo>\backend"

param(
    [switch]$Publish
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

if ($Publish -and -not $env:GH_TOKEN) {
    throw "-Publish requires a GitHub token in `$env:GH_TOKEN (PAT with 'repo' scope). Set it, then re-run."
}

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Root .venv not found at $venvPython - create it and install backend\requirements.txt first."
}

$backendDir = Join-Path $root "backend"
$backendDist = Join-Path $backendDir "dist\FloatNoteBackend"
$reactDir = Join-Path $root "frontend\react-app"
$electronDir = Join-Path $root "frontend\electron"

Write-Host "==> Building React UI" -ForegroundColor Cyan
Push-Location $reactDir
npm run build
Pop-Location

Write-Host "==> Freezing Python backend with PyInstaller" -ForegroundColor Cyan
Push-Location $backendDir
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
& $venvPython -m PyInstaller floatnote_backend.spec --noconfirm
Pop-Location

if (-not (Test-Path (Join-Path $backendDist "FloatNoteBackend.exe"))) {
    throw "PyInstaller build did not produce FloatNoteBackend.exe - check the log above."
}

Write-Host "==> Bundling portable Tesseract-OCR" -ForegroundColor Cyan
$tesseractSrc = "C:\Program Files\Tesseract-OCR"
if (Test-Path $tesseractSrc) {
    $tesseractDest = Join-Path $backendDist "tesseract"
    Remove-Item -Recurse -Force $tesseractDest -ErrorAction SilentlyContinue
    Copy-Item $tesseractSrc $tesseractDest -Recurse
} else {
    Write-Warning "Tesseract-OCR not found at $tesseractSrc - OCR will be unavailable in this build."
}

Write-Host "==> Bundling cached Whisper model" -ForegroundColor Cyan
$whisperCache = Join-Path $env:USERPROFILE ".cache\whisper\base.pt"
if (Test-Path $whisperCache) {
    $whisperDest = Join-Path $backendDist "whisper_assets"
    New-Item -ItemType Directory -Force -Path $whisperDest | Out-Null
    Copy-Item $whisperCache $whisperDest
} else {
    Write-Warning "No cached base.pt found at $whisperCache - the app will download it on first run instead."
}

Push-Location $electronDir
if ($Publish) {
    Write-Host "==> Packaging Electron app + uploading to GitHub draft release" -ForegroundColor Cyan
    npm run dist:publish
} else {
    Write-Host "==> Packaging Electron app (NSIS installer)" -ForegroundColor Cyan
    npm run dist
}
Pop-Location

if ($Publish) {
    Write-Host "Done. Draft release uploaded - review it at https://github.com/ParvTiwari/FloatNote/releases and click Publish." -ForegroundColor Green
} else {
    Write-Host "Done. Installer is under release\" -ForegroundColor Green
}
