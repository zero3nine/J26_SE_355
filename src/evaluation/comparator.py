"""
Field-by-Field Comparator and Normalization Module.
Academic Research Component for Information Extraction Quality Benchmark.

Features:
- Preserves both raw and normalized values for every comparison.
- Evaluates exact agreement rate and normalized agreement rate.
- Enforces strict currency and pay-period compatibility checks before numeric salary comparison.
- Computes numeric absolute error (MAE) on comparable monetary values.
- Multi-label evaluation for canonical skill sets.
- Generates structured error records categorizing missing, incorrect, over-extracted, and incompatible predictions.
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
    "correct",                  # Verified reference matched prediction (True Positive)
    "incorrect",                # Verified reference differed from prediction (Extraction Error)
    "missing_prediction",       # Verified reference was not extracted by the system (False Negative)
    "correct_absence",          # Unavailable reference correctly left empty by system (True Negative)
    "over_extracted",           # Unavailable reference was hallucinated/extracted (False Positive)
    "ambiguous_excluded",       # Ambiguous reference excluded from strict evaluation
    "not_reviewed",             # Field not reviewed, excluded from calculation
    "incompatible_currency",    # Salary amount cannot be compared due to mismatched currency
    "incompatible_pay_period",  # Salary amount cannot be compared due to mismatched pay frequency
}


@dataclass
class FieldEvaluationResult:
    """Outcome of evaluating a single field for a record, preserving raw and normalized states."""
    field_name: str
    status: str                 # One of FIELD_OUTCOMES
    reference_status: str       # 'verified', 'unavailable', 'ambiguous', 'not_reviewed'
    expected_raw: Any
    expected_normalized: Any
    predicted_raw: Any
    predicted_normalized: Any
    is_exact_match: bool = False
    is_normalized_match: bool = False
    error_category: str = "none"  # 'missing', 'incorrect_value', 'hallucination', 'incompatible_currency', etc.
    error_type: str = "none"      # 'none', 'missing', 'incorrect', 'ambiguous', 'over_extracted'
    numeric_error: Optional[float] = None  # |predicted - expected| for comparable amounts
    details: str = ""

    # Backwards compatibility properties
    @property
    def expected_value(self) -> Any:
        return self.expected_raw

    @property
    def predicted_value(self) -> Any:
        return self.predicted_raw


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
    # Remove common corporate suffixes across LK, IN, SG, MY
    suffixes = [
        r"\bpvt\s*ltd\b", r"\bprivate\s*limited\b", r"\bpte\s*ltd\b",
        r"\bsdn\s*bhd\b", r"\bbhd\b", r"\bberhad\b",
        r"\bltd\b", r"\blimited\b", r"\binc\b", r"\bcorporation\b",
        r"\bcorp\b", r"\bco\b", r"\bllc\b", r"\bgmbh\b",
        r"\bhiring\s*for\s*client\s*(companies)?\b"
    ]
    for suf in suffixes:
        s = re.sub(suf, "", s)
    return " ".join(s.split())


def normalize_date_to_iso(date_val: Any) -> str:
    """Standardizes date representations to YYYY-MM-DD."""
    if not date_val or str(date_val).strip().lower() in ("nan", "none", "null", ""):
        return ""
    s = str(date_val).strip()
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


def normalize_currency_code(curr: Any) -> str:
    """Normalizes currency token to ISO 4217 uppercase code."""
    if not curr or str(curr).strip().lower() in ("nan", "none", "null", ""):
        return ""
    s = str(curr).strip().lower()
    mapping = {
        "lkr": "LKR", "slr": "LKR", "rs": "LKR", "inr": "INR", "₹": "INR",
        "lpa": "INR", "sgd": "SGD", "s$": "SGD", "myr": "MYR", "rm": "MYR",
        "ringgit": "MYR", "usd": "USD", "us$": "USD", "eur": "EUR", "€": "EUR",
        "gbp": "GBP", "£": "GBP"
    }
    return mapping.get(s, s.upper())


def normalize_pay_period(period: Any) -> str:
    """Standardizes pay frequency to hourly, daily, monthly, annual, or unspecified."""
    if not period or str(period).strip().lower() in ("nan", "none", "null", ""):
        return "unspecified"
    s = str(period).strip().lower()
    if "hour" in s:
        return "hourly"
    if "day" in s or "daily" in s:
        return "daily"
    if "month" in s:
        return "monthly"
    if "year" in s or "annum" in s or "annual" in s or "lpa" in s:
        return "annual"
    return "unspecified"


COUNTRY_CANONICAL_MAP: Dict[str, str] = {
    "lk": "sri lanka", "lka": "sri lanka", "sri lanka": "sri lanka", "srilanka": "sri lanka", "ceylon": "sri lanka",
    "in": "india", "ind": "india", "india": "india", "bharat": "india",
    "sg": "singapore", "sgp": "singapore", "singapore": "singapore",
    "my": "malaysia", "mys": "malaysia", "malaysia": "malaysia",
    "us": "united states", "usa": "united states", "united states": "united states",
    "uk": "united kingdom", "united kingdom": "united kingdom",
    "au": "australia", "australia": "australia",
}


def normalize_country_name(country: Any) -> str:
    """Normalizes country names and ISO alpha-2/3 codes to canonical lowercase standard."""
    if not country or str(country).strip().lower() in ("nan", "none", "null", ""):
        return ""
    clean = re.sub(r"[^\w\s]", "", str(country).lower().strip())
    clean_sq = re.sub(r"\s+", " ", clean).strip()
    return COUNTRY_CANONICAL_MAP.get(clean_sq, clean_sq)


# ============================================================================
# Field-Specific Evaluation Functions
# ============================================================================

def evaluate_text_field(
    field_name: str,
    reference_status: str,
    expected_raw: Any,
    predicted_raw: Any,
    normalizer=normalize_text_for_comparison,
    min_overlap: float = 0.80
) -> FieldEvaluationResult:
    """Evaluates a text field preserving raw and normalized representations."""
    exp_str = "" if expected_raw is None else str(expected_raw).strip()
    if exp_str.lower() in ("nan", "none", "null"):
        exp_str = ""
    pred_str = "" if predicted_raw is None else str(predicted_raw).strip()
    if pred_str.lower() in ("nan", "none", "null"):
        pred_str = ""

    norm_exp = normalizer(exp_str)
    norm_pred = normalizer(pred_str)

    is_exact = bool(exp_str and pred_str and exp_str.lower() == pred_str.lower())
    is_norm = False

    if reference_status == "not_reviewed":
        return FieldEvaluationResult(
            field_name, "not_reviewed", reference_status,
            exp_str, norm_exp, pred_str, norm_pred,
            is_exact_match=False, is_normalized_match=False
        )

    if reference_status == "ambiguous":
        return FieldEvaluationResult(
            field_name, "ambiguous_excluded", reference_status,
            exp_str, norm_exp, pred_str, norm_pred,
            error_category="ambiguous_source_data", error_type="ambiguous",
            details="Field is ambiguous in source; excluded from strict agreement rates."
        )

    if reference_status == "unavailable":
        if not norm_pred:
            return FieldEvaluationResult(
                field_name, "correct_absence", reference_status,
                exp_str, norm_exp, pred_str, norm_pred,
                is_exact_match=True, is_normalized_match=True
            )
        else:
            return FieldEvaluationResult(
                field_name, "over_extracted", reference_status,
                exp_str, norm_exp, pred_str, norm_pred,
                is_exact_match=False, is_normalized_match=False,
                error_category="hallucination_on_unavailable_field", error_type="over_extracted",
                details=f"Field unavailable in source but prediction extracted: '{pred_str}'"
            )

    # reference_status == "verified"
    if not norm_pred:
        return FieldEvaluationResult(
            field_name, "missing_prediction", reference_status,
            exp_str, norm_exp, pred_str, norm_pred,
            is_exact_match=False, is_normalized_match=False,
            error_category="missing_prediction", error_type="missing",
            details=f"Expected verified '{exp_str}', but prediction was empty."
        )

    # Check normalized agreement
    if norm_exp == norm_pred:
        is_norm = True
    else:
        # Check token Jaccard similarity
        tokens_e = set(norm_exp.split())
        tokens_p = set(norm_pred.split())
        if tokens_e and tokens_p:
            jaccard = len(tokens_e & tokens_p) / len(tokens_e | tokens_p)
            if jaccard >= min_overlap:
                is_norm = True

    if is_norm:
        return FieldEvaluationResult(
            field_name, "correct", reference_status,
            exp_str, norm_exp, pred_str, norm_pred,
            is_exact_match=is_exact, is_normalized_match=True
        )
    else:
        return FieldEvaluationResult(
            field_name, "incorrect", reference_status,
            exp_str, norm_exp, pred_str, norm_pred,
            is_exact_match=False, is_normalized_match=False,
            error_category="incorrect_text_value", error_type="incorrect",
            details=f"Mismatch: expected '{norm_exp}' != predicted '{norm_pred}'"
        )


def evaluate_date_field(
    field_name: str,
    reference_status: str,
    expected_raw: Any,
    predicted_raw: Any
) -> FieldEvaluationResult:
    """Evaluates date fields using unambiguous ISO YYYY-MM-DD parsing."""
    exp_str = "" if expected_raw is None else str(expected_raw).strip()
    pred_str = "" if predicted_raw is None else str(predicted_raw).strip()
    norm_exp = normalize_date_to_iso(exp_str)
    norm_pred = normalize_date_to_iso(pred_str)

    is_exact = bool(exp_str and pred_str and exp_str == pred_str)
    is_norm = bool(norm_exp and norm_pred and norm_exp == norm_pred)

    if reference_status == "not_reviewed":
        return FieldEvaluationResult(
            field_name, "not_reviewed", reference_status,
            exp_str, norm_exp, pred_str, norm_pred
        )
    if reference_status == "ambiguous":
        return FieldEvaluationResult(
            field_name, "ambiguous_excluded", reference_status,
            exp_str, norm_exp, pred_str, norm_pred,
            error_category="ambiguous_date_format", error_type="ambiguous",
            details="Relative or ambiguous date in source; excluded from strict accuracy."
        )
    if reference_status == "unavailable":
        if not norm_pred:
            return FieldEvaluationResult(
                field_name, "correct_absence", reference_status,
                exp_str, norm_exp, pred_str, norm_pred,
                is_exact_match=True, is_normalized_match=True
            )
        else:
            return FieldEvaluationResult(
                field_name, "over_extracted", reference_status,
                exp_str, norm_exp, pred_str, norm_pred,
                is_exact_match=False, is_normalized_match=False,
                error_category="hallucinated_date", error_type="over_extracted",
                details=f"Date unavailable in source but prediction extracted: '{pred_str}'"
            )

    # Verified
    if not norm_pred:
        return FieldEvaluationResult(
            field_name, "missing_prediction", reference_status,
            exp_str, norm_exp, pred_str, norm_pred,
            is_exact_match=False, is_normalized_match=False,
            error_category="missing_date", error_type="missing",
            details=f"Expected verified date '{norm_exp}', but prediction was empty/unparseable."
        )

    if is_norm:
        return FieldEvaluationResult(
            field_name, "correct", reference_status,
            exp_str, norm_exp, pred_str, norm_pred,
            is_exact_match=is_exact, is_normalized_match=True
        )
    else:
        return FieldEvaluationResult(
            field_name, "incorrect", reference_status,
            exp_str, norm_exp, pred_str, norm_pred,
            is_exact_match=False, is_normalized_match=False,
            error_category="date_mismatch", error_type="incorrect",
            details=f"Date mismatch: expected '{norm_exp}' != predicted '{norm_pred}'"
        )


def evaluate_numeric_salary_amount(
    field_name: str,
    reference_status: str,
    expected_amount: Optional[float],
    predicted_raw: Any,
    expected_curr: str,
    predicted_curr: str,
    expected_period: str,
    predicted_period: str,
    tolerance: float = 1.0
) -> FieldEvaluationResult:
    """Evaluates numeric salary minimum or maximum with currency and period compatibility checks."""
    pred_num = normalize_float(predicted_raw)
    exp_num = expected_amount

    norm_exp_curr = normalize_currency_code(expected_curr)
    norm_pred_curr = normalize_currency_code(predicted_curr)
    norm_exp_period = normalize_pay_period(expected_period)
    norm_pred_period = normalize_pay_period(predicted_period)

    if reference_status == "not_reviewed":
        return FieldEvaluationResult(
            field_name, "not_reviewed", reference_status,
            exp_num, exp_num, predicted_raw, pred_num
        )
    if reference_status == "ambiguous":
        return FieldEvaluationResult(
            field_name, "ambiguous_excluded", reference_status,
            exp_num, exp_num, predicted_raw, pred_num,
            error_category="ambiguous_salary", error_type="ambiguous"
        )
    if reference_status == "unavailable" or exp_num is None:
        if pred_num is None:
            return FieldEvaluationResult(
                field_name, "correct_absence", reference_status,
                exp_num, exp_num, predicted_raw, pred_num,
                is_exact_match=True, is_normalized_match=True
            )
        else:
            return FieldEvaluationResult(
                field_name, "over_extracted", reference_status,
                exp_num, exp_num, predicted_raw, pred_num,
                error_category="hallucinated_salary_amount", error_type="over_extracted",
                details=f"Salary is unavailable in source but prediction extracted: {pred_num}"
            )

    # reference_status == "verified" and exp_num is not None
    if pred_num is None:
        return FieldEvaluationResult(
            field_name, "missing_prediction", reference_status,
            exp_num, exp_num, predicted_raw, pred_num,
            error_category="missing_salary_amount", error_type="missing",
            details=f"Expected verified salary amount {exp_num}, but prediction had no value."
        )

    # Check Currency Compatibility
    if norm_exp_curr and norm_pred_curr and norm_exp_curr != norm_pred_curr:
        return FieldEvaluationResult(
            field_name, "incompatible_currency", reference_status,
            exp_num, exp_num, predicted_raw, pred_num,
            error_category="incompatible_currency", error_type="incorrect",
            details=f"Cannot compare numeric amounts: expected {norm_exp_curr} vs predicted {norm_pred_curr}"
        )

    # Check Pay Period Compatibility
    if (norm_exp_period != "unspecified" and norm_pred_period != "unspecified" and
            norm_exp_period != norm_pred_period):
        return FieldEvaluationResult(
            field_name, "incompatible_pay_period", reference_status,
            exp_num, exp_num, predicted_raw, pred_num,
            error_category="incompatible_pay_period", error_type="incorrect",
            details=f"Cannot compare numeric amounts: expected period '{norm_exp_period}' vs predicted '{norm_pred_period}'"
        )

    # Compatible: compute numeric absolute error
    abs_err = abs(pred_num - exp_num)
    is_exact = abs_err == 0.0
    is_norm = abs_err <= tolerance

    if is_norm:
        return FieldEvaluationResult(
            field_name, "correct", reference_status,
            exp_num, exp_num, predicted_raw, pred_num,
            is_exact_match=is_exact, is_normalized_match=True,
            numeric_error=abs_err
        )
    else:
        return FieldEvaluationResult(
            field_name, "incorrect", reference_status,
            exp_num, exp_num, predicted_raw, pred_num,
            is_exact_match=False, is_normalized_match=False,
            error_category="numeric_salary_mismatch", error_type="incorrect",
            numeric_error=abs_err,
            details=f"Numeric mismatch: expected {exp_num} != predicted {pred_num} (abs error: {abs_err:.2f})"
        )


def evaluate_multi_label_skills(
    reference_status: str,
    expected_skills_raw: str,
    predicted_raw: Any,
    min_jaccard: float = 0.50
) -> FieldEvaluationResult:
    """Evaluates multi-label canonical skill extraction."""
    def _parse_skills(val: Any) -> Set[str]:
        if not val or str(val).strip().lower() in ("nan", "none", "null", ""):
            return set()
        s = str(val).strip()
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

    if reference_status == "not_reviewed":
        return FieldEvaluationResult(
            "skills", "not_reviewed", reference_status,
            expected_skills_raw, exp_set, predicted_raw, pred_set
        )
    if reference_status == "ambiguous":
        return FieldEvaluationResult(
            "skills", "ambiguous_excluded", reference_status,
            expected_skills_raw, exp_set, predicted_raw, pred_set,
            error_category="ambiguous_skills", error_type="ambiguous"
        )
    if reference_status == "unavailable":
        if not pred_set:
            return FieldEvaluationResult(
                "skills", "correct_absence", reference_status,
                expected_skills_raw, exp_set, predicted_raw, pred_set,
                is_exact_match=True, is_normalized_match=True
            )
        else:
            return FieldEvaluationResult(
                "skills", "over_extracted", reference_status,
                expected_skills_raw, exp_set, predicted_raw, pred_set,
                error_category="hallucinated_skills", error_type="over_extracted",
                details=f"Skills unavailable in source but predicted {len(pred_set)} labels."
            )

    # Verified
    if not pred_set:
        return FieldEvaluationResult(
            "skills", "missing_prediction", reference_status,
            expected_skills_raw, exp_set, predicted_raw, pred_set,
            error_category="missing_skills", error_type="missing",
            details="Verified skill labels were not extracted."
        )

    is_exact = exp_set == pred_set
    jaccard = len(exp_set & pred_set) / len(exp_set | pred_set) if (exp_set or pred_set) else 1.0
    is_norm = (jaccard >= min_jaccard) or exp_set.issubset(pred_set)

    if is_norm:
        return FieldEvaluationResult(
            "skills", "correct", reference_status,
            expected_skills_raw, exp_set, predicted_raw, pred_set,
            is_exact_match=is_exact, is_normalized_match=True,
            details=f"Skill overlap Jaccard: {jaccard:.2f}"
        )
    else:
        return FieldEvaluationResult(
            "skills", "incorrect", reference_status,
            expected_skills_raw, exp_set, predicted_raw, pred_set,
            is_exact_match=False, is_normalized_match=False,
            error_category="skills_mismatch", error_type="incorrect",
            details=f"Skills mismatch: expected {len(exp_set)} labels vs predicted {len(pred_set)} (Jaccard: {jaccard:.2f})"
        )


def evaluate_salary_composite(
    benchmark: BenchmarkRecord,
    prediction: Dict[str, Any]
) -> FieldEvaluationResult:
    """Evaluates composite salary: disclosure, min, max, currency, period."""
    status_sal = benchmark.status_salary
    if status_sal == "not_reviewed":
        return FieldEvaluationResult("salary", "not_reviewed", status_sal, None, None, None, None)
    if status_sal == "ambiguous":
        return FieldEvaluationResult(
            "salary", "ambiguous_excluded", status_sal, None, None, None, None,
            error_category="ambiguous_salary", error_type="ambiguous"
        )

    pred_disc_raw = prediction.get("salary_disclosed")
    if pred_disc_raw is not None and str(pred_disc_raw).strip() != "":
        pred_disc = str(pred_disc_raw).strip().lower() in ("true", "1", "yes")
    else:
        s_min = prediction.get("salary_min_normalized") or prediction.get("salary_min_raw")
        s_txt = str(prediction.get("salary_text_raw", "") or "").strip()
        pred_disc = bool(s_min and str(s_min).strip().lower() not in ("nan", "none", "")) or bool(s_txt)

    exp_disc = benchmark.expected_salary_disclosed
    if status_sal == "unavailable" or not exp_disc:
        if not pred_disc:
            return FieldEvaluationResult(
                "salary", "correct_absence", status_sal,
                "undisclosed", "undisclosed", "undisclosed", "undisclosed",
                is_exact_match=True, is_normalized_match=True
            )
        else:
            return FieldEvaluationResult(
                "salary", "over_extracted", status_sal,
                "undisclosed", "undisclosed", "disclosed", "disclosed",
                error_category="hallucinated_salary_disclosure", error_type="over_extracted",
                details="Salary undisclosed in source but predicted disclosed."
            )

    # verified and disclosed
    if not pred_disc:
        return FieldEvaluationResult(
            "salary", "missing_prediction", status_sal,
            f"{benchmark.expected_salary_currency} {benchmark.expected_salary_min}-{benchmark.expected_salary_max}",
            "disclosed", "undisclosed", "undisclosed",
            error_category="missing_salary_amount", error_type="missing",
            details="Salary disclosed in source but missed by system."
        )

    pred_min = normalize_float(prediction.get("salary_min_normalized") or prediction.get("salary_min_raw"))
    pred_max = normalize_float(prediction.get("salary_max_normalized") or prediction.get("salary_max_raw"))
    pred_curr = normalize_currency_code(prediction.get("salary_currency_normalized") or prediction.get("salary_currency_raw"))
    exp_curr = normalize_currency_code(benchmark.expected_salary_currency)

    mismatches = []
    if benchmark.expected_salary_min is not None:
        if pred_min is None or abs(pred_min - benchmark.expected_salary_min) > 1.0:
            mismatches.append(f"min {pred_min} != {benchmark.expected_salary_min}")
    if benchmark.expected_salary_max is not None:
        if pred_max is None or abs(pred_max - benchmark.expected_salary_max) > 1.0:
            mismatches.append(f"max {pred_max} != {benchmark.expected_salary_max}")
    if exp_curr and pred_curr and exp_curr != pred_curr:
        mismatches.append(f"currency {pred_curr} != {exp_curr}")

    exp_str = f"{exp_curr} {benchmark.expected_salary_min}-{benchmark.expected_salary_max}"
    pred_str = f"{pred_curr} {pred_min}-{pred_max}"

    if not mismatches:
        return FieldEvaluationResult(
            "salary", "correct", status_sal,
            exp_str, exp_str, pred_str, pred_str,
            is_exact_match=True, is_normalized_match=True
        )
    else:
        return FieldEvaluationResult(
            "salary", "incorrect", status_sal,
            exp_str, exp_str, pred_str, pred_str,
            error_category="salary_mismatch", error_type="incorrect",
            details="; ".join(mismatches)
        )


# ============================================================================
# Main Record Comparison Engine
# ============================================================================

def compare_single_record(
    benchmark: BenchmarkRecord,
    prediction: Optional[Dict[str, Any]]
) -> RecordEvaluationResult:
    """Evaluates a single benchmark record against a prediction record across all fields."""
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
            "employer": benchmark.status_company,
            "company": benchmark.status_company,
            "country": benchmark.status_location,
            "location": benchmark.status_location,
            "location_raw": benchmark.status_location,
            "work_mode": benchmark.status_work_mode,
            "posting_date": benchmark.status_posted_date,
            "posted_date": benchmark.status_posted_date,
            "closing_date": benchmark.status_closing_date,
            "job_description": benchmark.status_description,
            "description": benchmark.status_description,
            "salary": benchmark.status_salary,
            "salary_disclosed": benchmark.status_salary,
            "salary_min": benchmark.status_salary,
            "salary_max": benchmark.status_salary,
            "currency": benchmark.status_salary,
            "pay_period": benchmark.status_salary,
            "skills": benchmark.status_skills,
        }
        for fld, st in status_map.items():
            if st == "verified":
                outcome = "missing_prediction"
                err_cat = "unmatched_record_missing"
                err_type = "missing"
            elif st == "unavailable":
                outcome = "correct_absence"
                err_cat = "none"
                err_type = "none"
            elif st == "ambiguous":
                outcome = "ambiguous_excluded"
                err_cat = "ambiguous_source_data"
                err_type = "ambiguous"
            else:
                outcome = "not_reviewed"
                err_cat = "none"
                err_type = "none"

            rec_res.field_results[fld] = FieldEvaluationResult(
                field_name=fld,
                status=outcome,
                reference_status=st,
                expected_raw=None,
                expected_normalized=None,
                predicted_raw=None,
                predicted_normalized=None,
                error_category=err_cat,
                error_type=err_type,
                details="No matching prediction record found for advertisement."
            )
        return rec_res

    rec_res.matched_prediction_id = str(prediction.get("job_id", ""))

    # 1. Job Title
    pred_title = prediction.get("job_title_raw") or prediction.get("job_title", "")
    rec_res.field_results["job_title"] = evaluate_text_field(
        "job_title", benchmark.status_job_title, benchmark.expected_job_title_raw, pred_title
    )

    # 2. Employer (Company)
    pred_company = prediction.get("company_raw") or prediction.get("company", "")
    rec_res.field_results["employer"] = evaluate_text_field(
        "employer", benchmark.status_company, benchmark.expected_company_raw, pred_company,
        normalizer=normalize_company_name
    )
    rec_res.field_results["company"] = rec_res.field_results["employer"]

    # 3. Country (Normalized and Raw)
    pred_country = prediction.get("country_normalized") or prediction.get("country_raw") or prediction.get("country", "")
    rec_res.field_results["country"] = evaluate_text_field(
        "country", benchmark.status_location, benchmark.expected_country_normalized, pred_country,
        normalizer=normalize_country_name
    )

    # 4. Location (Geographic text)
    pred_loc = prediction.get("location_raw") or prediction.get("location", "")
    rec_res.field_results["location"] = evaluate_text_field(
        "location", benchmark.status_location, benchmark.expected_location_raw, pred_loc
    )
    rec_res.field_results["location_raw"] = rec_res.field_results["location"]

    # 5. Work Mode
    pred_work_mode = prediction.get("work_mode") or prediction.get("work_mode_raw", "")
    rec_res.field_results["work_mode"] = evaluate_text_field(
        "work_mode", benchmark.status_work_mode, benchmark.expected_work_mode, pred_work_mode
    )

    # 6. Posting Date
    pred_posted = (
        prediction.get("posted_date_raw") or
        prediction.get("posted_date") or
        prediction.get("listing_posted_date_raw", "")
    )
    rec_res.field_results["posting_date"] = evaluate_date_field(
        "posting_date", benchmark.status_posted_date, benchmark.expected_posted_date, pred_posted
    )
    rec_res.field_results["posted_date"] = rec_res.field_results["posting_date"]

    # 7. Closing Date
    pred_closing = prediction.get("closing_date_raw") or prediction.get("closing_date", "")
    rec_res.field_results["closing_date"] = evaluate_date_field(
        "closing_date", benchmark.status_closing_date, benchmark.expected_closing_date, pred_closing
    )

    # 8. Job Description
    pred_desc = prediction.get("job_description_raw") or prediction.get("job_description", "")
    rec_res.field_results["job_description"] = evaluate_text_field(
        "job_description", benchmark.status_description,
        benchmark.expected_description_snippet, pred_desc,
        min_overlap=0.60
    )
    rec_res.field_results["description"] = rec_res.field_results["job_description"]

    # 9. Salary Disclosed (Binary)
    pred_sal_disc_raw = prediction.get("salary_disclosed")
    if pred_sal_disc_raw is not None and str(pred_sal_disc_raw).strip() != "":
        pred_sal_disc = str(pred_sal_disc_raw).strip().lower() in ("true", "1", "yes")
    else:
        # Infer from presence of text or numeric amounts
        s_min = prediction.get("salary_min_normalized") or prediction.get("salary_min_raw")
        s_txt = str(prediction.get("salary_text_raw", "") or "").strip()
        pred_sal_disc = bool(s_min and str(s_min).strip().lower() not in ("nan", "none", "")) or bool(s_txt)

    exp_disc = benchmark.expected_salary_disclosed
    status_sal = benchmark.status_salary
    if status_sal == "verified":
        if pred_sal_disc == exp_disc:
            rec_res.field_results["salary_disclosed"] = FieldEvaluationResult(
                "salary_disclosed", "correct", status_sal,
                exp_disc, exp_disc, pred_sal_disc, pred_sal_disc,
                is_exact_match=True, is_normalized_match=True
            )
        else:
            rec_res.field_results["salary_disclosed"] = FieldEvaluationResult(
                "salary_disclosed", "incorrect", status_sal,
                exp_disc, exp_disc, pred_sal_disc, pred_sal_disc,
                is_exact_match=False, is_normalized_match=False,
                error_category="salary_disclosure_mismatch", error_type="incorrect",
                details=f"Expected disclosed={exp_disc} != predicted disclosed={pred_sal_disc}"
            )
    elif status_sal == "unavailable":
        if not pred_sal_disc:
            rec_res.field_results["salary_disclosed"] = FieldEvaluationResult(
                "salary_disclosed", "correct_absence", status_sal,
                False, False, False, False,
                is_exact_match=True, is_normalized_match=True
            )
        else:
            rec_res.field_results["salary_disclosed"] = FieldEvaluationResult(
                "salary_disclosed", "over_extracted", status_sal,
                False, False, True, True,
                error_category="hallucinated_salary_disclosure", error_type="over_extracted"
            )
    else:
        rec_res.field_results["salary_disclosed"] = FieldEvaluationResult(
            "salary_disclosed", "ambiguous_excluded", status_sal,
            exp_disc, exp_disc, pred_sal_disc, pred_sal_disc
        )

    # 10. Salary Minimum (Numeric with compatibility checks)
    pred_s_min = prediction.get("salary_min_normalized") or prediction.get("salary_min_raw")
    pred_curr = prediction.get("salary_currency_normalized") or prediction.get("salary_currency_raw", "")
    pred_period = prediction.get("salary_period_normalized") or prediction.get("salary_period_raw", "")

    rec_res.field_results["salary_min"] = evaluate_numeric_salary_amount(
        "salary_min", status_sal, benchmark.expected_salary_min, pred_s_min,
        benchmark.expected_salary_currency, str(pred_curr),
        benchmark.expected_salary_period, str(pred_period)
    )

    # 11. Salary Maximum (Numeric with compatibility checks)
    pred_s_max = prediction.get("salary_max_normalized") or prediction.get("salary_max_raw")
    rec_res.field_results["salary_max"] = evaluate_numeric_salary_amount(
        "salary_max", status_sal, benchmark.expected_salary_max, pred_s_max,
        benchmark.expected_salary_currency, str(pred_curr),
        benchmark.expected_salary_period, str(pred_period)
    )

    # 12. Currency
    rec_res.field_results["currency"] = evaluate_text_field(
        "currency", status_sal if benchmark.expected_salary_currency else "unavailable",
        benchmark.expected_salary_currency, pred_curr,
        normalizer=normalize_currency_code
    )

    # 13. Pay Period
    rec_res.field_results["pay_period"] = evaluate_text_field(
        "pay_period", status_sal if benchmark.expected_salary_period != "unspecified" else "unavailable",
        benchmark.expected_salary_period if benchmark.expected_salary_period != "unspecified" else "",
        pred_period,
        normalizer=normalize_pay_period
    )

    # 14. Composite Salary
    rec_res.field_results["salary"] = evaluate_salary_composite(benchmark, prediction)

    # 15. Skills (Multi-label)
    pred_skills = prediction.get("skills_raw") or prediction.get("skills", "")
    rec_res.field_results["skills"] = evaluate_multi_label_skills(
        benchmark.status_skills, benchmark.expected_skills, pred_skills
    )

    return rec_res


def compare_records(
    benchmarks: List[BenchmarkRecord],
    predictions: List[Dict[str, Any]],
    match_key: str = "auto"
) -> Tuple[List[RecordEvaluationResult], List[BenchmarkRecord], List[Dict[str, Any]]]:
    """Matches predictions to benchmark records and executes field-by-field evaluation.
    
    Returns:
        tuple: (evaluated_results, unmatched_benchmarks, extra_predictions)
    """
    def _canon_url(u: Any) -> str:
        if not u:
            return ""
        s = str(u).strip().lower()
        return re.sub(r"/+$", "", s)

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

    extra_predictions: List[Dict[str, Any]] = []
    bm_urls = {_canon_url(bm.source_url) for bm in benchmarks}
    for p in predictions:
        pid = str(p.get("job_id", ""))
        url = _canon_url(p.get("source_url") or p.get("final_url"))
        if pid not in matched_prediction_ids and url not in bm_urls:
            extra_predictions.append(p)

    return results, unmatched_benchmarks, extra_predictions
