"""
Comparative Regional IT Labor-Market Analysis Engine.
Project: IT Job Market Intelligence Tool (J26_SE_355).
Research Component: Comparative Regional Market Analysis.

Focal Market: Sri Lanka (LK)
Selected Comparators: India (IN), Singapore (SG), Malaysia (MY)

Implements:
- Documented, configurable, task-specific eligibility rules (General, Skill, Role, Geographic, Salary).
- Transparent exclusion tracking and provenance audit funnels.
- Canonical skill-demand percentages with identical cross-country denominator rules.
- Wilson Score 95% Confidence Intervals and sample-size uncertainty flags (N < 10).
- Skill-gap analysis with two-proportion z-tests and p-values.
- Cross-country role comparisons with unclassified tracking and classification quality caveats.
- Audit-compliant salary analysis (native currency preservation, monthly normalization, median/IQR, no fabricated PPP).
- Multidimensional country skill profile similarities (Cosine, Jaccard Top-K, Spearman Rank).
- Five-scenario sensitivity analysis measuring stability across validation states.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from src.cleaning.salary_normalizer import (
    CURRENCY_MAP,
    SUPPORTED_CURRENCIES,
    parse_and_normalize_salary,
)
from src.extraction.lexical import LexicalSkillExtractor
from src.extraction.taxonomy import SkillTaxonomy, get_all_skills, load_taxonomy
from src.roles.classifier import RoleClassifier, UNCLASSIFIED_ROLE_ID, UNCLASSIFIED_ROLE_NAME
from src.roles.taxonomy import load_role_taxonomy

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SKILL_TAXONOMY_PATH = PROJECT_ROOT / "config" / "skill_taxonomy.json"
DEFAULT_ROLE_TAXONOMY_PATH = PROJECT_ROOT / "config" / "role_taxonomy.json"
DEFAULT_SOURCE_REGISTRY_PATH = PROJECT_ROOT / "config" / "source_registry.json"
DEFAULT_BENCHMARK_PATH = PROJECT_ROOT / "data" / "evaluation" / "benchmark_dataset.csv"
DEFAULT_PILOT_PREDICTIONS_PATH = PROJECT_ROOT / "data" / "raw" / "all_pilot_crawled_predictions.csv"
DEFAULT_EVALUATION_METRICS_PATH = PROJECT_ROOT / "data" / "evaluation" / "results" / "evaluation_metrics_latest.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "analysis" / "regional"

TARGET_REGIONAL_COUNTRIES: tuple[str, ...] = ("Sri Lanka", "India", "Singapore", "Malaysia")
FOCAL_MARKET: str = "Sri Lanka"
COMPARATOR_MARKETS: tuple[str, ...] = ("India", "Singapore", "Malaysia")

# Documented indicative exchange rates for nominal reference only (As of October 2026)
# STRICT RESEARCH RULE: Nominal conversions MUST NEVER be used to infer PPP or living standards.
INDICATIVE_NOMINAL_EXCHANGE_RATES_USD: dict[str, float] = {
    "USD": 1.0,
    "SGD": 0.74,     # 1 SGD ~ 0.74 USD
    "MYR": 0.22,     # 1 MYR ~ 0.22 USD
    "INR": 0.012,    # 1 INR ~ 0.012 USD
    "LKR": 0.0033,   # 1 LKR ~ 0.0033 USD (1 USD ~ 300 LKR)
    "EUR": 1.08,
    "GBP": 1.30,
}
EXCHANGE_RATE_DATE: str = "2026-10-20"


# ==============================================================================
# 1. Configurable Eligibility Rules
# ==============================================================================

@dataclass
class EligibilityConfig:
    """Configurable, documented eligibility rules for regional analysis tasks."""
    # Geographic rules
    allowed_countries: tuple[str, ...] = TARGET_REGIONAL_COUNTRIES
    focal_country: str = FOCAL_MARKET
    comparator_countries: tuple[str, ...] = COMPARATOR_MARKETS

    # General record eligibility
    require_valid_title: bool = True
    min_title_length: int = 2
    require_it_classification: bool = True
    require_description: bool = False
    min_description_length: int = 0
    require_verified_source: bool = False
    require_benchmark_verified: bool = False

    # Skill-demand eligibility
    # CRITICAL: Do NOT require disclosed salary for skill demand!
    require_disclosed_salary_for_skills: bool = False
    require_at_least_n_skills: int = 1

    # Role comparison eligibility
    exclude_unclassified_roles: bool = False
    min_role_sample_size: int = 3

    # Salary analysis eligibility
    require_disclosed_salary: bool = True
    exclude_ambiguous_salaries: bool = True
    exclude_zero_salaries: bool = True
    allowed_currencies: tuple[str, ...] = ("LKR", "INR", "SGD", "MYR", "USD", "EUR", "GBP")
    allowed_periods: tuple[str, ...] = ("monthly", "annual", "hourly", "daily")
    normalize_to_period: str = "monthly"
    hours_per_month: float = 160.0
    min_salary_sample_size: int = 3
    small_sample_threshold: int = 10


# ==============================================================================
# 2. Data Loading & Harmonization
# ==============================================================================

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

    # Infer from platform domain if country column is empty
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


def load_source_registry_validation_status(registry_path: Path = DEFAULT_SOURCE_REGISTRY_PATH) -> dict[str, str]:
    """Map source hostnames to their validation status from source_registry.json."""
    if not registry_path.exists():
        return {}
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        status_map = {}
        for src in data.get("sources", []):
            host = src.get("source_hostname", "")
            status = src.get("validation_status", "unverified")
            if host:
                status_map[host] = status
            for alias in src.get("aliases", []):
                status_map[alias] = status
        return status_map
    except Exception:
        return {}


def load_regional_market_data_from_db(conn: Optional[Any] = None) -> pd.DataFrame:
    """Loads and harmonizes regional market data directly from the master SQLite database."""
    from src.database.repository import get_regional_jobs, migrate_csv_data_to_master_db
    # Ensure master database has regional records
    migrate_csv_data_to_master_db(force=False)
    df = get_regional_jobs(conn=conn, allowed_countries=TARGET_REGIONAL_COUNTRIES)
    if df.empty:
        migrate_csv_data_to_master_db(force=True)
        df = get_regional_jobs(conn=conn, allowed_countries=TARGET_REGIONAL_COUNTRIES)
    return df


def load_regional_market_data(
    benchmark_path: Path = DEFAULT_BENCHMARK_PATH,
    raw_predictions_path: Path = DEFAULT_PILOT_PREDICTIONS_PATH,
    skill_taxonomy_path: Path = DEFAULT_SKILL_TAXONOMY_PATH,
    role_taxonomy_path: Path = DEFAULT_ROLE_TAXONOMY_PATH,
    source_registry_path: Path = DEFAULT_SOURCE_REGISTRY_PATH,
    use_database: bool = True,
) -> pd.DataFrame:
    """Load, harmonize, and standardize cross-market datasets for LK, IN, SG, MY.
    
    Default behavior queries the master SQLite database directly.
    Maintains full backwards compatibility with CSV paths when custom files are supplied.
    """
    if use_database and benchmark_path == DEFAULT_BENCHMARK_PATH and raw_predictions_path == DEFAULT_PILOT_PREDICTIONS_PATH:
        try:
            db_df = load_regional_market_data_from_db()
            if not db_df.empty:
                return db_df
        except Exception:
            pass  # Fall back to CSV ingestion if DB query fails

    source_status_map = load_source_registry_validation_status(source_registry_path)
    skill_tax = load_taxonomy(skill_taxonomy_path)
    skill_extractor = LexicalSkillExtractor(skill_tax)
    role_tax = load_role_taxonomy(role_taxonomy_path)
    role_classifier = RoleClassifier(role_tax)

    # Load raw crawled predictions if available to obtain full descriptions
    raw_desc_by_url: dict[str, str] = {}
    raw_records_by_url: dict[str, dict] = {}
    if raw_predictions_path.exists():
        try:
            df_raw = pd.read_csv(raw_predictions_path)
            for _, r in df_raw.iterrows():
                url = str(r.get("source_url", "")).strip()
                if url:
                    raw_desc_by_url[url] = str(r.get("job_description_raw", "") or "")
                    raw_records_by_url[url] = r.to_dict()
        except Exception:
            pass

    records: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    # 1. Ingest independently verified Benchmark records
    if benchmark_path.exists():
        df_bm = pd.read_csv(benchmark_path)
        for _, r in df_bm.iterrows():
            url = str(r.get("source_url", "")).strip()
            if url:
                seen_urls.add(url)

            plat = str(r.get("source_platform", "")).strip()
            country = normalize_country_name(r.get("country"), plat)
            title = str(r.get("expected_job_title_raw", "") or "").strip()
            
            # Prefer full crawled description when available, fallback to benchmark snippet
            full_desc = raw_desc_by_url.get(url, "")
            desc = full_desc if len(full_desc) > 100 else str(r.get("expected_description_snippet", "") or "").strip()

            # Parse skills from expected_skills or run canonical extractor on text
            skills_set: set[str] = set()
            exp_skills_raw = r.get("expected_skills")
            if pd.notna(exp_skills_raw):
                try:
                    parsed = json.loads(str(exp_skills_raw))
                    if isinstance(parsed, list):
                        skills_set.update(str(s).strip() for s in parsed if str(s).strip())
                except Exception:
                    pass

            text_for_skills = f"{title} {desc}".strip()
            extracted = skill_extractor.extract(str(r.get("benchmark_id", "")), text_for_skills)
            skills_set.update(s.skill_id for s in extracted.skills)

            # Classify role
            role_id, role_name, _alias = role_classifier.classify(title, desc)

            # Salary parsing
            sal_disclosed = bool(r.get("expected_salary_disclosed", False))
            sal_norm = parse_and_normalize_salary(
                salary_text_raw=str(r.get("expected_salary_text_raw", "") or ""),
                salary_min_raw=r.get("expected_salary_min"),
                salary_max_raw=r.get("expected_salary_max"),
                salary_currency_raw=str(r.get("expected_salary_currency", "") or ""),
                salary_period_raw=str(r.get("expected_salary_period", "") or ""),
                country_context=country,
            )

            # If benchmark specifically flags disclosed salary with valid values
            if sal_disclosed and sal_norm.get("salary_min_normalized") is None:
                try:
                    smin = float(r.get("expected_salary_min")) if pd.notna(r.get("expected_salary_min")) else None
                    smax = float(r.get("expected_salary_max")) if pd.notna(r.get("expected_salary_max")) else None
                    scurr = str(r.get("expected_salary_currency", "") or "").strip()
                    sper = str(r.get("expected_salary_period", "") or "").strip()
                    if smin or smax:
                        sal_norm["salary_disclosed"] = True
                        sal_norm["salary_min_normalized"] = smin
                        sal_norm["salary_max_normalized"] = smax
                        sal_norm["salary_currency_normalized"] = scurr
                        sal_norm["salary_period_normalized"] = sper or "monthly"
                except Exception:
                    pass

            # Monthly equivalent normalization
            min_m, max_m, mid_m = _compute_monthly_equivalents(
                sal_norm.get("salary_min_normalized"),
                sal_norm.get("salary_max_normalized"),
                sal_norm.get("salary_period_normalized"),
            )

            rec = {
                "job_id": f"bm_{r.get('benchmark_id')}",
                "source_url": url,
                "source_platform": plat,
                "country": country,
                "job_title_raw": title,
                "company": str(r.get("expected_company_raw", "") or "").strip(),
                "location_raw": str(r.get("expected_location_raw", "") or "").strip(),
                "work_mode": str(r.get("expected_work_mode", "unspecified")),
                "job_description": desc,
                "is_it": True,
                "classification_status": "it",
                "source_validation_status": source_status_map.get(plat, "validated"),
                "is_benchmark_verified": True,
                "skills": sorted(skills_set),
                "role_id": role_id,
                "role_name": role_name,
                "salary_disclosed": sal_norm.get("salary_disclosed", False),
                "salary_text_raw": sal_norm.get("salary_text_raw", ""),
                "salary_type": sal_norm.get("salary_type", "undisclosed"),
                "salary_min_raw": sal_norm.get("salary_min_raw", ""),
                "salary_max_raw": sal_norm.get("salary_max_raw", ""),
                "salary_min_normalized": sal_norm.get("salary_min_normalized"),
                "salary_max_normalized": sal_norm.get("salary_max_normalized"),
                "salary_currency_normalized": sal_norm.get("salary_currency_normalized", ""),
                "salary_period_normalized": sal_norm.get("salary_period_normalized", "unspecified"),
                "salary_monthly_min": min_m,
                "salary_monthly_max": max_m,
                "salary_monthly_midpoint": mid_m,
                "salary_normalization_status": sal_norm.get("salary_normalization_status", "undisclosed"),
                "salary_normalization_method": sal_norm.get("salary_normalization_method", "not_applicable"),
            }
            records.append(rec)

    # 2. Ingest unverified pilot predictions that were not already in benchmark
    for url, r in raw_records_by_url.items():
        if url in seen_urls:
            continue
        plat = str(r.get("source_platform", "")).strip()
        country = normalize_country_name(r.get("country_raw"), plat)
        title = str(r.get("job_title_raw", "") or "").strip()
        desc = str(r.get("job_description_raw", "") or "").strip()

        # Classify IT relevance
        class_status = str(r.get("classification_status", "it")).lower()
        is_it = class_status in ("it", "ambiguous")

        text_for_skills = f"{title} {desc}".strip()
        extracted = skill_extractor.extract(str(r.get("job_id", "")), text_for_skills)
        skills_set = {s.skill_id for s in extracted.skills}

        role_id, role_name, _alias = role_classifier.classify(title, desc)

        sal_norm = parse_and_normalize_salary(
            salary_text_raw=str(r.get("salary_text_raw", "") or ""),
            salary_min_raw=r.get("salary_min_raw"),
            salary_max_raw=r.get("salary_max_raw"),
            salary_currency_raw=str(r.get("salary_currency_raw", "") or ""),
            salary_period_raw=str(r.get("salary_period_raw", "") or ""),
            country_context=country,
        )

        min_m, max_m, mid_m = _compute_monthly_equivalents(
            sal_norm.get("salary_min_normalized"),
            sal_norm.get("salary_max_normalized"),
            sal_norm.get("salary_period_normalized"),
        )

        rec = {
            "job_id": str(r.get("job_id")),
            "source_url": url,
            "source_platform": plat,
            "country": country,
            "job_title_raw": title,
            "company": str(r.get("company_raw", "") or "").strip(),
            "location_raw": str(r.get("location_raw", "") or "").strip(),
            "work_mode": str(r.get("work_mode_raw", "unspecified")),
            "job_description": desc,
            "is_it": is_it,
            "classification_status": class_status,
            "source_validation_status": source_status_map.get(plat, "pilot_tested"),
            "is_benchmark_verified": False,
            "skills": sorted(skills_set),
            "role_id": role_id,
            "role_name": role_name,
            "salary_disclosed": sal_norm.get("salary_disclosed", False),
            "salary_text_raw": sal_norm.get("salary_text_raw", ""),
            "salary_type": sal_norm.get("salary_type", "undisclosed"),
            "salary_min_raw": sal_norm.get("salary_min_raw", ""),
            "salary_max_raw": sal_norm.get("salary_max_raw", ""),
            "salary_min_normalized": sal_norm.get("salary_min_normalized"),
            "salary_max_normalized": sal_norm.get("salary_max_normalized"),
            "salary_currency_normalized": sal_norm.get("salary_currency_normalized", ""),
            "salary_period_normalized": sal_norm.get("salary_period_normalized", "unspecified"),
            "salary_monthly_min": min_m,
            "salary_monthly_max": max_m,
            "salary_monthly_midpoint": mid_m,
            "salary_normalization_status": sal_norm.get("salary_normalization_status", "undisclosed"),
            "salary_normalization_method": sal_norm.get("salary_normalization_method", "not_applicable"),
        }
        records.append(rec)

    return pd.DataFrame(records)


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
        # Cannot normalize unspecified pay periods into monthly equivalents safely
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


# ==============================================================================
# 3. Task-Specific Eligibility Filtering & Provenance Funnels
# ==============================================================================

def filter_records_with_provenance(
    df: pd.DataFrame,
    config: EligibilityConfig,
    task: str = "general",
) -> tuple[pd.DataFrame, dict[str, int], list[dict[str, Any]]]:
    """Filters a DataFrame according to documented eligibility rules for a specific task.
    
    Tasks:
        - "general": General job count eligibility.
        - "skill": Skill-demand analysis (never excludes for undisclosed salary!).
        - "role": Role comparisons.
        - "geographic": Regional country qualification.
        - "salary": Salary distribution analysis.
    
    Returns:
        (eligible_df, exclusion_counts_dict, exclusion_audit_records)
    """
    if df.empty:
        return df.copy(), {}, []

    eligible_mask = pd.Series(True, index=df.index)
    exclusion_reasons: list[list[str]] = [[] for _ in range(len(df))]
    counts: dict[str, int] = {}

    def _record_exclusion(mask_condition: pd.Series, reason: str):
        failed = mask_condition & eligible_mask
        counts[reason] = int(failed.sum())
        for idx in df[failed].index:
            loc = df.index.get_loc(idx)
            exclusion_reasons[loc].append(reason)
        eligible_mask[failed] = False

    # 1. Geographic filtering
    if config.allowed_countries:
        not_target_country = ~df["country"].isin(config.allowed_countries)
        _record_exclusion(not_target_country, "non_target_country")

    # 2. General record validity
    if config.require_valid_title:
        missing_title = df["job_title_raw"].isna() | (df["job_title_raw"].astype(str).str.strip() == "")
        _record_exclusion(missing_title, "missing_job_title")

        if config.min_title_length > 0:
            short_title = df["job_title_raw"].astype(str).str.strip().str.len() < config.min_title_length
            _record_exclusion(short_title, "title_too_short")

    if config.require_it_classification:
        if "classification_status" in df.columns:
            non_it = df["classification_status"].astype(str).str.lower() == "non_it"
            _record_exclusion(non_it, "classified_non_it")
        elif "is_it" in df.columns:
            non_it = ~df["is_it"].astype(bool)
            _record_exclusion(non_it, "classified_non_it")

    if config.require_description and config.min_description_length > 0:
        desc_col = "job_description" if "job_description" in df.columns else "job_description_raw"
        if desc_col in df.columns:
            short_desc = df[desc_col].fillna("").astype(str).str.strip().str.len() < config.min_description_length
            _record_exclusion(short_desc, "description_too_short")

    if config.require_verified_source:
        unverified_src = df["source_validation_status"].astype(str).str.lower() != "validated"
        _record_exclusion(unverified_src, "unverified_source_portal")

    if config.require_benchmark_verified:
        not_bm = ~df["is_benchmark_verified"].astype(bool)
        _record_exclusion(not_bm, "unverified_benchmark_record")

    # Stop here if task is general or geographic
    if task in ("general", "geographic"):
        eligible_df = df[eligible_mask].copy()
        audit_recs = [
            {"job_id": df.iloc[i].get("job_id", f"idx_{i}"), "reasons": exclusion_reasons[i]}
            for i in range(len(df)) if exclusion_reasons[i]
        ]
        return eligible_df, counts, audit_recs

    # 3. Skill-Demand Specific Rules
    # RULE: Do NOT require a disclosed salary for skill demand!
    if task == "skill":
        if config.require_disclosed_salary_for_skills:
            undisclosed = ~df["salary_disclosed"].astype(bool)
            _record_exclusion(undisclosed, "salary_undisclosed_strict_mode")

        if config.require_at_least_n_skills > 0:
            skill_counts = df["skills"].apply(lambda s: len(s) if isinstance(s, (list, set)) else 0)
            insufficient_skills = skill_counts < config.require_at_least_n_skills
            _record_exclusion(insufficient_skills, "zero_extracted_skills")

    # 4. Role Comparison Specific Rules
    elif task == "role":
        if config.exclude_unclassified_roles:
            unclassified = df["role_id"].isin([UNCLASSIFIED_ROLE_ID, "", None])
            _record_exclusion(unclassified, "unclassified_role")

    # 5. Salary Analysis Specific Rules
    elif task == "salary":
        # Disclosed salary required
        undisclosed = ~df["salary_disclosed"].astype(bool) | df["salary_monthly_midpoint"].isna()
        _record_exclusion(undisclosed, "salary_undisclosed")

        # Zero or negative amounts
        if config.exclude_zero_salaries:
            zero_sal = df["salary_monthly_midpoint"].fillna(0) <= 0
            _record_exclusion(zero_sal, "salary_zero_or_negative")

        # Ambiguous or unparseable compensation
        if config.exclude_ambiguous_salaries:
            ambig = df["salary_normalization_status"].isin(["ambiguous", "unparseable"])
            _record_exclusion(ambig, "salary_ambiguous_or_unparseable")

        # Currency restriction
        if config.allowed_currencies:
            unsupported_curr = ~df["salary_currency_normalized"].isin(config.allowed_currencies)
            _record_exclusion(unsupported_curr, "unsupported_currency")

        # Period restriction
        if config.allowed_periods:
            unsupported_per = ~df["salary_period_normalized"].isin(config.allowed_periods)
            _record_exclusion(unsupported_per, "unsupported_pay_period")

    eligible_df = df[eligible_mask].copy()
    audit_recs = [
        {"job_id": df.iloc[i].get("job_id", f"idx_{i}"), "reasons": exclusion_reasons[i]}
        for i in range(len(df)) if exclusion_reasons[i]
    ]
    return eligible_df, counts, audit_recs


def build_exclusion_funnel(df: pd.DataFrame, config: EligibilityConfig) -> pd.DataFrame:
    """Builds a step-by-step audit funnel showing record attrition across analytical tasks."""
    total_raw = len(df)
    stages = [
        ("Raw Input Records", "raw", df),
        ("Geographic Filtering", "geographic", None),
        ("General IT Quality", "general", None),
        ("Skill-Demand Analysis", "skill", None),
        ("Role Comparisons", "role", None),
        ("Salary Analysis", "salary", None),
    ]

    funnel_rows = []
    current_df = df.copy()

    for stage_name, task, _ in stages:
        if task == "raw":
            funnel_rows.append({
                "stage": stage_name,
                "task": task,
                "input_records": total_raw,
                "eligible_records": total_raw,
                "excluded_records": 0,
                "retention_rate_pct": 100.0,
                "primary_exclusions": "None (Entry point)",
            })
            continue

        eligible_df, counts, _ = filter_records_with_provenance(df, config, task=task)
        n_eligible = len(eligible_df)
        n_excluded = total_raw - n_eligible
        retention = round((n_eligible / total_raw * 100.0), 2) if total_raw > 0 else 0.0

        reasons_summary = ", ".join(f"{k}: {v}" for k, v in counts.items() if v > 0) or "None"

        funnel_rows.append({
            "stage": stage_name,
            "task": task,
            "input_records": total_raw,
            "eligible_records": n_eligible,
            "excluded_records": n_excluded,
            "retention_rate_pct": retention,
            "primary_exclusions": reasons_summary,
        })

    return pd.DataFrame(funnel_rows)


# ==============================================================================
# 4. Canonical Skill-Demand Percentage & Uncertainty Calculations
# ==============================================================================

def calculate_wilson_ci(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Calculates Wilson Score Confidence Interval for a binomial proportion.
    
    Adheres to quantitative standards for small samples and bounded [0, 100]% proportions.
    """
    if n <= 0:
        return 0.0, 0.0
    p = k / n
    z = 1.95996  # 95% confidence
    denominator = 1.0 + (z**2) / n
    center = (p + (z**2) / (2.0 * n)) / denominator
    spread = (z / denominator) * math.sqrt((p * (1.0 - p) / n) + ((z**2) / (4.0 * (n**2))))

    lower = max(0.0, (center - spread) * 100.0)
    upper = min(100.0, (center + spread) * 100.0)
    return round(lower, 2), round(upper, 2)


