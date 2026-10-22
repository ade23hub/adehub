"""Locations that differ between running from source and the packaged Windows app."""

import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
APP_DIR = Path(__file__).resolve().parent


def resource_dir():
    """Folder that holds the bundled read-only files (asset/, splash .ui)."""
    if FROZEN:
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return APP_DIR.parent


def data_dir():
    """Writable folder for the database, test sandbox and exports."""
    if not FROZEN:
        return APP_DIR
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    folder = Path(base) / "GOPILOT"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def set_app_id():
    """Give Windows its own taskbar identity so the GOPILOT logo shows instead of Python's."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Sulaimon.GOPILOT.FileOrganizer.1")
    except (AttributeError, OSError):
        pass
