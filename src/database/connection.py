"""SQLite connection and schema initialization."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from contextlib import contextmanager

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "master_jobs.sqlite3"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def initialize_database() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
        # Migrate any new columns to existing jobs table if needed
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        new_job_columns = [
            ("work_mode", "TEXT"),
            ("salary_disclosed", "INTEGER DEFAULT 0"),
            ("salary_text_raw", "TEXT"),
            ("salary_type", "TEXT"),
            ("salary_min_normalized", "REAL"),
            ("salary_max_normalized", "REAL"),
            ("salary_currency_normalized", "TEXT"),
            ("salary_period_normalized", "TEXT"),
            ("salary_normalization_status", "TEXT"),
            ("salary_normalization_method", "TEXT"),
            ("classification_status", "TEXT DEFAULT 'it'"),
            ("is_benchmark_verified", "INTEGER DEFAULT 0"),
            ("source_validation_status", "TEXT"),
            ("role_id", "TEXT"),
            ("role_name", "TEXT"),
        ]
        for col_name, col_type in new_job_columns:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_benchmark_verified ON jobs(is_benchmark_verified)")

        # Migrate version columns if needed
        version_cols = {row["name"] for row in conn.execute("PRAGMA table_info(job_versions)").fetchall()}
        new_version_columns = [
            ("work_mode", "TEXT"),
            ("salary_disclosed", "INTEGER DEFAULT 0"),
            ("salary_min_normalized", "REAL"),
            ("salary_max_normalized", "REAL"),
            ("salary_currency_normalized", "TEXT"),
        ]
        for col_name, col_type in new_version_columns:
            if col_name not in version_cols:
                conn.execute(f"ALTER TABLE job_versions ADD COLUMN {col_name} {col_type}")

        # Ensure benchmark_jobs does not have UNIQUE(source_url)
        bm_table_sql = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='benchmark_jobs'").fetchone()
        if bm_table_sql and "UNIQUE(source_url)" in bm_table_sql[0]:
            conn.execute("ALTER TABLE benchmark_jobs RENAME TO benchmark_jobs_legacy")
            conn.executescript(schema)
            conn.execute("INSERT OR REPLACE INTO benchmark_jobs SELECT * FROM benchmark_jobs_legacy")
            conn.execute("DROP TABLE benchmark_jobs_legacy")


@contextmanager
def database_connection():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