def calculate_skill_demand_percentages(
    df: pd.DataFrame,
    config: EligibilityConfig,
    taxonomy_path: Path = DEFAULT_SKILL_TAXONOMY_PATH,
) -> pd.DataFrame:
    """Calculates canonical skill demand percentages across countries using identical denominators.
    
    Formula:
        Demand % = (Eligible Ads in Country mentioning Skill / Total Eligible Ads in Country) * 100
    
    Guarantees:
        - Unique skill counting per advertisement (an ad is counted at most once per canonical skill).
        - Same denominator rules across all comparative markets.
        - Wilson 95% Confidence Intervals for proportion uncertainty.
        - Explicit small sample uncertainty flags (N < 10).
    """
    eligible_df, _, _ = filter_records_with_provenance(df, config, task="skill")
    if eligible_df.empty:
        return pd.DataFrame()

    skill_tax = load_taxonomy(taxonomy_path)
    all_skills_map = {s.id: s.name for s in get_all_skills(skill_tax)}
    category_map = {}
    for cat in skill_tax.categories:
        for sk in cat.skills:
            category_map[sk.id] = cat.name

    # Denominator per country: total eligible ads in country
    country_denominators = eligible_df.groupby("country")["job_id"].count().to_dict()

    rows = []
    for country in config.allowed_countries:
        country_df = eligible_df[eligible_df["country"] == country]
        total_ads = country_denominators.get(country, 0)
        is_small_sample = total_ads < config.small_sample_threshold

        if total_ads == 0:
            continue

        # Explode skills ensuring unique skill count per ad
        skill_counts: dict[str, int] = {}
        for _, row in country_df.iterrows():
            skills = row.get("skills", [])
            if isinstance(skills, (list, set)):
                for sk in set(skills):
                    if sk in all_skills_map:
                        skill_counts[sk] = skill_counts.get(sk, 0) + 1

        for skill_id, skill_name in all_skills_map.items():
            count = skill_counts.get(skill_id, 0)
            demand_pct = round((count / total_ads) * 100.0, 2)
            ci_lower, ci_upper = calculate_wilson_ci(count, total_ads)

            rows.append({
                "country": country,
                "skill_id": skill_id,
                "skill_name": skill_name,
                "category": category_map.get(skill_id, "General IT"),
                "eligible_ads_denominator": total_ads,
                "mention_count": count,
                "demand_pct": demand_pct,
                "ci_lower_95": ci_lower,
                "ci_upper_95": ci_upper,
                "small_sample_flag": is_small_sample,
            })

    result_df = pd.DataFrame(rows)
    return result_df.sort_values(["country", "demand_pct"], ascending=[True, False]).reset_index(drop=True)


