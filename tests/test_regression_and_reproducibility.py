"""
Comprehensive Regression and Reproducibility Test Suite for Tasks 1–6.
Project: IT Job Market Intelligence Tool (J26_SE_355).

Covers:
1. Schema & Normalization Regression (salaries, locations, work modes, currencies, legacy files).
2. Web Scraping Adapters & Security Regression (JSON-LD, Shine, MCF, TimesJobs, SSRF validation, deduplication).
3. Evaluation Engine & Reproducibility Manifest (metrics, MAE, stratified results, SHA-256 hashes, deterministic output).
4. Regional Analytics & Sensitivity Regression (denominators, deduplicated skills, z-tests, salary decoupling, 5 scenarios).
5. Dashboard & Human-in-the-Loop Workflow Regression (empty states, populated states, annotation persistence).
6. Local End-to-End Pipeline Smoke Test (offline, self-contained, no network access).
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import pathlib
import tempfile
import unittest
from typing import Any, Dict, List
from unittest.mock import patch

import numpy as np
import pandas as pd

# Core modules across Tasks 1–6
from src.cleaning.salary_normalizer import (
    CURRENCY_MAP,
    SUPPORTED_CURRENCIES,
    VALID_SALARY_PERIODS,
    VALID_SALARY_TYPES,
    detect_currency,
    detect_period,
    parse_and_normalize_salary,
)
from src.cleaning.location_normalizer import (
    WORK_MODES,
    normalize_country,
    parse_and_normalize_location,
)
from src.cleaning.clean_jobs import (
    clean_raw_dataframe,
    migrate_legacy_dataframe,
    standardize_location,
)
from src.cleaning.validate_jobs import run_validation_pipeline
from src.security.url_validator import validate_url, validate_redirect_url, is_approved_domain
from src.scraping.models import RAW_SCHEMA_COLUMNS, TEAM_SCHEMA_COLUMNS, ExtractionResult, generate_job_id
from src.scraping.source_registry import get_source_registry
from src.scraping.extractors.shine import ShineExtractor
from src.scraping.extractors.timesjobs import TimesJobsExtractor
from src.scraping.extractors.mycareersfuture import MyCareersFutureExtractor
from src.scraping.extractors.jsonld import JsonLdExtractor
from src.scraping.extractors.generic_html import GenericHtmlExtractor
from src.roles.taxonomy import load_role_taxonomy
from src.roles.classifier import RoleClassifier, UNCLASSIFIED_ROLE_ID
from src.extraction.taxonomy import load_taxonomy
from src.extraction.lexical import LexicalSkillExtractor
from src.evaluation.schema import BenchmarkRecord, validate_benchmark_records, load_benchmark_dataset
from src.evaluation.comparator import compare_records, compare_single_record, RecordEvaluationResult, FieldEvaluationResult
from src.evaluation.metrics import (
    compute_evaluation_metrics,
    wilson_score_interval,
    GlobalEvaluationMetrics,
    FieldMetricSummary,
    StratifiedMetricGroup,
    MultiLabelSkillMetrics,
)
from src.evaluation.reporter import export_reproducibility_record, generate_markdown_report
from src.evaluation.dashboard_data import (
    discover_evaluation_runs,
    load_review_annotations,
    save_review_annotation,
    get_correction_history,
)
from src.analytics.regional_analysis import (
    EligibilityConfig,
    _compute_monthly_equivalents,
    _df_to_markdown,
    analyze_regional_salaries,
    build_exclusion_funnel,
    calculate_country_similarities,
    calculate_skill_demand_percentages,
    calculate_skill_gaps,
    calculate_wilson_ci,
    compare_regional_roles,
    filter_records_with_provenance,
    normalize_country_name,
    run_regional_sensitivity_analysis,
)

FIXTURES_DIR = pathlib.Path(__file__).resolve().parent / "fixtures"


def read_fixture(filename: str) -> str:
    path = FIXTURES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Fixture missing: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ==============================================================================
# 1. Schema & Normalization Regression Suite (Task 1)
# ==============================================================================

class TestSchemaAndNormalizationRegression(unittest.TestCase):
    """Deep regression tests for salary, location, work mode, and legacy migrations."""

    def test_salary_type_and_boundary_conditions(self):
        """Test fixed, range, starting_from, up_to, and reversed salary bounds."""
        # 1. Fixed
        res_fixed = parse_and_normalize_salary("LKR 200,000 per month", country_context="LK")
        self.assertTrue(res_fixed["salary_disclosed"])
        self.assertEqual(res_fixed["salary_type"], "fixed")
        self.assertEqual(res_fixed["salary_min_normalized"], 200000.0)
        self.assertEqual(res_fixed["salary_max_normalized"], 200000.0)
        self.assertEqual(res_fixed["salary_currency_normalized"], "LKR")

        # 2. Starting from
        res_start = parse_and_normalize_salary("Starting from $6,000 monthly", country_context="SG")
        self.assertTrue(res_start["salary_disclosed"])
        self.assertEqual(res_start["salary_type"], "starting_from")
        self.assertEqual(res_start["salary_min_normalized"], 6000.0)
        self.assertIsNone(res_start["salary_max_normalized"])
        self.assertEqual(res_start["salary_currency_normalized"], "SGD")

        # 3. Up to
        res_upto = parse_and_normalize_salary("Up to 18 LPA", country_context="IN")
        self.assertTrue(res_upto["salary_disclosed"])
        self.assertEqual(res_upto["salary_type"], "up_to")
        self.assertIsNone(res_upto["salary_min_normalized"])
        self.assertEqual(res_upto["salary_max_normalized"], 1800000.0)
        self.assertEqual(res_upto["salary_currency_normalized"], "INR")

        # 4. Standard Range
        res_range = parse_and_normalize_salary("5,000 - 8,000 SGD per month", country_context="SG")
        self.assertTrue(res_range["salary_disclosed"])
        self.assertEqual(res_range["salary_type"], "range")
        self.assertEqual(res_range["salary_min_normalized"], 5000.0)
        self.assertEqual(res_range["salary_max_normalized"], 8000.0)

        # 5. Reversed range (e.g. 8000 - 5000 SGD) -> marked ambiguous/unparseable
        res_rev = parse_and_normalize_salary("8000 - 5000 SGD", country_context="SG")
        self.assertTrue(res_rev["salary_disclosed"])
        self.assertEqual(res_rev["salary_type"], "unparseable")
        self.assertEqual(res_rev["salary_normalization_status"], "ambiguous")

        # 6. Negative values -> marked ambiguous
        res_neg = parse_and_normalize_salary(salary_min_raw="-5000", salary_max_raw="-2000", salary_currency_raw="USD")
        self.assertEqual(res_neg["salary_normalization_status"], "ambiguous")

        # 7. Zero salary -> disclosed is True, but bounds are 0.0
        res_zero = parse_and_normalize_salary("0 LKR per month")
        self.assertTrue(res_zero["salary_disclosed"])
        self.assertEqual(res_zero["salary_min_normalized"], 0.0)
        self.assertEqual(res_zero["salary_max_normalized"], 0.0)

        # 8. Undisclosed salary expressions
        for text in ["Competitive salary", "Negotiable", "Not disclosed", "Best in industry"]:
            res_und = parse_and_normalize_salary(text)
            self.assertFalse(res_und["salary_disclosed"])
            self.assertEqual(res_und["salary_type"], "undisclosed")

    def test_currency_disambiguation_with_and_without_context(self):
        """Test currency token resolution and contextual disambiguation."""
        # Generic '$' without country context -> remains '$' (partial status)
        c_none, _ = detect_currency("Salary is $5000 per month")
        self.assertEqual(c_none, "$")
        res_none = parse_and_normalize_salary("$5,000 - $8,000 per month")
        self.assertEqual(res_none["salary_normalization_status"], "partial")

        # Generic '$' with Singapore context -> resolved to SGD
        c_sg, _ = detect_currency("Salary is $5000 per month", country_context="Singapore")
        self.assertEqual(c_sg, "SGD")
        res_sg = parse_and_normalize_salary("$5,000 - $8,000 per month", country_context="Singapore")
        self.assertEqual(res_sg["salary_currency_normalized"], "SGD")
        self.assertEqual(res_sg["salary_normalization_status"], "normalized")

        # Generic 'Rs' with Sri Lanka context -> LKR
        c_lk, _ = detect_currency("Rs. 150,000 monthly", country_context="Sri Lanka")
        self.assertEqual(c_lk, "LKR")

        # Generic 'Rs' with India context -> INR
        c_in, _ = detect_currency("Rs. 50,000 pm", country_context="India")
        self.assertEqual(c_in, "INR")

        # Indian tech LPA (Lakhs Per Annum)
        res_lpa = parse_and_normalize_salary("12 - 15 LPA", country_context="IN")
        self.assertEqual(res_lpa["salary_currency_normalized"], "INR")
        self.assertEqual(res_lpa["salary_period_normalized"], "annual")
        self.assertEqual(res_lpa["salary_min_normalized"], 1200000.0)
        self.assertEqual(res_lpa["salary_max_normalized"], 1500000.0)

        # Malaysian Ringgit (RM / MYR)
        res_myr = parse_and_normalize_salary("RM 7,000 - 10,000 per month", country_context="Malaysia")
        self.assertEqual(res_myr["salary_currency_normalized"], "MYR")
        self.assertEqual(res_myr["salary_period_normalized"], "monthly")
        self.assertEqual(res_myr["salary_min_normalized"], 7000.0)

    def test_pay_period_standardization_and_conversions(self):
        """Test detection and monthly equivalent standardization across all pay periods."""
        # Hourly -> monthly (160 hrs)
        min_m, max_m, mid_m = _compute_monthly_equivalents(50.0, 75.0, "hourly", hours_per_month=160.0)
        self.assertEqual(min_m, 8000.0)
        self.assertEqual(max_m, 12000.0)
        self.assertEqual(mid_m, 10000.0)

        # Daily -> monthly (20 days)
        min_m, max_m, mid_m = _compute_monthly_equivalents(400.0, 600.0, "daily")
        self.assertEqual(min_m, 8000.0)
        self.assertEqual(max_m, 12000.0)
        self.assertEqual(mid_m, 10000.0)

        # Annual -> monthly (12 months)
        min_m, max_m, mid_m = _compute_monthly_equivalents(120000.0, 180000.0, "annual")
        self.assertEqual(min_m, 10000.0)
        self.assertEqual(max_m, 15000.0)
        self.assertEqual(mid_m, 12500.0)

        # Unspecified period -> cannot convert safely
        min_m, max_m, mid_m = _compute_monthly_equivalents(5000.0, 8000.0, "unspecified")
        self.assertIsNone(min_m)
        self.assertIsNone(mid_m)

    def test_rounding_and_normalization_consistency(self):
        """Test deterministic floating point rounding for monthly midpoints."""
        min_m, max_m, mid_m = _compute_monthly_equivalents(100000.0, 150000.0, "annual")
        self.assertEqual(round(min_m, 2), 8333.33)
        self.assertEqual(round(max_m, 2), 12500.0)
        self.assertEqual(round(mid_m, 2), 10416.67)

    def test_location_and_work_mode_disaggregation(self):
        """Test location normalization, remote/hybrid/on-site disaggregation, and missing location safety."""
        # Missing location with known country: city is empty, work mode is unspecified (NOT remote)
        loc_empty = parse_and_normalize_location("", "Sri Lanka", "Senior Software Engineer", "Java developer")
        self.assertEqual(loc_empty["city_normalized"], "")
        self.assertEqual(loc_empty["work_mode"], "unspecified")
        self.assertEqual(loc_empty["location_normalization_status"], "partial")

        # Both missing
        loc_none = parse_and_normalize_location("", "", "", "")
        self.assertEqual(loc_none["location_normalization_status"], "unspecified")

        # Explicit remote title/desc
        loc_remote = parse_and_normalize_location("Colombo", "Sri Lanka", "Remote Python Developer", "Work from home")
        self.assertEqual(loc_remote["city_normalized"], "Colombo")
        self.assertEqual(loc_remote["work_mode"], "remote")

        # Hybrid
        loc_hybrid = parse_and_normalize_location("Bengaluru", "India", "Full Stack Engineer", "Hybrid role (2 days office)")
        self.assertEqual(loc_hybrid["city_normalized"], "Bengaluru")
        self.assertEqual(loc_hybrid["work_mode"], "hybrid")

        # On-site
        loc_onsite = parse_and_normalize_location("Singapore", "Singapore", "DevOps Engineer", "100% on-site at client premises")
        self.assertEqual(loc_onsite["work_mode"], "on_site")

        # Multiple locations
        loc_multi = parse_and_normalize_location("Bengaluru / Hyderabad / Pune", "India", "Tech Lead", "Office location options")
        self.assertIn("Bengaluru", loc_multi["city_normalized"])

        # Country normalization without false assumptions
        self.assertEqual(normalize_country("LK"), "Sri Lanka")
        self.assertEqual(normalize_country("lk"), "Sri Lanka")
        self.assertEqual(normalize_country("in"), "India")
        self.assertEqual(normalize_country("sgp"), "Singapore")
        self.assertEqual(normalize_country("mys"), "Malaysia")
        self.assertEqual(normalize_country("Unknown Realm"), "Unknown Realm")
        # Regional analysis country normalization handles SL alias and maps unmapped to Unknown
        self.assertEqual(normalize_country_name("SL"), "Sri Lanka")
        self.assertEqual(normalize_country_name("Unknown Realm"), "Unknown")

    def test_legacy_dataset_migration_and_backfilling(self):
        """Test backward compatibility of legacy dataframes without new Task 1 schema columns."""
        legacy_df = pd.DataFrame([
            {
                "job_id": "leg_1",
                "job_title_raw": "PHP Developer",
                "company": "Legacy Corp",
                "location": "Colombo",
                "country": "Sri Lanka",
                "job_description": "We need a skilled PHP and MySQL developer.",
            }
        ])

        migrated = migrate_legacy_dataframe(legacy_df)
        self.assertIn("salary_disclosed", migrated.columns)
        self.assertIn("salary_type", migrated.columns)
        self.assertIn("salary_min_normalized", migrated.columns)
        self.assertIn("work_mode", migrated.columns)
        self.assertIn("country_normalized", migrated.columns)
        self.assertIn("city_normalized", migrated.columns)

        self.assertFalse(bool(migrated.iloc[0]["salary_disclosed"]))
        self.assertEqual(migrated.iloc[0]["salary_type"], "undisclosed")
        self.assertEqual(migrated.iloc[0]["country_normalized"], "Sri Lanka")
        self.assertEqual(migrated.iloc[0]["city_normalized"], "Colombo")

    def test_missing_and_additional_columns_and_data_types(self):
        """Test schema migration with unexpected extra columns and missing optional fields."""
        custom_df = pd.DataFrame([
            {
                "job_id": "cust_1",
                "job_title_raw": "Cloud Architect",
                "company": "Global Solutions",
                "location": "Singapore",
                "country": "Singapore",
                "job_description": "Terraform and AWS expert.",
                "unexpected_research_metric": 42,
                "legacy_scraping_tag": "tagA",
            }
        ])

        migrated = migrate_legacy_dataframe(custom_df)
        self.assertIn("unexpected_research_metric", migrated.columns)
        self.assertIn("salary_disclosed", migrated.columns)
        self.assertIsInstance(migrated.iloc[0]["salary_disclosed"], (bool, np.bool_))

    def test_stable_job_identifiers_and_hash_consistency(self):
        """Verify generate_job_id creates stable, reproducible IDs across runs."""
        id1 = generate_job_id("shine.com", "12345", "https://shine.com/jobs/12345")
        id2 = generate_job_id("shine.com", "12345", "https://shine.com/jobs/12345")
        self.assertEqual(id1, id2)
        self.assertEqual(id1, "shine.com_12345")

        id_hash1 = generate_job_id("mycareersfuture.gov.sg", "", "https://mycareersfuture.gov.sg/job/100")
        id_hash2 = generate_job_id("mycareersfuture.gov.sg", None, "https://mycareersfuture.gov.sg/job/100")
        self.assertEqual(id_hash1, id_hash2)
        self.assertTrue(id_hash1.startswith("mycareersfuture.gov.sg_hash_"))

    def test_preservation_of_raw_source_data(self):
        """Verify raw fields are untouched and preserved during cleaning."""
        raw_df = pd.DataFrame([{
            "job_id": "raw_test_1",
            "source_job_id": "SJ-01",
            "job_title_raw": "Lead Java Developer",
            "company_raw": "Acme Corp Ltd.",
            "country_raw": "LK",
            "location_raw": "Colombo 03",
            "job_description_raw": "Core Java developer required.",
            "requirements_raw": "Java 17+",
            "posted_date_raw": "2026-09-01",
            "closing_date_raw": "2026-10-01",
            "salary_text_raw": "250,000 LKR",
            "salary_currency_raw": "LKR",
            "salary_min_raw": "250000",
            "salary_max_raw": "250000",
            "salary_period_raw": "monthly",
            "source_hostname": "topjobs.lk",
            "source_platform": "www.topjobs.lk",
            "source_url": "https://topjobs.lk/jobs/01",
            "extraction_status": "success",
        }])

        internal_df, team_df, stats = clean_raw_dataframe(raw_df)
        self.assertEqual(internal_df.iloc[0]["job_title_raw"], "Lead Java Developer")
        self.assertEqual(internal_df.iloc[0]["company_raw"], "Acme Corp Ltd.")
        self.assertEqual(internal_df.iloc[0]["salary_text_raw"], "250,000 LKR")


# ==============================================================================
# 2. Web Scraping Adapters & Security Regression Suite (Task 2 & 5)
# ==============================================================================

class TestScrapingAdaptersAndSecurityRegression(unittest.TestCase):
    """Regression tests for source adapters on saved offline HTML fixtures and security checks."""

    def test_security_url_validator_ssrf_prevention(self):
        """Verify URL validation prevents SSRF, private IPs, non-http schemes, and unapproved domains."""
        blocked_urls = [
            "http://localhost:8080/admin",
            "http://127.0.0.1/secret",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1/private",
            "http://192.168.1.1/router",
            "file:///etc/passwd",
            "ftp://files.example.com",
            "javascript:alert(1)",
        ]
        for url in blocked_urls:
            is_valid, reason = validate_url(url)
            self.assertFalse(is_valid, f"Should block SSRF URL: {url} (reason: {reason})")

        # Valid approved domain
        valid_shine, _ = validate_url("https://www.shine.com/jobs/dev/123")
        self.assertTrue(valid_shine)

    def test_url_redirect_validation_and_failures(self):
        """Verify redirect validation rejects transitions to internal or invalid schemes."""
        valid_orig = "https://www.shine.com/jobs/123"
        safe_redirect = "https://www.shine.com/jobs/123-applied"
        unsafe_redirect = "http://127.0.0.1:9000/admin"

        ok_safe, _ = validate_redirect_url(valid_orig, safe_redirect)
        self.assertTrue(ok_safe)

        ok_unsafe, reason = validate_redirect_url(valid_orig, unsafe_redirect)
        self.assertFalse(ok_unsafe)
        self.assertIn("rejected", reason.lower())

    def test_jsonld_structured_jobposting_extractor(self):
        """Verify JSON-LD extraction extracts Title, Org, Salary, Location, and WorkMode."""
        html_content = read_fixture("shine_detail_bengaluru.html")
        url = "https://www.shine.com/jobs/19582041"
        extractor = JsonLdExtractor()
        res = ExtractionResult.create_for_url(url, "batch_test")
        res = extractor.extract(url, html_content, res)

        self.assertEqual(res.extraction_status, "success")
        self.assertEqual(res.job_title_raw, "Senior Python Backend Developer")
        self.assertEqual(res.company_raw, "Infosys Limited")
        self.assertIn("Bengaluru", res.location_raw)
        self.assertEqual(res.salary_currency_raw, "INR")
        self.assertEqual(res.salary_min_raw, "1500000")
        self.assertEqual(res.salary_max_raw, "2500000")

    def test_shine_adapter_on_offline_fixtures(self):
        """Test dedicated Shine adapter on normal, missing-fields, and remote fixtures."""
        adapter = ShineExtractor()

        # 1. Normal Bengaluru posting
        html_normal = read_fixture("shine_detail_bengaluru.html")
        url_normal = "https://www.shine.com/jobs/19582041"
        res_normal = ExtractionResult.create_for_url(url_normal, "batch_test")
        res_normal = adapter.extract(url_normal, html_normal, res_normal)
        self.assertEqual(res_normal.extraction_status, "success")
        self.assertEqual(res_normal.job_title_raw, "Senior Python Backend Developer")
        self.assertEqual(res_normal.company_raw, "Infosys Limited")

        # 2. Missing fields fixture
        html_missing = read_fixture("shine_detail_missing_fields.html")
        url_missing = "https://www.shine.com/jobs/99999999"
        res_missing = ExtractionResult.create_for_url(url_missing, "batch_test")
        res_missing = adapter.extract(url_missing, html_missing, res_missing)
        self.assertEqual(res_missing.job_title_raw, "Frontend React Developer")
        self.assertIn(res_missing.extraction_status, ("partial", "success"))

        # 3. Remote / International fixture
        html_remote = read_fixture("shine_detail_remote_international.html")
        url_remote = "https://www.shine.com/jobs/88888888"
        res_remote = ExtractionResult.create_for_url(url_remote, "batch_test")
        res_remote = adapter.extract(url_remote, html_remote, res_remote)
        self.assertEqual(res_remote.work_mode_raw, "remote")

    def test_mycareersfuture_adapter_on_offline_fixture(self):
        """Test MyCareersFuture (Singapore) adapter on saved HTML fixture."""
        adapter = MyCareersFutureExtractor()
        html_mcf = read_fixture("mycareersfuture_detail.html")
        url_mcf = "https://www.mycareersfuture.gov.sg/job/tech/cyber-sec-12345"
        res = ExtractionResult.create_for_url(url_mcf, "batch_test")
        res = adapter.extract(url_mcf, html_mcf, res)

        self.assertEqual(res.extraction_status, "success")
        self.assertEqual(res.job_title_raw, "Senior Cyber Security Specialist")
        self.assertEqual(res.company_raw, "Government Technology Agency (GovTech)")
        self.assertEqual(res.location_raw, "Central, Singapore")
        self.assertEqual(res.country_raw, "SG")

    def test_timesjobs_adapter_on_offline_fixture(self):
        """Test TimesJobs adapter on saved HTML fixture."""
        adapter = TimesJobsExtractor()
        html_tj = read_fixture("timesjobs_detail.html")
        url_tj = "https://www.timesjobs.com/job-detail/lead-full-stack-98765"
        res = ExtractionResult.create_for_url(url_tj, "batch_test")
        res = adapter.extract(url_tj, html_tj, res)

        self.assertEqual(res.extraction_status, "success")
        self.assertEqual(res.job_title_raw, "Lead Full Stack Engineer")
        self.assertEqual(res.company_raw, "Tata Consultancy Services")
        self.assertIn("Hyderabad", res.location_raw)

    def test_generic_html_extractor_fallback(self):
        """Test generic HTML fallback on HTML with title and description."""
        html = """
        <html>
        <head>
            <title>Senior DevOps Engineer at CloudTech - Careers</title>
            <meta name="description" content="CloudTech is hiring a Senior DevOps Engineer.">
        </head>
        <body>
            <h1>Senior DevOps Engineer</h1>
            <p>Join us to build high-scale cloud platforms using Kubernetes and AWS.</p>
        </body>
        </html>
        """
        url = "https://generic-company.com/jobs/devops-123"
        extractor = GenericHtmlExtractor()
        res = ExtractionResult.create_for_url(url, "batch_test")
        res = extractor.extract(url, html, res)
        self.assertIn(res.extraction_status, ("success", "partial"))
        self.assertIn("DevOps Engineer", res.job_title_raw)

    def test_partial_extraction_and_missing_fields(self):
        """Test extraction behavior when mandatory fields like title are absent."""
        html_empty = "<html><body><div>Just a random blog post</div></body></html>"
        url = "https://generic-company.com/not-a-job"
        extractor = GenericHtmlExtractor()
        res = ExtractionResult.create_for_url(url, "batch_test")
        res = extractor.extract(url, html_empty, res)
        self.assertEqual(res.extraction_status, "unsupported")

    def test_deduplication_pipeline(self):
        """Verify 3-step deduplication catches exact URLs, syndicated copies, and content fingerprints."""
        raw_df = pd.DataFrame([
            {
                "job_id": "j1",
                "source_job_id": "1",
                "job_title_raw": "DevOps Engineer",
                "company_raw": "CloudCorp",
                "country_raw": "Sri Lanka",
                "location_raw": "Colombo",
                "job_description_raw": "<p>DevOps Kubernetes Docker AWS CI/CD pipeline automation engineer needed.</p>",
                "requirements_raw": "DevOps",
                "posted_date_raw": "2026-09-01",
                "closing_date_raw": "2026-10-01",
                "source_hostname": "itpro.lk",
                "source_url": "https://itpro.lk/jobs/1",
                "extraction_status": "success",
            },
            # Exact duplicate URL
            {
                "job_id": "j2",
                "source_job_id": "1",
                "job_title_raw": "DevOps Engineer",
                "company_raw": "CloudCorp",
                "country_raw": "Sri Lanka",
                "location_raw": "Colombo",
                "job_description_raw": "<p>DevOps Kubernetes Docker AWS CI/CD pipeline automation engineer needed.</p>",
                "requirements_raw": "DevOps",
                "posted_date_raw": "2026-09-01",
                "closing_date_raw": "2026-10-01",
                "source_hostname": "itpro.lk",
                "source_url": "https://itpro.lk/jobs/1",
                "extraction_status": "success",
            },
            # Syndicated posting (different URL, identical title, company, date)
            {
                "job_id": "j3",
                "source_job_id": "3",
                "job_title_raw": "DevOps Engineer",
                "company_raw": "CloudCorp",
                "country_raw": "Sri Lanka",
                "location_raw": "Colombo",
                "job_description_raw": "<p>DevOps Kubernetes Docker AWS CI/CD pipeline automation engineer needed.</p>",
                "requirements_raw": "DevOps",
                "posted_date_raw": "2026-09-01",
                "closing_date_raw": "2026-10-01",
                "source_hostname": "topjobs.lk",
                "source_url": "https://topjobs.lk/jobs/99",
                "extraction_status": "success",
            },
        ])

        internal_df, team_df, stats = clean_raw_dataframe(raw_df)
        self.assertEqual(len(internal_df), 1)
        self.assertEqual(stats["total_raw_records"], 3)
        self.assertEqual(stats["final_internal_records"], 1)


# ==============================================================================
# 3. Benchmark Evaluation & Reproducibility Suite (Task 3 & 4)
# ==============================================================================

class TestBenchmarkEvaluationAndReproducibilityRegression(unittest.TestCase):
    """Tests evaluation accuracy, numeric salary error, and the repeatable evaluation procedure."""

    def test_precision_recall_f1_and_error_categories(self):
        """Verify precision, recall, F1, exact match, and error categorization."""
        bm_records = [
            BenchmarkRecord(
                benchmark_id="BM-001",
                source_url="https://example.com/job1",
                source_platform="shine.com",
                country="India",
                collection_context="pilot",
                extraction_method="jsonld",
                expected_job_title_raw="Backend Python Developer",
                expected_company_raw="Infosys",
                expected_location_raw="Bengaluru",
                expected_country_normalized="India",
                expected_city_normalized="Bengaluru",
                expected_work_mode="hybrid",
                expected_posted_date="2026-09-10",
                expected_closing_date="2026-10-10",
                expected_description_snippet="Python developer with AWS and Docker experience.",
                expected_description_hash="hash1",
                expected_description_min_len=20,
                expected_salary_disclosed=True,
                expected_salary_text_raw="15 LPA",
                expected_salary_type="fixed",
                expected_salary_min=1500000.0,
                expected_salary_max=1500000.0,
                expected_salary_currency="INR",
                expected_salary_period="annual",
                expected_skills='["python", "aws"]',
                status_job_title="verified",
                status_company="verified",
                status_location="verified",
                status_work_mode="verified",
                status_posted_date="verified",
                status_closing_date="verified",
                status_description="verified",
                status_salary="verified",
                status_skills="verified",
                verification_timestamp="2026-09-10T00:00:00Z",
                verified_by="evaluator1",
                evidence_source="page_screenshot",
                reviewer_notes="",
            )
        ]

        pred_perfect = [
            {
                "source_url": "https://example.com/job1",
                "job_title_raw": "Backend Python Developer",
                "company_raw": "Infosys",
                "location_raw": "Bengaluru",
                "country_normalized": "India",
                "city_normalized": "Bengaluru",
                "work_mode": "hybrid",
                "posted_date": "2026-09-10",
                "closing_date": "2026-10-10",
                "job_description_raw": "Python developer with AWS and Docker experience in Bengaluru.",
                "salary_disclosed": True,
                "salary_min_normalized": 1500000.0,
                "salary_max_normalized": 1500000.0,
                "salary_currency_normalized": "INR",
                "salary_period_normalized": "annual",
                "skills": ["python", "aws"],
            }
        ]

        results, unmatched_bm, extra = compare_records(bm_records, pred_perfect, match_key="auto")
        metrics = compute_evaluation_metrics(results, len(bm_records), len(pred_perfect), len(unmatched_bm), len(extra))

        self.assertEqual(metrics.matched_records_count, 1)
        self.assertEqual(results[0].field_results["job_title"].status, "correct")
        self.assertEqual(results[0].field_results["company"].status, "correct")
        self.assertEqual(metrics.fully_correct_records, 1)
        self.assertEqual(metrics.exact_match_rate, 1.0)
        self.assertEqual(metrics.macro_precision, 1.0)
        self.assertEqual(metrics.macro_recall, 1.0)
        self.assertEqual(metrics.macro_f1, 1.0)

    def test_missing_reference_labels_and_unverified_exclusion(self):
        """Verify unverified or ambiguous benchmark labels are excluded from accuracy denominator."""
        bm_records = [
            BenchmarkRecord(
                benchmark_id="BM-002",
                source_url="https://example.com/job2",
                source_platform="shine.com",
                country="India",
                collection_context="pilot",
                extraction_method="jsonld",
                expected_job_title_raw="Software Engineer",
                status_job_title="verified",
                expected_company_raw="",
                status_company="unavailable",
                status_location="ambiguous",
                status_work_mode="not_reviewed",
                status_posted_date="not_reviewed",
                status_closing_date="not_reviewed",
                status_description="not_reviewed",
                status_salary="not_reviewed",
                status_skills="not_reviewed",
            )
        ]
        pred = [{
            "source_url": "https://example.com/job2",
            "job_title_raw": "Software Engineer",
            "company_raw": "Some Corp",
        }]

        results, unmatched_bm, extra = compare_records(bm_records, pred, match_key="auto")
        metrics = compute_evaluation_metrics(results, len(bm_records), len(pred), len(unmatched_bm), len(extra))

        self.assertEqual(metrics.field_metrics["job_title"].eligible_references, 1)
        self.assertEqual(metrics.field_metrics["job_title"].correct_values, 1)
        self.assertEqual(metrics.field_metrics["employer"].eligible_references, 0)
        self.assertEqual(metrics.field_metrics["employer"].unavailable_references, 1)

    def test_missing_and_extra_predictions(self):
        """Verify tracking of unmatched benchmark records and extra predictions."""
        bm_records = [
            BenchmarkRecord(
                benchmark_id="BM-003",
                source_url="https://example.com/expected_only",
                source_platform="shine.com",
                country="India",
                collection_context="pilot",
                extraction_method="jsonld",
                expected_job_title_raw="Architect",
                status_job_title="verified",
                status_company="not_reviewed",
                status_location="not_reviewed",
                status_work_mode="not_reviewed",
                status_posted_date="not_reviewed",
                status_closing_date="not_reviewed",
                status_description="not_reviewed",
                status_salary="not_reviewed",
                status_skills="not_reviewed",
            )
        ]
        pred = [
            {"source_url": "https://example.com/unmatched_pred_1", "job_title_raw": "Tester"},
            {"source_url": "https://example.com/unmatched_pred_2", "job_title_raw": "Analyst"},
        ]

        results, unmatched_bm, extra = compare_records(bm_records, pred, match_key="auto")
        metrics = compute_evaluation_metrics(results, len(bm_records), len(pred), len(unmatched_bm), len(extra))

        self.assertEqual(metrics.unmatched_benchmark_count, 1)
        self.assertEqual(metrics.extra_predictions_count, 2)
        self.assertEqual(len(unmatched_bm), 1)
        self.assertEqual(len(extra), 2)
        self.assertEqual(results[0].field_results["job_title"].status, "missing_prediction")

    def test_numeric_salary_metrics_and_error_distribution(self):
        """Verify MAE, Median AE, and currency incompatibility exclusions."""
        f_summary = FieldMetricSummary(field_name="salary_min", is_numeric=True)
        errors = [100.0, 200.0, 300.0, 400.0, 500.0]
        f_summary.compute_statistics(numeric_errors=errors)

        self.assertEqual(f_summary.comparable_count, 5)
        self.assertEqual(f_summary.mae, 300.0)
        self.assertEqual(f_summary.median_ae, 300.0)

    def test_empty_evaluation_subsets_and_stratification(self):
        """Verify groups with 0 or small record counts compute rates without ZeroDivisionError."""
        group = StratifiedMetricGroup(group_name="EmptyCountry", dimension="country", total_records=0)
        group.compute_rates()
        self.assertEqual(group.exact_match_rate, 0.0)
        self.assertTrue(group.is_small_sample)

    def test_deterministic_report_generation(self):
        """Verify generate_markdown_report produces deterministic output given identical metrics."""
        mock_metrics = GlobalEvaluationMetrics(
            timestamp="2026-09-25T09:13:02Z",
            total_benchmark_records=1,
            total_predictions_loaded=1,
            matched_records_count=1,
            unmatched_benchmark_count=0,
            extra_predictions_count=0,
            fully_correct_records=1,
            exact_match_rate=1.0,
            exact_match_ci_lower=0.20,
            exact_match_ci_upper=1.0,
            macro_coverage=1.0,
            macro_correctness=1.0,
            macro_precision=1.0,
            macro_recall=1.0,
            macro_f1=1.0,
        )

        md1 = generate_markdown_report(mock_metrics, [], "benchmark.csv", "predictions.csv", match_key="auto")
        md2 = generate_markdown_report(mock_metrics, [], "benchmark.csv", "predictions.csv", match_key="auto")
        self.assertEqual(md1, md2)
        self.assertIn("# Information Extraction Quality & Benchmark Evaluation Report", md1)

    def test_repeatable_evaluation_procedure_and_checksum_manifest(self):
        """Verify repeatable evaluation procedure records file hashes, versions, parameters, and commit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            bm_file = tmp_path / "synthetic_bm.csv"
            pred_file = tmp_path / "synthetic_pred.csv"
            repro_file = tmp_path / "reproducibility.json"

            pd.DataFrame([{"benchmark_id": "BM-1", "source_url": "http://example.com/1"}]).to_csv(bm_file, index=False)
            pd.DataFrame([{"source_url": "http://example.com/1", "job_title_raw": "Engineer"}]).to_csv(pred_file, index=False)

            mock_metrics = GlobalEvaluationMetrics(
                timestamp="2026-09-25T09:13:02Z",
                total_benchmark_records=1,
                total_predictions_loaded=1,
                matched_records_count=1,
                unmatched_benchmark_count=0,
                extra_predictions_count=0,
                fully_correct_records=1,
                exact_match_rate=1.0,
                exact_match_ci_lower=0.20,
                exact_match_ci_upper=1.0,
                macro_coverage=1.0,
                macro_correctness=1.0,
                macro_precision=1.0,
                macro_recall=1.0,
                macro_f1=1.0,
            )

            export_reproducibility_record(
                benchmark_path=bm_file,
                predictions_path=pred_file,
                output_dir=tmp_path,
                match_key="url",
                metrics=mock_metrics,
                output_file=repro_file,
            )

            self.assertTrue(repro_file.exists())
            with open(repro_file, "r") as f:
                repro_data = json.load(f)

            self.assertEqual(repro_data["benchmark_version"], "1.0.0")
            self.assertIn("code_version", repro_data)
            self.assertIn("model_versions", repro_data)
            self.assertIn("taxonomy_versions", repro_data)
            self.assertIn("normalization_parameters", repro_data)
            self.assertIn("input_artifacts", repro_data)
            self.assertIn("benchmark_dataset_sha256", repro_data["input_artifacts"])
            self.assertIn("predictions_sha256", repro_data["input_artifacts"])
            self.assertNotEqual(repro_data["input_artifacts"]["benchmark_dataset_sha256"], "not_found")


