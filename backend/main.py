import os
import sys
import warnings

# Force UTF-8 output so emoji log lines never crash on a non-UTF-8 Windows
# console or when stdout is redirected to a file (cp1252). Must run before any
# print, and works in the frozen exe where PYTHONIOENCODING is unreliable.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

warnings.filterwarnings(
    "ignore",
    message="TypedStorage is deprecated"
)

from ai_modules.stt.whisper_engine import run_server


if __name__ == "__main__":
    print("🌐 Running Server...\n")
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    run_server(host=host, port=port)
