import csv
import json
import shutil
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QByteArray, QObject, QSize, Qt, Signal, QDate, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QFont, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QFormLayout,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTextBrowser,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QDateEdit,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

import db
import monitor
import organized
import paths

APP_NAME = "GOPILOT"
PROJECT_ROOT = paths.data_dir()
TEST_FOLDER = (PROJECT_ROOT / "test").resolve()
TEST_DESTINATION_ROOT = (TEST_FOLDER / "organized").resolve()

ICON_DIR = paths.resource_dir() / "asset" / "icons"
LOGO_PATH = paths.resource_dir() / "asset" / "logo.png"

# (icon file, title, category, color)
DESTINATION_ITEMS = [
    ("picture", "Pictures", "picture", "#2698ff"),
    ("video", "Videos", "video", "#8b70ff"),
    ("audio", "Music", "audio", "#ffb545"),
    ("document", "Documents", "document", "#ff6868"),
    ("text", "Text", "text", "#27c7d9"),
    ("archives", "Archives", "archives", "#a0a8ff"),
    ("unknown", "Unknown", "unknown", "#83baff"),
]

NAV_ITEMS = [("Home", "home"), ("Settings", "settings"), ("Logs", "logs"), ("About", "about")]

ABOUT_MARKDOWN = """# About GOPILOT
**GOPILOT — Smart Windows File Organizer**

GOPILOT is a Windows desktop application developed by Durosinmi Sulaimon Adewunmi to make file management easier, safer, and more efficient.

GOPILOT monitors a selected folder, identifies incoming files by type, and organizes them into the appropriate destination folders. It can also scan files that already exist in the watched folder, wait for files to finish copying or downloading, and prevent accidental overwriting by choosing a different filename when necessary.

Designed with safety and flexibility in mind, GOPILOT includes a Test Mode for safe experimentation and a Production Mode for organizing files in real Windows folders. Users can optionally review files before they are moved, skip files they want to leave untouched, and undo recorded file moves.

Through its configurable settings, users can choose watched folders, customize destination paths, edit file-extension rules, and decide how unknown file types should be handled. GOPILOT also maintains an SQLite activity database, providing live statistics, searchable logs, status and date filters, and CSV export.

### Key Features

- Automatic file organization by category

- Folder monitoring and initial file scanning

- File-readiness checks before moving files

- Collision-safe file naming

- Test and Production modes

- Optional approval before moving files

- Undo support for recorded moves

- Custom folder destinations and extension rules

- Configurable handling of unknown file types

- Live activity statistics and SQLite records

- Searchable logs with CSV export

- System-tray operation and file-review notifications 

- Confirmation safeguards for important actions

### Developer
**Developed by Durosinmi Sulaimon Adewunmi**

GOPILOT is a software development project focused on practical desktop automation, productivity, and efficient file management.

### Technology
Python · PySide6 · Watchdog · SQLite

**GOPILOT — Organize your files. Automatically.**

Version 1.0
"""


def load_icon_pixmap(name, color, size=20):
    """Render an SVG from asset/icons, tinted with `color`, at 2x for sharp scaling."""
    svg = (ICON_DIR / f"{name}.svg").read_text(encoding="utf-8").replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return pixmap


def make_icon_label(name, color, size=20):
    label = QLabel()
    label.setPixmap(load_icon_pixmap(name, color, size))
    label.setFixedSize(size, size)
    label.setStyleSheet("background: transparent;")
    return label


class MonitorWorker(QObject):
    """Runs the folder monitor from monitor.py and forwards events to the GUI thread."""

    file_event = Signal(dict)

    def __init__(self, folder, preview_only=False):
        super().__init__()
        self.folder = Path(folder)
        self.preview_only = preview_only
        self.observer = None
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self.observer = monitor.start_monitoring(
            self.folder, self.file_event.emit, self.preview_only
        )
        self._thread = threading.Thread(target=self._scan, daemon=True)
        self._thread.start()

    def _scan(self):
        monitor.scan_existing_files(
            self.folder, self.file_event.emit, self._stop.is_set, self.preview_only
        )

    def stop(self):
        self._stop.set()
        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None


