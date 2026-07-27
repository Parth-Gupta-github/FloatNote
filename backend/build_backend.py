"""Build the FloatNote backend executable with PyInstaller.

Python 3.10.0 ships a bug in ``dis._get_const_info`` that raises IndexError
while disassembling some bytecode (fixed in 3.10.1+). PyInstaller's static
analysis walks bytecode and trips over it. We patch the function defensively
before invoking PyInstaller: its return value is only used to render a
human-readable constant for display, not for PyInstaller's import detection,
so returning a placeholder on failure is harmless and lets analysis finish.

Usage (from the backend/ directory):
    python build_backend.py
"""

import dis

_orig_get_const_info = dis._get_const_info


def _safe_get_const_info(*args, **kwargs):
    try:
        return _orig_get_const_info(*args, **kwargs)
    except IndexError:
        return None, "None"


dis._get_const_info = _safe_get_const_info

# Same defensive guard for the name-info helper, which shares the buggy path.
_orig_get_name_info = dis._get_name_info


def _safe_get_name_info(*args, **kwargs):
    try:
        return _orig_get_name_info(*args, **kwargs)
    except IndexError:
        return "", ""


dis._get_name_info = _safe_get_name_info

import PyInstaller.__main__

PyInstaller.__main__.run(
    [
        "floatnote_backend.spec",
        "--noconfirm",
        "--clean",
    ]
)
