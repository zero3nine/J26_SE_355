"""
Location and Work-Mode Normalization Module.
Academic Research Component for Regional Comparative IT Labor-Market Analysis.

Focus Regions: Sri Lanka, India, Singapore, Malaysia, and Global/Remote.

Features:
- Disaggregates location into city_normalized, state_region_normalized, country_normalized, and work_mode.
- Never maps missing/empty locations to 'Remote Work' (categorizes as 'unspecified').
- Preserves raw location and raw country text exactly for data provenance.
- Identifies work modes: 'remote', 'hybrid', 'on_site', 'unspecified', 'unknown'.
- Preserves multiple locations (e.g., 'Colombo; Kandy') without silent data loss.
- Regional gazetteer matching for administrative boundaries.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple


WORK_MODES: set[str] = {"remote", "hybrid", "on_site", "unspecified", "unknown"}

# ============================================================================
# Regional Gazetteers and Dictionaries
# ============================================================================

COUNTRY_ALIASES: dict[str, str] = {
    # Sri Lanka
    "sri lanka": "Sri Lanka",
    "srilanka": "Sri Lanka",
    "lk": "Sri Lanka",
    "lka": "Sri Lanka",
    "ceylon": "Sri Lanka",
    
    # India
    "india": "India",
    "in": "India",
    "ind": "India",
    "bharat": "India",
    
    # Singapore
    "singapore": "Singapore",
    "sg": "Singapore",
    "sgp": "Singapore",
    
    # Malaysia
    "malaysia": "Malaysia",
    "my": "Malaysia",
    "mys": "Malaysia",

    # Common international benchmarks
    "united states": "United States",
    "usa": "United States",
    "us": "United States",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "australia": "Australia",
    "au": "Australia",
    "germany": "Germany",
    "de": "Germany",
    "canada": "Canada",
    "ca": "Canada",
}

# City -> (Standard City Name, State/Region, Country)
CITY_GAZETTEER: list[tuple[re.Pattern, str, str, str]] = [
    # --- Sri Lanka ---
    # Colombo & Suburbs
    (re.compile(r"(?i)\b(colombo(?:\s*\d+)?|kollupitiya|bambalapitiya|cinnamon\s*gardens|borella|dematagoda|maradana|pettah|fort)\b"), "Colombo", "Western Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(dehiwala|mount\s*lavinia|ratmalana|moratuwa|panadura)\b"), "Dehiwala-Mount Lavinia", "Western Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(nugegoda|maharagama|kotte|rajagiriya|battaramulla|malabe|thalawathugoda|pannipitiya|kaduwela|homagama)\b"), "Colombo Suburbs", "Western Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(gampaha|negombo|katunayake|kelaniya|wattala|ja-ela|kadawatha|kiribathgoda)\b"), "Gampaha / Negombo", "Western Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(kalutara|beruwala|aluthgama|wadduwa|horana)\b"), "Kalutara", "Western Province", "Sri Lanka"),
    # Kandy & Central
    (re.compile(r"(?i)\b(kandy|peradeniya|katugastota|gampola|kundasale)\b"), "Kandy", "Central Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(matale|dambulla)\b"), "Matale", "Central Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(nuwara\s*eliya|hatton)\b"), "Nuwara Eliya", "Central Province", "Sri Lanka"),
    # Southern
    (re.compile(r"(?i)\b(galle|hikkaduwa|karapitiya)\b"), "Galle", "Southern Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(matara|weligama)\b"), "Matara", "Southern Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(hambantota|tangalle)\b"), "Hambantota", "Southern Province", "Sri Lanka"),
    # Northern & Eastern
    (re.compile(r"(?i)\b(jaffna|chavakachcheri|point\s*pedro)\b"), "Jaffna", "Northern Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(vavuniya|kilinochchi|mannar)\b"), "Northern Region", "Northern Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(batticaloa|kattankudy)\b"), "Batticaloa", "Eastern Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(trincomalee)\b"), "Trincomalee", "Eastern Province", "Sri Lanka"),
    # North Western & North Central
    (re.compile(r"(?i)\b(kurunegala|kuliyapitiya)\b"), "Kurunegala", "North Western Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(anuradhapura)\b"), "Anuradhapura", "North Central Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(polonnaruwa)\b"), "Polonnaruwa", "North Central Province", "Sri Lanka"),
    # Sabaragamuwa & Uva
    (re.compile(r"(?i)\b(ratnapura|balangoda)\b"), "Ratnapura", "Sabaragamuwa Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(kegalle|mawanella)\b"), "Kegalle", "Sabaragamuwa Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(badulla|bandarawela)\b"), "Badulla", "Uva Province", "Sri Lanka"),
    (re.compile(r"(?i)\b(island\s*wide|all\s*island)\b"), "", "Island Wide", "Sri Lanka"),

    # --- India ---
    (re.compile(r"(?i)\b(bengaluru|bangalore|whitefield|electronic\s*city)\b"), "Bengaluru", "Karnataka", "India"),
    (re.compile(r"(?i)\b(hyderabad|secunderabad|cyberabad|hitech\s*city|gachibowli)\b"), "Hyderabad", "Telangana", "India"),
    (re.compile(r"(?i)\b(pune|hinjewadi|magarpatta)\b"), "Pune", "Maharashtra", "India"),
    (re.compile(r"(?i)\b(mumbai|bombay|navi\s*mumbai|thane|andheri|bkc)\b"), "Mumbai", "Maharashtra", "India"),
    (re.compile(r"(?i)\b(chennai|madras|omr|taramani)\b"), "Chennai", "Tamil Nadu", "India"),
    (re.compile(r"(?i)\b(gurugram|gurgaon|cyber\s*city)\b"), "Gurugram", "Haryana (NCR)", "India"),
    (re.compile(r"(?i)\b(noida|greater\s*noida)\b"), "Noida", "Uttar Pradesh (NCR)", "India"),
    (re.compile(r"(?i)\b(delhi|new\s*delhi)\b"), "Delhi", "Delhi NCR", "India"),
    (re.compile(r"(?i)\b(kolkata|calcutta|salt\s*lake|new\s*town)\b"), "Kolkata", "West Bengal", "India"),
    (re.compile(r"(?i)\b(kochi|cochin|infopark|kakkanad)\b"), "Kochi", "Kerala", "India"),
    (re.compile(r"(?i)\b(thiruvananthapuram|trivandrum|technopark)\b"), "Thiruvananthapuram", "Kerala", "India"),
    (re.compile(r"(?i)\b(ahmedabad|gandhinagar|gift\s*city)\b"), "Ahmedabad", "Gujarat", "India"),
    (re.compile(r"(?i)\b(coimbatore)\b"), "Coimbatore", "Tamil Nadu", "India"),
    (re.compile(r"(?i)\b(indore)\b"), "Indore", "Madhya Pradesh", "India"),
    (re.compile(r"(?i)\b(jaipur)\b"), "Jaipur", "Rajasthan", "India"),
    (re.compile(r"(?i)\b(chandigarh|mohali)\b"), "Chandigarh", "Punjab / Haryana", "India"),
    (re.compile(r"(?i)\b(bhubaneswar)\b"), "Bhubaneswar", "Odisha", "India"),

    # --- Singapore ---
    (re.compile(r"(?i)\b(singapore|changi|jurong|woodlands|tampines|marina\s*bay|raffles\s*place|buona\s*vista|one-north)\b"), "Singapore", "Central", "Singapore"),

    # --- Malaysia ---
    (re.compile(r"(?i)\b(kuala\s*lumpur|klcc|bangsar|mont\s*kiara|bukit\s*bintang)\b"), "Kuala Lumpur", "Federal Territory of Kuala Lumpur", "Malaysia"),
    (re.compile(r"(?i)\b(cyberjaya)\b"), "Cyberjaya", "Selangor", "Malaysia"),
    (re.compile(r"(?i)\b(putrajaya)\b"), "Putrajaya", "Federal Territory of Putrajaya", "Malaysia"),
    (re.compile(r"(?i)\b(petaling\s*jaya|pj|damansara|subang\s*jaya|sunway|shah\s*alam|puchong|klang)\b"), "Petaling Jaya", "Selangor", "Malaysia"),
    (re.compile(r"(?i)\b(george\s*town)\b"), "George Town", "Penang", "Malaysia"),
    (re.compile(r"(?i)\b(bayan\s*lepas)\b"), "Bayan Lepas", "Penang", "Malaysia"),
    (re.compile(r"(?i)\b(penang)\b"), "Penang", "Penang", "Malaysia"),
    (re.compile(r"(?i)\b(johor\s*bahru|jb|iskandar)\b"), "Johor Bahru", "Johor", "Malaysia"),
    (re.compile(r"(?i)\b(melaka|malacca)\b"), "Melaka", "Melaka", "Malaysia"),
    (re.compile(r"(?i)\b(ipoh)\b"), "Ipoh", "Perak", "Malaysia"),
    (re.compile(r"(?i)\b(kuching)\b"), "Kuching", "Sarawak", "Malaysia"),
    (re.compile(r"(?i)\b(kota\s*kinabalu)\b"), "Kota Kinabalu", "Sabah", "Malaysia"),
]


# ============================================================================
# Work Mode Patterns
# ============================================================================

REMOTE_PATTERNS = [
    r"(?i)\b100%\s*remote\b",
    r"(?i)\bfully\s*remote\b",
    r"(?i)\bwork\s*from\s*home\b",
    r"(?i)\bwfh\b",
    r"(?i)\btelecommute\b",
    r"(?i)\bvirtual\s*(?:role|position|job|work)?\b",
    r"(?i)\bremote\s*(?:work|first|friendly|eligible|available|basis|only)?\b",
]

HYBRID_PATTERNS = [
    r"(?i)\bhybrid\b",
    r"(?i)\bpartial\s*remote\b",
    r"(?i)\b\d+\s*days?\s*(?:in\s*)?office\b",
    r"(?i)\b\d+\s*days?\s*(?:from\s*)?(?:home|remote|wfh)\b",
    r"(?i)\bflexible\s*work(?:ing)?\b",
]

ONSITE_PATTERNS = [
    r"(?i)\bon[\-\s]*site\b",
    r"(?i)\bin[\-\s]*office\b",
    r"(?i)\bwork\s*from\s*office\b",
    r"(?i)\bwfo\b",
    r"(?i)\boffice[\-\s]*based\b",
]


def detect_work_mode(
    location_text: str = "",
    job_title: str = "",
    job_description: str = "",
    has_physical_city: bool = False,
) -> Tuple[str, str]:
    """Classifies the work mode based on textual evidence across location, title, and description.

    Returns:
        (work_mode: 'remote' | 'hybrid' | 'on_site' | 'unspecified' | 'unknown', reason: str)
    """
    combined_signal = f"{location_text} {job_title}".strip()

    is_remote_explicit = any(re.search(pat, combined_signal) for pat in REMOTE_PATTERNS)
    is_hybrid_explicit = any(re.search(pat, combined_signal) for pat in HYBRID_PATTERNS)
    is_onsite_explicit = any(re.search(pat, combined_signal) for pat in ONSITE_PATTERNS)

    # If title/location has no signal, check description headers/intro
    if not (is_remote_explicit or is_hybrid_explicit or is_onsite_explicit) and job_description:
        desc_sample = job_description[:1200]
        is_remote_explicit = any(re.search(pat, desc_sample) for pat in REMOTE_PATTERNS)
        is_hybrid_explicit = any(re.search(pat, desc_sample) for pat in HYBRID_PATTERNS)
        is_onsite_explicit = any(re.search(pat, desc_sample) for pat in ONSITE_PATTERNS)

    # Evaluate combinations and conflicts
    if is_hybrid_explicit:
        return "hybrid", "Explicit hybrid arrangement specified in posting"

    if is_remote_explicit and is_onsite_explicit:
        return "unknown", "Conflicting signals: both remote and onsite indicators found"

    if is_remote_explicit:
        return "remote", "Explicit remote/work-from-home indicator identified"

    if is_onsite_explicit:
        return "on_site", "Explicit onsite/in-office requirement specified"

    # Default heuristic: if a physical city is clearly specified, infer on_site
    if has_physical_city:
        return "on_site", "Physical office location specified with no remote indicators"

    # If location is completely empty and no remote indicators exist:
    # Rule B: NEVER convert empty location to remote!
    return "unspecified", "No work mode or location mentioned in posting"


def normalize_country(raw_country: str) -> str:
    """Standardizes country name to official research taxonomy."""
    if not raw_country or not isinstance(raw_country, str):
        return ""
    cleaned = raw_country.strip().lower()
    cleaned = re.sub(r"[^\w\s]", " ", cleaned).strip()
    return COUNTRY_ALIASES.get(cleaned, raw_country.strip())


def parse_and_normalize_location(
    location_raw: str = "",
    country_raw: str = "",
    job_title: str = "",
    job_description: str = "",
) -> Dict[str, Any]:
    """Standardizes geographic location, administrative region, country, and work mode.

    Returns a dict with:
        location_raw (str): Exact original input string preserved
        country_raw (str): Exact original country string preserved
        country_normalized (str): Standardized country name or ''
        city_normalized (str): Standardized city or semi-colon separated cities
        state_region_normalized (str): Standardized administrative division
        work_mode (str): 'remote', 'hybrid', 'on_site', 'unspecified', 'unknown'
        location_normalization_status (str): 'normalized', 'partial', 'unspecified', 'ambiguous'
        location_normalization_method (str): 'gazetteer_match', 'country_standardized', 'work_mode_extracted', 'unspecified'
    """
    loc_clean = str(location_raw or "").strip()
    cntry_clean = str(country_raw or "").strip()

    # Normalize placeholder strings to empty
    if loc_clean.lower() in ("unspecified", "unknown", "n/a", "na", "none", "-", "null", "not specified"):
        loc_clean = ""
    if cntry_clean.lower() in ("unspecified", "unknown", "n/a", "na", "none", "-", "null", "not specified"):
        cntry_clean = ""

    # Rule B Check: Empty location string must never become Remote Work
    if not loc_clean and not cntry_clean:
        # Check if title has remote keywords
        mode, mode_reason = detect_work_mode("", job_title, job_description, has_physical_city=False)
        status = "partial" if mode in ("remote", "hybrid") else "unspecified"
        method = "work_mode_extracted" if mode in ("remote", "hybrid") else "unspecified"
        return {
            "location_raw": "",
            "country_raw": "",
            "country_normalized": "",
            "city_normalized": "",
            "state_region_normalized": "",
            "work_mode": mode,
            "location_normalization_status": status,
            "location_normalization_method": method,
        }

    # Normalize Country from raw country input if provided
    norm_country = normalize_country(cntry_clean)

    # Search for cities in gazetteer across location_raw, title, and country_raw
    matched_cities: list[str] = []
    matched_states: list[str] = []
    matched_countries: list[str] = []

    search_text = f"{loc_clean} {job_title}".strip()

    for pattern, city_name, state_name, country_name in CITY_GAZETTEER:
        if pattern.search(search_text):
            if city_name and city_name not in matched_cities:
                matched_cities.append(city_name)
            if state_name and state_name not in matched_states:
                matched_states.append(state_name)
            if country_name and country_name not in matched_countries:
                matched_countries.append(country_name)

    # Also check if country appears explicitly in loc_clean text
    loc_lower = loc_clean.lower()
    for alias, std_name in COUNTRY_ALIASES.items():
        if re.search(r"(?i)\b" + re.escape(alias) + r"\b", loc_lower):
            if std_name not in matched_countries:
                matched_countries.append(std_name)

    # Combine country resolution
    if not norm_country and matched_countries:
        # Resolve from matched city country
        norm_country = matched_countries[0]
    elif norm_country and matched_countries and norm_country not in matched_countries:
        # Multiple conflicting country signals
        pass  # keep norm_country from explicit field

    # If a specific city was matched, filter out redundant state names from matched_cities
    if len(matched_cities) > 1:
        specific_cities = [c for c in matched_cities if c not in matched_states]
        if specific_cities:
            matched_cities = specific_cities

    final_city = "; ".join(matched_cities) if matched_cities else ""
    final_state = "; ".join(matched_states) if matched_states else ""

    has_physical_city = bool(final_city)
    work_mode, mode_reason = detect_work_mode(loc_clean, job_title, job_description, has_physical_city=has_physical_city)

    # Assess Normalization Status
    if len(matched_countries) > 1 and norm_country == "":
        status = "ambiguous"
        method = "gazetteer_match"
    elif final_city and norm_country:
        status = "normalized"
        method = "gazetteer_match"
    elif norm_country or work_mode in ("remote", "hybrid"):
        status = "partial"
        method = "country_standardized" if norm_country else "work_mode_extracted"
    elif loc_clean:
        # Location text present but unmapped to regional gazetteer
        status = "partial"
        method = "unmapped_text"
        final_city = loc_clean.split(",")[0].strip()
    else:
        status = "unspecified"
        method = "unspecified"

    return {
        "location_raw": loc_clean,
        "country_raw": cntry_clean,
        "country_normalized": norm_country,
        "city_normalized": final_city,
        "state_region_normalized": final_state,
        "work_mode": work_mode,
        "location_normalization_status": status,
        "location_normalization_method": method,
    }
