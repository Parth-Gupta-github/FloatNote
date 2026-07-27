# Overrides pyinstaller-hooks-contrib's hook-webrtcvad.py, which assumes the
# PyPI dist name is "webrtcvad" -- this project installs "webrtcvad-wheels"
# (same `webrtcvad` import name, different dist metadata), so copy_metadata()
# raises PackageNotFoundError and aborts the whole build.
from PyInstaller.utils.hooks import copy_metadata

try:
    datas = copy_metadata("webrtcvad-wheels")
except Exception:
    datas = []
