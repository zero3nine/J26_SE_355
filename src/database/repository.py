"""Repository functions for importing jobs and reading master-dataset data."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .connection import database_connection, initialize_database


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def as_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    value = str(value).strip()
    return value if value and value.lower() not in {"nan", "none", "nat"} else None


def first_value(row: dict, *keys: str) -> str | None:
    for key in keys:
        if key in row:
            value = as_text(row[key])
            if value:
                return value
    return None


def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    return url.strip().rstrip("/")


def job_payload(row: dict) -> dict:
    source_url = canonical_url(first_value(row, "source_url", "job_url", "url"))
    title = first_value(row, "job_title", "job_title_raw", "title")
    company = first_value(row, "company_name", "company", "company_raw", "employer")
    description = first_value(
        row, "job_description", "job_description_clean",
        "description", "job_description_raw"
    )
    platform = first_value(row, "source_platform", "source_hostname", "source")
    hostname = first_value(row, "source_hostname")
    location = first_value(row, "location", "location_raw")
    country = first_value(row, "country", "country_normalized", "country_raw")
    posting_date = first_value(row, "posting_date", "date_posted", "posted_date")
    source_job_id = first_value(row, "job_id", "source_job_id")

    # Hash only normalized job content, not transient scraping metadata.
    hash_content = json.dumps(
        {
            "url": source_url,
            "title": title,
            "company": company,
            "location": location,
            "country": country,
            "posting_date": posting_date,
            "description": description,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    content_hash = hashlib.sha256(hash_content.encode("utf-8")).hexdigest()
    job_id = source_job_id or hashlib.sha256(
        (source_url or content_hash).encode("utf-8")
    ).hexdigest()[:24]

    return {
        "job_id": job_id,
        "source_platform": platform,
        "source_hostname": hostname,
        "source_url": source_url,
        "job_title": title,
        "company_name": company,
        "location": location,
        "country": country,
        "posting_date": posting_date,
        "job_description": description,
        "content_hash": content_hash,
    }


def import_jobs_dataframe(df: pd.DataFrame, source_name: str = "streamlit_upload") -> dict:
    """Import cleaned jobs idempotently, retaining changed versions."""
    if df is None or df.empty:
        return {
            "import_run_id": None, "input_rows": 0, "inserted_jobs": 0,
            "updated_jobs": 0, "skipped_duplicates": 0, "failed_rows": 0,
        }

    initialize_database()
    run_id = str(uuid.uuid4())
    now = utc_now()
    inserted = updated = skipped = failed = 0

    with database_connection() as conn:
        conn.execute(
            """INSERT INTO import_runs
               (import_run_id, source_name, started_at, input_rows, status)
               VALUES (?, ?, ?, ?, 'running')""",
            (run_id, source_name, now, len(df)),
        )

        for _, series in df.iterrows():
            try:
                payload = job_payload(series.to_dict())
                if not payload["source_url"]:
                    failed += 1
                    continue

                existing = conn.execute(
                    "SELECT job_id, content_hash FROM jobs WHERE source_url = ?",
                    (payload["source_url"],),
                ).fetchone()

                if existing is None:
                    # If a supplied job_id already belongs to a different URL,
                    # generate a deterministic ID from the URL to avoid collision.
                    collision = conn.execute(
                        "SELECT source_url FROM jobs WHERE job_id = ?",
                        (payload["job_id"],),
                    ).fetchone()
                    if collision and collision["source_url"] != payload["source_url"]:
                        payload["job_id"] = hashlib.sha256(
                            payload["source_url"].encode("utf-8")
                        ).hexdigest()[:24]

                    conn.execute(
                        """INSERT INTO jobs (
                            job_id, source_platform, source_hostname, source_url,
                            job_title, company_name, location, country, posting_date,
                            job_description, content_hash, first_seen_at, last_seen_at,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            payload["job_id"], payload["source_platform"],
                            payload["source_hostname"], payload["source_url"],
                            payload["job_title"], payload["company_name"],
                            payload["location"], payload["country"], payload["posting_date"],
                            payload["job_description"], payload["content_hash"],
                            now, now, now, now,
                        ),
                    )
                    conn.execute(
                        """INSERT OR IGNORE INTO job_versions (
                            job_id, content_hash, job_title, company_name, location,
                            country, posting_date, job_description, observed_at, import_run_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            payload["job_id"], payload["content_hash"],
                            payload["job_title"], payload["company_name"],
                            payload["location"], payload["country"], payload["posting_date"],
                            payload["job_description"], now, run_id,
                        ),
                    )
                    inserted += 1
                else:
                    if existing["content_hash"] == payload["content_hash"]:
                        conn.execute(
                            "UPDATE jobs SET last_seen_at = ?, updated_at = ? WHERE job_id = ?",
                            (now, now, existing["job_id"]),
                        )
                        skipped += 1
                        continue

                    job_id = existing["job_id"]
                    conn.execute(
                        """UPDATE jobs SET
                            source_platform = ?, source_hostname = ?, job_title = ?,
                            company_name = ?, location = ?, country = ?, posting_date = ?,
                            job_description = ?, content_hash = ?, last_seen_at = ?,
                            updated_at = ?
                           WHERE job_id = ?""",
                        (
                            payload["source_platform"], payload["source_hostname"],
                            payload["job_title"], payload["company_name"], payload["location"],
                            payload["country"], payload["posting_date"], payload["job_description"],
                            payload["content_hash"], now, now, job_id,
                        ),
                    )
                    conn.execute(
                        """INSERT OR IGNORE INTO job_versions (
                            job_id, content_hash, job_title, company_name, location,
                            country, posting_date, job_description, observed_at, import_run_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            job_id, payload["content_hash"], payload["job_title"],
                            payload["company_name"], payload["location"], payload["country"],
                            payload["posting_date"], payload["job_description"], now, run_id,
                        ),
                    )
                    updated += 1
            except Exception:
                failed += 1

        conn.execute(
            """UPDATE import_runs SET completed_at = ?, inserted_jobs = ?,
               updated_jobs = ?, skipped_duplicates = ?, failed_rows = ?, status = ?
               WHERE import_run_id = ?""",
            (
                utc_now(), inserted, updated, skipped, failed,
                "completed" if failed == 0 else "completed_with_errors", run_id,
            ),
        )

    return {
        "import_run_id": run_id,
        "input_rows": len(df),
        "inserted_jobs": inserted,
        "updated_jobs": updated,
        "skipped_duplicates": skipped,
        "failed_rows": failed,
    }


