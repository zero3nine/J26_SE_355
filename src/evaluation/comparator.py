"""
Field-by-Field Comparator and Normalization Module.
Academic Research Component for Information Extraction Quality Benchmark.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from dateutil.parser import parse as parse_date

from src.evaluation.schema import BenchmarkRecord


# Valid evaluation outcomes for a single field comparison
FIELD_OUTCOMES: Set[str] = {
    "correct",              # Verified reference matched prediction (True Positive)
    "incorrect",            # Verified reference differed from prediction (Extraction Error)
    "missing_prediction",   # Verified reference was not extracted by the system (False Negative)
    "correct_absence",      # Unavailable reference correctly left empty by system (True Negative)
    "over_extracted",       # Unavailable reference was hallucinated/extracted (False Positive)
    "ambiguous_excluded",   # Ambiguous reference excluded from strict evaluation
    "not_reviewed",         # Field not reviewed, excluded from calculation
}


@dataclass
class FieldEvaluationResult:
    """Outcome of evaluating a single field for a record."""
    field_name: str
    status: str             # One of FIELD_OUTCOMES
    reference_status: str   # 'verified', 'unavailable', 'ambiguous', 'not_reviewed'
    expected_value: Any
    predicted_value: Any
    details: str = ""


@dataclass
class RecordEvaluationResult:
    """Outcome of evaluating all fields for a single job advertisement."""
    benchmark_id: str
    source_url: str
    source_platform: str
    country: str
    collection_context: str
    extraction_method: str
    field_results: Dict[str, FieldEvaluationResult] = field(default_factory=dict)
    matched_prediction_id: Optional[str] = None

    @property
    def is_fully_correct(self) -> bool:
        """True if every verified and unavailable field is correct/correct_absence."""
        for fr in self.field_results.values():
            if fr.reference_status == "verified" and fr.status != "correct":
                return False
            if fr.reference_status == "unavailable" and fr.status != "correct_absence":
                return False
        return True


# ============================================================================
# Normalization Helper Functions
# ============================================================================

def normalize_text_for_comparison(text: Any) -> str:
    """Normalizes string for comparison: lowercase, strip punctuation, collapse whitespace."""
    if text is None:
        return ""
    s = str(text).strip().lower()
    if s in ("nan", "none", "null", "undefined"):
        return ""
    # Strip punctuation and multiple spaces
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


def normalize_company_name(name: Any) -> str:
    """Normalizes company name, removing legal entity suffixes and whitespace."""
    s = normalize_text_for_comparison(name)
    if not s:
        return ""
    # Remove common corporate suffixes
    suffixes = [
        r"\bpvt\s*ltd\b", r"\bprivate\s*limited\b", r"\bpte\s*ltd\b",
        r"\bltd\b", r"\blimited\b", r"\binc\b", r"\bcorporation\b",
        r"\bcorp\b", r"\bco\b", r"\bllc\b", r"\bgmbh\b", r"\bhiring\s*for\s*client\b"
    ]
    for suf in suffixes:
        s = re.sub(suf, "", s)
    return " ".join(s.split())


def normalize_date_to_iso(date_val: Any) -> str:
    """Standardizes date representations to YYYY-MM-DD."""
    if not date_val or str(date_val).strip().lower() in ("nan", "none", "null", ""):
        return ""
    s = str(date_val).strip()
    # Try direct prefix extraction if standard ISO 8601 (YYYY-MM-DDTHH:MM:SS)
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    if match:
        return match.group(1)
    try:
        dt = parse_date(s)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


def normalize_float(val: Any) -> Optional[float]:
    """Converts a value to float, handling string formats with commas."""
    if val is None or str(val).strip().lower() in ("nan", "none", "null", ""):
        return None
    try:
        clean_str = str(val).replace(",", "").strip()
        return float(clean_str)
    except (ValueError, TypeError):
        return None


# ============================================================================
# Field Evaluation Dispatchers
# ============================================================================

def evaluate_string_field(
    field_name: str,
    reference_status: str,
    expected_raw: str,
    predicted_raw: Any,
    normalizer=normalize_text_for_comparison,
    min_overlap: float = 0.8
) -> FieldEvaluationResult:
    """Compares a text field with appropriate handling of reference status."""
    if reference_status == "not_reviewed":
        return FieldEvaluationResult(field_name, "not_reviewed", reference_status, expected_raw, predicted_raw)

    if reference_status == "ambiguous":
        return FieldEvaluationResult(
            field_name, "ambiguous_excluded", reference_status, expected_raw, predicted_raw,
            details="Source value is ambiguous and excluded from strict accuracy calculation."
        )

    norm_pred = normalizer(predicted_raw)
    norm_exp = normalizer(expected_raw)

    if reference_status == "unavailable":
        if not norm_pred:
            return FieldEvaluationResult(field_name, "correct_absence", reference_status, expected_raw, predicted_raw)
        else:
            return FieldEvaluationResult(
                field_name, "over_extracted", reference_status, expected_raw, predicted_raw,
                details=f"Field is unavailable in source but prediction extracted: '{predicted_raw}'"
            )

    # reference_status == "verified"
    if not norm_pred:
        return FieldEvaluationResult(
            field_name, "missing_prediction", reference_status, expected_raw, predicted_raw,
            details=f"Expected verified value '{expected_raw}', but prediction was empty."
        )

    # Exact normalized match
    if norm_pred == norm_exp:
        return FieldEvaluationResult(field_name, "correct", reference_status, expected_raw, predicted_raw)

    # Substring / Token containment check (e.g. for long company names or slightly varied titles)
    tokens_exp = set(norm_exp.split())
    tokens_pred = set(norm_pred.split())
    if tokens_exp and tokens_pred:
        jaccard = len(tokens_exp & tokens_pred) / len(tokens_exp | tokens_pred)
        if jaccard >= min_overlap:
            return FieldEvaluationResult(
                field_name, "correct", reference_status, expected_raw, predicted_raw,
                details=f"Token overlap match (Jaccard: {jaccard:.2f})"
            )

    return FieldEvaluationResult(
        field_name, "incorrect", reference_status, expected_raw, predicted_raw,
        details=f"Mismatch: expected '{expected_raw}' != predicted '{predicted_raw}'"
    )


def evaluate_date_field(
    field_name: str,
    reference_status: str,
    expected_iso: str,
    predicted_raw: Any
) -> FieldEvaluationResult:
    """Evaluates posting or closing date fields against ISO format."""
    if reference_status == "not_reviewed":
        return FieldEvaluationResult(field_name, "not_reviewed", reference_status, expected_iso, predicted_raw)

    if reference_status == "ambiguous":
        return FieldEvaluationResult(field_name, "ambiguous_excluded", reference_status, expected_iso, predicted_raw)

    pred_iso = normalize_date_to_iso(predicted_raw)
    exp_iso = normalize_date_to_iso(expected_iso)

    if reference_status == "unavailable":
        if not pred_iso:
            return FieldEvaluationResult(field_name, "correct_absence", reference_status, expected_iso, predicted_raw)
        else:
            return FieldEvaluationResult(
                field_name, "over_extracted", reference_status, expected_iso, predicted_raw,
                details=f"Date unavailable in source but predicted as '{pred_iso}'"
            )

    # reference_status == "verified"
    if not pred_iso:
        return FieldEvaluationResult(
            field_name, "missing_prediction", reference_status, expected_iso, predicted_raw,
            details=f"Expected verified date '{exp_iso}', but prediction was empty/unparseable."
        )

    if pred_iso == exp_iso:
        return FieldEvaluationResult(field_name, "correct", reference_status, expected_iso, predicted_raw)
    else:
        return FieldEvaluationResult(
            field_name, "incorrect", reference_status, expected_iso, predicted_raw,
            details=f"Date mismatch: expected '{exp_iso}' != predicted '{pred_iso}'"
        )


def evaluate_description_field(
    reference_status: str,
    expected_snippet: str,
    expected_min_len: int,
    predicted_raw: Any
) -> FieldEvaluationResult:
    """Evaluates job description extraction using snippet presence and length criteria."""
    if reference_status == "not_reviewed":
        return FieldEvaluationResult("description", "not_reviewed", reference_status, expected_snippet, predicted_raw)

    if reference_status == "ambiguous":
        return FieldEvaluationResult("description", "ambiguous_excluded", reference_status, expected_snippet, predicted_raw)

    pred_text = str(predicted_raw or "").strip()
    if pred_text.lower() in ("nan", "none", "null"):
        pred_text = ""

    if reference_status == "unavailable":
        if not pred_text:
            return FieldEvaluationResult("description", "correct_absence", reference_status, expected_snippet, predicted_raw)
        else:
            return FieldEvaluationResult(
                "description", "over_extracted", reference_status, expected_snippet, predicted_raw,
                details=f"Description unavailable in source but prediction extracted {len(pred_text)} chars"
            )

    # Verified
    if not pred_text:
        return FieldEvaluationResult(
            "description", "missing_prediction", reference_status, expected_snippet, predicted_raw,
            details="Verified description missing in prediction."
        )

    # Check minimum length threshold
    if expected_min_len > 0 and len(pred_text) < expected_min_len:
        return FieldEvaluationResult(
            "description", "incorrect", reference_status, expected_snippet, predicted_raw,
            details=f"Predicted description too short ({len(pred_text)} chars < expected {expected_min_len} chars)"
        )

    # Check snippet containment if provided
    if expected_snippet:
        norm_pred = normalize_text_for_comparison(pred_text)
        norm_snip = normalize_text_for_comparison(expected_snippet)
        if norm_snip and norm_snip not in norm_pred:
            # Check partial snippet overlap
            snip_tokens = norm_snip.split()
            if len(snip_tokens) > 3:
                sub_snip = " ".join(snip_tokens[:4])
                if sub_snip not in norm_pred:
                    return FieldEvaluationResult(
                        "description", "incorrect", reference_status, expected_snippet, predicted_raw,
                        details="Key excerpt snippet not found in extracted description."
                    )

    return FieldEvaluationResult("description", "correct", reference_status, expected_snippet, f"{len(pred_text)} chars")


def evaluate_salary_fields(
    benchmark: BenchmarkRecord,
    prediction: Dict[str, Any]
) -> FieldEvaluationResult:
    """Evaluates salary extraction and normalization (disclosure, min, max, currency, period)."""
    status_sal = benchmark.status_salary
    if status_sal == "not_reviewed":
        return FieldEvaluationResult("salary", "not_reviewed", status_sal, None, None)
    if status_sal == "ambiguous":
        return FieldEvaluationResult("salary", "ambiguous_excluded", status_sal, None, None)

    # Determine predicted disclosure status
    pred_disclosed_raw = prediction.get("salary_disclosed")
    if pred_disclosed_raw is not None and str(pred_disclosed_raw).strip() != "":
        pred_disclosed = str(pred_disclosed_raw).strip().lower() in ("true", "1", "yes")
    else:
        # Infer from raw or normalized min/max/text
        sal_text = str(prediction.get("salary_text_raw", "") or "")
        sal_min = prediction.get("salary_min_normalized") or prediction.get("salary_min_raw")
        pred_disclosed = bool(sal_min and str(sal_min).strip().lower() not in ("nan", "none", "")) or bool(sal_text.strip())

    if status_sal == "unavailable" or not benchmark.expected_salary_disclosed:
        if not pred_disclosed:
            return FieldEvaluationResult(
                "salary", "correct_absence", status_sal,
                "undisclosed", "undisclosed"
            )
        else:
            return FieldEvaluationResult(
                "salary", "over_extracted", status_sal,
                "undisclosed", f"disclosed (text: {prediction.get('salary_text_raw')})",
                details="Salary is undisclosed in source, but prediction claimed disclosed salary."
            )

    # status_salary is verified and expected_salary_disclosed is True
    if not pred_disclosed:
        return FieldEvaluationResult(
            "salary", "missing_prediction", status_sal,
            f"min={benchmark.expected_salary_min}, max={benchmark.expected_salary_max}",
            "undisclosed",
            details="Salary was disclosed in source advertisement but missed/marked undisclosed by system."
        )

    # Verify quantitative values
    pred_min = normalize_float(prediction.get("salary_min_normalized") or prediction.get("salary_min_raw"))
    pred_max = normalize_float(prediction.get("salary_max_normalized") or prediction.get("salary_max_raw"))
    pred_curr = str(prediction.get("salary_currency_normalized") or prediction.get("salary_currency_raw") or "").strip().upper()
    pred_period = str(prediction.get("salary_period_normalized") or prediction.get("salary_period_raw") or "").strip().lower()

    mismatches = []
    # Check minimum amount
    if benchmark.expected_salary_min is not None:
        if pred_min is None or abs(pred_min - benchmark.expected_salary_min) > 1.0:
            mismatches.append(f"min {pred_min} != {benchmark.expected_salary_min}")

    # Check maximum amount
    if benchmark.expected_salary_max is not None:
        if pred_max is None or abs(pred_max - benchmark.expected_salary_max) > 1.0:
            mismatches.append(f"max {pred_max} != {benchmark.expected_salary_max}")

    # Check currency if verified
    if benchmark.expected_salary_currency:
        if pred_curr != benchmark.expected_salary_currency.upper():
            mismatches.append(f"curr {pred_curr} != {benchmark.expected_salary_currency}")

    # Check pay period if verified
    if benchmark.expected_salary_period and benchmark.expected_salary_period != "unspecified":
        if pred_period and pred_period != benchmark.expected_salary_period:
            mismatches.append(f"period {pred_period} != {benchmark.expected_salary_period}")

    if not mismatches:
        return FieldEvaluationResult(
            "salary", "correct", status_sal,
            f"{benchmark.expected_salary_currency} {benchmark.expected_salary_min}-{benchmark.expected_salary_max}",
            f"{pred_curr} {pred_min}-{pred_max}"
        )
    else:
        return FieldEvaluationResult(
            "salary", "incorrect", status_sal,
            f"{benchmark.expected_salary_currency} {benchmark.expected_salary_min}-{benchmark.expected_salary_max}",
            f"{pred_curr} {pred_min}-{pred_max}",
            details="Salary mismatch: " + "; ".join(mismatches)
        )


def evaluate_skills_field(
    reference_status: str,
    expected_skills_raw: str,
    predicted_raw: Any,
    min_jaccard: float = 0.5
) -> FieldEvaluationResult:
    """Evaluates canonical skill labels."""
    if reference_status == "not_reviewed":
        return FieldEvaluationResult("skills", "not_reviewed", reference_status, expected_skills_raw, predicted_raw)
    if reference_status == "ambiguous":
        return FieldEvaluationResult("skills", "ambiguous_excluded", reference_status, expected_skills_raw, predicted_raw)

    def _parse_skills(val: Any) -> Set[str]:
        if not val or str(val).strip().lower() in ("nan", "none", "null", ""):
            return set()
        s = str(val).strip()
        # Handle JSON array or comma separated
        if s.startswith("[") and s.endswith("]"):
            import json
            try:
                items = json.loads(s)
                return {normalize_text_for_comparison(x) for x in items if x}
            except Exception:
                pass
        return {normalize_text_for_comparison(x) for x in s.split(",") if x.strip()}

    exp_set = _parse_skills(expected_skills_raw)
    pred_set = _parse_skills(predicted_raw)

    if reference_status == "unavailable":
        if not pred_set:
            return FieldEvaluationResult("skills", "correct_absence", reference_status, expected_skills_raw, predicted_raw)
        else:
            return FieldEvaluationResult("skills", "over_extracted", reference_status, expected_skills_raw, predicted_raw)

    # Verified
    if not pred_set:
        return FieldEvaluationResult("skills", "missing_prediction", reference_status, expected_skills_raw, predicted_raw)

    # Compute Jaccard
    jaccard = len(exp_set & pred_set) / len(exp_set | pred_set) if (exp_set or pred_set) else 1.0
    if jaccard >= min_jaccard or exp_set.issubset(pred_set):
        return FieldEvaluationResult(
            "skills", "correct", reference_status, expected_skills_raw, predicted_raw,
            details=f"Jaccard similarity: {jaccard:.2f}"
        )
    else:
        return FieldEvaluationResult(
            "skills", "incorrect", reference_status, expected_skills_raw, predicted_raw,
            details=f"Skills mismatch (Jaccard: {jaccard:.2f})"
        )


# ============================================================================
# Main Record Comparator
# ============================================================================

def compare_single_record(
    benchmark: BenchmarkRecord,
    prediction: Optional[Dict[str, Any]]
) -> RecordEvaluationResult:
    """Compares one verified benchmark record against a prediction dictionary."""
    rec_res = RecordEvaluationResult(
        benchmark_id=benchmark.benchmark_id,
        source_url=benchmark.source_url,
        source_platform=benchmark.source_platform,
        country=benchmark.country,
        collection_context=benchmark.collection_context,
        extraction_method=benchmark.extraction_method,
    )

    if prediction is None:
        # All verified fields become missing_prediction; all unavailable become correct_absence
        status_map = {
            "job_title": benchmark.status_job_title,
            "company": benchmark.status_company,
            "location_raw": benchmark.status_location,
            "country_normalized": benchmark.status_location,
            "city_normalized": benchmark.status_location,
            "work_mode": benchmark.status_work_mode,
            "posted_date": benchmark.status_posted_date,
            "closing_date": benchmark.status_closing_date,
            "description": benchmark.status_description,
            "salary": benchmark.status_salary,
            "skills": benchmark.status_skills,
        }
        for fld, st in status_map.items():
            if st == "verified":
                outcome = "missing_prediction"
            elif st == "unavailable":
                outcome = "correct_absence"
            elif st == "ambiguous":
                outcome = "ambiguous_excluded"
            else:
                outcome = "not_reviewed"
            rec_res.field_results[fld] = FieldEvaluationResult(
                fld, outcome, st, None, None, details="No matching prediction record found for URL/ID."
            )
        return rec_res

    rec_res.matched_prediction_id = str(prediction.get("job_id", ""))

    # 1. Job Title
    pred_title = prediction.get("job_title_raw") or prediction.get("job_title", "")
    rec_res.field_results["job_title"] = evaluate_string_field(
        "job_title", benchmark.status_job_title, benchmark.expected_job_title_raw, pred_title
    )

    # 2. Company
    pred_company = prediction.get("company_raw") or prediction.get("company", "")
    rec_res.field_results["company"] = evaluate_string_field(
        "company", benchmark.status_company, benchmark.expected_company_raw, pred_company,
        normalizer=normalize_company_name
    )

    # 3. Location Raw
    pred_loc_raw = prediction.get("location_raw") or prediction.get("location", "")
    rec_res.field_results["location_raw"] = evaluate_string_field(
        "location_raw", benchmark.status_location, benchmark.expected_location_raw, pred_loc_raw
    )

    # 4. Country Normalized (evaluates location normalizer from Task 1)
    pred_country = prediction.get("country_normalized") or prediction.get("country_raw") or prediction.get("country", "")
    rec_res.field_results["country_normalized"] = evaluate_string_field(
        "country_normalized", benchmark.status_location, benchmark.expected_country_normalized, pred_country
    )

    # 5. City Normalized
    pred_city = prediction.get("city_normalized", "")
    rec_res.field_results["city_normalized"] = evaluate_string_field(
        "city_normalized", benchmark.status_location, benchmark.expected_city_normalized, pred_city
    )

    # 6. Work Mode
    pred_work_mode = prediction.get("work_mode") or prediction.get("work_mode_raw", "")
    rec_res.field_results["work_mode"] = evaluate_string_field(
        "work_mode", benchmark.status_work_mode, benchmark.expected_work_mode, pred_work_mode
    )

    # 7. Posted Date
    pred_posted = (
        prediction.get("posted_date_raw") or
        prediction.get("posted_date") or
        prediction.get("listing_posted_date_raw", "")
    )
    rec_res.field_results["posted_date"] = evaluate_date_field(
        "posted_date", benchmark.status_posted_date, benchmark.expected_posted_date, pred_posted
    )

    # 8. Closing Date
    pred_closing = prediction.get("closing_date_raw") or prediction.get("closing_date", "")
    rec_res.field_results["closing_date"] = evaluate_date_field(
        "closing_date", benchmark.status_closing_date, benchmark.expected_closing_date, pred_closing
    )

    # 9. Description
    pred_desc = prediction.get("job_description_raw") or prediction.get("job_description", "")
    rec_res.field_results["description"] = evaluate_description_field(
        benchmark.status_description,
        benchmark.expected_description_snippet,
        benchmark.expected_description_min_len,
        pred_desc
    )

    # 10. Salary
    rec_res.field_results["salary"] = evaluate_salary_fields(benchmark, prediction)

    # 11. Skills
    pred_skills = prediction.get("skills_raw") or prediction.get("skills", "")
    rec_res.field_results["skills"] = evaluate_skills_field(
        benchmark.status_skills, benchmark.expected_skills, pred_skills
    )

    return rec_res


def compare_records(
    benchmarks: List[BenchmarkRecord],
    predictions: List[Dict[str, Any]],
    match_key: str = "auto"
) -> Tuple[List[RecordEvaluationResult], List[BenchmarkRecord], List[Dict[str, Any]]]:
    """Matches predictions to benchmark records and evaluates field by field.
    
    Args:
        benchmarks: List of verified BenchmarkRecord instances.
        predictions: List of prediction dictionaries (e.g. from scraping CSV).
        match_key: Matching strategy ('auto', 'source_url', 'job_id').

    Returns:
        tuple: (evaluated_records, unmatched_benchmarks, extra_predictions)
    """
    def _canon_url(u: Any) -> str:
        if not u:
            return ""
        s = str(u).strip().lower()
        s = re.sub(r"/+$", "", s)
        return s

    # Index predictions
    pred_by_url: Dict[str, Dict[str, Any]] = {}
    pred_by_id: Dict[str, Dict[str, Any]] = {}

    for p in predictions:
        url = _canon_url(p.get("source_url") or p.get("final_url"))
        if url and url not in pred_by_url:
            pred_by_url[url] = p
        jid = str(p.get("job_id", "")).strip()
        if jid and jid not in pred_by_id:
            pred_by_id[jid] = p
        sjid = str(p.get("source_job_id", "")).strip()
        if sjid and sjid not in pred_by_id:
            pred_by_id[sjid] = p

    results: List[RecordEvaluationResult] = []
    unmatched_benchmarks: List[BenchmarkRecord] = []
    matched_prediction_ids: Set[str] = set()

    for bm in benchmarks:
        pred_match: Optional[Dict[str, Any]] = None
        bm_url = _canon_url(bm.source_url)

        if match_key in ("auto", "source_url"):
            pred_match = pred_by_url.get(bm_url)

        if pred_match is None and match_key in ("auto", "job_id"):
            # Try to match by source_job_id or URL substring in predictions
            pred_match = pred_by_id.get(bm.benchmark_id)

        if pred_match is not None:
            pid = str(pred_match.get("job_id", ""))
            if pid:
                matched_prediction_ids.add(pid)
            res = compare_single_record(bm, pred_match)
            results.append(res)
        else:
            unmatched_benchmarks.append(bm)
            res = compare_single_record(bm, None)
            results.append(res)

    # Identify extra predictions not in benchmark
    extra_predictions: List[Dict[str, Any]] = []
    for p in predictions:
        pid = str(p.get("job_id", ""))
        url = _canon_url(p.get("source_url") or p.get("final_url"))
        bm_urls = {_canon_url(bm.source_url) for bm in benchmarks}
        if pid not in matched_prediction_ids and url not in bm_urls:
            extra_predictions.append(p)

    return results, unmatched_benchmarks, extra_predictions