# ==============================================================================
# 4. Regional Analytics & Sensitivity Regression Suite (Task 5)
# ==============================================================================

class TestRegionalAnalyticsAndSensitivityRegression(unittest.TestCase):
    """Tests cross-country denominator consistency, skill deduplication, salary decoupling, and sensitivity."""

    def setUp(self):
        self.config = EligibilityConfig()
        self.df = pd.DataFrame([
            # Sri Lanka
            {"job_id": "l1", "country": "Sri Lanka", "job_title_raw": "Software Engineer", "job_description": "Software engineer with Python and Java.", "skills": ["python", "java"], "is_it": True, "classification_status": "it", "salary_disclosed": False, "salary_monthly_midpoint": None, "source_validation_status": "validated", "is_benchmark_verified": True, "role_id": "software_engineer", "role_name": "Software Engineer / Developer"},
            {"job_id": "l2", "country": "Sri Lanka", "job_title_raw": "DevOps Engineer", "job_description": "DevOps engineer with Python, Docker, AWS.", "skills": ["python", "docker", "aws"], "is_it": True, "classification_status": "it", "salary_disclosed": True, "salary_monthly_midpoint": 350000.0, "salary_currency_normalized": "LKR", "salary_period_normalized": "monthly", "salary_normalization_status": "normalized", "source_validation_status": "validated", "is_benchmark_verified": True, "role_id": "devops_engineer", "role_name": "DevOps Engineer"},
            # India
            {"job_id": "i1", "country": "India", "job_title_raw": "Python Architect", "job_description": "Cloud architect with Python and AWS.", "skills": ["python", "aws"], "is_it": True, "classification_status": "it", "salary_disclosed": True, "salary_monthly_midpoint": 200000.0, "salary_currency_normalized": "INR", "salary_period_normalized": "monthly", "salary_normalization_status": "normalized", "source_validation_status": "validated", "is_benchmark_verified": True, "role_id": "software_engineer", "role_name": "Software Engineer / Developer"},
            # Singapore
            {"job_id": "s1", "country": "Singapore", "job_title_raw": "Backend Lead", "job_description": "Backend lead with Python and Docker.", "skills": ["python", "docker"], "is_it": True, "classification_status": "it", "salary_disclosed": True, "salary_monthly_midpoint": 9000.0, "salary_currency_normalized": "SGD", "salary_period_normalized": "monthly", "salary_normalization_status": "normalized", "source_validation_status": "validated", "is_benchmark_verified": True, "role_id": "software_engineer", "role_name": "Software Engineer / Developer"},
            # Malaysia
            {"job_id": "m1", "country": "Malaysia", "job_title_raw": "Full Stack Dev", "job_description": "Full stack with JS and Python.", "skills": ["javascript", "python"], "is_it": True, "classification_status": "it", "salary_disclosed": True, "salary_monthly_midpoint": 7000.0, "salary_currency_normalized": "MYR", "salary_period_normalized": "monthly", "salary_normalization_status": "normalized", "source_validation_status": "validated", "is_benchmark_verified": True, "role_id": "software_engineer", "role_name": "Software Engineer / Developer"},
        ])

    def test_denominators_and_unique_skill_counting(self):
        """Verify denominators are independent per country and skills are deduplicated."""
        demands = calculate_skill_demand_percentages(self.df, self.config)
        self.assertFalse(demands.empty)

        # Sri Lanka has 2 eligible ads. Python appears in both -> 2/2 = 100%
        lk_py = demands[(demands["country"] == "Sri Lanka") & (demands["skill_id"] == "python")].iloc[0]
        self.assertEqual(int(lk_py["eligible_ads_denominator"]), 2)
        self.assertEqual(int(lk_py["mention_count"]), 2)
        self.assertEqual(float(lk_py["demand_pct"]), 100.0)

    def test_salary_decoupling_preserves_undisclosed_ads_for_skills(self):
        """Verify job l1 (undisclosed salary) participates in skill demand but is excluded from salary."""
        eligible_skill, _, _ = filter_records_with_provenance(self.df, self.config, task="skill")
        self.assertIn("l1", eligible_skill["job_id"].values)

        eligible_sal, _, _ = filter_records_with_provenance(self.df, self.config, task="salary")
        self.assertNotIn("l1", eligible_sal["job_id"].values)

    def test_unequal_country_sample_sizes_and_empty_groups(self):
        """Verify two-proportion z-tests and Wilson CIs handle unequal sample sizes gracefully."""
        ci_lo, ci_hi = calculate_wilson_ci(10, 100)
        self.assertGreater(ci_lo, 0.0)
        self.assertLess(ci_hi, 100.0)

        demands = calculate_skill_demand_percentages(self.df, self.config)
        gaps = calculate_skill_gaps(demands, focal_country="Sri Lanka")
        self.assertFalse(gaps.empty)
        self.assertIn("z_statistic", gaps.columns)
        self.assertIn("p_value", gaps.columns)

    def test_role_comparisons_and_cross_country_distribution(self):
        """Verify role comparisons distribution across countries."""
        role_counts, role_skill_demand, unclass_summary = compare_regional_roles(self.df, self.config)
        self.assertFalse(role_counts.empty)
        self.assertIn("role_id", role_counts.columns)
        self.assertIn("pct_of_country", role_counts.columns)

    def test_quality_based_record_exclusion_with_provenance(self):
        """Verify quality-based exclusions (non-IT, unvalidated source, unverified benchmark)."""
        df_unqual = self.df.copy()
        df_unqual.loc[0, "classification_status"] = "non_it"

        filtered, counts, audit = filter_records_with_provenance(df_unqual, self.config, task="general")
        self.assertNotIn("l1", filtered["job_id"].values)
        self.assertEqual(counts.get("classified_non_it", 0), 1)

    def test_sensitivity_analysis_five_regimes_determinism(self):
        """Verify sensitivity analysis computes baseline and all 4 comparative scenarios deterministically."""
        summary, details = run_regional_sensitivity_analysis(self.df, self.config)
        self.assertEqual(len(summary), 5)
        self.assertEqual(summary.iloc[0]["scenario_key"], "1_baseline")
        self.assertEqual(summary.iloc[0]["mean_abs_demand_shift_pp"], 0.0)