def record_extraction_run(
    run_type: str,
    model_name: str | None = None,
    model_version: str | None = None,
    taxonomy_version: str | None = None,
    semantic_threshold: float | None = None,
    source_batch_id: str | None = None,
    notes: str | None = None,
) -> str:
    initialize_database()
    run_id = str(uuid.uuid4())
    with database_connection() as conn:
        conn.execute(
            """INSERT INTO extraction_runs (
                run_id, run_type, model_name, model_version, taxonomy_version,
                semantic_threshold, started_at, completed_at, source_batch_id, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, run_type, model_name, model_version, taxonomy_version,
                semantic_threshold, utc_now(), utc_now(), source_batch_id, notes,
            ),
        )
    return run_id


def store_extracted_skills(
    jobs_df: pd.DataFrame,
    run_id: str,
    method: str,
    skills_column: str,
) -> int:
    """Store skill lists from an extracted dataframe against existing master jobs."""
    initialize_database()
    saved = 0
    with database_connection() as conn:
        for _, series in jobs_df.iterrows():
            row = series.to_dict()
            source_url = canonical_url(first_value(row, "source_url", "job_url", "url"))
            if not source_url:
                continue
            job = conn.execute(
                "SELECT job_id FROM jobs WHERE source_url = ?", (source_url,)
            ).fetchone()
            if not job:
                continue

            raw_skills = row.get(skills_column, [])
            if isinstance(raw_skills, str):
                try:
                    parsed = json.loads(raw_skills)
                    raw_skills = parsed if isinstance(parsed, list) else []
                except json.JSONDecodeError:
                    raw_skills = [x.strip() for x in raw_skills.split(",") if x.strip()]
            if not isinstance(raw_skills, (list, tuple, set)):
                continue

            for skill in raw_skills:
                skill_name = as_text(skill)
                if not skill_name:
                    continue
                conn.execute(
                    """INSERT OR IGNORE INTO extracted_skills
                       (job_id, run_id, method, skill_name, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (job["job_id"], run_id, method, skill_name, utc_now()),
                )
                saved += 1
    return saved


def get_master_jobs() -> pd.DataFrame:
    initialize_database()
    with database_connection() as conn:
        return pd.read_sql_query(
            """SELECT j.*,
                      (SELECT COUNT(*) FROM job_versions v WHERE v.job_id = j.job_id) AS version_count,
                      (SELECT COUNT(DISTINCT es.run_id) FROM extracted_skills es WHERE es.job_id = j.job_id) AS extraction_run_count
               FROM jobs j
               ORDER BY j.last_seen_at DESC""",
            conn,
        )


def get_database_summary() -> dict:
    initialize_database()
    with database_connection() as conn:
        jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        versions = conn.execute("SELECT COUNT(*) FROM job_versions").fetchone()[0]
        skills = conn.execute("SELECT COUNT(*) FROM extracted_skills").fetchone()[0]
        runs = conn.execute("SELECT COUNT(*) FROM extraction_runs").fetchone()[0]
        imports = conn.execute("SELECT COUNT(*) FROM import_runs").fetchone()[0]
    return {
        "jobs": jobs, "versions": versions, "skill_mentions": skills,
        "extraction_runs": runs, "import_runs": imports,
    }