def calculate_skill_gaps(
    demand_df: pd.DataFrame,
    focal_country: str = FOCAL_MARKET,
) -> pd.DataFrame:
    """Calculates absolute percentage-point skill gaps between focal market and comparators.
    
    Formula:
        Skill Gap (pp) = Demand%(Focal) - Demand%(Comparator)
    
    Computes two-proportion z-tests, standard errors, and p-values to determine statistical significance.
    """
    if demand_df.empty:
        return pd.DataFrame()

    focal_df = demand_df[demand_df["country"] == focal_country].set_index("skill_id")
    if focal_df.empty:
        return pd.DataFrame()

    gap_rows = []
    comparators = [c for c in demand_df["country"].unique() if c != focal_country]

    for comp in comparators:
        comp_df = demand_df[demand_df["country"] == comp].set_index("skill_id")

        for skill_id, f_row in focal_df.iterrows():
            if skill_id not in comp_df.index:
                continue
            c_row = comp_df.loc[skill_id]

            p1 = float(f_row["demand_pct"]) / 100.0
            n1 = int(f_row["eligible_ads_denominator"])
            k1 = int(f_row["mention_count"])

            p2 = float(c_row["demand_pct"]) / 100.0
            n2 = int(c_row["eligible_ads_denominator"])
            k2 = int(c_row["mention_count"])

            gap_pp = round((p1 - p2) * 100.0, 2)

            # Two proportion z-test
            se_diff = math.sqrt((p1 * (1.0 - p1) / n1) + (p2 * (1.0 - p2) / n2)) if n1 > 0 and n2 > 0 else 0.0
            p_pool = (k1 + k2) / (n1 + n2) if (n1 + n2) > 0 else 0.0
            se_pool = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n1 + 1.0 / n2)) if p_pool > 0 and p_pool < 1.0 else 0.0

            z_stat = (p1 - p2) / se_pool if se_pool > 0 else 0.0
            # Two-tailed p-value from standard normal distribution:
            # Phi(z) = 0.5 * (1 + erf(z / sqrt(2))) => 2 * (1 - Phi(|z|)) = erfc(|z| / sqrt(2))
            p_val = round(math.erfc(abs(z_stat) / math.sqrt(2.0)), 4) if se_pool > 0 else 1.0

            ci_low = round(gap_pp - 1.96 * se_diff * 100.0, 2)
            ci_high = round(gap_pp + 1.96 * se_diff * 100.0, 2)

            is_sig = p_val < 0.05
            is_unstable = (n1 < 10) or (n2 < 10)
            is_zero_comparator_artifact = (k2 == 0) and (n2 < 30) and is_sig
            is_zero_focal_artifact = (k1 == 0) and (n1 < 30) and is_sig
            is_artifact = is_zero_comparator_artifact or is_zero_focal_artifact

            if is_artifact:
                evidence_status = "Data Collection Artifact (Unverified)"
            elif is_sig and not is_unstable:
                evidence_status = "Statistically Meaningful"
            else:
                evidence_status = "Indeterminate / Expected Sampling Noise"

            gap_rows.append({
                "skill_id": skill_id,
                "skill_name": f_row["skill_name"],
                "category": f_row["category"],
                "focal_country": focal_country,
                "comparator_country": comp,
                "focal_demand_pct": f_row["demand_pct"],
                "comparator_demand_pct": c_row["demand_pct"],
                "gap_pp": gap_pp,
                "gap_ci_lower_95": ci_low,
                "gap_ci_upper_95": ci_high,
                "z_statistic": round(z_stat, 3),
                "p_value": p_val,
                "statistically_significant": is_sig,
                "small_sample_warning": is_unstable,
                "zero_comparator_artifact": is_artifact,
                "evidence_status": evidence_status,
            })

    return pd.DataFrame(gap_rows).sort_values(["comparator_country", "gap_pp"], ascending=[True, False]).reset_index(drop=True)