# ==============================================================================
# 5. Dashboard & Human-in-the-Loop Workflow Regression Suite (Task 6)
# ==============================================================================

class TestDashboardAndWorkflowRegression(unittest.TestCase):
    """Tests dashboard discovery states, empty states, and human review persistence."""

    def test_manual_review_persistence_and_audit_history(self):
        """Verify review annotation saving and round-trip retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            review_file = tmp_path / "review_annotations.json"
            history_file = tmp_path / "correction_history.jsonl"

            success, msg = save_review_annotation(
                benchmark_id="BM-LK-001",
                field_name="job_title",
                status="verified",
                reviewer_id="senior_evaluator",
                reviewer_notes="Title verified against primary portal evidence",
                corrected_value="Senior Software Engineer",
                storage_path=review_file,
                history_path=history_file,
            )
            self.assertTrue(success, msg)

            annotations = load_review_annotations(review_file)
            self.assertIn("BM-LK-001::job_title", annotations)
            saved = annotations["BM-LK-001::job_title"]
            self.assertEqual(saved["status"], "verified")
            self.assertEqual(saved["reviewer_id"], "senior_evaluator")

            history = get_correction_history(history_file)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["benchmark_id"], "BM-LK-001")

    def test_dashboard_empty_evaluation_state_handling(self):
        """Verify discover_evaluation_runs returns an empty list without error when results dir is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runs = discover_evaluation_runs(pathlib.Path(tmpdir))
            self.assertEqual(len(runs), 0)

    def test_dashboard_populated_evaluation_run_discovery(self):
        """Verify discover_evaluation_runs discovers real results files in the workspace."""
        results_dir = pathlib.Path("data/evaluation/results")
        if results_dir.exists():
            runs = discover_evaluation_runs(results_dir)
            self.assertIsInstance(runs, list)
            if runs:
                self.assertIn("run_id", runs[0])
                self.assertIn("metrics_file", runs[0])

    def test_dashboard_invalid_user_annotation_handling(self):
        """Verify save_review_annotation validates input actions and IDs safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            review_file = pathlib.Path(tmpdir) / "reviews.json"
            history_file = pathlib.Path(tmpdir) / "history.jsonl"

            # Invalid status rejection
            ok, msg = save_review_annotation("BM-1", "title", "invalid_status", "rev1", "notes", storage_path=review_file, history_path=history_file)
            self.assertFalse(ok)
            self.assertIn("Invalid review status", msg)

            # Missing reviewer notes rejection
            ok2, msg2 = save_review_annotation("BM-1", "title", "verified", "rev1", "", storage_path=review_file, history_path=history_file)
            self.assertFalse(ok2)
            self.assertIn("mandatory", msg2.lower())


# ==============================================================================
# 6. Local End-to-End Pipeline Smoke Test (Integration)
# ==============================================================================

class TestLocalEndToEndIntegrationSmoke(unittest.TestCase):
    """End-to-End local smoke test connecting scraping, cleaning, extraction, roles, evaluation, and analytics."""

    def test_full_pipeline_offline_execution(self):
        """Execute end-to-end data pipeline completely offline using temporary fixtures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)

            # Step 1: Scrape fixture
            html_content = read_fixture("shine_detail_bengaluru.html")
            url_smoke = "https://www.shine.com/jobs/19582041"
            extractor = ShineExtractor()
            scrape_res = ExtractionResult.create_for_url(url_smoke, "batch_smoke")
            scrape_res = extractor.extract(url_smoke, html_content, scrape_res)
            self.assertEqual(scrape_res.extraction_status, "success")

            # Step 2: Clean and Normalize
            raw_data = pd.DataFrame([{
                "job_id": "smoke_1",
                "source_job_id": "19582041",
                "job_title_raw": scrape_res.job_title_raw,
                "company_raw": scrape_res.company_raw,
                "country_raw": "India",
                "location_raw": scrape_res.location_raw,
                "job_description_raw": scrape_res.job_description_raw,
                "requirements_raw": scrape_res.requirements_raw,
                "posted_date_raw": scrape_res.posted_date_raw,
                "closing_date_raw": scrape_res.closing_date_raw,
                "salary_text_raw": scrape_res.salary_text_raw,
                "salary_currency_raw": scrape_res.salary_currency_raw,
                "salary_min_raw": scrape_res.salary_min_raw,
                "salary_max_raw": scrape_res.salary_max_raw,
                "salary_period_raw": scrape_res.salary_period_raw,
                "source_hostname": "shine.com",
                "source_platform": "www.shine.com",
                "source_url": "https://www.shine.com/jobs/19582041",
                "extraction_status": "success",
            }])

            internal_df, team_df, stats = clean_raw_dataframe(raw_data)
            self.assertEqual(len(internal_df), 1)
            self.assertTrue(bool(internal_df.iloc[0]["salary_disclosed"]))
            self.assertEqual(internal_df.iloc[0]["salary_currency_normalized"], "INR")

            # Step 3: Skill Extraction
            skill_tax = load_taxonomy(pathlib.Path("config/skill_taxonomy.json"))
            skill_extractor = LexicalSkillExtractor(skill_tax)
            desc_text = internal_df.iloc[0].get("job_description_clean") or internal_df.iloc[0].get("job_description_raw", "")
            full_text_for_skills = f"{internal_df.iloc[0]['job_title_raw']} {desc_text}".strip()
            extracted_skills = skill_extractor.extract("smoke_1", full_text_for_skills)
            extracted_skill_ids = [s.skill_id for s in extracted_skills.skills]
            self.assertIn("python", extracted_skill_ids)

            # Step 4: Role Classification
            role_tax = load_role_taxonomy(pathlib.Path("config/role_taxonomy.json"))
            role_clf = RoleClassifier(role_tax)
            rid, rname, _ = role_clf.classify(internal_df.iloc[0]["job_title_raw"], desc_text)
            self.assertEqual(rid, "software_engineer")

            # Step 5: Regional Analysis
            internal_df["job_description"] = [desc_text]
            internal_df["skills"] = [extracted_skill_ids]
            internal_df["role_id"] = [rid]
            internal_df["role_name"] = [rname]
            internal_df["country"] = ["India"]
            internal_df["is_it"] = [True]
            internal_df["classification_status"] = ["it"]
            internal_df["is_benchmark_verified"] = [True]
            internal_df["source_validation_status"] = ["validated"]
            internal_df["salary_monthly_midpoint"] = [166666.67]

            cfg = EligibilityConfig()
            demands = calculate_skill_demand_percentages(internal_df, cfg)
            self.assertFalse(demands.empty)
            py_row = demands[demands["skill_id"] == "python"].iloc[0]
            self.assertEqual(float(py_row["demand_pct"]), 100.0)


if __name__ == "__main__":
    unittest.main()
