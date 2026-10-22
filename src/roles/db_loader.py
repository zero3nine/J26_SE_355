from __future__ import annotations

import json
import sqlite3

import pandas as pd

METHODS = ("lexical", "semantic")

OUTPUT_COLUMNS = [
    "job_id", "job_title_raw", "job_description",
    "lexical_skills", "semantic_skills",
    "country", "source_platform", "posting_date", "run_id",
]

def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None

def database_summary(conn: sqlite3.Connection) -> dict:
    """Headline counts shown at the top of the page."""
    if not _has_table(conn, "jobs"):
        return {"jobs": 0, "countries": 0, "sources": 0, "runs": 0, "mentions": 0}
    jobs, countries, sources = conn.execute(
        "SELECT COUNT(*), COUNT(DISTINCT NULLIF(TRIM(country), '')), "
        "COUNT(DISTINCT NULLIF(TRIM(source_platform), '')) FROM jobs"
    ).fetchone()
    runs = mentions = 0
    if _has_table(conn, "extracted_skills"):
        runs, mentions = conn.execute(
            "SELECT COUNT(DISTINCT run_id), COUNT(*) FROM extracted_skills"
        ).fetchone()
    return {
        "jobs": jobs, "countries": countries, "sources": sources,
        "runs": runs, "mentions": mentions,
    }

def list_extraction_runs(conn: sqlite3.Connection) -> pd.DataFrame:
    """Extraction runs that actually have saved skills, newest first."""
    columns = ["run_id", "started_at", "model_name", "semantic_threshold",
               "jobs_with_skills", "lexical_mentions", "semantic_mentions"]
    if not (_has_table(conn, "extracted_skills") and _has_table(conn, "extraction_runs")):
        return pd.DataFrame(columns=columns)
    rows = conn.execute(
        """
        SELECT r.run_id, r.started_at, r.model_name, r.semantic_threshold,
               COUNT(DISTINCT e.job_id) AS jobs_with_skills,
               SUM(CASE WHEN e.method = 'lexical'  THEN 1 ELSE 0 END) AS lexical_mentions,
               SUM(CASE WHEN e.method = 'semantic' THEN 1 ELSE 0 END) AS semantic_mentions
        FROM extraction_runs r
        JOIN extracted_skills e ON e.run_id = r.run_id
        GROUP BY r.run_id
        ORDER BY r.started_at DESC, r.run_id
        """
    ).fetchall()
    return pd.DataFrame([tuple(r) for r in rows], columns=columns)

def list_filter_values(conn: sqlite3.Connection, column: str) -> list[str]:
    """Distinct non-empty values of jobs.country or jobs.source_platform."""
    if column not in ("country", "source_platform"):
        raise ValueError(f"Cannot filter on {column!r}")
    if not _has_table(conn, "jobs"):
        return []
    rows = conn.execute(
        f"SELECT DISTINCT TRIM({column}) FROM jobs "
        f"WHERE {column} IS NOT NULL AND TRIM({column}) <> '' ORDER BY 1"
    ).fetchall()
    return [r[0] for r in rows]

def load_extracted_jobs(
    conn: sqlite3.Connection,
    run_id: str,
    countries: list[str] | None = None,
    sources: list[str] | None = None,
    include_jobs_without_skills: bool = False,
) -> pd.DataFrame:
    if not (_has_table(conn, "jobs") and _has_table(conn, "extracted_skills")):
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    filters, params = [], []
    if countries:
        filters.append(f"TRIM(j.country) IN ({','.join('?' * len(countries))})")
        params += list(countries)
    if sources:
        filters.append(f"TRIM(j.source_platform) IN ({','.join('?' * len(sources))})")
        params += list(sources)
    where = (" AND " + " AND ".join(filters)) if filters else ""

    jobs_sql = f"""
        SELECT j.job_id, j.job_title, j.job_description, j.country,
               j.source_platform, j.posting_date
        FROM jobs j
        WHERE (
            EXISTS (SELECT 1 FROM extracted_skills e
                    WHERE e.job_id = j.job_id AND e.run_id = ?)
            {"OR j.first_seen_at <= (SELECT started_at FROM extraction_runs WHERE run_id = ?)"
             if include_jobs_without_skills else ""}
        ){where}
        ORDER BY j.job_id
    """
    jobs_params = [run_id] + ([run_id] if include_jobs_without_skills else []) + params
    jobs = [tuple(r) for r in conn.execute(jobs_sql, jobs_params).fetchall()]

    skills: dict[tuple[str, str], set[str]] = {}
    for job_id, method, name in conn.execute(
        "SELECT job_id, method, skill_name FROM extracted_skills WHERE run_id = ?",
        (run_id,),
    ).fetchall():
        name = (name or "").strip()
        if name:
            skills.setdefault((job_id, method), set()).add(name)

    records = []
    for job_id, title, description, country, source, posting_date in jobs:
        record = {
            "job_id": job_id,
            "job_title_raw": title or "",
            "job_description": description or "",
            "country": country or "",
            "source_platform": source or "",
            "posting_date": posting_date or "",
            "run_id": run_id,
        }
        for method in METHODS:
            record[f"{method}_skills"] = json.dumps(
                sorted(skills.get((job_id, method), set())), ensure_ascii=False
            )
        records.append(record)

    return pd.DataFrame(records, columns=OUTPUT_COLUMNS)