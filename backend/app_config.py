"""Resolves and loads the user-writable .env config.

In dev, this is backend/.env (as before). In a packaged build, the Electron
shell has no fixed install directory to write into, so it points us at its
per-user data folder via FLOATNOTE_CONFIG_DIR and writes API keys there
through the first-run settings screen.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent


def resolve_config_path() -> Path:
    override = os.getenv("FLOATNOTE_CONFIG_DIR")
    if override:
        return Path(override) / ".env"
    return BACKEND_DIR / ".env"


def load_user_config() -> Path:
    path = resolve_config_path()
    load_dotenv(path, override=True)
    return path
