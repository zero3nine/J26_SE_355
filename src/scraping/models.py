"""
Data models for multi-site job extraction results.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional
import hashlib
import urllib.parse


# Valid extraction statuses
EXTRACTION_STATUSES = {
    "success",       # Job data extracted successfully
    "partial",       # Some fields extracted, others missing
    "unsupported",   # Page cannot be extracted by any available extractor
    "manual_review", # Ambiguous — needs human review
    "blocked",       # Server returned 403 or similar access restriction
    "rate_limited",  # Server returned 429
    "invalid_url",   # URL failed security validation
    "network_error", # Connection/timeout/DNS failure
    "parse_error",   # HTML/JSON parsing failed
    "not_a_job_page",# Page exists but is not a job advertisement
}

# Valid extraction methods
EXTRACTION_METHODS = {
    "jsonld",           # Schema.org JobPosting JSON-LD
    "site_adapter",     # Website-specific adapter
    "generic_html",     # Generic HTML fallback
    "listing_page",     # From listing page discovery
    "none",             # No extraction performed
}

# Internal raw schema column order
RAW_SCHEMA_COLUMNS = [
    "job_id", "source_job_id", "job_title_raw", "company_raw",
    "country_raw", "location_raw", "job_description_raw", "requirements_raw",
    "posted_date_raw", "closing_date_raw", "employment_type_raw",
    "skills_raw", "qualifications_raw", "industry_raw",
    "source_platform", "source_hostname", "source_url", "final_url",
    "extractor_name", "extraction_method", "extraction_status",
    "extraction_confidence", "description_type",
    "advert_image_urls", "ocr_status",
    "collection_batch_id", "scraped_at",
    "error_type", "error_message", "manual_review_reason",
    # Task 2 Auditing and Browser Fallback Fields
    "fetch_method", "rendering_used", "failure_reason",
    # Task 7 Date Conversion Fields
    "date_conversion_method", "date_parse_status", "date_parse_warning",
    # Task 4 Provenance and Validation JSON Field
    "field_provenance",
    # Task 5 Classification Fields
    "classification_status", "classification_explanation", "classification_override"
]

# Team export schema
TEAM_SCHEMA_COLUMNS = [
    "job_id", "job_title_raw", "company", "country", "location_raw",
    "job_description", "requirements", "posted_date", "closing_date", "source_platform", "source_url",
    "scraped_at",
]


def generate_job_id(source_hostname, source_job_id, url):
    """Generates a stable job_id from hostname + source identifier or URL hash."""
    platform = source_hostname or "unknown"
    if source_job_id and source_job_id.strip():
        return f"{platform}_{source_job_id.strip()}"
    elif url:
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return f"{platform}_hash_{url_hash}"
    else:
        import time
        return f"{platform}_unknown_{int(time.time() * 1000)}"


def get_hostname(url):
    """Extracts hostname from a URL."""
    try:
        return urllib.parse.urlparse(url).hostname or ""
    except Exception:
        return ""


@dataclass
class ExtractionResult:
    """Result of attempting to extract job data from a single URL."""
    # Identity
    job_id: str = ""
    source_job_id: str = ""

    # Job fields (raw, unmodified)
    job_title_raw: str = ""
    company_raw: str = ""
    country_raw: str = ""
    location_raw: str = ""
    job_description_raw: str = ""
    posted_date_raw: str = ""
    closing_date_raw: str = ""
    employment_type_raw: str = ""
    skills_raw: str = ""
    qualifications_raw: str = ""
    industry_raw: str = ""
    requirements_raw: str = ""

    # Source tracking
    source_platform: str = ""
    source_hostname: str = ""
    source_url: str = ""
    final_url: str = ""

    # Extraction metadata
    extractor_name: str = "none"
    extraction_method: str = "none"
    extraction_status: str = "network_error"
    extraction_confidence: float = 0.0
    description_type: str = "missing"  # html_text, image, hybrid, missing, jsonld

    # Image/OCR
    advert_image_urls: str = "[]"
    ocr_status: str = "not_required"

    # Batch tracking
    collection_batch_id: str = ""
    scraped_at: str = ""

    # Error tracking
    error_type: str = ""
    error_message: str = ""
    manual_review_reason: str = ""

    # Task 2 Fallback/Auditing Fields
    fetch_method: str = "none" # "http", "browser", "none"
    rendering_used: str = "False"
    failure_reason: str = ""

    # Task 7 Date Conversion Fields
    date_conversion_method: str = ""
    date_parse_status: str = ""
    date_parse_warning: str = ""

    # Task 4 Provenance and Validation JSON Field
    field_provenance: str = "{}"

    # Task 5 Classification Fields
    classification_status: str = "insufficient_data" # "it", "non_it", "ambiguous", "insufficient_data"
    classification_explanation: str = "{}"
    classification_override: str = "{}"

    def to_dict(self):
        """Converts to a flat dict matching RAW_SCHEMA_COLUMNS."""
        d = asdict(self)
        # Ensure all schema columns are present
        for col in RAW_SCHEMA_COLUMNS:
            if col not in d:
                d[col] = ""
        # Make sure boolean-like fields are strings to match CSV reading
        if not isinstance(d.get("rendering_used"), str):
            d["rendering_used"] = str(d.get("rendering_used", False))
        return {k: str(d[k]) for k in RAW_SCHEMA_COLUMNS if k in d}

    @staticmethod
    def create_for_url(url, batch_id):
        """Creates a pre-populated ExtractionResult for a URL."""
        hostname = get_hostname(url)
        return ExtractionResult(
            source_url=url,
            final_url=url,
            source_hostname=hostname,
            source_platform=hostname,
            collection_batch_id=batch_id,
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )
