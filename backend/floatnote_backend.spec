# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the FloatNote backend.
# Entry point is main.py, which imports run_server from ai_modules.stt.whisper_engine.
#
# collect_all() is used for every package that loads models / data / native
# libraries at runtime, because PyInstaller's static import analysis cannot see
# those dynamic paths and would otherwise leave them out (crash on first use).

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

DYNAMIC_PACKAGES = [
    "aiosqlite",                  # SQLite async driver, loaded by SQLAlchemy by name
    "sqlalchemy",                 # DB dialects resolved dynamically at runtime
    "greenlet",                   # required by SQLAlchemy's async engine
    "uvicorn",                    # ASGI server: loops/protocols loaded by name
    "cv2",                        # OpenCV (screen OCR): native DLLs
    "mss",                        # screen capture
    "pytesseract",                # Tesseract wrapper
    "whisper",                    # mel-filter + tokenizer assets
    "silero_vad",                 # bundled VAD model
    "resemblyzer",                # pretrained voice-encoder weights
    "soundcard",                  # WASAPI loopback wrapper
    "sounddevice",                # bundled PortAudio DLL
    "spacy",                      # pipeline + lookups data
    "en_core_web_sm",             # the NLP model package
    "faiss",                      # native similarity-search lib
    "torch",                      # the large one: many native libs
    "langchain",
    "langchain_core",
    "langchain_community",
    "langchain_huggingface",
    "langchain_text_splitters",
    "sentence_transformers",
    "transformers",
    "huggingface_hub",
    "tokenizers",
]

for pkg in DYNAMIC_PACKAGES:
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception as exc:  # a missing optional package must not abort the build
        print(f"[spec] skipping {pkg}: {exc}")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # webrtcvad is an optional VAD backend that silero_vad references but our
    # app never uses (we use Silero). Its hooks-contrib hook fails to load, and
    # excluding it is safe because nothing in the app imports it.
    excludes=["tkinter", "matplotlib", "PyQt5", "PySide2", "webrtcvad"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,       # onedir: keep libraries beside the exe (fast start)
    name="floatnote-backend",
    console=True,                # keep a console so logs are visible while testing
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="floatnote-backend",
)
