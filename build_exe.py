"""Build GOPILOT into a Windows app (no console window).

Usage (from the project root, with the virtual environment active):
    python build_exe.py

Output:
    dist\\GOPILOT\\GOPILOT.exe     the app folder
    dist\\GOPILOT-Windows.zip     a portable copy you can share
"""

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
ICON = ROOT / "asset" / "GOPILOT.ico"

EXCLUDES = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.Qt3DCore",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtMultimedia",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtSql", "PySide6.QtNetwork",
    "PySide6.QtBluetooth", "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtTest",
    "tkinter",
]


def make_icon():
    image = Image.open(ROOT / "asset" / "logo.png").convert("RGBA")
    image.save(ICON, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def build():
    make_icon()
    for folder in ("build", "dist"):
        shutil.rmtree(ROOT / folder, ignore_errors=True)

    separator = ";"
    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--windowed",
        "--name", "GOPILOT",
        "--icon", str(ICON),
        "--paths", str(ROOT / "app"),
        "--add-data", f"{ROOT / 'asset'}{separator}asset",
        "--add-data", f"{ROOT / 'GoPiliotsplashscreen.ui'}{separator}.",
        "--hidden-import", "GOPILOT",
        "--hidden-import", "watchdog.observers",
    ]
    for module in EXCLUDES:
        command += ["--exclude-module", module]
    command.append(str(ROOT / "app" / "splash.py"))
    subprocess.run(command, cwd=ROOT, check=True)

    shutil.make_archive(str(ROOT / "dist" / "GOPILOT-Windows"), "zip", ROOT / "dist", "GOPILOT")
    print("\nBuilt:", ROOT / "dist" / "GOPILOT" / "GOPILOT.exe")
    print("Portable zip:", ROOT / "dist" / "GOPILOT-Windows.zip")


if __name__ == "__main__":
    build()
