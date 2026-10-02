"""Local-only SQLite store for exercising the community board with dev_server.py."""
import sqlite3
import time
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "local_medisave.sqlite3"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute(
        """CREATE TABLE IF NOT EXISTS medicine_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine TEXT NOT NULL,
            strength TEXT NOT NULL DEFAULT '',
            city TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            display_name TEXT NOT NULL DEFAULT 'Local demo member',
            status TEXT NOT NULL DEFAULT 'open',
            created_at INTEGER NOT NULL
        )"""
    )
    return db


def list_requests(limit=30):
    with _connect() as db:
        rows = db.execute(
            "SELECT id, medicine, strength, city, notes, display_name, created_at "
            "FROM medicine_requests WHERE status = 'open' ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]


def add_request(payload):
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    medicine = str(payload.get("medicine", "")).strip()[:100]
    strength = str(payload.get("strength", "")).strip()[:40]
    city = str(payload.get("city", "")).strip()[:80]
    notes = str(payload.get("notes", "")).strip()[:500]
    if len(medicine) < 2:
        raise ValueError("Enter the medicine or active ingredient you need.")
    if not city:
        raise ValueError("Enter your city.")

    created_at = time.time_ns() // 1_000_000
    with _connect() as db:
        cursor = db.execute(
            "INSERT INTO medicine_requests "
            "(medicine, strength, city, notes, display_name, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'open', ?)",
            (medicine, strength, city, notes, "Local demo member", created_at),
        )
        request_id = cursor.lastrowid
    return {
        "id": str(request_id),
        "medicine": medicine,
        "strength": strength,
        "city": city,
        "notes": notes,
        "display_name": "Local demo member",
        "created_at": created_at,
    }
