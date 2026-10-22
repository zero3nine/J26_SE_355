"""Repository functions for importing jobs, reading master data, and serving regional/validation analytics."""
from __future__ import annotations

import glob
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from .connection import database_connection, initialize_database, get_connection, DB_PATH
from src.cleaning.salary_normalizer import parse_and_normalize_salary


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_PATH = PROJECT_ROOT / "data" / "evaluation" / "benchmark_dataset.csv"
PILOT_PREDICTIONS_PATH = PROJECT_ROOT / "data" / "raw" / "all_pilot_crawled_predictions.csv"
SKILL_TAXONOMY_PATH = PROJECT_ROOT / "config" / "skill_taxonomy.json"
ROLE_TAXONOMY_PATH = PROJECT_ROOT / "config" / "role_taxonomy.json"
SOURCE_REGISTRY_PATH = PROJECT_ROOT / "config" / "source_registry.json"


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


def normalize_country_name(country_val: Any, platform: str = "") -> str:
    """Normalize raw country strings or platform indicators to canonical country names."""
    if country_val is not None and not pd.isna(country_val):
        c_str = str(country_val).strip()
        c_lower = c_str.lower()
        if c_lower in ("sri lanka", "lk", "sl", "srilanka"):
            return "Sri Lanka"
        if c_lower in ("india", "in", "ind"):
            return "India"
        if c_lower in ("singapore", "sg", "sgp"):
            return "Singapore"
        if c_lower in ("malaysia", "my", "mys"):
            return "Malaysia"

    plat_lower = str(platform or "").lower()
    if ".lk" in plat_lower or "topjobs" in plat_lower or "itpro" in plat_lower or "ikman" in plat_lower:
        return "Sri Lanka"
    if "shine.com" in plat_lower or "naukri" in plat_lower or "timesjobs" in plat_lower:
        return "India"
    if "mycareersfuture" in plat_lower or ".sg" in plat_lower:
        return "Singapore"
    if "jobstreet.com.my" in plat_lower or "my.jobstreet" in plat_lower or "hiredly" in plat_lower or ".my" in plat_lower:
        return "Malaysia"

    return "Unknown"


