"""SQLite connection and schema initialization."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from contextlib import contextmanager

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "master_jobs.sqlite3"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    target_path = Path(db_path) if db_path else DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def initialize_database(db_path: Path | str | None = None) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with database_connection(db_path=db_path) as conn:
        conn.executescript(schema)


@contextmanager
def database_connection(db_path: Path | str | None = None):
    conn = get_connection(db_path=db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
