# PyInstaller spec for the FloatNote backend.
# Build with:  pyinstaller floatnote_backend.spec --noconfirm
# (run from the backend/ directory, with the project .venv active)

from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = []
binaries = []
hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "aiosqlite",
]

# Packages whose data files / dynamic imports PyInstaller's default analysis
# misses (ML model weights, spaCy pipeline data, native extensions, etc.).
for pkg in [
    "whisper",
    "spacy",
    "en_core_web_sm",
    "thinc",
    "blis",
    "silero_vad",
    "resemblyzer",
    "faiss",
    "librosa",
    "soundcard",
    "sounddevice",
    "langchain",
    "langchain_classic",
    "langchain_community",
    "langchain_core",
    "langchain_huggingface",
    "langchain_text_splitters",
    "sentence_transformers" if False else "tiktoken",
]:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:  # pragma: no cover
        print(f"[spec] collect_all skipped for {pkg}: {exc}")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=["pyi_hooks"],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FloatNoteBackend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FloatNoteBackend",
)