def _compute_monthly_equivalents(
    min_val: Optional[float],
    max_val: Optional[float],
    period: Optional[str],
    hours_per_month: float = 160.0,
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Converts annual, monthly, or hourly pay rates to standardized monthly amounts."""
    if min_val is None and max_val is None:
        return None, None, None

    per = str(period or "unspecified").lower()
    mult = 1.0
    if per == "monthly":
        mult = 1.0
    elif per == "annual":
        mult = 1.0 / 12.0
    elif per == "hourly":
        mult = float(hours_per_month)
    elif per == "daily":
        mult = float(hours_per_month) / 8.0
    else:
        return None, None, None

    min_m = round(min_val * mult, 2) if min_val is not None else None
    max_m = round(max_val * mult, 2) if max_val is not None else None

    if min_m is not None and max_m is not None:
        mid_m = round((min_m + max_m) / 2.0, 2)
    elif min_m is not None:
        mid_m = min_m
    else:
        mid_m = max_m

    return min_m, max_m, mid_m


def job_payload(row: dict) -> dict:
    source_url = canonical_url(first_value(row, "source_url", "job_url", "url"))
    title = first_value(row, "job_title", "job_title_raw", "title", "expected_job_title_raw")
    company = first_value(row, "company_name", "company", "company_raw", "employer", "expected_company_raw")
    description = first_value(
        row, "job_description", "job_description_clean",
        "description", "job_description_raw", "expected_description_snippet"
    )
    platform = first_value(row, "source_platform", "source_hostname", "source") or ""
    hostname = first_value(row, "source_hostname") or platform
    location = first_value(row, "location", "location_raw", "expected_location_raw")
    country_raw = first_value(row, "country", "country_normalized", "country_raw", "expected_country_normalized")
    country = normalize_country_name(country_raw, platform)
    posting_date = first_value(row, "posting_date", "date_posted", "posted_date", "posted_date_raw", "expected_posted_date")
    source_job_id = first_value(row, "job_id", "source_job_id", "benchmark_id")
    work_mode = first_value(row, "work_mode", "work_mode_raw", "expected_work_mode") or "unspecified"

    # Salary parsing & normalization
    sal_norm = parse_and_normalize_salary(
        salary_text_raw=str(first_value(row, "salary_text_raw", "expected_salary_text_raw") or ""),
        salary_min_raw=first_value(row, "salary_min_raw", "expected_salary_min", "salary_min_normalized"),
        salary_max_raw=first_value(row, "salary_max_raw", "expected_salary_max", "salary_max_normalized"),
        salary_currency_raw=str(first_value(row, "salary_currency_raw", "salary_currency_normalized", "expected_salary_currency") or ""),
        salary_period_raw=str(first_value(row, "salary_period_raw", "salary_period_normalized", "expected_salary_period") or ""),
        country_context=country,
    )

    raw_disclosed = row.get("salary_disclosed")
    if raw_disclosed is None:
        raw_disclosed = row.get("expected_salary_disclosed")
    if raw_disclosed is not None:
        if isinstance(raw_disclosed, str):
            sal_disclosed = raw_disclosed.strip().lower() in ("true", "1", "yes")
        else:
            sal_disclosed = bool(raw_disclosed)
    else:
        sal_disclosed = bool(sal_norm.get("salary_disclosed", False))

    s_min = sal_norm.get("salary_min_normalized")
    s_max = sal_norm.get("salary_max_normalized")
    s_curr = sal_norm.get("salary_currency_normalized") or ""
    s_period = sal_norm.get("salary_period_normalized") or "unspecified"
    s_type = sal_norm.get("salary_type", "undisclosed")
    s_status = sal_norm.get("salary_normalization_status", "undisclosed")
    s_method = sal_norm.get("salary_normalization_method", "not_applicable")

    if sal_disclosed and s_min is None:
        try:
            exp_min = first_value(row, "expected_salary_min", "salary_min_raw", "salary_min_normalized")
            exp_max = first_value(row, "expected_salary_max", "salary_max_raw", "salary_max_normalized")
            if exp_min or exp_max:
                s_min = float(exp_min) if exp_min else None
                s_max = float(exp_max) if exp_max else None
                s_curr = str(first_value(row, "expected_salary_currency", "salary_currency_raw") or "").strip()
                s_period = str(first_value(row, "expected_salary_period", "salary_period_raw") or "").strip() or "monthly"
        except Exception:
            pass

    class_status = str(first_value(row, "classification_status") or "it").lower()
    if class_status not in ("it", "non_it", "ambiguous"):
        class_status = "it"

    is_bm = 1 if (row.get("is_benchmark_verified") or row.get("benchmark_id") or str(source_job_id or "").startswith("bm_")) else 0
    source_val_status = first_value(row, "source_validation_status") or ("validated" if is_bm else "pilot_tested")

    role_id = first_value(row, "role_id")
    role_name = first_value(row, "role_name")

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
        "work_mode": work_mode,
        "salary_disclosed": 1 if sal_disclosed else 0,
        "salary_text_raw": sal_norm.get("salary_text_raw", ""),
        "salary_type": s_type,
        "salary_min_normalized": s_min,
        "salary_max_normalized": s_max,
        "salary_currency_normalized": s_curr,
        "salary_period_normalized": s_period,
        "salary_normalization_status": s_status,
        "salary_normalization_method": s_method,
        "classification_status": class_status,
        "is_benchmark_verified": is_bm,
        "source_validation_status": source_val_status,
        "role_id": role_id,
        "role_name": role_name,
    }


def import_jobs_dataframe(df: pd.DataFrame, source_name: str = "streamlit_upload") -> dict:
    """Import cleaned jobs idempotently, retaining changed versions and regional attributes."""
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
                            created_at, updated_at, work_mode, salary_disclosed,
                            salary_text_raw, salary_type, salary_min_normalized,
                            salary_max_normalized, salary_currency_normalized,
                            salary_period_normalized, salary_normalization_status,
                            salary_normalization_method, classification_status,
                            is_benchmark_verified, source_validation_status, role_id, role_name
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            payload["job_id"], payload["source_platform"],
                            payload["source_hostname"], payload["source_url"],
                            payload["job_title"], payload["company_name"],
                            payload["location"], payload["country"], payload["posting_date"],
                            payload["job_description"], payload["content_hash"],
                            now, now, now, now, payload["work_mode"], payload["salary_disclosed"],
                            payload["salary_text_raw"], payload["salary_type"],
                            payload["salary_min_normalized"], payload["salary_max_normalized"],
                            payload["salary_currency_normalized"], payload["salary_period_normalized"],
                            payload["salary_normalization_status"], payload["salary_normalization_method"],
                            payload["classification_status"], payload["is_benchmark_verified"],
                            payload["source_validation_status"], payload["role_id"], payload["role_name"],
                        ),
                    )
                    conn.execute(
                        """INSERT OR IGNORE INTO job_versions (
                            job_id, content_hash, job_title, company_name, location,
                            country, posting_date, job_description, observed_at, import_run_id,
                            work_mode, salary_disclosed, salary_min_normalized,
                            salary_max_normalized, salary_currency_normalized
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            payload["job_id"], payload["content_hash"],
                            payload["job_title"], payload["company_name"],
                            payload["location"], payload["country"], payload["posting_date"],
                            payload["job_description"], now, run_id,
                            payload["work_mode"], payload["salary_disclosed"],
                            payload["salary_min_normalized"], payload["salary_max_normalized"],
                            payload["salary_currency_normalized"],
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
                            updated_at = ?, work_mode = ?, salary_disclosed = ?,
                            salary_text_raw = ?, salary_type = ?, salary_min_normalized = ?,
                            salary_max_normalized = ?, salary_currency_normalized = ?,
                            salary_period_normalized = ?, salary_normalization_status = ?,
                            salary_normalization_method = ?, classification_status = ?,
                            is_benchmark_verified = ?, source_validation_status = ?,
                            role_id = ?, role_name = ?
                           WHERE job_id = ?""",
                        (
                            payload["source_platform"], payload["source_hostname"],
                            payload["job_title"], payload["company_name"], payload["location"],
                            payload["country"], payload["posting_date"], payload["job_description"],
                            payload["content_hash"], now, now, payload["work_mode"],
                            payload["salary_disclosed"], payload["salary_text_raw"],
                            payload["salary_type"], payload["salary_min_normalized"],
                            payload["salary_max_normalized"], payload["salary_currency_normalized"],
                            payload["salary_period_normalized"], payload["salary_normalization_status"],
                            payload["salary_normalization_method"], payload["classification_status"],
                            payload["is_benchmark_verified"], payload["source_validation_status"],
                            payload["role_id"], payload["role_name"], job_id,
                        ),
                    )
                    conn.execute(
                        """INSERT OR IGNORE INTO job_versions (
                            job_id, content_hash, job_title, company_name, location,
                            country, posting_date, job_description, observed_at, import_run_id,
                            work_mode, salary_disclosed, salary_min_normalized,
                            salary_max_normalized, salary_currency_normalized
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            job_id, payload["content_hash"], payload["job_title"],
                            payload["company_name"], payload["location"], payload["country"],
                            payload["posting_date"], payload["job_description"], now, run_id,
                            payload["work_mode"], payload["salary_disclosed"],
                            payload["salary_min_normalized"], payload["salary_max_normalized"],
                            payload["salary_currency_normalized"],
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
    """Fetch all master jobs with version count and extraction run count."""
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
    """Returns total counts across core entities in the master database."""
    initialize_database()
    with database_connection() as conn:
        jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        versions = conn.execute("SELECT COUNT(*) FROM job_versions").fetchone()[0]
        skills = conn.execute("SELECT COUNT(*) FROM extracted_skills").fetchone()[0]
        runs = conn.execute("SELECT COUNT(*) FROM extraction_runs").fetchone()[0]
        imports = conn.execute("SELECT COUNT(*) FROM import_runs").fetchone()[0]
        benchmarks = conn.execute("SELECT COUNT(*) FROM benchmark_jobs").fetchone()[0]
        eval_runs = conn.execute("SELECT COUNT(*) FROM evaluation_runs").fetchone()[0]
    return {
        "jobs": jobs,
        "versions": versions,
        "skill_mentions": skills,
        "extraction_runs": runs,
        "import_runs": imports,
        "benchmarks": benchmarks,
        "evaluation_runs": eval_runs,
    }


def import_benchmark_records(df_or_path: pd.DataFrame | str | Path | None = None) -> int:
    """Import benchmark dataset records into benchmark_jobs table and jobs table."""
    initialize_database()
    if df_or_path is None:
        if not BENCHMARK_PATH.exists():
            return 0
        df_bm = pd.read_csv(BENCHMARK_PATH)
    elif isinstance(df_or_path, (str, Path)):
        p = Path(df_or_path)
        if not p.exists():
            return 0
        df_bm = pd.read_csv(p)
    else:
        df_bm = df_or_path

    if df_bm.empty:
        return 0

    inserted = 0
    with database_connection() as conn:
        for _, row in df_bm.iterrows():
            d = row.to_dict()
            b_id = str(d.get("benchmark_id", "")).strip()
            s_url = canonical_url(d.get("source_url"))
            if not b_id or not s_url:
                continue

            cols = [
                "benchmark_id", "source_url", "source_platform", "country",
                "collection_context", "extraction_method", "expected_job_title_raw",
                "expected_company_raw", "expected_location_raw", "expected_country_normalized",
                "expected_city_normalized", "expected_work_mode", "expected_posted_date",
                "expected_closing_date", "expected_description_snippet", "expected_description_hash",
                "expected_description_min_len", "expected_salary_disclosed", "expected_salary_text_raw",
                "expected_salary_type", "expected_salary_min", "expected_salary_max",
                "expected_salary_currency", "expected_salary_period", "expected_skills",
                "status_job_title", "status_company", "status_location", "status_work_mode",
                "status_posted_date", "status_closing_date", "status_description",
                "status_salary", "status_skills", "verification_timestamp", "verified_by",
                "evidence_source", "reviewer_notes"
            ]
            valid_cols = [c for c in cols if c in d]
            placeholders = ", ".join(["?"] * len(valid_cols))
            col_str = ", ".join(valid_cols)
            vals = [d[c] for c in valid_cols]

            conn.execute(
                f"INSERT OR REPLACE INTO benchmark_jobs ({col_str}) VALUES ({placeholders})",
                vals,
            )
            inserted += 1

    return inserted


def get_benchmark_jobs(conn: Optional[sqlite3.Connection] = None) -> pd.DataFrame:
    """Retrieve all ground-truth benchmark records from the database."""
    initialize_database()
    if conn is not None:
        return pd.read_sql_query("SELECT * FROM benchmark_jobs ORDER BY benchmark_id", conn)
    with database_connection() as c:
        return pd.read_sql_query("SELECT * FROM benchmark_jobs ORDER BY benchmark_id", c)


def get_regional_jobs(
    conn: Optional[sqlite3.Connection] = None,
    allowed_countries: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Retrieve full harmonized dataset from master database ready for regional analysis.
    
    Returns a DataFrame conforming exactly to the 30-column regional specification.
    """
    initialize_database()

    def _query(c: sqlite3.Connection) -> pd.DataFrame:
        query = "SELECT * FROM jobs"
        params: list[Any] = []
        if allowed_countries:
            placeholders = ", ".join(["?"] * len(allowed_countries))
            query += f" WHERE country IN ({placeholders})"
            params.extend(allowed_countries)
        query += " ORDER BY country, last_seen_at DESC"

        jobs_rows = c.execute(query, params).fetchall()
        if not jobs_rows:
            return pd.DataFrame()

        # Build skill mentions map
        skills_map: dict[str, set[str]] = {}
        for r in c.execute("SELECT job_id, skill_name FROM extracted_skills").fetchall():
            skills_map.setdefault(str(r[0]), set()).add(str(r[1]))

        records = []
        for r in jobs_rows:
            d = dict(r)
            job_id = str(d["job_id"])
            c_status = str(d.get("classification_status") or "it").lower()
            is_it = c_status in ("it", "ambiguous")

            min_m, max_m, mid_m = _compute_monthly_equivalents(
                d.get("salary_min_normalized"),
                d.get("salary_max_normalized"),
                d.get("salary_period_normalized"),
            )

            rec = {
                "job_id": job_id,
                "source_url": str(d.get("source_url") or ""),
                "source_platform": str(d.get("source_platform") or ""),
                "country": str(d.get("country") or "Unknown"),
                "job_title_raw": str(d.get("job_title") or ""),
                "company": str(d.get("company_name") or ""),
                "location_raw": str(d.get("location") or ""),
                "work_mode": str(d.get("work_mode") or "unspecified"),
                "job_description": str(d.get("job_description") or ""),
                "is_it": is_it,
                "classification_status": c_status,
                "source_validation_status": str(d.get("source_validation_status") or "validated"),
                "is_benchmark_verified": bool(d.get("is_benchmark_verified")),
                "skills": sorted(skills_map.get(job_id, set())),
                "role_id": str(d.get("role_id") or "unclassified"),
                "role_name": str(d.get("role_name") or "Unclassified IT"),
                "salary_disclosed": bool(d.get("salary_disclosed")),
                "salary_text_raw": str(d.get("salary_text_raw") or ""),
                "salary_type": str(d.get("salary_type") or "undisclosed"),
                "salary_min_raw": str(d.get("salary_min_normalized") or ""),
                "salary_max_raw": str(d.get("salary_max_normalized") or ""),
                "salary_min_normalized": d.get("salary_min_normalized"),
                "salary_max_normalized": d.get("salary_max_normalized"),
                "salary_currency_normalized": str(d.get("salary_currency_normalized") or ""),
                "salary_period_normalized": str(d.get("salary_period_normalized") or "unspecified"),
                "salary_monthly_min": min_m,
                "salary_monthly_max": max_m,
                "salary_monthly_midpoint": mid_m,
                "salary_normalization_status": str(d.get("salary_normalization_status") or "undisclosed"),
                "salary_normalization_method": str(d.get("salary_normalization_method") or "not_applicable"),
            }
            records.append(rec)

        return pd.DataFrame(records)

    if conn is not None:
        return _query(conn)
    with database_connection() as c:
        return _query(c)


def save_evaluation_run(
    run_id: str,
    metrics: dict,
    errors_df: Optional[pd.DataFrame] = None,
    report_md: str = "",
    is_synthetic: bool = False,
    is_latest: bool = True,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """Stores an evaluation run and its field-level errors into the master database."""
    initialize_database()
    now = utc_now()
    meta = metrics.get("metadata", {})
    ts = meta.get("timestamp", now)
    total_bm = meta.get("total_benchmark_records", 0)
    matched = meta.get("matched_records_count", 0)
    em_rate = meta.get("exact_match_rate", 0.0)
    cov = meta.get("macro_coverage", 0.0)
    corr = meta.get("macro_correctness", 0.0)
    metrics_json = json.dumps(metrics, indent=2)

    def _execute(c: sqlite3.Connection):
        if is_latest:
            c.execute("UPDATE evaluation_runs SET is_latest = 0")

        c.execute(
            """INSERT OR REPLACE INTO evaluation_runs (
                run_id, is_latest, timestamp, total_benchmark, matched_records,
                exact_match_rate, macro_coverage, macro_correctness, is_synthetic,
                metrics_json, report_markdown, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, 1 if is_latest else 0, ts, total_bm, matched,
                em_rate, cov, corr, 1 if is_synthetic else 0,
                metrics_json, report_md, now
            ),
        )

        if errors_df is not None and not errors_df.empty:
            c.execute("DELETE FROM evaluation_errors WHERE run_id = ?", (run_id,))
            for _, r in errors_df.iterrows():
                c.execute(
                    """INSERT INTO evaluation_errors (
                        run_id, benchmark_id, field_name, country, source_platform,
                        extraction_method, expected_raw, expected_normalized, predicted_raw,
                        predicted_normalized, error_category, error_type, discrepancy_details,
                        source_url, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id, str(r.get("benchmark_id", "")), str(r.get("field_name", "")),
                        str(r.get("country", "")), str(r.get("source_platform", "")),
                        str(r.get("extraction_method", "")), str(r.get("expected_raw", "")),
                        str(r.get("expected_normalized", "")), str(r.get("predicted_raw", "")),
                        str(r.get("predicted_normalized", "")), str(r.get("error_category", "")),
                        str(r.get("error_type", "")), str(r.get("discrepancy_details", "")),
                        str(r.get("source_url", "")), now
                    ),
                )

    if conn is not None:
        _execute(conn)
    else:
        with database_connection() as c:
            _execute(c)


def get_evaluation_runs_from_db(conn: Optional[sqlite3.Connection] = None) -> list[dict]:
    """Retrieves all evaluation run summaries stored in SQLite."""
    initialize_database()

    def _get(c: sqlite3.Connection) -> list[dict]:
        rows = c.execute(
            """SELECT run_id, is_latest, timestamp, total_benchmark, matched_records,
                      exact_match_rate, macro_coverage, macro_correctness, is_synthetic
               FROM evaluation_runs
               ORDER BY is_latest DESC, created_at DESC"""
        ).fetchall()
        runs = []
        for r in rows:
            is_latest = bool(r["is_latest"])
            ts = r["timestamp"]
            tag = r["run_id"]
            is_syn = bool(r["is_synthetic"])
            label = f"Latest DB Run ({ts[:19]})" if is_latest else f"DB Run {tag} ({ts[:19]})"
            label += " [Synthetic Test]" if is_syn else " [Empirical Benchmark]"
            runs.append({
                "run_id": tag,
                "is_latest": is_latest,
                "label": label,
                "timestamp_iso": ts,
                "mtime": 0.0,
                "metrics_file": None,
                "total_benchmark": r["total_benchmark"],
                "matched_records": r["matched_records"],
                "exact_match_rate": (r["exact_match_rate"] or 0.0) * 100.0,
                "macro_coverage": (r["macro_coverage"] or 0.0) * 100.0,
                "macro_correctness": (r["macro_correctness"] or 0.0) * 100.0,
                "is_synthetic": is_syn,
                "from_database": True,
            })
        return runs

    if conn is not None:
        return _get(conn)
    with database_connection() as c:
        return _get(c)


def load_evaluation_run_data_from_db(
    run_id: str,
    conn: Optional[sqlite3.Connection] = None
) -> Optional[dict]:
    """Loads metrics, errors_df, and markdown report for an evaluation run from SQLite."""
    initialize_database()

    def _load(c: sqlite3.Connection) -> Optional[dict]:
        if run_id == "latest":
            row = c.execute("SELECT * FROM evaluation_runs WHERE is_latest = 1 ORDER BY created_at DESC LIMIT 1").fetchone()
            if not row:
                row = c.execute("SELECT * FROM evaluation_runs ORDER BY created_at DESC LIMIT 1").fetchone()
        else:
            row = c.execute("SELECT * FROM evaluation_runs WHERE run_id = ?", (run_id,)).fetchone()

        if not row:
            return None

        actual_run_id = row["run_id"]
        try:
            metrics = json.loads(row["metrics_json"])
        except Exception:
            metrics = {}

        err_rows = c.execute(
            "SELECT * FROM evaluation_errors WHERE run_id = ?", (actual_run_id,)
        ).fetchall()
        errors_df = pd.DataFrame([dict(r) for r in err_rows]) if err_rows else pd.DataFrame()

        return {
            "run_tag": actual_run_id,
            "is_synthetic": bool(row["is_synthetic"]),
            "metrics": metrics,
            "errors_df": errors_df,
            "summary_df": pd.DataFrame(),
            "report_md": row["report_markdown"] or "",
            "reproducibility": {},
            "metrics_file": f"sqlite://master_jobs.sqlite3/evaluation_runs/{actual_run_id}",
            "from_database": True,
        }

    if conn is not None:
        return _load(conn)
    with database_connection() as c:
        return _load(c)


def migrate_csv_data_to_master_db(force: bool = False) -> dict:
    """Comprehensive idempotent migration of all project CSV datasets into master_jobs.sqlite3.
    
    Migrates:
    - Benchmark ground-truth dataset (`data/evaluation/benchmark_dataset.csv`)
    - Crawled pilot predictions (`data/raw/all_pilot_crawled_predictions.csv`)
    - Operational cleaned jobs (`jobs_clean.csv`, `jobs_clean_internal.csv`)
    - Active crawler batch files (`data/raw/batches/*.csv`)
    - Canonical skill mentions and role classifications
    """
    initialize_database()
    now = utc_now()

    with database_connection() as conn:
        current_jobs_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        current_bm_count = conn.execute("SELECT COUNT(*) FROM benchmark_jobs").fetchone()[0]
        current_skills_count = conn.execute("SELECT COUNT(*) FROM extracted_skills").fetchone()[0]

    # Skip migration if already populated with rich regional data unless forced
    if not force and current_jobs_count >= 100 and current_bm_count >= 50 and current_skills_count >= 100:
        return {
            "status": "already_populated",
            "jobs_count": current_jobs_count,
            "benchmark_count": current_bm_count,
            "skills_count": current_skills_count,
        }

    # Lazy-load taxonomy extractors to avoid unnecessary overhead
    from src.extraction.taxonomy import load_taxonomy
    from src.extraction.lexical import LexicalSkillExtractor
    from src.roles.taxonomy import load_role_taxonomy
    from src.roles.classifier import RoleClassifier

    skill_tax = load_taxonomy(SKILL_TAXONOMY_PATH)
    skill_extractor = LexicalSkillExtractor(skill_tax)
    role_tax = load_role_taxonomy(ROLE_TAXONOMY_PATH)
    role_classifier = RoleClassifier(role_tax)

    # 1. Ingest Benchmark Ground Truth
    bm_count = import_benchmark_records(BENCHMARK_PATH)

    # 2. Cache longest raw crawled descriptions across CSVs
    raw_desc_by_url: dict[str, str] = {}
    csv_candidates = [PILOT_PREDICTIONS_PATH] + sorted(glob.glob(str(PROJECT_ROOT / "data" / "raw" / "batches" / "*.csv")))
    for p in csv_candidates:
        if not Path(p).exists():
            continue
        try:
            df_temp = pd.read_csv(p, low_memory=False)
            for _, r in df_temp.iterrows():
                u = canonical_url(r.get("source_url") or r.get("job_url"))
                d = str(r.get("job_description_raw") or r.get("job_description") or "").strip()
                if u and len(d) > len(raw_desc_by_url.get(u, "")):
                    raw_desc_by_url[u] = d
        except Exception:
            pass

    # 3. Import benchmark records into jobs table
    run_id = "run_master_canonical_lexical"
    with database_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO extraction_runs (
                run_id, run_type, model_name, model_version, taxonomy_version,
                started_at, completed_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, "lexical", "LexicalSkillExtractor", "1.0", "1.0", now, now, "Master database baseline extraction"),
        )

        if BENCHMARK_PATH.exists():
            df_bm = pd.read_csv(BENCHMARK_PATH)
            for _, r in df_bm.iterrows():
                url = canonical_url(r.get("source_url"))
                if not url:
                    continue
                job_id = f"bm_{r.get('benchmark_id')}"
                plat = str(r.get("source_platform") or "").strip()
                country = normalize_country_name(r.get("country"), plat)
                title = str(r.get("expected_job_title_raw") or "").strip()
                full_desc = raw_desc_by_url.get(url, "")
                desc = full_desc if len(full_desc) > 100 else str(r.get("expected_description_snippet") or "").strip()
                company = str(r.get("expected_company_raw") or "").strip()
                location = str(r.get("expected_location_raw") or "").strip()
                work_mode = str(r.get("expected_work_mode") or "unspecified").strip()
                posting_date = str(r.get("expected_posted_date") or "").strip()

                # Salary
                sal_norm = parse_and_normalize_salary(
                    salary_text_raw=str(r.get("expected_salary_text_raw") or ""),
                    salary_min_raw=r.get("expected_salary_min"),
                    salary_max_raw=r.get("expected_salary_max"),
                    salary_currency_raw=str(r.get("expected_salary_currency") or ""),
                    salary_period_raw=str(r.get("expected_salary_period") or ""),
                    country_context=country,
                )
                sal_disc = bool(r.get("expected_salary_disclosed", False))
                s_min = sal_norm.get("salary_min_normalized")
                s_max = sal_norm.get("salary_max_normalized")
                s_curr = sal_norm.get("salary_currency_normalized") or ""
                s_period = sal_norm.get("salary_period_normalized") or "unspecified"
                if sal_disc and s_min is None:
                    try:
                        s_min = float(r.get("expected_salary_min")) if pd.notna(r.get("expected_salary_min")) else None
                        s_max = float(r.get("expected_salary_max")) if pd.notna(r.get("expected_salary_max")) else None
                        s_curr = str(r.get("expected_salary_currency") or "").strip()
                        s_period = str(r.get("expected_salary_period") or "").strip() or "monthly"
                    except Exception:
                        pass

                role_id, role_name, _ = role_classifier.classify(title, desc)
                content_hash = hashlib.sha256(f"{url}:{title}:{desc}".encode()).hexdigest()

                conn.execute(
                    """INSERT OR REPLACE INTO jobs (
                        job_id, source_platform, source_hostname, source_url, job_title, company_name,
                        location, country, posting_date, job_description, content_hash, first_seen_at,
                        last_seen_at, created_at, updated_at, work_mode, salary_disclosed, salary_text_raw,
                        salary_type, salary_min_normalized, salary_max_normalized, salary_currency_normalized,
                        salary_period_normalized, salary_normalization_status, salary_normalization_method,
                        classification_status, is_benchmark_verified, source_validation_status, role_id, role_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        job_id, plat, plat, url, title, company, location, country, posting_date, desc,
                        content_hash, now, now, now, now, work_mode, 1 if sal_disc else 0,
                        sal_norm.get("salary_text_raw", ""), sal_norm.get("salary_type", "undisclosed"),
                        s_min, s_max, s_curr, s_period, sal_norm.get("salary_normalization_status", "undisclosed"),
                        sal_norm.get("salary_normalization_method", "not_applicable"), "it", 1, "validated",
                        role_id, role_name
                    ),
                )

                # Skills for benchmark job
                skills_set = set()
                exp_skills = r.get("expected_skills")
                if pd.notna(exp_skills):
                    try:
                        parsed = json.loads(str(exp_skills))
                        if isinstance(parsed, list):
                            skills_set.update(str(s).strip() for s in parsed if str(s).strip())
                    except Exception:
                        pass
                extracted = skill_extractor.extract(job_id, f"{title} {desc}")
                skills_set.update(s.skill_id for s in extracted.skills)
                for sk in sorted(skills_set):
                    conn.execute(
                        """INSERT OR IGNORE INTO extracted_skills (job_id, run_id, method, skill_name, created_at)
                           VALUES (?, ?, 'lexical', ?, ?)""",
                        (job_id, run_id, sk, now),
                    )

        # 4. Import crawled pilot predictions and batch CSV files
        existing_urls = {r[0] for r in conn.execute("SELECT source_url FROM jobs").fetchall()}
        all_crawled_sources = [
            PILOT_PREDICTIONS_PATH,
            PROJECT_ROOT / "data" / "processed" / "jobs_clean_internal.csv",
            PROJECT_ROOT / "data" / "processed" / "jobs_clean.csv",
        ] + sorted(PROJECT_ROOT.glob("data/raw/batches/*.csv"))

        for file_p in all_crawled_sources:
            if not file_p.exists():
                continue
            try:
                df_crawled = pd.read_csv(file_p, low_memory=False)
                for _, r in df_crawled.iterrows():
                    url = canonical_url(r.get("source_url") or r.get("job_url"))
                    if not url or url in existing_urls:
                        continue
                    existing_urls.add(url)

                    plat = str(r.get("source_platform") or r.get("source_hostname") or "").strip()
                    c_raw = r.get("country") or r.get("country_normalized") or r.get("country_raw")
                    country = normalize_country_name(c_raw, plat)
                    title = str(r.get("job_title") or r.get("job_title_raw") or "").strip()
                    desc = str(r.get("job_description") or r.get("job_description_raw") or "").strip()
                    company = str(r.get("company") or r.get("company_name") or r.get("company_raw") or "").strip()
                    location = str(r.get("location") or r.get("location_raw") or "").strip()
                    work_mode = str(r.get("work_mode") or r.get("work_mode_raw") or "unspecified").strip()
                    posting_date = str(r.get("posting_date") or r.get("posted_date_raw") or r.get("posted_date") or "").strip()
                    job_id = str(r.get("job_id") or hashlib.sha256(url.encode()).hexdigest()[:20])

                    sal_norm = parse_and_normalize_salary(
                        salary_text_raw=str(r.get("salary_text_raw") or ""),
                        salary_min_raw=r.get("salary_min_raw"),
                        salary_max_raw=r.get("salary_max_raw"),
                        salary_currency_raw=str(r.get("salary_currency_raw") or ""),
                        salary_period_raw=str(r.get("salary_period_raw") or ""),
                        country_context=country,
                    )
                    sal_disc = sal_norm.get("salary_disclosed", False)

                    role_id, role_name, _ = role_classifier.classify(title, desc)
                    content_hash = hashlib.sha256(f"{url}:{title}:{desc}".encode()).hexdigest()

                    conn.execute(
                        """INSERT OR REPLACE INTO jobs (
                            job_id, source_platform, source_hostname, source_url, job_title, company_name,
                            location, country, posting_date, job_description, content_hash, first_seen_at,
                            last_seen_at, created_at, updated_at, work_mode, salary_disclosed, salary_text_raw,
                            salary_type, salary_min_normalized, salary_max_normalized, salary_currency_normalized,
                            salary_period_normalized, salary_normalization_status, salary_normalization_method,
                            classification_status, is_benchmark_verified, source_validation_status, role_id, role_name
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            job_id, plat, plat, url, title, company, location, country, posting_date, desc,
                            content_hash, now, now, now, now, work_mode, 1 if sal_disc else 0,
                            sal_norm.get("salary_text_raw", ""), sal_norm.get("salary_type", "undisclosed"),
                            sal_norm.get("salary_min_normalized"), sal_norm.get("salary_max_normalized"),
                            sal_norm.get("salary_currency_normalized"), sal_norm.get("salary_period_normalized"),
                            sal_norm.get("salary_normalization_status", "undisclosed"),
                            sal_norm.get("salary_normalization_method", "not_applicable"), "it", 0, "pilot_tested",
                            role_id, role_name
                        ),
                    )

                    extracted = skill_extractor.extract(job_id, f"{title} {desc}")
                    for s in extracted.skills:
                        conn.execute(
                            """INSERT OR IGNORE INTO extracted_skills (job_id, run_id, method, skill_name, created_at)
                               VALUES (?, ?, 'lexical', ?, ?)""",
                            (job_id, run_id, s.skill_id, now),
                        )
            except Exception:
                pass

        # 5. Ensure all existing jobs have extracted skills
        existing_jobs = conn.execute("SELECT job_id, job_title, job_description FROM jobs").fetchall()
        for j in existing_jobs:
            jid = j["job_id"]
            has_skills = conn.execute("SELECT 1 FROM extracted_skills WHERE job_id = ? LIMIT 1", (jid,)).fetchone()
            if not has_skills:
                t = str(j["job_title"] or "")
                d = str(j["job_description"] or "")
                ext = skill_extractor.extract(jid, f"{t} {d}")
                for s in ext.skills:
                    conn.execute(
                        """INSERT OR IGNORE INTO extracted_skills (job_id, run_id, method, skill_name, created_at)
                           VALUES (?, ?, 'lexical', ?, ?)""",
                        (jid, run_id, s.skill_id, now),
                    )

        # 6. Ensure evaluation_runs has latest run from disk if available
        latest_metrics_file = PROJECT_ROOT / "data" / "evaluation" / "results" / "evaluation_metrics_latest.json"
        if latest_metrics_file.exists():
            try:
                with open(latest_metrics_file, "r", encoding="utf-8") as f:
                    eval_metrics = json.load(f)
                latest_errors_csv = PROJECT_ROOT / "data" / "evaluation" / "results" / "evaluation_errors_latest.csv"
                err_df = pd.read_csv(latest_errors_csv, dtype=str).fillna("") if latest_errors_csv.exists() else pd.DataFrame()
                latest_report_md = PROJECT_ROOT / "data" / "evaluation" / "results" / "evaluation_report_latest.md"
                rep_md = latest_report_md.read_text(encoding="utf-8") if latest_report_md.exists() else ""
                save_evaluation_run("latest", eval_metrics, err_df, rep_md, is_synthetic=False, is_latest=True, conn=conn)
            except Exception:
                pass

        final_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        final_bms = conn.execute("SELECT COUNT(*) FROM benchmark_jobs").fetchone()[0]
        final_skills = conn.execute("SELECT COUNT(*) FROM extracted_skills").fetchone()[0]

    return {
        "status": "migrated",
        "jobs_count": final_jobs,
        "benchmark_count": final_bms,
        "skills_count": final_skills,
    }

