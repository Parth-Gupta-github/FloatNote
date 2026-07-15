import importlib, traceback, sys, os
print("PYTHON:", sys.executable)
print("CWD:", os.getcwd())
try:
    m = importlib.import_module("ai_modules.stt.whisper_engine")
    print("IMPORT_OK")
    print("has run_server:", hasattr(m, "run_server"))
except Exception:
    print("IMPORT_ERROR")
    traceback.print_exc()
    sys.exit(1)
