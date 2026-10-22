from pathlib import Path
from threading import Lock
import time
import organized

try:
    from watchdog.observers import Observer  # type: ignore[import]
    from watchdog.events import FileSystemEventHandler  # type: ignore[import]
except ImportError:
    Observer = None

    class FileSystemEventHandler:  # type: ignore[no-redef]
        """Fallback base class when watchdog is missing."""

# Monitor folder
WATCH_FOLDER = Path.home() / "Downloads"
# Set to keep track of seen files to avoid duplicate processing
SEEN_FILES = set()
SEEN_FILES_LOCK = Lock()
# List of file types to monitor
FILES_TYPES = {
    "text": {".txt", ".md", ".log", ".csv"},
    "document": {".pdf", ".docx", ".doc", ".xlsx", ".pptx"},  # Fixed .xslx -> .xlsx
    "video": {".mp4", ".mkv", ".avi", ".mov", ".webm"},
    "picture": {".jpg", ".jpeg", ".png", ".gif", ".ico"},     # Removed duplicate .webm
    "audio": {".mp3", ".mkv", ".aac", ".flac", ".m4a", ".ogg"},
    "archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
}


def identify_file_type(file_path: Path) -> str:
    extension = file_path.suffix.lower()
    for category, extensions in FILES_TYPES.items():
        if extension in extensions:
            return category
    return "unknown"
# Function to identify the type of a file based on its extension
def mark_file_seen(file_path):
    file_key = str(file_path.resolve()).casefold()

    with SEEN_FILES_LOCK:
        if file_key in SEEN_FILES:
            return False

        SEEN_FILES.add(file_key)
        return True


def unmark_file_seen(file_path):
    file_key = str(Path(file_path).resolve()).casefold()
    with SEEN_FILES_LOCK:
        SEEN_FILES.discard(file_key)
#function for handling file type identification
def is_file_ready(file_path, checks=3, delay=1):
    if not file_path.exists():
        return False

    previous_size = -1

    for _ in range(checks):
        current_size = file_path.stat().st_size

        if current_size == previous_size:
            return True

        previous_size = current_size
        time.sleep(delay)

    return False
# to check if a file is read and ready for processing
def wait_for_file_ready(file_path, attempts=10, delay=1):
    for attempt in range(attempts):
        if is_file_ready(file_path, checks=2, delay=1):
            return True

        time.sleep(delay)

    return False
#folder monitoring class
def _noop(event):
    pass


def process_file(file_path, label, callback=_noop, preview_only=False):
    """Identify, move and report one file. Every call ends in a terminal event."""
    file_path = Path(file_path)
    name = file_path.name
    callback({"status": "pending", "filename": name})

    if not wait_for_file_ready(file_path):
        print(f"\n[FILE NOT READY] {name}")
        callback({"status": "not_ready", "filename": name, "source": str(file_path),
                  "detail": "File was not ready (still changing or missing)"})
        return

    if not mark_file_seen(file_path):
        callback({"status": "ignored", "filename": name})
        return

    category = identify_file_type(file_path)
    extension = file_path.suffix.lower() or "[no extension]"

    print(f"\n[{label}] {name}")
    print(f"[EXTENSION] {extension}")
    print(f"[TYPE] {category}")

    if category == "unknown" and organized.UNKNOWN_POLICY == "keep":
        unmark_file_seen(file_path)
        callback({
            "status": "kept",
            "filename": name,
            "extension": extension,
            "category": category,
            "source": str(file_path),
            "detail": "Unknown file types are configured to stay in the watched folder",
        })
        return

    if preview_only:
        destination = organized.preview_file_destination(file_path, category)
        unmark_file_seen(file_path)
        if destination is None:
            callback({
                "status": "error", "filename": name, "extension": extension,
                "category": category, "source": str(file_path),
                "detail": "Could not determine the destination",
            })
        else:
            callback({
                "status": "preview", "filename": name, "extension": extension,
                "category": category, "source": str(file_path),
                "destination": str(destination),
                "detail": "Awaiting your approval before moving",
            })
        return

    destination = organized.move_file(file_path, category)
    moved = bool(destination) and not file_path.exists()
    if moved:
        with SEEN_FILES_LOCK:
            SEEN_FILES.discard(str(file_path.resolve()).casefold())

    if destination and not moved:
        status, detail = "skipped", "Already in its destination folder"
    elif moved:
        status, detail = "moved", f"{category} -> {destination}"
    else:
        status, detail = "error", "Could not move file"

    callback({
        "status": status,
        "filename": name,
        "extension": extension,
        "category": category,
        "source": str(file_path),
        "destination": str(destination) if destination else "",
        "detail": detail,
    })

#folder monitoring class
class FolderMonitor(FileSystemEventHandler):  # type: ignore[misc]
    def __init__(self, callback=_noop, preview_only=False):
        super().__init__()
        self.callback = callback
        self.preview_only = preview_only

    def on_created(self, event):
        if not event.is_directory:
            process_file(event.src_path, "FILE FOUND", self.callback, self.preview_only)

    def on_moved(self, event):
        if not event.is_directory:
            process_file(event.dest_path, "FILE MOVED OR RENAMED", self.callback, self.preview_only)


#function to scan existing files in the watch folder
def scan_existing_files(folder=None, callback=_noop, should_stop=lambda: False, preview_only=False):
    folder = Path(folder or WATCH_FOLDER)
    print("\nScanning existing files...")

    for file_path in list(folder.iterdir()):
        if should_stop():
            break
        if file_path.is_file():
            process_file(file_path, "EXISTING FILE", callback, preview_only)

    print("\nExisting file scan complete.")


def start_monitoring(folder, callback=_noop, preview_only=False):
    """Start a watchdog observer on folder and return it (call stop() and join())."""
    if Observer is None:
        raise RuntimeError("'watchdog' is not installed. Install it with: pip install watchdog")

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    observer = Observer()
    observer.schedule(FolderMonitor(callback, preview_only), str(folder), recursive=False)
    observer.start()
    return observer


def main():
    try:
        observer = start_monitoring(WATCH_FOLDER)
    except RuntimeError as error:
        print(f"Error: {error}")
        return

    print("GOPILOT is monitoring:", WATCH_FOLDER)

    scan_existing_files()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()
        print("\nGOPILOT monitoring stopped.")

    observer.join()


if __name__ == "__main__":
    main()
