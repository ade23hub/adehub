import sqlite3
from contextlib import closing
from datetime import datetime

import paths

DB_PATH = paths.data_dir() / "gopilot.db"


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(_connect()) as conn, conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                filename TEXT NOT NULL,
                extension TEXT,
                category TEXT,
                source TEXT,
                destination TEXT,
                status TEXT NOT NULL,
                detail TEXT,
                mode TEXT
            )"""
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )


def get_setting(key, default=None):
    with closing(_connect()) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )


def log_activity(filename, status, detail="", extension="", category="",
                 source="", destination="", mode=""):
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO activity (ts, filename, extension, category, source, "
            "destination, status, detail, mode) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), filename, extension,
             category, source, destination, status, detail, mode),
        )


def recent_activity(limit=50):
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def update_activity_status(activity_id, status, detail=""):
    with closing(_connect()) as conn, conn:
        cursor = conn.execute(
            "UPDATE activity SET status = ?, detail = ? WHERE id = ?",
            (status, detail, activity_id),
        )
        return cursor.rowcount == 1


def get_stats():
    """Return lifetime totals: processed, moved, errors."""
    with closing(_connect()) as conn:
        rows = conn.execute("SELECT status, COUNT(*) AS n FROM activity GROUP BY status").fetchall()
    counts = {row["status"]: row["n"] for row in rows}
    return {
        "processed": sum(counts.values()),
        "moved": counts.get("moved", 0),
        "errors": counts.get("error", 0) + counts.get("not_ready", 0),
    }
