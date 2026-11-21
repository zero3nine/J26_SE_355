"""Read the explicit completed cohort of a saved extraction run."""

from __future__ import annotations

import hashlib
import json
import sqlite3

import pandas as pd

from src.database.provenance import job_provenance
from src.extraction.input_text import build_extraction_text


def list_matched_extraction_runs(conn: sqlite3.Connection) -> pd.DataFrame:
    """List runs with recorded lexical and semantic completion for each cohort member."""
    columns = ["run_id", "started_at", "completed_at", "model_name", "semantic_threshold", "job_count", "data_provenance"]
    if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='extraction_run_jobs'"
    ).fetchone() is None:
        return pd.DataFrame(columns=columns)

    job_columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    declaration = "j.data_provenance" if "data_provenance" in job_columns else "NULL"
    runs = {}
    for run_id, started, completed, model, threshold, source_url, declared in conn.execute(
        f"""SELECT r.run_id, r.started_at, r.completed_at, r.model_name, r.semantic_threshold,
                   j.source_url, {declaration}
            FROM extraction_run_jobs i
            JOIN extraction_runs r ON r.run_id = i.run_id
            LEFT JOIN jobs j ON j.job_id = i.job_id
            WHERE r.completed_at IS NOT NULL AND i.lexical_completed = 1 AND i.semantic_completed = 1
            ORDER BY r.started_at DESC, r.run_id"""
    ):
        run = runs.setdefault(run_id, dict(zip(columns, (run_id, started, completed, model, threshold, 0, set()))))
        run["job_count"] += 1
        run["data_provenance"].add(job_provenance({"source_url": source_url, "data_provenance": declared}))
    for run in runs.values():
        provenance = run["data_provenance"]
        run["data_provenance"] = provenance.pop() if len(provenance) == 1 else "mixed"
    return pd.DataFrame(runs.values(), columns=columns)


def research_run_options(runs: pd.DataFrame) -> dict[str, str]:
    """List explicitly labeled demonstration and mixed scopes after research defaults."""
    labels = {}
    other = {}
    for run in runs.itertuples(index=False):
        scope = getattr(run, "data_provenance", "unreviewed")
        target = other if scope in {"synthetic", "mixed"} else labels
        target[run.run_id] = f"{run.started_at[:10]} · {run.job_count:,} jobs · {scope} · {run.run_id[:8]}"
    return {**labels, "legacy": "Legacy data (unverified cohort)", **other}


def get_matched_extraction_dataset(
    conn: sqlite3.Connection,
    run_id: str,
    *,
    job_ids: set[str] | None = None,
    require_canonical: bool = False,
) -> pd.DataFrame:
    """Return the recorded cohort or a verified subset, including zero-mention jobs."""
    if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='extraction_run_jobs'"
    ).fetchone() is None:
        raise ValueError("This database has no recorded matched extraction cohorts.")

    cursor = conn.cursor()
    cursor.row_factory = sqlite3.Row
    rows = cursor.execute(
        """SELECT j.*, i.job_id AS saved_job_id, i.job_content_hash AS saved_content_hash,
                  i.input_sha256 AS saved_input_sha256, e.method AS saved_method,
                  COALESCE(s.canonical_name, e.skill_name) AS saved_skill,
                  s.canonical_name AS saved_canonical_name
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
        if job_ids is not None and job_id not in job_ids:
            continue
        expected_hash = job.pop("saved_content_hash")
        expected_input_hash = job.pop("saved_input_sha256")
        method = job.pop("saved_method")
        skill = job.pop("saved_skill")
        canonical_name = job.pop("saved_canonical_name")
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
                data_provenance=job_provenance(job),
            )
            jobs[job_id] = job
        if method in ("lexical", "semantic"):
            if require_canonical and not canonical_name:
                raise ValueError("The cohort has unmapped skill mentions. Review the taxonomy before publication.")
            if skill:
                jobs[job_id][f"{method}_skills"].add(skill)

    if job_ids is not None and job_ids.difference(jobs):
        raise ValueError("Some reviewed jobs were not completed by both methods in the selected extraction run.")
    if not jobs:
        raise ValueError(f"Run {run_id!r} has no recorded matched extraction cohort.")

    for job in jobs.values():
        for column in ("lexical_skills", "semantic_skills"):
            job[column] = json.dumps(sorted(job[column]), ensure_ascii=False)
    return pd.DataFrame(jobs.values())