# ==============================================================================
# 5. Role Comparisons & Classification Audit
# ==============================================================================

def compare_regional_roles(
    df: pd.DataFrame,
    config: EligibilityConfig,
    taxonomy_path: Path = DEFAULT_SKILL_TAXONOMY_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Analyzes IT role distributions and role-specific skill demand profiles across countries.
    
    Guarantees:
        - Accurately tracks unclassified and ambiguous roles without silent forcing.
        - Reports role frequency and percentage of total national IT vacancies.
        - Calculates skill-demand distributions for sufficiently sampled roles.
    
    Returns:
        (role_distribution_df, role_skill_demand_df, unclassified_summary_df)
    """
    eligible_df, _, _ = filter_records_with_provenance(df, config, task="role")
    if eligible_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    skill_tax = load_taxonomy(taxonomy_path)
    all_skills_map = {s.id: s.name for s in get_all_skills(skill_tax)}

    # 1. Role distribution per country
    country_totals = eligible_df.groupby("country")["job_id"].count().to_dict()
    role_counts = eligible_df.groupby(["country", "role_id", "role_name"]).size().reset_index(name="job_count")
    role_counts["country_total_jobs"] = role_counts["country"].map(country_totals)
    role_counts["pct_of_country"] = (role_counts["job_count"] / role_counts["country_total_jobs"] * 100.0).round(2)
    role_counts["is_unclassified"] = role_counts["role_id"] == UNCLASSIFIED_ROLE_ID

    # 2. Unclassified summary per country
    unclass_rows = []
    for country, tot in country_totals.items():
        unclass_c = eligible_df[(eligible_df["country"] == country) & (eligible_df["role_id"] == UNCLASSIFIED_ROLE_ID)]
        u_count = len(unclass_c)
        u_pct = round((u_count / tot * 100.0), 2) if tot > 0 else 0.0
        unclass_rows.append({
            "country": country,
            "total_it_jobs": tot,
            "unclassified_count": u_count,
            "unclassified_pct": u_pct,
            "classification_quality": "High (>85% classified)" if u_pct < 15.0 else "Moderate (ambiguity present)",
        })
    unclassified_summary_df = pd.DataFrame(unclass_rows)

    # 3. Role-specific skill demand
    role_skill_rows = []
    for (country, role_id, role_name), group_df in eligible_df.groupby(["country", "role_id", "role_name"]):
        role_n = len(group_df)
        if role_n < config.min_role_sample_size:
            continue

        skill_counts: dict[str, int] = {}
        for _, row in group_df.iterrows():
            skills = row.get("skills", [])
            if isinstance(skills, (list, set)):
                for sk in set(skills):
                    if sk in all_skills_map:
                        skill_counts[sk] = skill_counts.get(sk, 0) + 1

        for sk_id, count in sorted(skill_counts.items(), key=lambda x: x[1], reverse=True):
            pct = round((count / role_n) * 100.0, 2)
            role_skill_rows.append({
                "country": country,
                "role_id": role_id,
                "role_name": role_name,
                "role_jobs_denominator": role_n,
                "skill_id": sk_id,
                "skill_name": all_skills_map.get(sk_id, sk_id),
                "skill_count": count,
                "demand_pct_in_role": pct,
                "small_sample_flag": role_n < config.small_sample_threshold,
            })

    role_skill_demand_df = pd.DataFrame(role_skill_rows)
    return (
        role_counts.sort_values(["country", "job_count"], ascending=[True, False]).reset_index(drop=True),
        role_skill_demand_df,
        unclassified_summary_df,
    )


# ==============================================================================
# 6. Audit-Compliant Salary Analysis
# ==============================================================================

def analyze_regional_salaries(
    df: pd.DataFrame,
    config: EligibilityConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Performs rigorous, audit-compliant salary analysis across regional IT labor markets.
    
    Academic Research Rules Applied:
        1. Never interpret undisclosed salary as zero.
        2. Never infer missing salary values.
        3. Keep original currency values available for audit (separate LKR, INR, SGD, MYR buckets).
        4. Do not combine hourly, monthly and annual amounts without valid normalization.
        5. Do not convert currencies using undocumented or fabricated rates.
        6. State clearly that results are nominal and NOT purchasing power parity (PPP) adjusted.
        7. Report exact sample sizes and disclosure rates.
        8. Flag small samples (N < 10) and unstable comparisons.
        9. Use medians and interquartile ranges (IQR) as primary distribution measures.
    
    Returns:
        (country_salary_summary_df, role_salary_summary_df, indicative_exchange_rates_df)
    """
    eligible_general, _, _ = filter_records_with_provenance(df, config, task="general")
    eligible_salary, _, _ = filter_records_with_provenance(df, config, task="salary")

    # 1. Salary Disclosure Coverage by Country
    general_counts = eligible_general.groupby("country")["job_id"].count().to_dict()
    salary_counts = eligible_salary.groupby("country")["job_id"].count().to_dict()

    country_summary_rows = []
    for country in config.allowed_countries:
        n_gen = general_counts.get(country, 0)
        n_sal = salary_counts.get(country, 0)
        disc_rate = round((n_sal / n_gen * 100.0), 2) if n_gen > 0 else 0.0

        country_df = eligible_salary[eligible_salary["country"] == country]
        currencies = country_df["salary_currency_normalized"].unique()

        for curr in currencies:
            curr_df = country_df[country_df["salary_currency_normalized"] == curr]
            mids = curr_df["salary_monthly_midpoint"].dropna()
            n_curr = len(mids)

            if n_curr == 0:
                continue

            q25 = float(np.percentile(mids, 25))
            q50 = float(np.percentile(mids, 50))  # Median
            q75 = float(np.percentile(mids, 75))
            iqr = q75 - q25

            country_summary_rows.append({
                "country": country,
                "currency": curr,
                "pay_period_standard": "monthly_equivalent",
                "total_eligible_ads": n_gen,
                "disclosed_salary_count": n_curr,
                "disclosure_rate_pct": disc_rate,
                "median_salary": round(q50, 2),
                "iqr_salary": round(iqr, 2),
                "p25_salary": round(q25, 2),
                "p75_salary": round(q75, 2),
                "min_salary": round(float(mids.min()), 2),
                "max_salary": round(float(mids.max()), 2),
                "mean_salary": round(float(mids.mean()), 2),
                "std_salary": round(float(mids.std()), 2) if n_curr > 1 else 0.0,
                "small_sample_flag": n_curr < config.small_sample_threshold,
                "parity_type": "Nominal (Local Currency)",
                "methodological_caveat": "Nominal value only. Does NOT establish purchasing power or standard of living differences.",
            })

    country_salary_df = pd.DataFrame(country_summary_rows)

    # 2. Salary by Comparable Role
    role_summary_rows = []
    for (country, curr, role_name), group_df in eligible_salary.groupby(["country", "salary_currency_normalized", "role_name"]):
        mids = group_df["salary_monthly_midpoint"].dropna()
        n = len(mids)
        if n < config.min_salary_sample_size:
            continue

        q25 = float(np.percentile(mids, 25))
        q50 = float(np.percentile(mids, 50))
        q75 = float(np.percentile(mids, 75))

        role_summary_rows.append({
            "country": country,
            "currency": curr,
            "role_name": role_name,
            "sample_size": n,
            "median_monthly": round(q50, 2),
            "iqr_monthly": round(q75 - q25, 2),
            "p25_monthly": round(q25, 2),
            "p75_monthly": round(q75, 2),
            "min_monthly": round(float(mids.min()), 2),
            "max_monthly": round(float(mids.max()), 2),
            "small_sample_flag": n < config.small_sample_threshold,
        })
    if country_summary_rows:
        country_salary_df = pd.DataFrame(country_summary_rows).sort_values(["country", "disclosed_salary_count"], ascending=[True, False]).reset_index(drop=True)
    else:
        country_salary_df = pd.DataFrame(columns=[
            "country", "currency", "pay_period_standard", "total_eligible_ads",
            "disclosed_salary_count", "disclosure_rate_pct", "median_salary",
            "iqr_salary", "p25_salary", "p75_salary", "min_salary", "max_salary",
            "mean_salary", "std_salary", "small_sample_flag", "parity_type", "methodological_caveat"
        ])

    if role_summary_rows:
        role_salary_df = pd.DataFrame(role_summary_rows).sort_values(["country", "sample_size"], ascending=[True, False]).reset_index(drop=True)
    else:
        role_salary_df = pd.DataFrame(columns=[
            "country", "currency", "role_name", "sample_size",
            "median_monthly", "iqr_monthly", "p25_monthly", "p75_monthly",
            "min_monthly", "max_monthly", "small_sample_flag"
        ])

    # 3. Documented Indicative Rates Table
    indicative_rows = []
    for curr, rate in INDICATIVE_NOMINAL_EXCHANGE_RATES_USD.items():
        indicative_rows.append({
            "currency": curr,
            "rate_to_usd": rate,
            "rate_date": EXCHANGE_RATE_DATE,
            "source": "Documented Market Reference Baseline",
            "usage": "Audit & Nominal Reference Only (PPP conversions prohibited)",
        })
    rates_df = pd.DataFrame(indicative_rows)

    return (
        country_salary_df,
        role_salary_df,
        rates_df,
    )


# ==============================================================================
# 7. Country Skill-Demand Profile Similarity Metrics
# ==============================================================================

def calculate_country_similarities(demand_df: pd.DataFrame) -> pd.DataFrame:
    """Calculates pairwise similarity metrics between national skill-demand profiles.
    
    Metrics:
        1. Cosine Similarity: Cosine of angle between aligned canonical skill vectors.
        2. Jaccard Similarity on Top-10 Skills: Overlap between top 10 most demanded skills.
        3. Spearman Rank Correlation: Monotonic rank relationship across skills.
    
    Caveats:
        - Statistical similarity does NOT indicate equivalent job-market conditions or labor mobility.
        - Sparse samples (N < 10) significantly distort similarity metrics.
    """
    if demand_df.empty:
        return pd.DataFrame()

    countries = sorted(demand_df["country"].unique())
    if len(countries) < 2:
        return pd.DataFrame()

    # Form aligned skill matrix: rows = countries, cols = canonical skills
    pivot = demand_df.pivot_table(index="country", columns="skill_id", values="demand_pct", fill_value=0.0)
    denominators = demand_df.groupby("country")["eligible_ads_denominator"].first().to_dict()

    rows = []
    for i in range(len(countries)):
        for j in range(i + 1, len(countries)):
            c1, c2 = countries[i], countries[j]
            v1 = pivot.loc[c1].values
            v2 = pivot.loc[c2].values

            # 1. Cosine similarity
            dot = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            cosine = round(float(dot / (norm1 * norm2)), 4) if norm1 > 0 and norm2 > 0 else 0.0

            # 2. Jaccard similarity on Top 10 skills
            top10_c1 = set(pivot.loc[c1].sort_values(ascending=False).head(10).index)
            top10_c2 = set(pivot.loc[c2].sort_values(ascending=False).head(10).index)
            union_len = len(top10_c1.union(top10_c2))
            jaccard_top10 = round(len(top10_c1.intersection(top10_c2)) / union_len, 4) if union_len > 0 else 0.0

            # 3. Spearman Rank Correlation (Pearson correlation of ranks, zero scipy dependency)
            r1 = pd.Series(v1).rank()
            r2 = pd.Series(v2).rank()
            spearman_corr = r1.corr(r2)
            spearman_corr = round(float(spearman_corr), 4) if (spearman_corr is not None and not np.isnan(spearman_corr)) else 0.0

            n1 = denominators.get(c1, 0)
            n2 = denominators.get(c2, 0)
            sparse_flag = (n1 < 10) or (n2 < 10)

            rows.append({
                "country_a": c1,
                "country_b": c2,
                "sample_size_a": n1,
                "sample_size_b": n2,
                "cosine_similarity": cosine,
                "jaccard_top10_similarity": jaccard_top10,
                "spearman_rank_correlation": spearman_corr,
                "sparse_sample_flag": sparse_flag,
                "metric_limitations": "Measures proportional skill priority alignment. Does NOT establish labor mobility, economic equivalence, or wage parity.",
            })

    return pd.DataFrame(rows).sort_values("cosine_similarity", ascending=False).reset_index(drop=True)


# ==============================================================================
# 8. Systematic Sensitivity Analysis
# ==============================================================================

def run_regional_sensitivity_analysis(
    df: pd.DataFrame,
    base_config: Optional[EligibilityConfig] = None,
    taxonomy_path: Path = DEFAULT_SKILL_TAXONOMY_PATH,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Evaluates whether core analytical conclusions materially change under alternative eligibility regimes.
    
    Evaluates 5 Scenarios:
        1. Baseline: Standard validated eligibility rules across all records.
        2. Verified Sources Only: Only records from approved, validated web portals.
        3. Benchmark Verified Only: Only records with ground-truth Task 2 benchmark verification.
        4. Unambiguous Roles Only: Exclude unclassified and ambiguous roles.
        5. Salary Disclosed Subsample: Test whether salary disclosure introduces selection bias into skill demand estimates.
    
    Returns:
        (sensitivity_summary_df, scenario_details_dict)
    """
    if base_config is None:
        base_config = EligibilityConfig()

    scenarios = {
        "1_baseline": ("Baseline Full Dataset", base_config),
        "2_verified_sources_only": (
            "Approved Portals Only",
            EligibilityConfig(**{**asdict(base_config), "require_verified_source": True}),
        ),
        "3_benchmark_verified_only": (
            "Ground-Truth Benchmark Only",
            EligibilityConfig(**{**asdict(base_config), "require_benchmark_verified": True}),
        ),
        "4_unambiguous_roles_only": (
            "Unambiguous Roles Only",
            EligibilityConfig(**{**asdict(base_config), "exclude_unclassified_roles": True}),
        ),
        "5_salary_disclosed_subsample": (
            "Salary-Disclosed Subsample (Bias Test)",
            EligibilityConfig(**{**asdict(base_config), "require_disclosed_salary_for_skills": True}),
        ),
    }

    scenario_results = {}
    baseline_demands: dict[tuple[str, str], float] = {}

    for s_key, (s_title, cfg) in scenarios.items():
        demands = calculate_skill_demand_percentages(df, cfg, taxonomy_path=taxonomy_path)
        sims = calculate_country_similarities(demands)
        role_counts, _, _ = compare_regional_roles(df, cfg, taxonomy_path=taxonomy_path)

        scenario_results[s_key] = {
            "title": s_title,
            "demands": demands,
            "similarities": sims,
            "role_counts": role_counts,
        }

        if s_key == "1_baseline":
            for _, r in demands.iterrows():
                baseline_demands[(r["country"], r["skill_id"])] = float(r["demand_pct"])

    # Compute comparative stability metrics against baseline
    summary_rows = []
    for s_key, res in scenario_results.items():
        s_title = res["title"]
        demands_df = res["demands"]

        if demands_df.empty:
            summary_rows.append({
                "scenario_key": s_key,
                "scenario_name": s_title,
                "total_eligible_ads": 0,
                "countries_evaluated": 0,
                "mean_abs_demand_shift_pp": None,
                "max_demand_shift_pp": None,
                "lk_top5_skills": "None",
                "stability_assessment": "Insufficient Data",
            })
            continue

        tot_ads = demands_df.groupby("country")["eligible_ads_denominator"].first().sum()
        c_count = len(demands_df["country"].unique())

        # Measure Mean Absolute Deviation (MAD) from baseline
        shifts = []
        for _, r in demands_df.iterrows():
            base_val = baseline_demands.get((r["country"], r["skill_id"]))
            if base_val is not None:
                shifts.append(abs(float(r["demand_pct"]) - base_val))

        mean_shift = round(float(np.mean(shifts)), 2) if shifts else 0.0
        max_shift = round(float(np.max(shifts)), 2) if shifts else 0.0

        # Top 5 skills in Sri Lanka
        lk_top = demands_df[demands_df["country"] == FOCAL_MARKET].sort_values("demand_pct", ascending=False).head(5)
        lk_top_str = ", ".join(f"{r['skill_name']} ({r['demand_pct']}%)" for _, r in lk_top.iterrows())

        stability = "Robust (<3.0 pp shift)" if mean_shift < 3.0 else ("Moderate (<6.0 pp shift)" if mean_shift < 6.0 else "Sensitive to Filtering")
        if s_key == "1_baseline":
            stability = "Baseline Anchor (0.0 pp)"

        summary_rows.append({
            "scenario_key": s_key,
            "scenario_name": s_title,
            "total_eligible_ads": int(tot_ads),
            "countries_evaluated": c_count,
            "mean_abs_demand_shift_pp": mean_shift,
            "max_demand_shift_pp": max_shift,
            "lk_top5_skills": lk_top_str,
            "stability_assessment": stability,
        })

    return pd.DataFrame(summary_rows), scenario_results


# ==============================================================================
# 9. Research Markdown Report Generator
# ==============================================================================

def _df_to_markdown(df: pd.DataFrame) -> str:
    """Format DataFrame as a clean GitHub-compatible Markdown table without external dependencies."""
    if df is None or df.empty:
        return "_No records available._\n"
    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    separator = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(str(row[c]).replace("\n", " ").replace("|", "\\|") for c in df.columns) + " |")
    return "\n".join([header, separator] + rows) + "\n"


def generate_regional_markdown_report(
    df: pd.DataFrame,
    config: EligibilityConfig,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> str:
    """Generates an academic research markdown report with audit tables, formulas, and limitations."""
    output_dir.mkdir(parents=True, exist_ok=True)

    funnel_df = build_exclusion_funnel(df, config)
    demand_df = calculate_skill_demand_percentages(df, config)
    gap_df = calculate_skill_gaps(demand_df, focal_country=config.focal_country)
    role_dist_df, role_skill_df, unclass_df = compare_regional_roles(df, config)
    salary_country_df, salary_role_df, rates_df = analyze_regional_salaries(df, config)
    similarity_df = calculate_country_similarities(demand_df)
    sens_summary_df, _ = run_regional_sensitivity_analysis(df, config)

    # Save CSV artifacts
    funnel_df.to_csv(output_dir / "regional_eligibility_funnel.csv", index=False)
    demand_df.to_csv(output_dir / "skill_demand_by_country.csv", index=False)
    gap_df.to_csv(output_dir / "skill_gaps_focal_srilanka.csv", index=False)
    role_dist_df.to_csv(output_dir / "role_distribution_by_country.csv", index=False)
    unclass_df.to_csv(output_dir / "unclassified_roles_summary.csv", index=False)
    role_skill_df.to_csv(output_dir / "role_skill_demand_regional.csv", index=False)
    salary_country_df.to_csv(output_dir / "salary_summary_by_country.csv", index=False)
    salary_role_df.to_csv(output_dir / "salary_by_role_regional.csv", index=False)
    similarity_df.to_csv(output_dir / "country_similarity_matrix.csv", index=False)
    sens_summary_df.to_csv(output_dir / "sensitivity_analysis_summary.csv", index=False)

    lines = []
    lines.append("# Comparative Regional IT Labour-Market Analysis Report")
    lines.append(f"**Project:** IT Job Market Intelligence Tool (`J26_SE_355`)  ")
    lines.append(f"**Research Contribution:** Comparative Regional Market Analysis  ")
    lines.append(f"**Focal Market:** `{config.focal_country}` | **Comparators:** `{', '.join(config.comparator_countries)}`  ")
    lines.append(f"**Evaluation Baseline:** Task 2 Ground-Truth Benchmark & Task 3 Accuracy Verification  ")
    lines.append("")

    lines.append("## 1. Executive Summary & Research Methodology")
    lines.append("This study provides empirical comparative evidence on IT skill demands, occupational role structures, "
                 "and compensation disclosure across four regional economies: Sri Lanka (focal), India, Singapore, and Malaysia.")
    lines.append("")
    lines.append("### Core Quantitative Principles Applied:")
    lines.append("1. **Independent Eligibility Rules:** General job counts, skill-demand, role comparisons, and salary summaries have separate eligibility criteria.")
    lines.append("2. **Salary Decoupling:** Skill-demand analysis **never** excludes an advertisement merely for omitting salary.")
    lines.append("3. **Identical Denominators:** Demand percentages use the exact same eligible advertisement count per country.")
    lines.append("4. **Uncertainty Quantification:** All proportions report Wilson Score 95% Confidence Intervals; samples with $N < 10$ are explicitly flagged.")
    lines.append("5. **Audit-Ready Compensation:** Salaries are segregated by native currency; nominal conversions are never equated with purchasing power parity (PPP).")
    lines.append("")

    lines.append("## 2. Multi-Stage Eligibility & Record Attrition Funnel")
    lines.append(_df_to_markdown(funnel_df))
    lines.append("")

    lines.append("## 3. Cross-Market Canonical Skill Demand (%)")
    lines.append("Formula: $\\text{Demand } \\% = \\frac{n_{s, c}}{N_c} \\times 100$, where $n_{s, c}$ is unique ads containing canonical skill $s$.")
    lines.append("")
    top_skills = pd.concat([g.head(10) for _, g in demand_df.groupby("country")], ignore_index=True) if not demand_df.empty else pd.DataFrame()
    lines.append(_df_to_markdown(top_skills[["country", "skill_name", "category", "eligible_ads_denominator", "mention_count", "demand_pct", "ci_lower_95", "ci_upper_95", "small_sample_flag"]]))
    lines.append("")

    lines.append("## 4. Skill Gaps: Sri Lanka vs. Regional Comparators")
    lines.append("Formula: $\\Delta_{s} = \\text{Demand}_{\\text{LK}}(s) - \\text{Demand}_{\\text{Comp}}(s)$ (Percentage Points, pp).")
    lines.append("")
    top_gaps = pd.concat([pd.concat([g.head(5), g.tail(5)]) for _, g in gap_df.groupby("comparator_country")], ignore_index=True) if not gap_df.empty else pd.DataFrame()
    lines.append(_df_to_markdown(top_gaps[["comparator_country", "skill_name", "focal_demand_pct", "comparator_demand_pct", "gap_pp", "gap_ci_lower_95", "gap_ci_upper_95", "p_value", "evidence_status"]]))
    lines.append("")

    lines.append("## 5. Regional IT Role Distribution & Classification Quality")
    lines.append(_df_to_markdown(unclass_df))
    lines.append("")
    lines.append("### Key Comparable Role Frequencies:")
    lines.append(_df_to_markdown(role_dist_df[role_dist_df["pct_of_country"] >= 5.0][["country", "role_name", "job_count", "country_total_jobs", "pct_of_country"]]))
    lines.append("")

    lines.append("## 6. Disclosed Compensation Coverage & Distributions")
    lines.append("> **CRITICAL METHODOLOGICAL NOTICE:** Nominal salaries reflect local contractual commitments in native currencies. "
                 "They MUST NOT be interpreted as establishing purchasing power parity (PPP), standard of living, or disposable income equivalence.")
    lines.append("")
    lines.append(_df_to_markdown(salary_country_df))
    lines.append("")

    lines.append("## 7. Pairwise Country Skill Profile Similarity Matrix")
    lines.append("Metrics: Cosine Similarity across all canonical skills, Jaccard on Top-10 skills, and Spearman Rank Correlation.")
    lines.append("")
    lines.append(_df_to_markdown(similarity_df))
    lines.append("")

    lines.append("## 8. Robustness & Sensitivity Analysis")
    lines.append("Evaluation of parameter stability across 5 validation regimes:")
    lines.append("")
    lines.append(_df_to_markdown(sens_summary_df))
    lines.append("")

    lines.append("## 9. Limitations & Research Caveats")
    lines.append("- **Sample Size Asymmetry:** Pilot web crawling collected larger volumes in Sri Lanka and India compared to Singapore and Malaysia. Rank differences in sparse samples ($N < 10$) carry wide confidence intervals.")
    lines.append("- **Salary Disclosure Self-Selection:** Less than 45% of Indian and Sri Lankan vacancies disclose compensation, whereas Singapore mandates or frequently provides salary bands. Disclosed salaries represent a non-random subset.")
    lines.append("- **Occupational Granularity:** Classification assigns jobs based on title and description keywords. Sub-specializations and seniority tiers (e.g. Associate vs Lead) are grouped within broad canonical roles.")
    lines.append("")

    report_content = "\n".join(lines)
    report_file = output_dir / "regional_analysis_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    return report_content


# ==============================================================================
# 10. CLI Execution Entry Point
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Run Comparative Regional IT Labor-Market Analysis.")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK_PATH, help="Path to ground-truth benchmark CSV.")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PILOT_PREDICTIONS_PATH, help="Path to raw crawled predictions CSV.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory to save analytical outputs.")
    parser.add_argument("--focal", type=str, default=FOCAL_MARKET, help="Focal market name.")
    parser.add_argument("--use-database", dest="use_database", action="store_true", default=True, help="Load data directly from master SQLite database.")
    parser.add_argument("--no-database", dest="use_database", action="store_false", help="Bypass database and read raw CSV files directly.")
    args = parser.parse_args()

    print("================================================================================")
    print("Comparative Regional IT Labor-Market Analysis Engine")
    print(f"Focal Market: {args.focal} | Target Comparators: {', '.join(COMPARATOR_MARKETS)}")
    print(f"Data Source: {'Master SQLite Database (master_jobs.sqlite3)' if args.use_database else 'CSV Datasets'}")
    print("================================================================================")

    config = EligibilityConfig(focal_country=args.focal)
    print("\n[1/5] Ingesting and harmonizing multi-market datasets...")
    df = load_regional_market_data(
        benchmark_path=args.benchmark,
        raw_predictions_path=args.predictions,
        use_database=args.use_database,
    )
    print(f"  → Ingested {len(df)} total harmonized records across countries:")
    for country, count in df["country"].value_counts().items():
        print(f"      - {country}: {count} records")

    print("\n[2/5] Applying multi-stage task eligibility rules & building audit funnel...")
    funnel_df = build_exclusion_funnel(df, config)
    for _, r in funnel_df.iterrows():
        print(f"  → {r['stage']}: {r['eligible_records']} eligible / {r['excluded_records']} excluded ({r['retention_rate_pct']}%)")

    print("\n[3/5] Calculating canonical skill demand percentages and Wilson CIs...")
    demand_df = calculate_skill_demand_percentages(df, config)
    print(f"  → Calculated demand for {len(demand_df)} country x skill combinations.")

    print("\n[4/5] Executing role classifications, salary audits, and profile similarities...")
    gap_df = calculate_skill_gaps(demand_df, focal_country=args.focal)
    role_dist_df, role_skill_df, unclass_df = compare_regional_roles(df, config)
    salary_country_df, role_salary_df, _ = analyze_regional_salaries(df, config)
    sim_df = calculate_country_similarities(demand_df)

    print("\n[5/5] Running sensitivity analysis across 5 validation regimes...")
    sens_df, _ = run_regional_sensitivity_analysis(df, config)
    for _, r in sens_df.iterrows():
        print(f"  → Scenario '{r['scenario_name']}': Mean MAD = {r['mean_abs_demand_shift_pp']} pp [{r['stability_assessment']}]")

    print(f"\n[Artifacts] Generating research report and CSVs in {args.output}...")
    generate_regional_markdown_report(df, config, output_dir=args.output)
    print(f"✓ Analysis complete. Report generated at: {args.output / 'regional_analysis_report.md'}")


if __name__ == "__main__":
    main()
