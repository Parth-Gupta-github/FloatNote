import os
import sys
import warnings
import traceback
from datetime import datetime
from pathlib import Path


def _log_dir() -> Path:
    """Where to write backend.log: the Electron-provided config dir if set,
    otherwise next to the frozen exe (packaged) or the backend dir (dev)."""
    cfg = os.getenv("FLOATNOTE_CONFIG_DIR")
    if cfg:
        return Path(cfg)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


# In a frozen build, always log to a file. Launched directly (windowed,
# console=False) there is no stdout at all; launched by the Electron shell
# stdout is a pipe nobody can see in production. Either way, backend.log in
# the config dir is the only place startup progress and crashes are visible.
_LOG_FILE = None
if getattr(sys, "frozen", False) or sys.stdout is None or sys.stderr is None:
    try:
        log_path = _log_dir() / "backend.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _LOG_FILE = open(log_path, "a", encoding="utf-8", buffering=1)
        sys.stdout = _LOG_FILE
        sys.stderr = _LOG_FILE
    except Exception:
        pass
else:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

warnings.filterwarnings(
    "ignore",
    message="TypedStorage is deprecated"
)


def main() -> None:
    from app_config import load_user_config

    load_user_config()

    from ai_modules.stt.whisper_engine import run_server

    print("🌐 Running Server...\n", flush=True)
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    run_server(host=host, port=port)


if __name__ == "__main__":
    print(f"\n===== backend start {datetime.now().isoformat()} =====", flush=True)
    try:
        main()
    except BaseException:
        traceback.print_exc()
        if _LOG_FILE is not None:
            _LOG_FILE.flush()
        raise
