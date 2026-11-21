"""Read the explicit completed cohort of a saved extraction run."""

from __future__ import annotations

import hashlib
import json
import sqlite3

import pandas as pd

from src.extraction.input_text import build_extraction_text


def list_matched_extraction_runs(conn: sqlite3.Connection) -> pd.DataFrame:
    """List runs with recorded lexical and semantic completion for each cohort member."""
    columns = ["run_id", "started_at", "completed_at", "model_name", "semantic_threshold", "job_count"]
    if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='extraction_run_jobs'"
    ).fetchone() is None:
        return pd.DataFrame(columns=columns)

    return pd.read_sql_query(
        """SELECT r.run_id, r.started_at, r.completed_at, r.model_name, r.semantic_threshold,
                  COUNT(*) AS job_count
           FROM extraction_runs r JOIN extraction_run_jobs i ON i.run_id = r.run_id
           WHERE r.completed_at IS NOT NULL AND i.lexical_completed = 1 AND i.semantic_completed = 1
           GROUP BY r.run_id
           ORDER BY r.started_at DESC, r.run_id""",
        conn,
    )


def get_matched_extraction_dataset(conn: sqlite3.Connection, run_id: str) -> pd.DataFrame:
    """Return matched inputs and mentions, including jobs with zero mentions in either method."""
    if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='extraction_run_jobs'"
    ).fetchone() is None:
        raise ValueError("This database has no recorded matched extraction cohorts.")

    cursor = conn.cursor()
    cursor.row_factory = sqlite3.Row
    rows = cursor.execute(
        """SELECT j.*, i.job_id AS saved_job_id, i.job_content_hash AS saved_content_hash,
                  i.input_sha256 AS saved_input_sha256, e.method AS saved_method,
                  COALESCE(s.canonical_name, e.skill_name) AS saved_skill
           FROM extraction_run_jobs i
           JOIN extraction_runs r ON r.run_id = i.run_id
           LEFT JOIN jobs j ON j.job_id = i.job_id
           LEFT JOIN extracted_skills e ON e.run_id = i.run_id AND e.job_id = i.job_id
           LEFT JOIN skills s ON s.skill_id = e.canonical_skill_id
           WHERE i.run_id = ? AND r.completed_at IS NOT NULL
                 AND i.lexical_completed = 1 AND i.semantic_completed = 1
           ORDER BY i.job_id""",
        (run_id,),
    )
    jobs = {}
    for row in rows:
        job = dict(row)
        job_id = job.pop("saved_job_id")
        expected_hash = job.pop("saved_content_hash")
        expected_input_hash = job.pop("saved_input_sha256")
        method = job.pop("saved_method")
        skill = job.pop("saved_skill")
        if job_id not in jobs:
            text, _ = build_extraction_text(job)
            if (
                job["job_id"] is None or expected_hash is None or expected_hash != job["content_hash"]
                or hashlib.sha256(text.encode("utf-8")).hexdigest() != expected_input_hash
            ):
                raise ValueError(
                    f"The saved inputs for run {run_id!r} no longer match the master dataset. "
                    "Choose another run or repeat the extraction."
                )
            job.update(
                job_title_raw=job["job_title"], company=job["company_name"], location_raw=job["location"],
                run_id=run_id, lexical_skills=set(), semantic_skills=set(),
            )
            jobs[job_id] = job
        if method in ("lexical", "semantic") and skill:
            jobs[job_id][f"{method}_skills"].add(skill)

    if not jobs:
        raise ValueError(f"Run {run_id!r} has no recorded matched extraction cohort.")

    for job in jobs.values():
        for column in ("lexical_skills", "semantic_skills"):
            job[column] = json.dumps(sorted(job[column]), ensure_ascii=False)
    return pd.DataFrame(jobs.values())
