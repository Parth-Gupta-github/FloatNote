"""Runtime configuration for FloatNote.

In development the backend reads secrets from ``backend/.env``. In the shipped
desktop app there is no ``.env`` — Electron owns a per-user data directory and
passes it to the backend via the ``FLOATNOTE_DATA_DIR`` environment variable.
The HuggingFace token is resolved, in order, from:

  1. the ``HUGGINGFACEHUB_API_TOKEN`` environment variable (what Electron
     injects when it spawns the backend), then
  2. ``config.json`` inside the data directory (what the first-run settings
     screen writes).

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


def get_hf_token() -> str:
    """Resolve the HuggingFace token: injected env var first, then config.json."""
    token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    if token:
        return token.strip()
    return str(load_config().get("huggingface_token", "")).strip()


def models_dir() -> Path:
    """Directory where downloaded models are cached (used in first-run setup)."""
    path = data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path
