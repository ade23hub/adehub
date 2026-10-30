# GOPILOT — Smart Windows File Organizer

GOPILOT watches a folder, identifies files by type and automatically sorts them into the
right destination folders. Built with Python, PySide6, Watchdog and SQLite.

**Developed by Durosinmi Sulaimon Adewunmi.**

## Features
- Automatic file organization by extension and category
- Folder monitoring that waits until a file has finished downloading
- Test mode (safe sandbox) and Production mode (real Windows folders)
- Optional review-before-moving with Approve / Skip, including a popup when hidden in the tray
- Undo, searchable activity log and CSV export
- Editable destinations and extension rules, saved between runs
- Background mode in the system tray with a safe stop

## Install
See **[INSTALL.md](INSTALL.md)** for the ready-made Windows app and for running from source.

## Project layout
| Path | Purpose |
|---|---|
| `app/splash.py` | Entry point (splash screen, then the main window) |
| `app/GOPILOT.py` | Main PySide6 window and dialogs |
| `app/monitor.py` | Watchdog folder monitor |
| `app/organized.py` | Destinations and file moving |
| `app/db.py` | SQLite settings and activity log |
| `build_exe.py` | Builds the Windows `.exe` with PyInstaller |
