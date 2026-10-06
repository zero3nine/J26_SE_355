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


def import_jobs_dataframe(
    df: pd.DataFrame,
    source_name: str = "streamlit_upload",
    db_path: Path | str | None = None,
) -> dict:
    """Import cleaned jobs idempotently, retaining changed versions."""
    if df is None or df.empty:
        return {
            "import_run_id": None, "input_rows": 0, "inserted_jobs": 0,
            "updated_jobs": 0, "skipped_duplicates": 0, "failed_rows": 0,
        }

    initialize_database(db_path=db_path)
    run_id = str(uuid.uuid4())
    now = utc_now()
    inserted = updated = skipped = failed = 0

    with database_connection(db_path=db_path) as conn:
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


def seed_skills_taxonomy(
    taxonomy_path: Path | str | None = None,
    db_path: Path | str | None = None,
) -> int:
    """
    Seed the skills table from skill_taxonomy.json using a safe, repeatable UPSERT process.
    Returns the count of seeded canonical skills.
    """
    initialize_database(db_path=db_path)
    tax_path = Path(taxonomy_path) if taxonomy_path else (Path(__file__).resolve().parents[2] / "config" / "skill_taxonomy.json")
    if not tax_path.exists():
        return 0

    with open(tax_path, "r", encoding="utf-8") as f:
        tax_data = json.load(f)

    tax_version = str(tax_data.get("taxonomy_version", "0.1.0"))
    categories = tax_data.get("categories", [])
    seeded_count = 0

    with database_connection(db_path=db_path) as conn:
        for cat in categories:
            cat_name = as_text(cat.get("name"))
            for sk in cat.get("skills", []):
                canonical_name = as_text(sk.get("name"))
                if not canonical_name:
                    continue
                aliases = list(sk.get("aliases", []))
                sk_id = sk.get("id")
                if sk_id and sk_id not in aliases:
                    aliases.append(sk_id)
                aliases_json = json.dumps(sorted(list(set(aliases))), ensure_ascii=False)

                conn.execute(
                    """INSERT INTO skills (canonical_name, category, taxonomy_version, aliases_json)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(canonical_name) DO UPDATE SET
                           category = excluded.category,
                           taxonomy_version = excluded.taxonomy_version,
                           aliases_json = excluded.aliases_json""",
                    (canonical_name, cat_name, tax_version, aliases_json),
                )
                seeded_count += 1
    return seeded_count


def get_skill_taxonomy_mapping(conn) -> dict[str, int]:
    """Return a lookup mapping from alias/canonical (casefolded) to skill_id."""
    mapping: dict[str, int] = {}
    rows = conn.execute("SELECT skill_id, canonical_name, aliases_json FROM skills").fetchall()
    for row in rows:
        skill_id = row["skill_id"]
        c_name = row["canonical_name"]
        if c_name:
            mapping[c_name.strip().casefold()] = skill_id
        aliases_raw = row["aliases_json"]
        if aliases_raw:
            try:
                aliases = json.loads(aliases_raw)
                if isinstance(aliases, list):
                    for a in aliases:
                        if a:
                            mapping[str(a).strip().casefold()] = skill_id
            except Exception:
                pass
    return mapping


