"""Normalize external historical job datasets to the collector's raw schema."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable
import urllib.parse

import pandas as pd

from src.scraping.models import RAW_SCHEMA_COLUMNS, generate_job_id

TARGET_ALIASES = {
    "job_title_raw": ["job_title_raw", "job_title", "title", "position", "vacancy_title", "designation", "role"],
    "company_raw": ["company_raw", "company", "employer", "organization", "organisation", "company_name"],
    "job_description_raw": ["job_description_raw", "job_description", "description", "job_details", "advertisement_text", "full_text", "text"],
    "requirements_raw": ["requirements_raw", "requirements", "qualifications", "responsibilities", "technical_requirements"],
    "posted_date_raw": ["posted_date_raw", "posting_date", "posted_date", "date_published", "datepublished", "published_at", "date", "publication_date"],
    "closing_date_raw": ["closing_date_raw", "closing_date", "deadline", "application_deadline"],
    "country_raw": ["country_raw", "country", "country_name"],
    "location_raw": ["location_raw", "location", "city", "job_location", "region"],
    "source_url": ["source_url", "url", "job_url", "advert_url", "link", "original_url"],
    "source_platform": ["source_platform", "source", "source_name", "job_board", "portal", "dataset_source"],
    "source_job_id": ["source_job_id", "external_id", "job_id", "id", "advert_id", "posting_id"],
    "employment_type_raw": ["employment_type_raw", "employment_type", "job_type", "type"],
    "skills_raw": ["skills_raw", "skills", "required_skills", "skill_list"],
    "salary_text_raw": ["salary_text_raw", "salary", "salary_range", "compensation"],
    "work_mode_raw": ["work_mode_raw", "work_mode", "remote_status", "working_arrangement"],
}


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def read_dataset(uploaded_file) -> pd.DataFrame:
    """Read an uploaded CSV or Excel file without changing source values."""
    name = getattr(uploaded_file, "name", "uploaded.csv").lower()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(uploaded_file, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, dtype=str, keep_default_na=False, encoding="latin-1")
    if name.endswith(('.xlsx', '.xls')):
        return pd.read_excel(uploaded_file, dtype=str).fillna("")
    raise ValueError("Unsupported file type. Upload a CSV, XLSX, or XLS file.")


def suggest_mapping(columns: Iterable[str]) -> Dict[str, str]:
    """Suggest common source-column mappings; blank means unmapped."""
    lookup = {_key(c): c for c in columns}
    result = {}
    for target, aliases in TARGET_ALIASES.items():
        match = next((lookup[_key(alias)] for alias in aliases if _key(alias) in lookup), "")
        result[target] = match
    return result


def normalize_historical_dataset(
    source_df: pd.DataFrame,
    mapping: Dict[str, str],
    dataset_source: str,
    batch_id: str,
    default_country: str = "Sri Lanka",
) -> pd.DataFrame:
    """Map source columns to RAW_SCHEMA_COLUMNS and attach provenance fields."""
    if source_df.empty:
        raise ValueError("The uploaded dataset contains no records.")
    if not mapping.get("job_title_raw"):
        raise ValueError("Map a source column to Job Title before importing.")

    now = datetime.now(timezone.utc).isoformat()
    result = pd.DataFrame("", index=source_df.index, columns=RAW_SCHEMA_COLUMNS)
    for target, source_col in mapping.items():
        if source_col and source_col in source_df.columns and target in result.columns:
            result[target] = source_df[source_col].fillna("").astype(str).str.strip()

    # Preserve title/company/description as source text; downstream cleaning handles normalization.
    if "country_raw" in result:
        result["country_raw"] = result["country_raw"].replace("", default_country)
    result["source_platform"] = result["source_platform"].replace("", dataset_source)
    result["source_hostname"] = result.apply(
        lambda row: urllib.parse.urlparse(str(row.get("source_url", ""))).hostname or ""
        if str(row.get("source_url", "")).startswith(("http://", "https://")) else "", axis=1
    )
    result["final_url"] = result["source_url"]
    result["collection_batch_id"] = batch_id
    result["scraped_at"] = now  # Import timestamp, not the original posting date.
    result["extractor_name"] = "historical_dataset_import"
    result["extraction_method"] = "dataset_import"
    result["extraction_status"] = result.apply(
        lambda r: "success" if r["job_title_raw"].strip() and r["job_description_raw"].strip()
        else ("partial" if r["job_title_raw"].strip() else "manual_review"), axis=1
    )
    result["extraction_confidence"] = "1.0"
    result["description_type"] = result["job_description_raw"].apply(
        lambda x: "full_text" if len(str(x).strip()) >= 100 else ("short_text" if str(x).strip() else "missing")
    )
    result["fetch_method"] = "file_import"
    result["rendering_used"] = "False"
    result["field_provenance"] = result.apply(
        lambda r: '{"collection_method":"historical_import","dataset_source":"' +
        str(dataset_source).replace('\\', '\\\\').replace('"', '\\"') + '"}', axis=1
    )

    for idx, row in result.iterrows():
        url = str(row.get("source_url", "")).strip()
        source_id = str(row.get("source_job_id", "")).strip()
        host = str(row.get("source_hostname", "")).strip() or re.sub(r"[^a-z0-9]+", "_", dataset_source.lower()).strip("_")
        if not source_id and not url:
            # Stable within the same source file for rows with no external identifier.
            stable = "|".join(str(row.get(c, "")) for c in ("job_title_raw", "company_raw", "posted_date_raw", "job_description_raw"))
            source_id = "row_" + hashlib.sha256(stable.encode("utf-8")).hexdigest()[:16]
            result.at[idx, "source_job_id"] = source_id
        result.at[idx, "job_id"] = generate_job_id(host, source_id, url)

    return result.fillna("")


def duplicate_mask(df: pd.DataFrame) -> pd.Series:
    """Flag likely duplicates using URL first, then title/company/date fingerprints."""
    url = df.get("source_url", pd.Series("", index=df.index)).astype(str).str.strip().str.lower()
    fingerprint_cols = [c for c in ["job_title_raw", "company_raw", "posted_date_raw"] if c in df.columns]
    fingerprint = df[fingerprint_cols].astype(str).apply(lambda r: "|".join(v.strip().lower() for v in r), axis=1) if fingerprint_cols else pd.Series("", index=df.index)
    seen_url = url.ne("") & url.duplicated(keep="first")
    seen_fingerprint = fingerprint.ne("") & fingerprint.duplicated(keep="first")
    return seen_url | seen_fingerprint
