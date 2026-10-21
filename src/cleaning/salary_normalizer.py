"""
Salary Normalization and Extraction Module.
Academic Research Component for Regional Comparative IT Labor-Market Analysis.

Supports:
- Diverse currencies: LKR, INR, SGD, MYR, USD, EUR, GBP.
- Indian numbering notation (Lakhs, Crores, LPA).
- Suffix multipliers (k, M).
- Pay period standardization (hourly, daily, monthly, annual).
- Structured JSON-LD MonetaryAmount inputs and unstructured text parsing.
- Precise distinction between undisclosed, zero, and disclosed salaries.
- Audit trail preserving raw strings and normalization methods.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple


SUPPORTED_CURRENCIES: set[str] = {"LKR", "INR", "SGD", "MYR", "USD", "EUR", "GBP"}
VALID_SALARY_PERIODS: set[str] = {"hourly", "daily", "monthly", "annual", "unspecified"}
VALID_SALARY_TYPES: set[str] = {"range", "fixed", "starting_from", "up_to", "undisclosed", "unparseable"}

# Currency token mappings to ISO 4217 codes
CURRENCY_MAP: dict[str, str] = {
    "lkr": "LKR",
    "slr": "LKR",
    "sri lankan rupee": "LKR",
    "sri lanka rupee": "LKR",
    "රු": "LKR",
    "inr": "INR",
    "₹": "INR",
    "indian rupee": "INR",
    "lpa": "INR",          # Lakhs per annum (standard Indian tech compensation unit)
    "sgd": "SGD",
    "s$": "SGD",
    "singapore dollar": "SGD",
    "myr": "MYR",
    "rm": "MYR",
    "ringgit": "MYR",
    "malaysian ringgit": "MYR",
    "usd": "USD",
    "us$": "USD",
    "us dollar": "USD",
    "eur": "EUR",
    "€": "EUR",
    "euro": "EUR",
    "gbp": "GBP",
    "£": "GBP",
    "pound": "GBP",
}

# Explicit undisclosed keywords and phrases
UNDISCLOSED_PATTERNS = [
    r"\bundisclosed\b",
    r"\bnot disclosed\b",
    r"\bcompetitive\b",
    r"\bnegotiable\b",
    r"\bbest in industry\b",
    r"\bas per (?:market|industry|company)(?:\s+standards?)?\b",
    r"\bmarket standards?\b",
    r"\bmarket rates?\b",
    r"\bto be discussed\b",
    r"\bdepending on experience\b",
    r"\bdoe\b",
    r"\bna\b",
    r"\bn/a\b",
    r"\bconfidential\b",
]

# Ambiguous / non-numeric compensation signals
AMBIGUOUS_PATTERNS = [
    r"\bbonus\b",
    r"\bcommission\b",
    r"\ballowance\b",
    r"\bincentive\b",
    r"\bprofit\s*sharing\b",
    r"\bequity\b",
    r"\besop\b",
    r"\bstock\s*options\b",
    r"\battractive\s*(?:salary|package|remuneration)\b",
]

# Pay period patterns
PERIOD_PATTERNS: list[tuple[str, str]] = [
    (r"(?i)\b(per\s*hour|hourly|/hr|/hour|p/h|hr)\b", "hourly"),
    (r"(?i)\b(per\s*day|daily|/day|p/d)\b", "daily"),
    (r"(?i)\b(per\s*month|monthly|/month|/mo|p\.m\.|pm|p/m)\b", "monthly"),
    (r"(?i)\b(per\s*annum|per\s*year|annually|yearly|/year|/annum|p\.a\.|pa|p/a|lpa)\b", "annual"),
]


def _clean_numeric_str(val_str: str) -> Optional[float]:
    """Parse a numeric string taking into account multipliers (k, lakh, crore)."""
    if not val_str:
        return None
    val_str = val_str.strip().replace(",", "")
    
    # Check for LPA (Lakhs Per Annum)
    lpa_match = re.match(r"^([\d.]+)\s*lpa$", val_str, re.IGNORECASE)
    if lpa_match:
        try:
            return float(lpa_match.group(1)) * 100_000.0
        except ValueError:
            return None

    # Check for Lakhs / Lacs
    lakh_match = re.match(r"^([\d.]+)\s*(?:lakhs?|lacs?|lac|l)$", val_str, re.IGNORECASE)
    if lakh_match:
        try:
            return float(lakh_match.group(1)) * 100_000.0
        except ValueError:
            return None

    # Check for Crores / Cr
    cr_match = re.match(r"^([\d.]+)\s*(?:crores?|cr)$", val_str, re.IGNORECASE)
    if cr_match:
        try:
            return float(cr_match.group(1)) * 10_000_000.0
        except ValueError:
            return None

    # Check for 'k' suffix (thousands)
    k_match = re.match(r"^([\d.]+)\s*k$", val_str, re.IGNORECASE)
    if k_match:
        try:
            return float(k_match.group(1)) * 1_000.0
        except ValueError:
            return None

    # Check for 'm' suffix (millions)
    m_match = re.match(r"^([\d.]+)\s*m$", val_str, re.IGNORECASE)
    if m_match:
        try:
            return float(m_match.group(1)) * 1_000_000.0
        except ValueError:
            return None

    try:
        return float(val_str)
    except ValueError:
        return None


def detect_currency(
    text: str,
    country_context: str = "",
) -> Tuple[str, str]:
    """Detects currency from explicit text tokens.
    
    Returns:
        (normalized_currency, raw_currency_matched)
    
    Note: Adheres to Rule 6 — does NOT assume currency from domain or market averages.
    Only uses country_context to disambiguate generic 'Rs'/'Rs.' when explicitly provided.
    """
    if not text:
        return "", ""

    lower_text = text.lower()

    # Look for unambiguous currency symbols/codes first
    for token, iso in CURRENCY_MAP.items():
        # Match as word or symbol
        if re.search(r"(?i)(?<!\w)" + re.escape(token) + r"(?!\w)", text) or token in lower_text:
            return iso, token.upper()

    # Generic '$' without prefix
    if "$" in text:
        # If country context is Singapore, resolve to SGD
        if country_context and country_context.lower() in ("singapore", "sg", "sgp"):
            return "SGD", "$"
        # If country context is US, resolve to USD
        if country_context and country_context.lower() in ("united states", "usa", "us"):
            return "USD", "$"
        # Otherwise keep raw '$' and mark ambiguous currency
        return "$", "$"

    # Generic 'Rs' / 'Rs.' without prefix
    if re.search(r"(?i)\brs\.?\b", text):
        if country_context and country_context.lower() in ("sri lanka", "lk", "srilanka"):
            return "LKR", "Rs."
        if country_context and country_context.lower() in ("india", "in", "ind"):
            return "INR", "Rs."
        # Generic Rs without country context
        return "Rs", "Rs."

    return "", ""


def detect_period(
    text: str,
    default_period: str = "unspecified",
) -> Tuple[str, str]:
    """Identifies the pay period from text."""
    if not text:
        return default_period, ""

    for pattern, period in PERIOD_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return period, match.group(0)

    # Standard Schema.org unit texts
    upper = text.upper()
    if "HOUR" in upper or "HUR" in upper:
        return "hourly", "HOUR"
    if "DAY" in upper:
        return "daily", "DAY"
    if "MONTH" in upper or "MON" in upper:
        return "monthly", "MONTH"
    if "YEAR" in upper or "ANN" in upper or "ANNU" in upper:
        return "annual", "YEAR"

    return default_period, ""


def parse_and_normalize_salary(
    salary_text_raw: str = "",
    salary_min_raw: Any = None,
    salary_max_raw: Any = None,
    salary_currency_raw: str = "",
    salary_period_raw: str = "",
    country_context: str = "",
    job_description_snippet: str = "",
) -> Dict[str, Any]:
    """Normalizes raw salary parameters or unparsed text into a structured, audit-ready schema.

    Returns a dict with:
        salary_text_raw (str)
        salary_min_raw (str)
        salary_max_raw (str)
        salary_currency_raw (str)
        salary_period_raw (str)
        salary_disclosed (bool)
        salary_type (str): 'range', 'fixed', 'starting_from', 'up_to', 'undisclosed', 'unparseable'
        salary_min_normalized (float or None)
        salary_max_normalized (float or None)
        salary_currency_normalized (str): ISO 4217 code (LKR, INR, SGD, MYR, USD, etc.) or ''
        salary_period_normalized (str): 'hourly', 'daily', 'monthly', 'annual', 'unspecified'
        salary_normalization_status (str): 'normalized', 'partial', 'undisclosed', 'ambiguous', 'unparseable'
        salary_normalization_method (str): 'jsonld_structured', 'regex_parsed', 'not_applicable'
    """
    raw_text = str(salary_text_raw or "").strip()
    min_in = str(salary_min_raw).strip() if salary_min_raw is not None and str(salary_min_raw).strip() not in ("", "None", "nan") else ""
    max_in = str(salary_max_raw).strip() if salary_max_raw is not None and str(salary_max_raw).strip() not in ("", "None", "nan") else ""
    curr_in = str(salary_currency_raw or "").strip()
    period_in = str(salary_period_raw or "").strip()

    # 1. Check if structured JSON-LD numbers were passed directly
    if min_in or max_in:
        min_val = _clean_numeric_str(min_in)
        max_val = _clean_numeric_str(max_in)

        # Distinguish undisclosed from zero
        is_zero_min = (min_val == 0.0)
        is_zero_max = (max_val == 0.0)

        # If both are None or negative
        if min_val is None and max_val is None:
            pass  # Fall through to text analysis
        else:
            # Currency from structured input or fallback
            norm_curr, detected_raw_curr = detect_currency(curr_in or raw_text, country_context)
            final_raw_curr = curr_in or detected_raw_curr

            # Period from structured input or fallback
            norm_period, detected_raw_period = detect_period(period_in or raw_text)
            final_raw_period = period_in or detected_raw_period

            # Determine type
            if min_val is not None and max_val is not None:
                if min_val == max_val:
                    sal_type = "fixed"
                elif min_val < max_val:
                    sal_type = "range"
                else:
                    # min > max: invalid range
                    return {
                        "salary_text_raw": raw_text or f"{min_in} - {max_in} {curr_in}",
                        "salary_min_raw": min_in,
                        "salary_max_raw": max_in,
                        "salary_currency_raw": final_raw_curr,
                        "salary_period_raw": final_raw_period,
                        "salary_disclosed": True,
                        "salary_type": "unparseable",
                        "salary_min_normalized": min_val,
                        "salary_max_normalized": max_val,
                        "salary_currency_normalized": norm_curr,
                        "salary_period_normalized": norm_period,
                        "salary_normalization_status": "ambiguous",
                        "salary_normalization_method": "jsonld_structured",
                    }
            elif min_val is not None:
                sal_type = "starting_from"
            else:
                sal_type = "up_to"

            # Check boundary conditions
            if (min_val is not None and min_val < 0) or (max_val is not None and max_val < 0):
                status = "ambiguous"
            elif not norm_curr or norm_curr in ("$", "Rs"):
                status = "partial"
            elif norm_period == "unspecified":
                status = "partial"
            else:
                status = "normalized"

            return {
                "salary_text_raw": raw_text or f"{min_in} - {max_in} {curr_in}",
                "salary_min_raw": min_in,
                "salary_max_raw": max_in,
                "salary_currency_raw": final_raw_curr,
                "salary_period_raw": final_raw_period,
                "salary_disclosed": True,
                "salary_type": sal_type,
                "salary_min_normalized": min_val,
                "salary_max_normalized": max_val,
                "salary_currency_normalized": norm_curr,
                "salary_period_normalized": norm_period,
                "salary_normalization_status": status,
                "salary_normalization_method": "jsonld_structured",
            }

    # 2. Check for empty or undisclosed text
    candidate_text = raw_text
    if not candidate_text and job_description_snippet:
        # Check if description has explicit salary line
        sal_line_match = re.search(r"(?i)(?:salary|compensation|remuneration|stipend|pay)\s*[:\-]\s*([^\n\r<]{3,80})", job_description_snippet)
        if sal_line_match:
            candidate_text = sal_line_match.group(1).strip()

    if not candidate_text:
        return {
            "salary_text_raw": "",
            "salary_min_raw": "",
            "salary_max_raw": "",
            "salary_currency_raw": "",
            "salary_period_raw": "",
            "salary_disclosed": False,
            "salary_type": "undisclosed",
            "salary_min_normalized": None,
            "salary_max_normalized": None,
            "salary_currency_normalized": "",
            "salary_period_normalized": "unspecified",
            "salary_normalization_status": "undisclosed",
            "salary_normalization_method": "not_applicable",
        }

    # Check for known undisclosed keywords
    for pattern in UNDISCLOSED_PATTERNS:
        if re.search(pattern, candidate_text, re.IGNORECASE):
            return {
                "salary_text_raw": candidate_text,
                "salary_min_raw": "",
                "salary_max_raw": "",
                "salary_currency_raw": "",
                "salary_period_raw": "",
                "salary_disclosed": False,
                "salary_type": "undisclosed",
                "salary_min_normalized": None,
                "salary_max_normalized": None,
                "salary_currency_normalized": "",
                "salary_period_normalized": "unspecified",
                "salary_normalization_status": "undisclosed",
                "salary_normalization_method": "not_applicable",
            }

    # 3. Regex Parsing of Free Text
    norm_curr, raw_curr = detect_currency(candidate_text, country_context)
    norm_period, raw_period = detect_period(candidate_text)

    # Patterns for numeric values
    # Match numbers like 1,50,000 or 150,000 or 12.5 or 150k or 12 Lakhs or 15 LPA
    num_pat = r"(\d+(?:,\d+)*(?:\.\d+)?\s*(?:k|lakhs?|lacs?|lac|crores?|cr|lpa|m(?![a-zA-Z]))?)"

    # Range pattern: e.g. "LKR 200,000 - 350,000" or "10 to 15 LPA" or "RM 5,000 - RM 8,000"
    range_regex = re.compile(
        rf"(?:from\s+)?{num_pat}\s*(?:-|–|—|to)\s*(?:[A-Za-z$₹£€\.]+\s*)?{num_pat}",
        re.IGNORECASE
    )

    # Starting from pattern: e.g. "From 200,000", "Starting at $4,000", "Min 50k"
    start_regex = re.compile(
        rf"(?:from|starting\s*(?:at|from)?|min(?:imum)?|above)\s*(?:[A-Za-z$₹£€\.]+\s*)?{num_pat}",
        re.IGNORECASE
    )

    # Up to pattern: e.g. "Up to 500,000", "Max 100k", "maximum $8,000"
    upto_regex = re.compile(
        rf"(?:up\s*to|max(?:imum)?|below)\s*(?:[A-Za-z$₹£€\.]+\s*)?{num_pat}",
        re.IGNORECASE
    )

    # Single amount pattern: e.g. "$5,000 / month" or "Rs. 250,000"
    single_regex = re.compile(
        rf"(?:salary|compensation|remuneration|pay)?\s*[:\-]?\s*(?:{re.escape(raw_curr)})?\s*{num_pat}",
        re.IGNORECASE
    ) if raw_curr else re.compile(rf"{num_pat}", re.IGNORECASE)

    range_m = range_regex.search(candidate_text)
    if range_m:
        raw_m1, raw_m2 = range_m.group(1).strip(), range_m.group(2).strip()
        v1 = _clean_numeric_str(raw_m1)
        v2 = _clean_numeric_str(raw_m2)

        # Handle multiplier inheritance in ranges: e.g. "12 - 18 LPA" -> v1 is 12, v2 is 18*100k
        if v1 is not None and v2 is not None:
            if v1 < 100 and v2 >= 100_000:
                # Inherit Lakhs or multiplier from upper bound
                if "lakh" in raw_m2.lower() or "lac" in raw_m2.lower() or "lpa" in candidate_text.lower():
                    v1 = v1 * 100_000.0
                elif "cr" in raw_m2.lower():
                    v1 = v1 * 10_000_000.0
                elif "k" in raw_m2.lower():
                    v1 = v1 * 1_000.0

            if v1 < 0 or v2 < 0 or v1 > v2:
                # Invalid bounds
                return {
                    "salary_text_raw": candidate_text,
                    "salary_min_raw": raw_m1,
                    "salary_max_raw": raw_m2,
                    "salary_currency_raw": raw_curr,
                    "salary_period_raw": raw_period,
                    "salary_disclosed": True,
                    "salary_type": "unparseable",
                    "salary_min_normalized": v1,
                    "salary_max_normalized": v2,
                    "salary_currency_normalized": norm_curr,
                    "salary_period_normalized": norm_period,
                    "salary_normalization_status": "ambiguous",
                    "salary_normalization_method": "regex_parsed",
                }

            status = "normalized" if norm_curr and norm_curr not in ("$", "Rs") and norm_period != "unspecified" else "partial"
            return {
                "salary_text_raw": candidate_text,
                "salary_min_raw": raw_m1,
                "salary_max_raw": raw_m2,
                "salary_currency_raw": raw_curr,
                "salary_period_raw": raw_period,
                "salary_disclosed": True,
                "salary_type": "range" if v1 != v2 else "fixed",
                "salary_min_normalized": v1,
                "salary_max_normalized": v2,
                "salary_currency_normalized": norm_curr,
                "salary_period_normalized": norm_period,
                "salary_normalization_status": status,
                "salary_normalization_method": "regex_parsed",
            }

    start_m = start_regex.search(candidate_text)
    if start_m:
        raw_m = start_m.group(1).strip()
        v = _clean_numeric_str(raw_m)
        if v is not None and v >= 0:
            status = "normalized" if norm_curr and norm_curr not in ("$", "Rs") and norm_period != "unspecified" else "partial"
            return {
                "salary_text_raw": candidate_text,
                "salary_min_raw": raw_m,
                "salary_max_raw": "",
                "salary_currency_raw": raw_curr,
                "salary_period_raw": raw_period,
                "salary_disclosed": True,
                "salary_type": "starting_from",
                "salary_min_normalized": v,
                "salary_max_normalized": None,
                "salary_currency_normalized": norm_curr,
                "salary_period_normalized": norm_period,
                "salary_normalization_status": status,
                "salary_normalization_method": "regex_parsed",
            }

    upto_m = upto_regex.search(candidate_text)
    if upto_m:
        raw_m = upto_m.group(1).strip()
        v = _clean_numeric_str(raw_m)
        if v is not None and v >= 0:
            status = "normalized" if norm_curr and norm_curr not in ("$", "Rs") and norm_period != "unspecified" else "partial"
            return {
                "salary_text_raw": candidate_text,
                "salary_min_raw": "",
                "salary_max_raw": raw_m,
                "salary_currency_raw": raw_curr,
                "salary_period_raw": raw_period,
                "salary_disclosed": True,
                "salary_type": "up_to",
                "salary_min_normalized": None,
                "salary_max_normalized": v,
                "salary_currency_normalized": norm_curr,
                "salary_period_normalized": norm_period,
                "salary_normalization_status": status,
                "salary_normalization_method": "regex_parsed",
            }

    # Search for single number match if currency or period was identified
    if norm_curr or norm_period != "unspecified":
        # Find numeric tokens in text
        tokens = re.findall(r"[\d,]+(?:\.\d+)?\s*(?:k|lakhs?|lacs?|crores?|cr|lpa|m(?![a-zA-Z]))?", candidate_text, re.IGNORECASE)
        for t in tokens:
            v = _clean_numeric_str(t)
            # Filter trivial numbers like 2026 (years) unless currency precedes it
            if v is not None and v >= 0:
                if v in (2024, 2025, 2026, 2027) and not raw_curr:
                    continue  # likely a year
                status = "normalized" if norm_curr and norm_curr not in ("$", "Rs") and norm_period != "unspecified" else "partial"
                return {
                    "salary_text_raw": candidate_text,
                    "salary_min_raw": t.strip(),
                    "salary_max_raw": t.strip(),
                    "salary_currency_raw": raw_curr,
                    "salary_period_raw": raw_period,
                    "salary_disclosed": True,
                    "salary_type": "fixed",
                    "salary_min_normalized": v,
                    "salary_max_normalized": v,
                    "salary_currency_normalized": norm_curr,
                    "salary_period_normalized": norm_period,
                    "salary_normalization_status": status,
                    "salary_normalization_method": "regex_parsed",
                }

    # Check for ambiguous remuneration terms (bonuses, incentives, non-numeric perks)
    for pattern in AMBIGUOUS_PATTERNS:
        if re.search(pattern, candidate_text, re.IGNORECASE):
            return {
                "salary_text_raw": candidate_text,
                "salary_min_raw": "",
                "salary_max_raw": "",
                "salary_currency_raw": raw_curr,
                "salary_period_raw": raw_period,
                "salary_disclosed": False,
                "salary_type": "undisclosed",
                "salary_min_normalized": None,
                "salary_max_normalized": None,
                "salary_currency_normalized": norm_curr,
                "salary_period_normalized": norm_period,
                "salary_normalization_status": "ambiguous",
                "salary_normalization_method": "regex_parsed",
            }

    # If text is present but could not be parsed into numbers
    return {
        "salary_text_raw": candidate_text,
        "salary_min_raw": "",
        "salary_max_raw": "",
        "salary_currency_raw": raw_curr,
        "salary_period_raw": raw_period,
        "salary_disclosed": False,
        "salary_type": "unparseable",
        "salary_min_normalized": None,
        "salary_max_normalized": None,
        "salary_currency_normalized": norm_curr,
        "salary_period_normalized": norm_period,
        "salary_normalization_status": "unparseable",
        "salary_normalization_method": "regex_parsed",
    }
