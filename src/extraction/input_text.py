from __future__ import annotations

import pandas as pd


BOILERPLATE_MARKERS = (
    "please refer the full details",
    "refer the full details",
    "please see the full job description",
    "please refer to the full details",
    "please refer to the vacancy advert",
    "topjobs sri lanka job network",
    "most popular online job site in sri lanka",
    "recruitment automation for employers",
    "refer to the image flyer",
    "all terms and conditions apply",
)


def safe_text(value) -> str:
    """Convert a scalar missing value to an empty string."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    value = str(value).strip()
    return "" if value.lower() in {"nan", "none", "nat"} else value


def is_boilerplate(text: str) -> bool:
    normalised = text.casefold()
    return any(marker in normalised for marker in BOILERPLATE_MARKERS)


def build_extraction_text(row: pd.Series | dict) -> tuple[str, str]:
    """
    Build the exact text used by both production extraction and evaluation.

    Combines title, description, and requirements when present. Requirements
    must be genuine input available to the system; do not pass a label-derived
    requirements field when measuring extraction accuracy against that same
    ground truth.
    """
    description = safe_text(row.get("job_description", ""))
    title = safe_text(row.get("job_title_raw", row.get("job_title", "")))
    requirements = safe_text(row.get("requirements", ""))

    usable_description = bool(description) and not is_boilerplate(description)
    parts = [part for part in (title, description, requirements) if part]
    text = " ".join(parts)

    if not usable_description:
        provenance = "title_fallback"
    elif "--- OCR Text ---" in description:
        provenance = "hybrid"
    elif "ocr" in safe_text(row.get("description_source", "")).lower():
        provenance = "ocr"
    else:
        provenance = "description"

    return text, provenance