def record_extraction_run(
    run_type: str,
    model_name: str | None = None,
    model_version: str | None = None,
    taxonomy_version: str | None = None,
    semantic_threshold: float | None = None,
    source_batch_id: str | None = None,
    notes: str | None = None,
    db_path: Path | str | None = None,
) -> str:
    """Record an extraction run in the extraction_runs table."""
    initialize_database(db_path=db_path)
    run_id = str(uuid.uuid4())
    with database_connection(db_path=db_path) as conn:
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
    db_path: Path | str | None = None,
    taxonomy_path: Path | str | None = None,
) -> int:
    """
    Store skill mentions from an extracted dataframe against jobs in the master database.
    Maps extracted mentions to canonical_skill_id, preserves provenance & confidence.
    """
    initialize_database(db_path=db_path)
    # Ensure skills taxonomy is seeded
    seed_skills_taxonomy(taxonomy_path=taxonomy_path, db_path=db_path)

    saved = 0
    now = utc_now()
    with database_connection(db_path=db_path) as conn:
        skill_mapping = get_skill_taxonomy_mapping(conn)

        for _, series in jobs_df.iterrows():
            row = series.to_dict()
            source_url = canonical_url(first_value(row, "source_url", "job_url", "url"))
            source_job_id = first_value(row, "job_id", "source_job_id")

            # Resolve job_id in jobs table
            job = None
            if source_url:
                job = conn.execute(
                    "SELECT job_id FROM jobs WHERE source_url = ?", (source_url,)
                ).fetchone()
            if not job and source_job_id:
                job = conn.execute(
                    "SELECT job_id FROM jobs WHERE job_id = ?", (source_job_id,)
                ).fetchone()

            if not job:
                # If job is not in jobs table yet but has a valid source_url or job_id,
                # safely ensure the job record exists so the foreign key constraint is satisfied.
                if source_url or source_job_id:
                    payload = job_payload(row)
                    if payload["source_url"]:
                        conn.execute(
                            """INSERT OR IGNORE INTO jobs (
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
                        target_job_id = payload["job_id"]
                    else:
                        continue
                else:
                    continue
            else:
                target_job_id = job["job_id"]

            raw_skills = row.get(skills_column, [])
            if isinstance(raw_skills, str):
                try:
                    parsed = json.loads(raw_skills)
                    raw_skills = parsed if isinstance(parsed, list) else []
                except json.JSONDecodeError:
                    raw_skills = [x.strip() for x in raw_skills.split(",") if x.strip()]
            if not isinstance(raw_skills, (list, tuple, set)):
                continue

            # Provenance / source evidence
            provenance = first_value(row, "skill_provenance", "provenance", "description_source")

            for skill in raw_skills:
                skill_name = as_text(skill)
                if not skill_name:
                    continue

                # Map to canonical skill ID in skills table
                canonical_id = skill_mapping.get(skill_name.casefold())
                if not canonical_id:
                    try:
                        from src.extraction.normalization import normalize_skill
                        norm_name = normalize_skill(skill_name)
                        canonical_id = skill_mapping.get(norm_name.casefold())
                    except Exception:
                        canonical_id = None

                # Confidence: 1.0 for lexical; for semantic, look for score or default 1.0
                confidence = 1.0 if "lexical" in method.lower() else 1.0

                conn.execute(
                    """INSERT OR IGNORE INTO extracted_skills
                       (job_id, run_id, method, skill_name, canonical_skill_id,
                        original_span, confidence, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (target_job_id, run_id, method, skill_name, canonical_id,
                     provenance, confidence, now),
                )
                saved += 1
    return saved


def get_extracted_skills_dataset(
    run_id: str | None = None,
    db_path: Path | str | None = None,
) -> pd.DataFrame:
    """
    Load an integrated dataframe from the master SQLite database joining
    jobs and extracted_skills (and canonical taxonomy skills).
    Aggregates per job_id with 'lexical_skills' and 'semantic_skills' JSON columns.
    """
    initialize_database(db_path=db_path)
    with database_connection(db_path=db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM extracted_skills").fetchone()[0]
        if count == 0:
            return pd.DataFrame(columns=[
                "job_id", "job_title_raw", "company", "location_raw", "country",
                "posting_date", "job_description", "source_platform", "source_url",
                "lexical_skills", "semantic_skills", "skill_provenance", "collection_batch_id"
            ])

        query = """
            SELECT 
                j.job_id,
                COALESCE(j.job_title, '') AS job_title_raw,
                COALESCE(j.company_name, '') AS company,
                COALESCE(j.location, '') AS location_raw,
                COALESCE(j.country, '') AS country,
                COALESCE(j.posting_date, '') AS posting_date,
                COALESCE(j.job_description, '') AS job_description,
                COALESCE(j.source_platform, '') AS source_platform,
                COALESCE(j.source_url, '') AS source_url,
                es.mention_id,
                es.run_id,
                es.method,
                es.skill_name,
                es.canonical_skill_id,
                es.original_span,
                es.confidence,
                s.canonical_name,
                s.category
            FROM jobs j
            JOIN extracted_skills es ON j.job_id = es.job_id
            LEFT JOIN skills s ON es.canonical_skill_id = s.skill_id
            WHERE (? IS NULL OR es.run_id = ?)
            ORDER BY j.job_id, es.method, es.skill_name
        """
        rows = conn.execute(query, (run_id, run_id)).fetchall()

        if not rows:
            return pd.DataFrame(columns=[
                "job_id", "job_title_raw", "company", "location_raw", "country",
                "posting_date", "job_description", "source_platform", "source_url",
                "lexical_skills", "semantic_skills", "skill_provenance", "collection_batch_id"
            ])

        grouped: dict[str, dict[str, Any]] = {}
        for r in rows:
            jid = r["job_id"]
            if jid not in grouped:
                grouped[jid] = {
                    "job_id": jid,
                    "job_title_raw": r["job_title_raw"],
                    "company": r["company"],
                    "location_raw": r["location_raw"],
                    "country": r["country"],
                    "posting_date": r["posting_date"],
                    "job_description": r["job_description"],
                    "source_platform": r["source_platform"],
                    "source_url": r["source_url"],
                    "lexical_set": set(),
                    "semantic_set": set(),
                    "provenances": set(),
                    "run_ids": set(),
                }

            # Use canonical_name if mapped, otherwise raw skill_name
            sk_label = r["canonical_name"] or r["skill_name"]
            method = str(r["method"]).lower()
            if "lexical" in method:
                grouped[jid]["lexical_set"].add(sk_label)
            elif "semantic" in method:
                grouped[jid]["semantic_set"].add(sk_label)
            else:
                grouped[jid]["lexical_set"].add(sk_label)

            if r["original_span"]:
                grouped[jid]["provenances"].add(r["original_span"])
            if r["run_id"]:
                grouped[jid]["run_ids"].add(r["run_id"])

        records = []
        for g in grouped.values():
            prov_str = ", ".join(sorted(g["provenances"])) if g["provenances"] else "description"
            batch_id = sorted(g["run_ids"])[0] if g["run_ids"] else ""
            records.append({
                "job_id": g["job_id"],
                "job_title_raw": g["job_title_raw"],
                "company": g["company"],
                "location_raw": g["location_raw"],
                "country": g["country"],
                "posting_date": g["posting_date"],
                "job_description": g["job_description"],
                "source_platform": g["source_platform"],
                "source_url": g["source_url"],
                "lexical_skills": json.dumps(sorted(list(g["lexical_set"])), ensure_ascii=False),
                "semantic_skills": json.dumps(sorted(list(g["semantic_set"])), ensure_ascii=False),
                "skill_provenance": prov_str,
                "collection_batch_id": batch_id,
            })

        return pd.DataFrame(records)


def get_master_jobs(db_path: Path | str | None = None) -> pd.DataFrame:
    """Fetch all master jobs with version and extraction counts."""
    initialize_database(db_path=db_path)
    with database_connection(db_path=db_path) as conn:
        return pd.read_sql_query(
            """SELECT j.*,
                      (SELECT COUNT(*) FROM job_versions v WHERE v.job_id = j.job_id) AS version_count,
                      (SELECT COUNT(DISTINCT es.run_id) FROM extracted_skills es WHERE es.job_id = j.job_id) AS extraction_run_count
               FROM jobs j
               ORDER BY j.last_seen_at DESC""",
            conn,
        )


def get_database_summary(db_path: Path | str | None = None) -> dict:
    """Return counts of jobs, versions, skill mentions, and runs."""
    initialize_database(db_path=db_path)
    with database_connection(db_path=db_path) as conn:
        jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        versions = conn.execute("SELECT COUNT(*) FROM job_versions").fetchone()[0]
        skills = conn.execute("SELECT COUNT(*) FROM extracted_skills").fetchone()[0]
        canonical = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
        runs = conn.execute("SELECT COUNT(*) FROM extraction_runs").fetchone()[0]
        imports = conn.execute("SELECT COUNT(*) FROM import_runs").fetchone()[0]
    return {
        "jobs": jobs,
        "versions": versions,
        "skill_mentions": skills,
        "canonical_skills": canonical,
        "extraction_runs": runs,
        "import_runs": imports,
    }
