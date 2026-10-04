"""Runtime configuration for FloatNote.

In development the backend reads secrets from ``backend/.env``. In the shipped
desktop app there is no ``.env`` — Electron owns a per-user data directory and
passes it to the backend via the ``FLOATNOTE_DATA_DIR`` environment variable.
The HuggingFace token is resolved, in order, from:

  1. the in-process runtime override (set via ``POST /settings/token`` so a
     freshly-saved token takes effect immediately without restarting),
  2. ``config.json`` inside the data directory (what the first-run settings
     screen and the Settings modal write), then
  3. the ``HUGGINGFACEHUB_API_TOKEN`` environment variable (``backend/.env``
     in dev, or injected by Electron at spawn time in production).

This keeps the token out of the bundled executable entirely.
"""

import json
import os
from pathlib import Path


def data_dir() -> Path:
    """Per-user directory for config, the database, and downloaded models.

    Electron sets FLOATNOTE_DATA_DIR to its userData path. Outside Electron we
    fall back to a per-OS default so the backend is still usable standalone.
    """
    env_dir = os.getenv("FLOATNOTE_DATA_DIR")
    if env_dir:
        base = Path(env_dir)
    elif os.name == "nt":
        base = Path(os.getenv("APPDATA", Path.home())) / "FloatNote"
    else:
        base = Path.home() / ".floatnote"
    base.mkdir(parents=True, exist_ok=True)
    return base


def config_path() -> Path:
    return data_dir() / "config.json"


def load_config() -> dict:
    path = config_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}
    return {}


def save_config(values: dict) -> None:
    """Merge and persist config values (used by the token settings flow)."""
    current = load_config()
    current.update(values)
    config_path().write_text(json.dumps(current, indent=2), encoding="utf-8")


# In-process override so a token saved via the API takes effect immediately
# without restarting the backend.
_runtime_token: str = ""


def set_hf_token(token: str) -> None:
    """Hot-update the token in memory (called by the /settings/token endpoint)."""
    global _runtime_token
    _runtime_token = token.strip()


def get_hf_token() -> str:
    """Resolve the HuggingFace token.

    Priority order (first non-empty wins):
      1. Runtime override  — set via the ``POST /settings/token`` API so a
         freshly-saved token is used immediately without restarting.
      2. config.json       — the persisted token written by Settings / TokenGate.
      3. Environment var   — ``HUGGINGFACEHUB_API_TOKEN`` from ``.env`` (dev) or
         injected by Electron (production).
    """
    if _runtime_token:
        return _runtime_token
    cfg_token = str(load_config().get("huggingface_token", "")).strip()
    if cfg_token:
        return cfg_token
    return (os.getenv("HUGGINGFACEHUB_API_TOKEN") or "").strip()


def is_ocr_enabled() -> bool:
    """Check if screen OCR is enabled (defaults to True)."""
    cfg = load_config()
    if "ocr_enabled" in cfg:
        return bool(cfg["ocr_enabled"])
    env_val = os.getenv("ENABLE_OCR")
    if env_val is not None:
        return env_val.strip().lower() in ("true", "1", "yes")
    return True


def set_ocr_enabled(enabled: bool) -> None:
    """Save the OCR toggle to config.json and update the environment variable."""
    save_config({"ocr_enabled": bool(enabled)})
    os.environ["ENABLE_OCR"] = "true" if enabled else "false"


def models_dir() -> Path:
    """Directory where downloaded models are cached (used in first-run setup)."""
    path = data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path

