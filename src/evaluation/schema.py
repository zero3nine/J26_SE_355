"""
Schema definitions and validation for the Information Extraction Benchmark Dataset.
Academic Research Component for Regional Comparative IT Labor-Market Analysis.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union


# Valid verification statuses according to benchmark protocol
ALLOWED_STATUSES: Set[str] = {
    "verified",      # Value verified directly against primary source page evidence
    "unavailable",   # Field is genuinely absent from the source page
    "ambiguous",     # Source page contains conflicting, vague, or indeterminate information
    "not_reviewed",  # Field has not yet been audited by an evaluator
}

# Supported geographic countries for regional comparative analysis
ALLOWED_COUNTRIES: Set[str] = {
    "Sri Lanka",
    "India",
    "Singapore",
    "Malaysia",
}

# Standardized work modes
ALLOWED_WORK_MODES: Set[str] = {
    "remote",
    "hybrid",
    "on_site",
    "unspecified",
}

# Allowed salary types aligned with Task 1 salary normalizer
ALLOWED_SALARY_TYPES: Set[str] = {
    "range",
    "fixed",
    "starting_from",
    "up_to",
    "undisclosed",
}

# Valid extraction methods
ALLOWED_EXTRACTION_METHODS: Set[str] = {
    "jsonld",
    "site_adapter",
    "generic_html",
    "browser_rendered",
    "none",
}

# Canonical column order for benchmark CSV exports
BENCHMARK_SCHEMA_COLUMNS: List[str] = [
    # 1. Identity & Provenance
    "benchmark_id",
    "source_url",
    "source_platform",
    "country",
    "collection_context",
    "extraction_method",

    # 2. Expected Core Job Fields
    "expected_job_title_raw",
    "expected_company_raw",
    "expected_location_raw",
    "expected_country_normalized",
    "expected_city_normalized",
    "expected_work_mode",
    "expected_posted_date",
    "expected_closing_date",

    # 3. Description Verification Representation
    "expected_description_snippet",
    "expected_description_hash",
    "expected_description_min_len",

    # 4. Expected Salary Information
    "expected_salary_disclosed",
    "expected_salary_text_raw",
    "expected_salary_type",
    "expected_salary_min",
    "expected_salary_max",
    "expected_salary_currency",
    "expected_salary_period",

    # 5. Expected Canonical Skills
    "expected_skills",

    # 6. Field-by-Field Verification Statuses
    "status_job_title",
    "status_company",
    "status_location",
    "status_work_mode",
    "status_posted_date",
    "status_closing_date",
    "status_description",
    "status_salary",
    "status_skills",

    # 7. Audit Trail & Reviewer Notes
    "verification_timestamp",
    "verified_by",
    "evidence_source",
    "reviewer_notes",
]

# Field status keys mapped to evaluated field names
STATUS_FIELD_MAP: Dict[str, str] = {
    "job_title": "status_job_title",
    "company": "status_company",
    "location": "status_location",
    "work_mode": "status_work_mode",
    "posted_date": "status_posted_date",
    "closing_date": "status_closing_date",
    "description": "status_description",
    "salary": "status_salary",
    "skills": "status_skills",
}


@dataclass
class BenchmarkRecord:
    """Represents a single verified ground truth benchmark record."""

    # Identity & Provenance
    benchmark_id: str
    source_url: str
    source_platform: str
    country: str
    collection_context: str = "operational_crawl"
    extraction_method: str = "jsonld"

    # Expected Core Job Fields
    expected_job_title_raw: str = ""
    expected_company_raw: str = ""
    expected_location_raw: str = ""
    expected_country_normalized: str = ""
    expected_city_normalized: str = ""
    expected_work_mode: str = "unspecified"
    expected_posted_date: str = ""
    expected_closing_date: str = ""

    # Description Verification Representation
    expected_description_snippet: str = ""
    expected_description_hash: str = ""
    expected_description_min_len: int = 0

    # Expected Salary Information
    expected_salary_disclosed: bool = False
    expected_salary_text_raw: str = ""
    expected_salary_type: str = "undisclosed"
    expected_salary_min: Optional[float] = None
    expected_salary_max: Optional[float] = None
    expected_salary_currency: str = ""
    expected_salary_period: str = "unspecified"

    # Expected Canonical Skills
    expected_skills: str = ""

    # Field-by-Field Verification Statuses
    status_job_title: str = "not_reviewed"
    status_company: str = "not_reviewed"
    status_location: str = "not_reviewed"
    status_work_mode: str = "not_reviewed"
    status_posted_date: str = "not_reviewed"
    status_closing_date: str = "not_reviewed"
    status_description: str = "not_reviewed"
    status_salary: str = "not_reviewed"
    status_skills: str = "not_reviewed"

    # Audit Trail & Reviewer Notes
    verification_timestamp: str = ""
    verified_by: str = ""
    evidence_source: str = "original_html_dom"
    reviewer_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Converts the record to a dictionary matching BENCHMARK_SCHEMA_COLUMNS."""
        data = asdict(self)
        # Ensure booleans and floats are formatted cleanly for CSV
        data["expected_salary_disclosed"] = "True" if self.expected_salary_disclosed else "False"
        data["expected_salary_min"] = "" if self.expected_salary_min is None else str(self.expected_salary_min)
        data["expected_salary_max"] = "" if self.expected_salary_max is None else str(self.expected_salary_max)
        data["expected_description_min_len"] = str(self.expected_description_min_len)
        return {col: data.get(col, "") for col in BENCHMARK_SCHEMA_COLUMNS}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BenchmarkRecord:
        """Constructs a BenchmarkRecord from a dictionary."""
        # Clean boolean
        raw_disclosed = data.get("expected_salary_disclosed", False)
        if isinstance(raw_disclosed, str):
            disclosed = raw_disclosed.strip().lower() in ("true", "1", "yes")
        else:
            disclosed = bool(raw_disclosed)

        # Clean floats
        def _to_float(v: Any) -> Optional[float]:
            if v is None or v == "" or str(v).strip().lower() in ("nan", "none", "null"):
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        # Clean integer
        def _to_int(v: Any) -> int:
            if v is None or v == "" or str(v).strip().lower() in ("nan", "none", "null"):
                return 0
            try:
                return int(float(v))
            except (ValueError, TypeError):
                return 0

        # Build dataclass kwargs
        kwargs: Dict[str, Any] = {
            "benchmark_id": str(data.get("benchmark_id", "")).strip(),
            "source_url": str(data.get("source_url", "")).strip(),
            "source_platform": str(data.get("source_platform", "")).strip(),
            "country": str(data.get("country", "")).strip(),
            "collection_context": str(data.get("collection_context", "operational_crawl")).strip(),
            "extraction_method": str(data.get("extraction_method", "jsonld")).strip(),
            "expected_job_title_raw": str(data.get("expected_job_title_raw", "")).strip(),
            "expected_company_raw": str(data.get("expected_company_raw", "")).strip(),
            "expected_location_raw": str(data.get("expected_location_raw", "")).strip(),
            "expected_country_normalized": str(data.get("expected_country_normalized", "")).strip(),
            "expected_city_normalized": str(data.get("expected_city_normalized", "")).strip(),
            "expected_work_mode": str(data.get("expected_work_mode", "unspecified")).strip(),
            "expected_posted_date": str(data.get("expected_posted_date", "")).strip(),
            "expected_closing_date": str(data.get("expected_closing_date", "")).strip(),
            "expected_description_snippet": str(data.get("expected_description_snippet", "")).strip(),
            "expected_description_hash": str(data.get("expected_description_hash", "")).strip(),
            "expected_description_min_len": _to_int(data.get("expected_description_min_len", 0)),
            "expected_salary_disclosed": disclosed,
            "expected_salary_text_raw": str(data.get("expected_salary_text_raw", "")).strip(),
            "expected_salary_type": str(data.get("expected_salary_type", "undisclosed")).strip(),
            "expected_salary_min": _to_float(data.get("expected_salary_min")),
            "expected_salary_max": _to_float(data.get("expected_salary_max")),
            "expected_salary_currency": str(data.get("expected_salary_currency", "")).strip(),
            "expected_salary_period": str(data.get("expected_salary_period", "unspecified")).strip(),
            "expected_skills": str(data.get("expected_skills", "")).strip(),
            "status_job_title": str(data.get("status_job_title", "not_reviewed")).strip(),
            "status_company": str(data.get("status_company", "not_reviewed")).strip(),
            "status_location": str(data.get("status_location", "not_reviewed")).strip(),
            "status_work_mode": str(data.get("status_work_mode", "not_reviewed")).strip(),
            "status_posted_date": str(data.get("status_posted_date", "not_reviewed")).strip(),
            "status_closing_date": str(data.get("status_closing_date", "not_reviewed")).strip(),
            "status_description": str(data.get("status_description", "not_reviewed")).strip(),
            "status_salary": str(data.get("status_salary", "not_reviewed")).strip(),
            "status_skills": str(data.get("status_skills", "not_reviewed")).strip(),
            "verification_timestamp": str(data.get("verification_timestamp", "")).strip(),
            "verified_by": str(data.get("verified_by", "")).strip(),
            "evidence_source": str(data.get("evidence_source", "original_html_dom")).strip(),
            "reviewer_notes": str(data.get("reviewer_notes", "")).strip(),
        }
        return cls(**kwargs)


