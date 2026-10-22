import shutil
from pathlib import Path


# Find the current Windows user's home folder
HOME_FOLDER = Path.home()

# Production destinations: existing Windows folders
SORT_DESTINATIONS = {
    "picture": HOME_FOLDER / "Pictures",
    "video": HOME_FOLDER / "Videos",
    "audio": HOME_FOLDER / "Music",
    "document": HOME_FOLDER / "Documents",
    "text": HOME_FOLDER / "Documents",
    "archives": HOME_FOLDER / "Downloads" / "Archives",
    "unknown": HOME_FOLDER / "Downloads",
}
PRODUCTION_DESTINATIONS = dict(SORT_DESTINATIONS)
TEST_MODE = False
UNKNOWN_POLICY = "move"


def set_mode(test_mode, test_root=None):
    """Switch between production folders and a test destination root."""
    global TEST_MODE
    TEST_MODE = bool(test_mode)
    SORT_DESTINATIONS.clear()

    if TEST_MODE:
        root = Path(test_root)
        SORT_DESTINATIONS.update({
            "picture": root / "Pictures",
            "video": root / "Videos",
            "audio": root / "Music",
            "document": root / "Documents",
            "text": root / "Documents",
            "archives": root / "Archives",
            "unknown": root / "Unknown",
        })
    else:
        SORT_DESTINATIONS.update(PRODUCTION_DESTINATIONS)


def set_unknown_policy(policy):
    """Choose whether unknown file types are moved or left in place."""
    global UNKNOWN_POLICY
    if policy not in {"move", "keep"}:
        raise ValueError("Unknown-file policy must be 'move' or 'keep'.")
    UNKNOWN_POLICY = policy


def preview_file_destination(file_path, category):
    """Return the collision-safe destination that a move would use."""
    file_path = Path(file_path)
    destination = get_destination(file_path, category)
    if destination is None:
        return None

    if file_path.resolve() == destination.resolve():
        return destination

    original_name = destination.stem
    extension = destination.suffix
    counter = 1
    while destination.exists():
        destination = destination.with_name(f"{original_name} ({counter}){extension}")
        counter += 1
    return destination


def get_destination(file_path, category):
    """Return the destination folder for a file category."""

    destination_folder = SORT_DESTINATIONS.get(category)

    if destination_folder is None:
        print(f"[WARNING] Unknown category: {category}")
        return None

    return destination_folder / file_path.name


def show_destinations():
    """Display the currently active file destinations."""

    mode = "TEST" if TEST_MODE else "PRODUCTION"

    print(f"GOPILOT {mode} Destinations")
    print("-" * 35)

    for category, folder in SORT_DESTINATIONS.items():
        print(f"{category} -> {folder}")



def move_file(file_path, category):
    """Move a file safely without overwriting an existing file."""

    file_path = Path(file_path)

    if not file_path.is_file():
        print(f"[ERROR] File not found: {file_path}")
        return None

    if category == "unknown" and UNKNOWN_POLICY == "keep":
        return None

    destination = preview_file_destination(file_path, category)

    if destination is None:
        return None

    if file_path.resolve() == destination.resolve():
        print("[SKIPPED] File is already in its destination.")
        return destination

    # Create the destination folder if it doesn't exist.
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Avoid overwriting files with the same name.
    if destination.exists():
        original_name = destination.stem
        extension = destination.suffix
        counter = 1

        while destination.exists():
            new_name = f"{original_name} ({counter}){extension}"
            destination = destination.with_name(new_name)
            counter += 1

    try:
        shutil.move(str(file_path), str(destination))
        print(f"[MOVED] {file_path.name} -> {destination}")
        return destination

    except OSError as error:
        print(f"[ERROR] Could not move {file_path.name}: {error}")
        return None


if __name__ == "__main__":
    show_destinations()

    