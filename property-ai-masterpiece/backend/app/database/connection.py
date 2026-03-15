"""SQLite database connection and helpers."""

import sqlite3
import os
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.getenv("DATABASE_PATH", "backend/app/database/property_ai.db")


def _init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    schema = Path(__file__).parent / "schema.sql"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if schema.exists():
        conn.executescript(schema.read_text())
        conn.commit()
    conn.close()


_init_db()


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetchall(query: str, params: tuple = ()):
    with get_db() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def fetchone(query: str, params: tuple = ()):
    with get_db() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def execute(query: str, params: tuple = ()):
    with get_db() as conn:
        cur = conn.execute(query, params)
        return cur.lastrowid