def validate_benchmark_records(records: List[BenchmarkRecord]) -> List[str]:
    """Validates an entire set of benchmark records for schema conformance.
    
    Returns:
        List of error messages (empty if all records are valid).
    """
    errors: List[str] = []
    seen_ids: Set[str] = set()
    status_fields = [
        "status_job_title", "status_company", "status_location",
        "status_work_mode", "status_posted_date", "status_closing_date",
        "status_description", "status_salary", "status_skills"
    ]

    for idx, rec in enumerate(records):
        line = idx + 1
        # Check benchmark ID
        if not rec.benchmark_id:
            errors.append(f"Record #{line}: Missing required 'benchmark_id'.")
        elif rec.benchmark_id in seen_ids:
            errors.append(f"Record #{line}: Duplicate benchmark_id '{rec.benchmark_id}'.")
        else:
            seen_ids.add(rec.benchmark_id)

        # Check source URL
        if not rec.source_url:
            errors.append(f"Record '{rec.benchmark_id or line}': Missing required 'source_url'.")
        elif not (rec.source_url.startswith("http://") or rec.source_url.startswith("https://")):
            errors.append(f"Record '{rec.benchmark_id}': Invalid URL format: '{rec.source_url}'.")

        # Check country
        if rec.country not in ALLOWED_COUNTRIES:
            errors.append(
                f"Record '{rec.benchmark_id}': Invalid country '{rec.country}'. "
                f"Must be one of {sorted(list(ALLOWED_COUNTRIES))}."
            )

        # Check work mode
        if rec.expected_work_mode and rec.expected_work_mode not in ALLOWED_WORK_MODES:
            errors.append(
                f"Record '{rec.benchmark_id}': Invalid expected_work_mode '{rec.expected_work_mode}'. "
                f"Must be one of {sorted(list(ALLOWED_WORK_MODES))}."
            )

        # Check field statuses
        for sf in status_fields:
            val = getattr(rec, sf, "")
            if val not in ALLOWED_STATUSES:
                errors.append(
                    f"Record '{rec.benchmark_id}': Invalid {sf} '{val}'. "
                    f"Must be one of {sorted(list(ALLOWED_STATUSES))}."
                )

    return errors


def load_benchmark_dataset(file_path: Union[str, Path]) -> List[BenchmarkRecord]:
    """Loads and validates a benchmark dataset from CSV or JSON.
    
    Args:
        file_path: Absolute or relative path to CSV or JSON file.

    Returns:
        List of validated BenchmarkRecord instances.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If file schema validation fails.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Benchmark dataset file not found: {path}")

    records: List[BenchmarkRecord] = []
    if path.suffix.lower() == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError(f"JSON benchmark dataset must contain a top-level array of records.")
            records = [BenchmarkRecord.from_dict(item) for item in data]
    elif path.suffix.lower() == ".csv":
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(BenchmarkRecord.from_dict(row))
    else:
        raise ValueError(f"Unsupported benchmark file extension: '{path.suffix}'. Expected .csv or .json.")

    errors = validate_benchmark_records(records)
    if errors:
        raise ValueError(
            f"Benchmark dataset '{path}' contains {len(errors)} validation error(s):\n" +
            "\n".join(f"  - {err}" for err in errors[:10]) +
            (f"\n  ... and {len(errors) - 10} more" if len(errors) > 10 else "")
        )

    return records
