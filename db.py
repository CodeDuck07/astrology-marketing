"""SQLite: учёт опубликованных фрагментов (без повторов)."""

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "posts.db"


class AllFragmentsPublishedError(Exception):
    """Все фрагменты из materials/ уже есть в базе опубликованных."""


def fragment_hash(source: str, fragment: str) -> str:
    payload = f"{source}\n{fragment}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS published (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT NOT NULL,
                fragment_hash TEXT NOT NULL UNIQUE,
                post_text TEXT NOT NULL,
                vk_post_id INTEGER,
                published_at TEXT NOT NULL,
                scheduled_for TEXT
            )
            """
        )
        try:
            conn.execute("ALTER TABLE published ADD COLUMN scheduled_for TEXT")
        except sqlite3.OperationalError:
            pass
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rotation (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_theme TEXT
            )
            """
        )


def get_last_theme() -> str | None:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT last_theme FROM rotation WHERE id = 1").fetchone()
    return row[0] if row else None


def set_last_theme(theme: str) -> None:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO rotation (id, last_theme) VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET last_theme = excluded.last_theme
            """,
            (theme,),
        )


def next_theme(themes: tuple[str, ...]) -> str:
    last = get_last_theme()
    if not last or last not in themes:
        return themes[0]
    idx = themes.index(last)
    return themes[(idx + 1) % len(themes)]


def get_published_hashes() -> set[str]:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT fragment_hash FROM published").fetchall()
    return {row[0] for row in rows}


def save_publication(
    source: str,
    fragment: str,
    post_text: str,
    vk_post_id: int | None = None,
    scheduled_for: str | None = None,
) -> None:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO published (source_file, fragment_hash, post_text, vk_post_id, published_at, scheduled_for)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                fragment_hash(source, fragment),
                post_text,
                vk_post_id,
                now,
                scheduled_for,
            ),
        )