def make_label(text, size=10, color="#dce8ff", bold=False):
    label = QLabel(text)
    label.setFont(QFont("Segoe UI", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    label.setStyleSheet(f"color: {color}; background: transparent;")
    return label


def make_button(text, primary=False):
    button = QPushButton(text)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setMinimumHeight(40)
    if primary:
        button.setStyleSheet("""
            QPushButton {
                background: #087cf0; color: white; border: 1px solid #168cff;
                border-radius: 9px; padding: 9px 14px; font-weight: 600;
            }
            QPushButton:hover { background: #168cff; }
            QPushButton:pressed { background: #0668ca; }
            QPushButton:disabled { background: #263a55; color: #8294ad; }
        """)
    else:
        button.setStyleSheet("""
            QPushButton {
                background: #14243a; color: #e5efff; border: 1px solid #2c4565;
                border-radius: 9px; padding: 9px 14px; font-weight: 600;
            }
            QPushButton:hover { background: #1b304c; border-color: #4773a5; }
            QPushButton:pressed { background: #102035; }
        """)
    return button


def make_panel():
    panel = QFrame()
    panel.setObjectName("panel")
    panel.setFrameShape(QFrame.Shape.NoFrame)
    return panel


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GOPILOT Settings")
        self.setMinimumWidth(680)
        self.setStyleSheet("""
            QDialog { background: #0c1728; color: #e5efff; }
            QLabel { color: #dce8ff; }
            QLineEdit, QPlainTextEdit, QComboBox {
                background:#101f33; color:#e5efff; border:1px solid #2a4262;
                border-radius:6px; padding:7px;
            }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background:#0c1728; }
            QScrollBar:vertical { background:#0a1626; width:12px; margin:0; }
            QScrollBar::handle:vertical { background:#3a5a82; border-radius:6px; min-height:30px; }
            QScrollBar::handle:vertical:hover { background:#4d77a8; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """)
        body = QWidget()
        body.setObjectName("settingsBody")
        body.setStyleSheet("#settingsBody { background: #0c1728; }")
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 24, 24, 12)
        layout.setSpacing(12)
        self.resize(720, 700)
        title = make_label("Settings", 20, "#ffffff", True)
        layout.addWidget(title)
        self.watch_input = QLineEdit(
            str(parent.watch_folder) if parent is not None else ""
        )
        watch_row = QHBoxLayout()
        watch_row.addWidget(self.watch_input, 1)
        browse_watch = make_button("Browse")
        browse_watch.clicked.connect(
            lambda: self._browse_into(self.watch_input, "Choose watched folder")
        )
        watch_row.addWidget(browse_watch)
        form = QFormLayout()
        form.addRow("Watched folder", watch_row)

        self.destination_inputs = {}
        for _, title_text, category, _ in DESTINATION_ITEMS:
            path_input = QLineEdit(str(organized.SORT_DESTINATIONS.get(category, "")))
            browse = make_button("Browse")
            browse.clicked.connect(
                lambda checked=False, field=path_input, label=title_text:
                self._browse_into(field, f"Choose {label} destination")
            )
            row = QHBoxLayout()
            row.addWidget(path_input, 1)
            row.addWidget(browse)
            form.addRow(f"{title_text} folder", row)
            self.destination_inputs[category] = path_input
        layout.addLayout(form)

        layout.addWidget(make_label("File extension rules", 10, "#7f9abd", True))
        layout.addWidget(make_label(
            "One category per line, for example: text: .txt, .md", 9, "#91a9c9"
        ))
        self.rules_input = QPlainTextEdit()
        self.rules_input.setMaximumHeight(140)
        self.rules_input.setPlainText("\n".join(
            f"{category}: {', '.join(sorted(extensions))}"
            for category, extensions in monitor.FILES_TYPES.items()
        ))
        layout.addWidget(self.rules_input)

        options = QHBoxLayout()
        self.unknown_policy = QComboBox()
        self.unknown_policy.addItem("Move to the Unknown destination", "move")
        self.unknown_policy.addItem("Keep unknown files where they are", "keep")
        current_policy = db.get_setting("unknown_policy", "move")
        self.unknown_policy.setCurrentIndex(
            max(0, self.unknown_policy.findData(current_policy))
        )
        options.addWidget(make_label("Unknown file types:", 10, "#dce8ff", True))
        options.addWidget(self.unknown_policy, 1)
        layout.addLayout(options)

        self.require_approval = QCheckBox(
            "Preview each file and wait for my approval before moving it"
        )
        self.require_approval.setChecked(
            parent.preview_approval if parent is not None else False
        )
        self.require_approval.setStyleSheet("color:#dce8ff;")
        layout.addWidget(self.require_approval)
        layout.addWidget(make_label(
            f"Settings and activity are stored in {db.DB_PATH.name}. "
            "Stop monitoring to edit these settings.",
            9, "#91a9c9"
        ))

        inline_save = make_button("Save Changes", True)
        inline_save.clicked.connect(self.save)
        layout.addWidget(inline_save)

        footer = QFrame()
        footer.setStyleSheet("QFrame { background:#0a1626; border-top:1px solid #203550; }")
        footer_row = QHBoxLayout(footer)
        footer_row.setContentsMargins(24, 14, 24, 14)
        footer_row.addStretch()
        cancel_button = make_button("Cancel")
        cancel_button.setMinimumWidth(110)
        cancel_button.clicked.connect(self.reject)
        footer_row.addWidget(cancel_button)
        save_button = make_button("Save Changes", True)
        save_button.setMinimumWidth(150)
        save_button.setDefault(True)
        save_button.clicked.connect(self.save)
        footer_row.addWidget(save_button)
        outer.addWidget(footer)

    def _browse_into(self, line_edit, title):
        selected = QFileDialog.getExistingDirectory(
            self, title, line_edit.text()
        )
        if selected:
            line_edit.setText(selected)

    def save(self):
        raw_rules = self.rules_input.toPlainText()
        try:
            rules = {}
            for line_number, line in enumerate(raw_rules.splitlines(), 1):
                if not line.strip():
                    continue
                category, separator, extensions = line.partition(":")
                category = category.strip().lower()
                if not separator or category not in monitor.FILES_TYPES:
                    raise ValueError(f"Invalid category on line {line_number}.")
                parsed = {
                    item.strip().lower() if item.strip().startswith(".")
                    else f".{item.strip().lower()}"
                    for item in extensions.split(",") if item.strip()
                }
                if not parsed:
                    raise ValueError(f"No extensions listed on line {line_number}.")
                rules[category] = parsed
            missing = set(monitor.FILES_TYPES) - set(rules)
            if missing:
                raise ValueError(f"Add rules for: {', '.join(sorted(missing))}.")
            if any(not path.text().strip() for path in self.destination_inputs.values()):
                raise ValueError("Every category must have a destination folder.")
            if not self.watch_input.text().strip():
                raise ValueError("Choose a watched folder.")
        except ValueError as error:
            QMessageBox.warning(self, "Invalid settings", str(error))
            return

        data = {
            "watch_folder": Path(self.watch_input.text().strip()).expanduser(),
            "destinations": {
                category: Path(field.text().strip()).expanduser()
                for category, field in self.destination_inputs.items()
            },
            "rules": rules,
            "unknown_policy": self.unknown_policy.currentData(),
            "preview_approval": self.require_approval.isChecked(),
        }
        if self.parent().save_settings(data):
            self.accept()


class ApprovalPopup(QDialog):
    approved = Signal()
    skipped = Signal()

    def __init__(self, event):
        super().__init__(None)
        self.key = event["source"]
        self.setWindowTitle("GOPILOT — Review before moving")
        self.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint
        )
        self.setStyleSheet("QDialog { background:#0c1728; border:1px solid #2c4565; }")
        self.setFixedWidth(400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        layout.addWidget(make_label("Review before moving", 12, "#ffffff", True))
        layout.addWidget(make_label(event["filename"], 11, "#e5efff", True))
        details = make_label(
            f"Type: {event.get('category', '')}\nMove to: {event.get('destination', '')}",
            9, "#c3d4ec",
        )
        details.setWordWrap(True)
        layout.addWidget(details)
        row = QHBoxLayout()
        skip = make_button("Skip")
        skip.clicked.connect(self.skipped.emit)
        approve = make_button("Approve", True)
        approve.clicked.connect(self.approved.emit)
        row.addWidget(skip)
        row.addWidget(approve)
        layout.addLayout(row)

    def show_bottom_right(self):
        self.adjustSize()
        area = QApplication.primaryScreen().availableGeometry()
        self.move(area.right() - self.width() - 16, area.bottom() - self.height() - 16)
        self.show()
        self.raise_()


class GoPilotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GOPILOT — File Organizer")
        self.app_icon = QIcon(str(LOGO_PATH))
        self.setWindowIcon(self.app_icon)
        self.resize(1450, 900)
        self.setMinimumSize(1120, 720)
        self.monitoring = False
        self.worker = None
        self.pending_count = 0
        self.pending_previews = {}
        self.popup_queue = []
        self.approval_popup = None
        self._allow_close = False
        db.init_db()
        self.preview_approval = db.get_setting("preview_approval", "1") != "0"
        self.test_mode = db.get_setting("mode", "test") != "production"
        self.watch_folder = TEST_FOLDER
        self.apply_mode(self.test_mode)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(72)
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(24, 0, 24, 0)
        logo = make_label("➤", 30, "#168cff", True)
        brand = make_label("GOPILOT", 22, "#f3f7ff", True)
        top_layout.addWidget(logo)
        top_layout.addSpacing(8)
        top_layout.addWidget(brand)
        top_layout.addStretch()
        top_layout.addWidget(make_label("WINDOWS FILE ORGANIZER", 9, "#7f9abd", True))
        root.addWidget(topbar)

        # Body columns
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        root.addLayout(body, 1)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 28, 16, 18)
        side_layout.setSpacing(10)

        self.nav_buttons = {}
        self.nav_icon_names = dict(NAV_ITEMS)
        for name, _icon in NAV_ITEMS:
            button = QPushButton(f"  {name}")
            button.setIcon(self.nav_icon(name, name == "Home"))
            button.setIconSize(QSize(20, 20))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(48)
            button.setCheckable(True)
            button.setChecked(name == "Home")
            button.setStyleSheet(self.nav_style(name == "Home"))
            button.clicked.connect(lambda checked=False, n=name: self.navigate(n))
            self.nav_buttons[name] = button
            side_layout.addWidget(button)

        side_layout.addStretch()
        side_layout.addWidget(make_label("➤  GOPILOT", 11, "#e4edff", True))
        tagline = make_label("Organize your files.\nAutomatically.", 10, "#91a9c9")
        tagline.setWordWrap(True)
        side_layout.addWidget(tagline)
        body.addWidget(sidebar)

        # Scrollable central dashboard
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 28, 26, 28)
        content_layout.setSpacing(20)

        heading = make_label("Welcome to GOPILOT", 27, "#f4f7ff", True)
        content_layout.addWidget(heading)
        intro = make_label(
            "Your personal file organizer. GOPILOT watches for new files and\n"
            "helps move them into the right folders automatically.",
            12, "#9bb9df"
        )
        intro.setWordWrap(True)
        content_layout.addWidget(intro)

        # Monitoring status panel
        monitor_panel = make_panel()
        monitor_panel.setStyleSheet(
            "#panel { background:#0d1b2d; border:1px solid #087f68; "
            "border-left:4px solid #00c995; border-radius:12px; }"
        )
        monitor_layout = QHBoxLayout(monitor_panel)
        monitor_layout.setContentsMargins(22, 18, 20, 18)
        status_col = QVBoxLayout()
        status_row = QHBoxLayout()
        self.status_dot = make_label("●", 18, "#f4bc42", True)
        self.status_title = make_label("Monitoring Stopped", 15, "#f4bc42", True)
        status_row.addWidget(self.status_dot)
        status_row.addWidget(self.status_title)
        status_row.addStretch()
        status_col.addLayout(status_row)
        self.watch_label = make_label(f"Watching: {self.watch_folder}", 9, "#9bb9df")
        self.watch_label.setWordWrap(True)
        status_col.addWidget(self.watch_label)
        monitor_layout.addLayout(status_col, 1)
        self.monitor_button = make_button("▶  Start Monitoring", True)
        self.monitor_button.clicked.connect(self.toggle_monitoring)
        monitor_layout.addWidget(self.monitor_button)
        content_layout.addWidget(monitor_panel)

        # Statistics cards
        stats = QGridLayout()
        stats.setSpacing(12)
        self.stat_values = {}
        for index, (key, title, symbol, accent) in enumerate([
            ("processed", "Files Processed", "▣", "#2698ff"),
            ("moved", "Successfully Moved", "✓", "#16d6a1"),
            ("pending", "Pending", "◷", "#f4bc42"),
            ("errors", "Errors", "!", "#ff6868"),
        ]):
            card = make_panel()
            card.setStyleSheet(
                "#panel { background:#101f33; border:1px solid #2a4262; border-radius:12px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 15, 18, 15)
            icon = make_label(symbol, 20, accent, True)
            value = make_label("0", 24, "#f4f7ff", True)
            label = make_label(title, 9, "#9bb9df")
            card_layout.addWidget(icon)
            card_layout.addWidget(value)
            card_layout.addWidget(label)
            stats.addWidget(card, 0, index)
            self.stat_values[key] = value
        content_layout.addLayout(stats)

        preview_panel = make_panel()
        preview_panel.setStyleSheet(
            "#panel { background:#101f33; border:1px solid #856a2b; border-radius:12px; }"
        )
        self.preview_panel = preview_panel
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(18, 16, 18, 16)
        preview_header = QHBoxLayout()
        preview_header.addWidget(make_label("Review Before Moving", 14, "#f3f7ff", True))
        preview_header.addStretch()
        preview_header.addWidget(make_label("APPROVAL REQUIRED", 8, "#f4bc42", True))
        preview_layout.addLayout(preview_header)
        self.preview_table = QTableWidget(0, 3)
        self.preview_table.setHorizontalHeaderLabels(["File", "Category", "Proposed destination"])
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.preview_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.preview_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.preview_table.setMaximumHeight(150)
        preview_layout.addWidget(self.preview_table)
        preview_actions = QHBoxLayout()
        preview_actions.addStretch()
        self.approve_button = make_button("Move Selected", True)
        self.approve_button.clicked.connect(self.approve_selected)
        self.skip_button = make_button("Skip Selected")
        self.skip_button.clicked.connect(self.skip_selected)
        preview_actions.addWidget(self.approve_button)
        preview_actions.addWidget(self.skip_button)
        preview_layout.addLayout(preview_actions)
        content_layout.addWidget(preview_panel)

        # Recent activity
        activity_panel = make_panel()
        activity_panel.setStyleSheet(
            "#panel { background:#101f33; border:1px solid #2a4262; border-radius:12px; }"
        )
        activity_layout = QVBoxLayout(activity_panel)
        activity_layout.setContentsMargins(20, 18, 20, 18)
        activity_header = QHBoxLayout()
        activity_header.addWidget(make_label("Recent Activity", 15, "#f3f7ff", True))
        activity_header.addStretch()
        activity_header.addWidget(make_label("SAVED TO DATABASE", 8, "#49b8ff", True))
        activity_layout.addLayout(activity_header)
        self.activity_list = QVBoxLayout()
        self.activity_list.setSpacing(0)
        activity_layout.addLayout(self.activity_list)
        content_layout.addWidget(activity_panel)
        content_layout.addStretch()

        scroll.setWidget(content)
        body.addWidget(scroll, 1)

        # Right column
        right = QFrame()
        right.setObjectName("rightPanel")
        right.setFixedWidth(330)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(18, 18, 18, 22)
        right_layout.setSpacing(18)

        destinations_panel = make_panel()
        destinations_panel.setStyleSheet(
            "#panel { background:#0e1c2f; border:1px solid #253c5b; border-radius:12px; }"
        )
        destinations_layout = QVBoxLayout(destinations_panel)
        destinations_layout.setContentsMargins(18, 18, 18, 16)
        destinations_layout.setSpacing(12)
        destinations_layout.addWidget(make_label("▱  Folder Destinations", 14, "#f3f7ff", True))
        mode_row = QHBoxLayout()
        mode_row.addWidget(make_label("Current Mode", 10, "#c5d7ef"))
        mode_row.addStretch()
        self.mode_badge = make_label("TEST MODE", 9, "#39e6b0", True)
        mode_row.addWidget(self.mode_badge)
        destinations_layout.addLayout(mode_row)
        self.mode_desc = make_label("", 9, "#91a9c9")
        self.mode_desc.setWordWrap(True)
        destinations_layout.addWidget(self.mode_desc)

        self.destination_labels = {}
        for icon_name, title, category, color in DESTINATION_ITEMS:
            row = QHBoxLayout()
            badge = make_icon_label(icon_name, color, 22)
            row.addWidget(badge)
            row.addSpacing(6)
            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            text_col.addWidget(make_label(title, 11, "#ffffff", True))
            path_label = make_label("", 9, "#c3d4ec")
            path_label.setWordWrap(True)
            text_col.addWidget(path_label)
            self.destination_labels[category] = path_label
            row.addLayout(text_col, 1)
            row.addWidget(make_label("›", 18, "#91a9c9"))
            item = QVBoxLayout()
            item.setSpacing(8)
            item.addLayout(row)
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet("background:#203550; border:none;")
            item.addWidget(line)
            destinations_layout.addLayout(item)
        right_layout.addWidget(destinations_panel)

        actions_panel = make_panel()
        actions_panel.setStyleSheet(
            "#panel { background:#0e1c2f; border:1px solid #253c5b; border-radius:12px; }"
        )
        actions_layout = QVBoxLayout(actions_panel)
        actions_layout.setContentsMargins(18, 18, 18, 18)
        actions_layout.setSpacing(10)
        actions_layout.addWidget(make_label("ϟ  Quick Actions", 14, "#f3f7ff", True))
        open_test = make_button("▱  Open Watched Folder", True)
        open_test.clicked.connect(self.open_test_folder)
        actions_layout.addWidget(open_test)
        open_destination = make_button("▤  Open Destination Root")
        open_destination.clicked.connect(self.open_destination_root)
        actions_layout.addWidget(open_destination)
        hide_to_tray = make_button("◴  Hide to Tray")
        hide_to_tray.clicked.connect(self.hide)
        actions_layout.addWidget(hide_to_tray)
        settings_button = make_button("⚙  View Settings")
        settings_button.clicked.connect(self.show_settings)
        actions_layout.addWidget(settings_button)
        right_layout.addWidget(actions_panel)
        right_layout.addStretch()
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setFixedWidth(340)
        right_scroll.setWidget(right)
        body.addWidget(right_scroll)

        self.setStyleSheet("""
            QMainWindow, QWidget#central { background:#091424; }
            QFrame#topbar { background:#0b1728; border-bottom:1px solid #203550; }
            QFrame#sidebar { background:#0a1626; border-right:1px solid #203550; }
            QFrame#rightPanel { background:#0a1626; border-left:1px solid #203550; }
            QScrollArea { background:transparent; }
            QScrollBar:vertical { background:#0a1626; width:10px; margin:0; }
            QScrollBar::handle:vertical { background:#2a4262; border-radius:5px; min-height:24px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """)

        self.refresh_mode_ui()
        self.refresh_stats()
        self.load_history()
        self._setup_tray()

    def apply_mode(self, test_mode):
        self.test_mode = bool(test_mode)
        if test_mode:
            organized.set_mode(True, TEST_DESTINATION_ROOT)
        else:
            organized.set_mode(False)

        mode_key = "test" if self.test_mode else "production"
        default_watch = TEST_FOLDER if self.test_mode else monitor.WATCH_FOLDER
        self.watch_folder = Path(
            db.get_setting(f"watch_folder_{mode_key}", str(default_watch))
        ).expanduser()
        for category, default_path in organized.SORT_DESTINATIONS.items():
            configured = db.get_setting(
                f"destination_{mode_key}_{category}", str(default_path)
            )
            organized.SORT_DESTINATIONS[category] = Path(configured).expanduser()

        saved_rules = db.get_setting("file_type_rules")
        if saved_rules:
            try:
                configured_rules = json.loads(saved_rules)
                if set(configured_rules) == set(monitor.FILES_TYPES):
                    monitor.FILES_TYPES = {
                        category: {extension.lower() for extension in extensions}
                        for category, extensions in configured_rules.items()
                    }
            except (TypeError, ValueError, AttributeError):
                QMessageBox.warning(
                    self, "Invalid saved rules",
                    "Saved extension rules could not be loaded. Using the built-in defaults.",
                )
        organized.set_unknown_policy(db.get_setting("unknown_policy", "move"))
        db.set_setting("mode", "test" if test_mode else "production")

    def refresh_mode_ui(self):
        if self.test_mode:
            self.mode_badge.setText("TEST MODE")
            self.mode_badge.setStyleSheet(
                "background:#10372f; color:#39e6b0; padding:6px 9px; border-radius:7px;")
            self.mode_desc.setText("Files will be directed to GOPILOT's test folders during development.")
        else:
            self.mode_badge.setText("PRODUCTION")
            self.mode_badge.setStyleSheet(
                "background:#3a2d10; color:#f4bc42; padding:6px 9px; border-radius:7px;")
            self.mode_desc.setText("Files will be moved into your real Windows folders.")
        self.watch_label.setText(f"Watching: {self.watch_folder}")
        self.preview_panel.setVisible(self.preview_approval)
        for category, label in self.destination_labels.items():
            full_path = str(organized.SORT_DESTINATIONS.get(category, ""))
            # Zero-width spaces let long Windows paths wrap instead of being clipped
            label.setText(full_path.replace("\\", "\\\u200b").replace("/", "/\u200b"))
            label.setToolTip(full_path)

    def save_settings(self, settings):
        if self.monitoring:
            QMessageBox.warning(
                self, "Monitoring Active",
                "Stop monitoring before changing folder and sorting settings.",
            )
            return False

        watch_folder = settings["watch_folder"].resolve()
        if watch_folder.exists() and not watch_folder.is_dir():
            QMessageBox.warning(self, "Invalid watched folder", "The watched path is not a folder.")
            return False

        mode_key = "test" if self.test_mode else "production"
        db.set_setting(f"watch_folder_{mode_key}", str(watch_folder))
        for category, path in settings["destinations"].items():
            resolved_path = path.resolve()
            db.set_setting(f"destination_{mode_key}_{category}", str(resolved_path))
            organized.SORT_DESTINATIONS[category] = resolved_path

        monitor.FILES_TYPES = settings["rules"]
        db.set_setting("file_type_rules", json.dumps({
            category: sorted(extensions)
            for category, extensions in monitor.FILES_TYPES.items()
        }))
        organized.set_unknown_policy(settings["unknown_policy"])
        db.set_setting("unknown_policy", settings["unknown_policy"])
        self.preview_approval = settings["preview_approval"]
        db.set_setting("preview_approval", "1" if self.preview_approval else "0")
        self.watch_folder = watch_folder
        self.refresh_mode_ui()
        return True

    def request_mode_switch(self):
        if self.monitoring:
            return
        if self.test_mode:
            answer = QMessageBox.warning(
                self, "Production Mode",
                f"Production mode will watch {monitor.WATCH_FOLDER} and move your real files "
                "into Pictures, Videos, Music and Documents.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.apply_mode(not self.test_mode)
        self.refresh_mode_ui()

    def refresh_stats(self):
        stats = db.get_stats()
        self.stat_values["processed"].setText(str(stats["processed"]))
        self.stat_values["moved"].setText(str(stats["moved"]))
        self.stat_values["errors"].setText(str(stats["errors"]))
        self.stat_values["pending"].setText(str(max(self.pending_count, 0)))

    def load_history(self):
        rows = db.recent_activity(8)
        if not rows:
            self.show_empty_state()
            return
        for row in reversed(rows):
            self.add_activity(row["filename"], row["detail"] or "", row["status"].upper(), clear=False)

    def show_empty_state(self):
        empty = make_label("No activity yet. Start monitoring to begin.", 10, "#8299b8")
        empty.setContentsMargins(0, 18, 0, 10)
        empty.setProperty("empty", True)
        self.activity_list.addWidget(empty)

    def nav_style(self, selected):
        if selected:
            return """
                QPushButton { text-align:left; background:#087cf0; color:white;
                    border:1px solid #168cff; border-radius:9px; padding:10px 14px;
                    font-size:12px; font-weight:600; }
                QPushButton:hover { background:#168cff; }
            """
        return """
            QPushButton { text-align:left; background:transparent; color:#b8cbe5;
                border:1px solid transparent; border-radius:9px; padding:10px 14px;
                font-size:12px; }
            QPushButton:hover { background:#13243a; border-color:#253c5b; }
        """

    def nav_icon(self, name, selected):
        color = "#ffffff" if selected else "#b8cbe5"
        return QIcon(load_icon_pixmap(self.nav_icon_names[name], color))

    def navigate(self, name):
        for nav_name, button in self.nav_buttons.items():
            selected = nav_name == name
            button.setChecked(selected)
            button.setStyleSheet(self.nav_style(selected))
            button.setIcon(self.nav_icon(nav_name, selected))
        if name == "Settings":
            self.show_settings()
        elif name == "Logs":
            self.show_logs()
            self.navigate("Home")
        elif name == "About":
            self.show_about()
            self.navigate("Home")

    def show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("About GOPILOT")
        dialog.resize(620, 640)
        dialog.setStyleSheet("QDialog { background:#0c1728; }")
        layout = QVBoxLayout(dialog)
        viewer = QTextBrowser()
        viewer.setOpenExternalLinks(True)
        viewer.setStyleSheet(
            "QTextBrowser { background:#0c1728; color:#dce8ff; border:none; font-size:11pt; }"
        )
        viewer.setMarkdown(ABOUT_MARKDOWN)
        layout.addWidget(viewer)
        close_button = make_button("Close", True)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

    def show_logs(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("GOPILOT Activity Log")
        dialog.resize(1100, 620)
        dialog.setStyleSheet("QDialog { background:#0c1728; }")
        layout = QVBoxLayout(dialog)
        filters = QHBoxLayout()
        search = QLineEdit()
        search.setPlaceholderText("Search filename, status, category or details")
        status_box = QComboBox()
        status_box.addItem("All statuses", "")
        for status in ["moved", "preview", "skipped", "skipped_by_user", "kept", "error", "not_ready", "undone"]:
            status_box.addItem(status.upper(), status)
        from_date = QDateEdit()
        from_date.setCalendarPopup(True)
        from_date.setDate(QDate.currentDate().addDays(-30))
        to_date = QDateEdit()
        to_date.setCalendarPopup(True)
        to_date.setDate(QDate.currentDate())
        filters.addWidget(make_label("Search", 9, "#dce8ff", True))
        filters.addWidget(search, 1)
        filters.addWidget(make_label("Status", 9, "#dce8ff", True))
        filters.addWidget(status_box)
        filters.addWidget(make_label("From", 9, "#dce8ff", True))
        filters.addWidget(from_date)
        filters.addWidget(make_label("To", 9, "#dce8ff", True))
        filters.addWidget(to_date)
        layout.addLayout(filters)

        table = QTableWidget(0, 8)
        table.setHorizontalHeaderLabels([
            "ID", "Time", "Status", "File", "Category", "Source", "Destination", "Detail"
        ])
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet("background:#101f33; color:#dce8ff;")
        layout.addWidget(table, 1)

        actions = QHBoxLayout()
        export_button = make_button("Export CSV")
        undo_button = make_button("Undo Selected Move")
        actions.addWidget(export_button)
        actions.addWidget(undo_button)
        actions.addStretch()
        layout.addLayout(actions)

        rows = db.recent_activity(2000)

        def refresh_table():
            query = search.text().strip().lower()
            wanted_status = status_box.currentData()
            start = from_date.date().toString("yyyy-MM-dd")
            end = to_date.date().toString("yyyy-MM-dd")
            filtered = []
            for row in rows:
                row_date = row["ts"][:10]
                if row_date < start or row_date > end:
                    continue
                if wanted_status and row["status"] != wanted_status:
                    continue
                if query:
                    haystack = " ".join([
                        str(row.get("filename", "")),
                        str(row.get("status", "")),
                        str(row.get("category", "")),
                        str(row.get("detail", "")),
                    ]).lower()
                    if query not in haystack:
                        continue
                filtered.append(row)

            table.setRowCount(0)
            for row in filtered:
                index = table.rowCount()
                table.insertRow(index)
                values = [
                    str(row["id"]), row["ts"], row["status"].upper(), row["filename"],
                    row.get("category", ""), row.get("source", ""),
                    row.get("destination", ""), row.get("detail", ""),
                ]
                for col, value in enumerate(values):
                    table.setItem(index, col, QTableWidgetItem(value))

        def export_csv():
            file_path, _ = QFileDialog.getSaveFileName(
                dialog, "Export activity", str(Path.home() / "Documents" / "activity-log.csv"), "CSV Files (*.csv)"
            )
            if not file_path:
                return
            try:
                with open(file_path, "w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(
                        ["id", "ts", "filename", "extension", "category", "source", "destination", "status", "detail", "mode"]
                    )
                    for row in rows:
                        writer.writerow([
                            row["id"], row["ts"], row["filename"], row.get("extension", ""),
                            row.get("category", ""), row.get("source", ""), row.get("destination", ""),
                            row.get("status", ""), row.get("detail", ""), row.get("mode", ""),
                        ])
            except OSError as error:
                QMessageBox.warning(dialog, "Export failed", str(error))
                return
            QMessageBox.information(dialog, "Export complete", f"Saved: {file_path}")

        def undo_selected():
            selected = table.currentRow()
            if selected < 0:
                QMessageBox.information(dialog, "Undo move", "Select a moved file row first.")
                return
            activity_id = int(table.item(selected, 0).text())
            status = table.item(selected, 2).text().lower()
            source = table.item(selected, 5).text()
            destination_item = table.item(selected, 6)
            if destination_item is None:
                QMessageBox.warning(dialog, "Undo move", "Could not read the destination for the selected row.")
                return
            destination = destination_item.text()
            filename = table.item(selected, 3).text()
            if status != "moved":
                QMessageBox.warning(dialog, "Undo move", "Only rows with MOVED status can be undone.")
                return
            source_path = Path(source)
            destination_path = Path(destination)
            if not destination_path.exists():
                QMessageBox.warning(dialog, "Undo move", "Destination file no longer exists.")
                return
            if source_path.exists():
                QMessageBox.warning(dialog, "Undo move", "The original source file path already exists.")
                return
            source_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(destination_path), str(source_path))
            except OSError as error:
                QMessageBox.warning(dialog, "Undo move failed", str(error))
                return
            db.update_activity_status(activity_id, "undone", f"Moved back to {source_path}")
            self.add_activity(filename, f"Moved back to {source_path}", "UNDONE")
            self.refresh_stats()
            QMessageBox.information(dialog, "Undo move", "Move reverted successfully.")
            dialog.accept()
            self.show_logs()

        search.textChanged.connect(refresh_table)
        status_box.currentIndexChanged.connect(refresh_table)
        from_date.dateChanged.connect(refresh_table)
        to_date.dateChanged.connect(refresh_table)
        export_button.clicked.connect(export_csv)
        undo_button.clicked.connect(undo_selected)
        refresh_table()

        close = make_button("Close", True)
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def toggle_monitoring(self):
        if self.monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self):
        self.watch_folder.mkdir(parents=True, exist_ok=True)
        worker = MonitorWorker(self.watch_folder, self.preview_approval)
        worker.file_event.connect(self.handle_event)
        try:
            worker.start()
        except (RuntimeError, OSError) as error:
            QMessageBox.critical(self, "Cannot start monitoring", str(error))
            return
        self.worker = worker
        self.monitoring = True
        self.status_dot.setStyleSheet("color:#00d7a0; background:transparent;")
        self.status_title.setText("Monitoring Active")
        self.status_title.setStyleSheet("color:#00d7a0; background:transparent;")
        self.monitor_button.setText("■  Stop Monitoring")
        self.monitor_button.setStyleSheet("""
            QPushButton { background:#172941; color:#e5efff; border:1px solid #456080;
                border-radius:9px; padding:9px 14px; font-weight:600; }
            QPushButton:hover { background:#223b5a; }
        """)
        self.add_activity("Monitoring started", str(self.watch_folder), "STARTED")

    def stop_monitoring(self):
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
        self.monitoring = False
        self.pending_count = 0
        self.pending_previews.clear()
        self._close_popups()
        self.preview_table.setRowCount(0)
        self.status_dot.setStyleSheet("color:#f4bc42; background:transparent;")
        self.status_title.setText("Monitoring Stopped")
        self.status_title.setStyleSheet("color:#f4bc42; background:transparent;")
        self.monitor_button.setText("▶  Start Monitoring")
        self.monitor_button.setStyleSheet("")
        self.add_activity("Monitoring stopped", "", "STOPPED")
        self.refresh_stats()

    def handle_event(self, event):
        status = event["status"]
        if status == "pending":
            self.pending_count += 1
        else:
            self.pending_count = max(self.pending_count - 1, 0)
            if status == "preview":
                self._queue_preview(event)
            elif status != "ignored":
                db.log_activity(
                    event["filename"], status, event.get("detail", ""),
                    event.get("extension", ""), event.get("category", ""),
                    event.get("source", ""), event.get("destination", ""),
                    "test" if self.test_mode else "production",
                )
                self.add_activity(event["filename"], event.get("detail", ""), status.upper())
        self.refresh_stats()

    def closeEvent(self, event):
        if self.monitoring and not self._allow_close and self.tray_icon is not None:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "GOPILOT",
                "Monitoring is still running in the background. Use tray menu > Stop monitoring and exit.",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )
            return
        if self.worker is not None:
            self.worker.stop()
            self.worker = None
        self._close_popups()
        super().closeEvent(event)
        QApplication.quit()

    def add_activity(self, filename, detail, status, clear=True):
        # Drop the empty-state label and keep the list short.
        if clear and self.activity_list.count():
            first_item = self.activity_list.itemAt(0)
            first = first_item.widget() if first_item is not None else None
            if first is not None and first.property("empty"):
                self.activity_list.takeAt(0)
                first.deleteLater()
        while self.activity_list.count() >= 8:
            item = self.activity_list.takeAt(self.activity_list.count() - 1)
            if item.widget():
                item.widget().deleteLater()

        row = QFrame()
        row.setStyleSheet("QFrame { background:transparent; border-bottom:1px solid #203550; }")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.addWidget(make_label("●", 12, "#2698ff", True))
        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        text_col.addWidget(make_label(filename, 10, "#e5efff", True))
        detail_label = make_label(detail, 8, "#91a9c9")
        detail_label.setWordWrap(True)
        text_col.addWidget(detail_label)
        layout.addLayout(text_col, 1)
        bad = status in ("ERROR", "NOT_READY")
        status_label = make_label(status, 8, "#ff6868" if bad else "#39e6b0", True)
        status_label.setStyleSheet(
            "background:#3a1414; color:#ff6868; padding:5px 7px; border-radius:6px;" if bad
            else "background:#10372f; color:#39e6b0; padding:5px 7px; border-radius:6px;"
        )
        layout.addWidget(status_label)
        self.activity_list.insertWidget(0, row)

    def open_test_folder(self):
        self.watch_folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.watch_folder)))

    def open_destination_root(self):
        destinations = [Path(path) for path in organized.SORT_DESTINATIONS.values()]
        if not destinations:
            return
        try:
            root = Path(destinations[0])
            for path in destinations[1:]:
                while not str(path).startswith(str(root)):
                    root = root.parent
                    if root == root.parent:
                        root = destinations[0].parent
                        break
            destination = root if root.exists() else destinations[0].parent
        except (RuntimeError, OSError):
            destination = destinations[0].parent
        destination.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(destination)))

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.app_icon)
        menu = QMenu(self)
        show_action = QAction("Show GOPILOT", self)
        show_action.triggered.connect(self._restore_from_tray)
        menu.addAction(show_action)
        stop_action = QAction("Stop monitoring and exit", self)
        stop_action.triggered.connect(self._safe_stop_and_exit)
        menu.addAction(stop_action)
        exit_action = QAction("Exit now", self)
        exit_action.triggered.connect(self._force_exit)
        menu.addAction(exit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(
            lambda reason: self._restore_from_tray()
            if reason == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        self.tray_icon.show()

    def _restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _safe_stop_and_exit(self):
        if self.monitoring:
            answer = QMessageBox.question(
                self, "Stop monitoring and exit",
                "This will stop background monitoring and close GOPILOT.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.stop_monitoring()
        self._allow_close = True
        self.close()

    def _force_exit(self):
        if self.monitoring:
            QMessageBox.information(
                self, "Safety stop required",
                "Use 'Stop monitoring and exit' to safely stop background monitoring first.",
            )
            return
        self._allow_close = True
        self.close()

    def _queue_preview(self, event):
        key = event["source"]
        self.pending_previews[key] = event
        row = self.preview_table.rowCount()
        self.preview_table.insertRow(row)
        self.preview_table.setItem(row, 0, QTableWidgetItem(event["filename"]))
        self.preview_table.setItem(row, 1, QTableWidgetItem(event["category"]))
        self.preview_table.setItem(row, 2, QTableWidgetItem(event.get("destination", "")))
        self.preview_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, key)
        if not self.isVisible() or self.isMinimized():
            self._notify_pending_approval(event)

    def _notify_pending_approval(self, event):
        if self.tray_icon is not None:
            self.tray_icon.showMessage(
                "GOPILOT — Review before moving",
                f"{event['filename']} → {event.get('destination', '')}",
                QSystemTrayIcon.MessageIcon.Information,
                5000,
            )
        self.popup_queue.append(event["source"])
        self._show_next_popup()

    def _show_next_popup(self):
        if self.approval_popup is not None:
            return
        while self.popup_queue:
            key = self.popup_queue.pop(0)
            event = self.pending_previews.get(key)
            if event is None:
                continue
            popup = ApprovalPopup(event)
            popup.approved.connect(lambda k=key: self._popup_decision(k, True))
            popup.skipped.connect(lambda k=key: self._popup_decision(k, False))
            popup.show_bottom_right()
            self.approval_popup = popup
            return

    def _popup_decision(self, key, approve):
        popup, self.approval_popup = self.approval_popup, None
        if popup is not None:
            popup.close()
            popup.deleteLater()
        if approve:
            self._approve_key(key)
        else:
            self._skip_key(key)
        self.refresh_stats()
        self._show_next_popup()

    def _close_popups(self):
        self.popup_queue.clear()
        if self.approval_popup is not None:
            popup, self.approval_popup = self.approval_popup, None
            popup.close()
            popup.deleteLater()

    def _remove_preview_row(self, key):
        for row in range(self.preview_table.rowCount()):
            item = self.preview_table.item(row, 0)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == key:
                self.preview_table.removeRow(row)
                return

    def _approve_key(self, key):
        preview = self.pending_previews.pop(key, None)
        if preview is None:
            return
        self._remove_preview_row(key)
        monitor.process_file(preview["source"], "APPROVED FILE", self.handle_event, preview_only=False)

    def _skip_key(self, key):
        preview = self.pending_previews.pop(key, None)
        if preview is None:
            return
        self._remove_preview_row(key)
        db.log_activity(
            preview["filename"], "skipped_by_user", "Skipped from approval queue",
            preview.get("extension", ""), preview.get("category", ""),
            preview.get("source", ""), preview.get("destination", ""),
            "test" if self.test_mode else "production",
        )
        self.add_activity(preview["filename"], "Skipped from approval queue", "SKIPPED")

    def _selected_preview_keys(self):
        keys = []
        seen = set()
        for item in self.preview_table.selectedItems():
            row = item.row()
            key_item = self.preview_table.item(row, 0)
            if key_item is None:
                continue
            key = key_item.data(Qt.ItemDataRole.UserRole)
            if key and key not in seen:
                seen.add(key)
                keys.append((row, key))
        return sorted(keys, key=lambda pair: pair[0], reverse=True)

    def approve_selected(self):
        selected = self._selected_preview_keys()
        if not selected:
            QMessageBox.information(self, "Approve files", "Select one or more preview rows.")
            return
        for row, key in selected:
            if key == getattr(self.approval_popup, "key", None):
                self._popup_decision(key, True)
            else:
                self._approve_key(key)
        self.refresh_stats()

    def skip_selected(self):
        selected = self._selected_preview_keys()
        if not selected:
            QMessageBox.information(self, "Skip files", "Select one or more preview rows.")
            return
        for row, key in selected:
            if key == getattr(self.approval_popup, "key", None):
                self._popup_decision(key, False)
            else:
                self._skip_key(key)
        self.refresh_stats()


def main():
    paths.set_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Segoe UI", 10))
    window = GoPilotWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
