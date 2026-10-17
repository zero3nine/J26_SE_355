import unittest
from pathlib import Path
import pandas as pd
import tempfile
import json

from src.cleaning.salary_normalizer import (
    parse_and_normalize_salary,
    SUPPORTED_CURRENCIES,
    VALID_SALARY_PERIODS,
    VALID_SALARY_TYPES
)
from src.cleaning.location_normalizer import (
    parse_and_normalize_location,
    normalize_country,
    WORK_MODES
)
from src.cleaning.clean_jobs import clean_raw_dataframe, migrate_legacy_dataframe, standardize_location
from src.cleaning.validate_jobs import run_validation_pipeline
from src.scraping.models import TEAM_SCHEMA_COLUMNS, RAW_SCHEMA_COLUMNS
from src.analytics.data_loader import load_extracted_jobs
from src.roles.role_skill_analysis import classify_roles


class TestSalaryNormalization(unittest.TestCase):
    """Tests for Section 2.A Salary Schema and Normalization Requirements."""

    def test_missing_and_undisclosed_salaries(self):
        """Verify undisclosed/negotiable salary is marked undisclosed, NOT zero."""
        undisclosed_phrases = [
            "",
            "   ",
            None,
            "Negotiable",
            "Not Disclosed",
            "Competitive salary",
            "DOE",
            "Best in industry",
            "Undisclosed",
            "As per market standards"
        ]
        for phrase in undisclosed_phrases:
            res = parse_and_normalize_salary(phrase)
            self.assertFalse(res["salary_disclosed"], f"Failed on: {phrase}")
            self.assertEqual(res["salary_type"], "undisclosed")
            self.assertEqual(res["salary_normalization_status"], "undisclosed")
            self.assertIsNone(res["salary_min_normalized"])
            self.assertIsNone(res["salary_max_normalized"])

    def test_distinguish_undisclosed_from_zero_salary(self):
        """Zero salary must not be classified as undisclosed, and vice versa."""
        zero_res = parse_and_normalize_salary("LKR 0 per month")
        self.assertTrue(zero_res["salary_disclosed"])
        self.assertEqual(zero_res["salary_min_normalized"], 0.0)
        self.assertEqual(zero_res["salary_max_normalized"], 0.0)
        self.assertEqual(zero_res["salary_type"], "fixed")

        undisclosed_res = parse_and_normalize_salary("Negotiable")
        self.assertFalse(undisclosed_res["salary_disclosed"])
        self.assertIsNone(undisclosed_res["salary_min_normalized"])

    def test_fixed_and_single_salaries(self):
        """Test single/fixed salary parsing for various formats and currencies."""
        # Singapore SGD monthly
        sg_res = parse_and_normalize_salary("SGD 6,500 / month")
        self.assertTrue(sg_res["salary_disclosed"])
        self.assertEqual(sg_res["salary_type"], "fixed")
        self.assertEqual(sg_res["salary_min_normalized"], 6500.0)
        self.assertEqual(sg_res["salary_max_normalized"], 6500.0)
        self.assertEqual(sg_res["salary_currency_normalized"], "SGD")
        self.assertEqual(sg_res["salary_period_normalized"], "monthly")

        # Sri Lanka LKR with country context
        sl_res = parse_and_normalize_salary("Rs. 250,000 monthly", country_context="Sri Lanka")
        self.assertTrue(sl_res["salary_disclosed"])
        self.assertEqual(sl_res["salary_type"], "fixed")
        self.assertEqual(sl_res["salary_min_normalized"], 250000.0)
        self.assertEqual(sl_res["salary_currency_normalized"], "LKR")
        self.assertEqual(sl_res["salary_period_normalized"], "monthly")

        # Explicit LKR without country context
        sl_explicit = parse_and_normalize_salary("LKR 250,000 monthly")
        self.assertEqual(sl_explicit["salary_currency_normalized"], "LKR")

        # Ambiguous Rs without country context (Rule 6: do not guess currency without evidence)
        generic_rs = parse_and_normalize_salary("Rs. 250,000 monthly")
        self.assertEqual(generic_rs["salary_currency_normalized"], "Rs")

    def test_salary_ranges(self):
        """Test salary ranges in multiple regional formats."""
        # Malaysia MYR
        my_res = parse_and_normalize_salary("MYR 4,000 - MYR 7,500 per month")
        self.assertTrue(my_res["salary_disclosed"])
        self.assertEqual(my_res["salary_type"], "range")
        self.assertEqual(my_res["salary_min_normalized"], 4000.0)
        self.assertEqual(my_res["salary_max_normalized"], 7500.0)
        self.assertEqual(my_res["salary_currency_normalized"], "MYR")
        self.assertEqual(my_res["salary_period_normalized"], "monthly")

        # India INR with LPA notation (1 Lakh = 100,000)
        in_res = parse_and_normalize_salary("₹ 12 - 18 LPA")
        self.assertTrue(in_res["salary_disclosed"])
        self.assertEqual(in_res["salary_type"], "range")
        self.assertEqual(in_res["salary_min_normalized"], 1200000.0)
        self.assertEqual(in_res["salary_max_normalized"], 1800000.0)
        self.assertEqual(in_res["salary_currency_normalized"], "INR")
        self.assertEqual(in_res["salary_period_normalized"], "annual")

        # India INR standard format
        in_std = parse_and_normalize_salary("INR 800,000 - 1,200,000 per annum")
        self.assertEqual(in_std["salary_min_normalized"], 800000.0)
        self.assertEqual(in_std["salary_max_normalized"], 1200000.0)
        self.assertEqual(in_std["salary_currency_normalized"], "INR")
        self.assertEqual(in_std["salary_period_normalized"], "annual")

    def test_starting_from_and_up_to(self):
        """Test one-sided bounds: 'Starting from' and 'Up to'."""
        start_res = parse_and_normalize_salary("Starting from SGD 5,000 a month")
        self.assertEqual(start_res["salary_type"], "starting_from")
        self.assertEqual(start_res["salary_min_normalized"], 5000.0)
        self.assertIsNone(start_res["salary_max_normalized"])
        self.assertEqual(start_res["salary_currency_normalized"], "SGD")

        upto_res = parse_and_normalize_salary("Up to LKR 400,000 monthly")
        self.assertEqual(upto_res["salary_type"], "up_to")
        self.assertIsNone(upto_res["salary_min_normalized"])
        self.assertEqual(upto_res["salary_max_normalized"], 400000.0)
        self.assertEqual(upto_res["salary_currency_normalized"], "LKR")

    def test_pay_periods(self):
        """Verify hourly, daily, monthly, and annual period parsing."""
        # Hourly
        h_res = parse_and_normalize_salary("SGD 45 / hr")
        self.assertEqual(h_res["salary_period_normalized"], "hourly")

        # Daily
        d_res = parse_and_normalize_salary("MYR 350 per day")
        self.assertEqual(d_res["salary_period_normalized"], "daily")

        # Monthly
        m_res = parse_and_normalize_salary("LKR 150000 pm")
        self.assertEqual(m_res["salary_period_normalized"], "monthly")

        # Annual
        a_res = parse_and_normalize_salary("SGD 120,000 per annum")
        self.assertEqual(a_res["salary_period_normalized"], "annual")

    def test_ambiguous_and_unparseable_salaries(self):
        """Verify ambiguous text is flagged, not discarded or silently coerced."""
        ambig_res = parse_and_normalize_salary("Attractive package + performance bonus")
        self.assertFalse(ambig_res["salary_disclosed"])
        self.assertEqual(ambig_res["salary_normalization_status"], "ambiguous")
        self.assertEqual(ambig_res["salary_text_raw"], "Attractive package + performance bonus")

    def test_no_currency_domain_assumption_and_raw_preservation(self):
        """Do not assume currency from domains or guess without text evidence."""
        no_curr_res = parse_and_normalize_salary("5,000 - 8,000 per month")
        self.assertTrue(no_curr_res["salary_disclosed"])
        self.assertEqual(no_curr_res["salary_currency_normalized"], "")
        self.assertEqual(no_curr_res["salary_normalization_status"], "partial")
        self.assertEqual(no_curr_res["salary_min_normalized"], 5000.0)
        self.assertEqual(no_curr_res["salary_max_normalized"], 8000.0)


class TestLocationAndWorkMode(unittest.TestCase):
    """Tests for Section 2.B Location and Work-Mode Schema."""

    def test_missing_location_never_maps_to_remote(self):
        """CRITICAL: Empty location must NOT be coerced to 'Remote Work'."""
        empty_locations = ["", "   ", None, "Unspecified", "Unknown", "N/A", "-"]
        for loc in empty_locations:
            res = parse_and_normalize_location(loc)
            self.assertNotEqual(res["city_normalized"], "Remote Work")
            self.assertNotEqual(res["state_region_normalized"], "Remote Work")
            self.assertEqual(res["work_mode"], "unspecified")
            self.assertIn(res["location_normalization_status"], ["missing", "unspecified"])

        # Also test legacy standardize_location helper directly
        legacy_std = standardize_location("")
        self.assertNotEqual(legacy_std, "Remote Work")
        self.assertEqual(legacy_std, "")

    def test_explicitly_remote_locations(self):
        """Explicit remote markers should be classified as remote work_mode."""
        remote_locs = [
            "Remote",
            "Fully Remote",
            "Remote - Sri Lanka",
            "Work from Home",
            "Anywhere in India (Remote)",
            "Remote, Singapore"
        ]
        for loc in remote_locs:
            res = parse_and_normalize_location(loc)
            self.assertEqual(res["work_mode"], "remote", f"Failed for: {loc}")

    def test_hybrid_and_onsite_work_modes(self):
        """Test hybrid and on-site classification."""
        hybrid_locs = [
            "Colombo (Hybrid)",
            "Bengaluru - 2 days office / 3 days home",
            "Singapore (Hybrid work model)"
        ]
        for loc in hybrid_locs:
            res = parse_and_normalize_location(loc)
            self.assertEqual(res["work_mode"], "hybrid", f"Failed for: {loc}")

        onsite_locs = [
            "Colombo 03 (Onsite)",
            "Cyberjaya (In-Office)",
            "Singapore (Work from office)"
        ]
        for loc in onsite_locs:
            res = parse_and_normalize_location(loc)
            self.assertEqual(res["work_mode"], "on_site", f"Failed for: {loc}")

    def test_sri_lanka_geographic_classification(self):
        """Test Sri Lanka city and provincial taxonomy."""
        res_col = parse_and_normalize_location("Colombo 07, Sri Lanka")
        self.assertEqual(res_col["country_normalized"], "Sri Lanka")
        self.assertEqual(res_col["city_normalized"], "Colombo")
        self.assertEqual(res_col["state_region_normalized"], "Western Province")

        res_kandy = parse_and_normalize_location("Kandy, Central Province")
        self.assertEqual(res_kandy["country_normalized"], "Sri Lanka")
        self.assertEqual(res_kandy["city_normalized"], "Kandy")
        self.assertEqual(res_kandy["state_region_normalized"], "Central Province")

    def test_india_geographic_classification(self):
        """Test India tech hubs and states."""
        res_blr = parse_and_normalize_location("Bengaluru, Karnataka, India")
        self.assertEqual(res_blr["country_normalized"], "India")
        self.assertEqual(res_blr["city_normalized"], "Bengaluru")
        self.assertEqual(res_blr["state_region_normalized"], "Karnataka")

        res_hyd = parse_and_normalize_location("Hyderabad, Telangana")
        self.assertEqual(res_hyd["country_normalized"], "India")
        self.assertEqual(res_hyd["city_normalized"], "Hyderabad")
        self.assertEqual(res_hyd["state_region_normalized"], "Telangana")

    def test_singapore_geographic_classification(self):
        """Test Singapore classification."""
        res_sg = parse_and_normalize_location("Jurong East, Singapore")
        self.assertEqual(res_sg["country_normalized"], "Singapore")
        self.assertEqual(res_sg["city_normalized"], "Singapore")

    def test_malaysia_geographic_classification(self):
        """Test Malaysia federal territory and states."""
        res_kl = parse_and_normalize_location("Kuala Lumpur, Malaysia")
        self.assertEqual(res_kl["country_normalized"], "Malaysia")
        self.assertEqual(res_kl["city_normalized"], "Kuala Lumpur")

        res_pen = parse_and_normalize_location("George Town, Penang")
        self.assertEqual(res_pen["country_normalized"], "Malaysia")
        self.assertEqual(res_pen["city_normalized"], "George Town")
        self.assertEqual(res_pen["state_region_normalized"], "Penang")

    def test_multiple_locations_preserved(self):
        """Multiple locations must be preserved without silent truncation."""
        multi_res = parse_and_normalize_location("Colombo; Kandy")
        self.assertIn("Colombo", multi_res["city_normalized"])
        self.assertIn("Kandy", multi_res["city_normalized"])


class TestLegacyMigrationAndDownstreamCompatibility(unittest.TestCase):
    """Tests for Section 2.D Schema Compatibility & Backward Migration."""

    def test_legacy_dataframe_migration(self):
        """Verify legacy 12-column datasets can be safely backfilled."""
        legacy_df = pd.DataFrame([{
            "job_id": "test_legacy_001",
            "job_title_raw": "Senior Software Engineer",
            "company": "Acme Corp",
            "country": "Sri Lanka",
            "location_raw": "Colombo",
            "job_description": "We need a Python developer with Django and AWS skills.",
            "requirements": "3+ years Python experience.",
            "posted_date": "2026-08-01",
            "closing_date": "2026-09-01",
            "source_platform": "TopJobs",
            "source_url": "https://example.com/job/001",
            "scraped_at": "2026-08-01 10:00:00"
        }])

        migrated_df = migrate_legacy_dataframe(legacy_df)

        # Assert all required new columns exist
        self.assertIn("salary_disclosed", migrated_df.columns)
        self.assertIn("salary_type", migrated_df.columns)
        self.assertIn("salary_min_normalized", migrated_df.columns)
        self.assertIn("salary_currency_normalized", migrated_df.columns)
        self.assertIn("work_mode", migrated_df.columns)
        self.assertIn("city_normalized", migrated_df.columns)

        # Assert safe deterministic values
        self.assertFalse(migrated_df.iloc[0]["salary_disclosed"])
        self.assertEqual(migrated_df.iloc[0]["salary_type"], "undisclosed")
        self.assertEqual(migrated_df.iloc[0]["city_normalized"], "Colombo")

    def test_cleaning_pipeline_with_regional_fields(self):
        """Verify end-to-end clean_raw_dataframe produces complete regional schema."""
        raw_df = pd.DataFrame([{
            "job_id": "job_reg_001",
            "source_job_id": "src_001",
            "job_title_raw": "Lead DevOps Engineer",
            "company_raw": "Virtusa",
            "country_raw": "Sri Lanka",
            "location_raw": "Colombo 03",
            "salary_text_raw": "LKR 400,000 - 600,000 / month",
            "salary_currency_raw": "LKR",
            "salary_min_raw": "400000",
            "salary_max_raw": "600000",
            "salary_period_raw": "monthly",
            "work_mode_raw": "hybrid",
            "job_description_raw": "Senior DevOps position designing CI/CD pipelines in Docker and Kubernetes.",
            "requirements_raw": "Hands-on experience with Terraform and Python.",
            "posted_date_raw": "2026-08-10",
            "closing_date_raw": "2026-09-10",
            "source_platform": "TopJobs",
            "source_url": "https://example.com/devops-job",
            "final_url": "https://example.com/devops-job",
            "collection_batch_id": "batch_test_001",
            "scraped_at": "2026-08-10 12:00:00"
        }])

        df_internal, df_team, stats = clean_raw_dataframe(raw_df)

        self.assertEqual(len(df_team), 1)
        row = df_team.iloc[0]

        # Verify salary normalization in clean output
        self.assertTrue(row["salary_disclosed"])
        self.assertEqual(row["salary_type"], "range")
        self.assertEqual(row["salary_min_normalized"], 400000.0)
        self.assertEqual(row["salary_max_normalized"], 600000.0)
        self.assertEqual(row["salary_currency_normalized"], "LKR")
        self.assertEqual(row["salary_period_normalized"], "monthly")

        # Verify location & work mode
        self.assertEqual(row["country_normalized"], "Sri Lanka")
        self.assertEqual(row["city_normalized"], "Colombo")
        self.assertEqual(row["state_region_normalized"], "Western Province")
        self.assertEqual(row["work_mode"], "hybrid")

        # Verify downstream compatibility: analytics data_loader expectations
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as tmp_file:
            # Emulate an extracted dataset matching TEAM_SCHEMA_COLUMNS + extracted skill cols
            extracted_df = df_team.copy()
            extracted_df["lexical_skills"] = json.dumps(["Docker", "Kubernetes"])
            extracted_df["semantic_skills"] = json.dumps(["Terraform", "Python"])
            extracted_df.to_csv(tmp_file.name, index=False)
            tmp_path = Path(tmp_file.name)

        try:
            loaded_df = load_extracted_jobs(tmp_path, skill_column="semantic_skills")
            self.assertEqual(len(loaded_df), 1)
            self.assertEqual(loaded_df.iloc[0]["job_id"], "job_reg_001")
            self.assertEqual(loaded_df.iloc[0]["skills"], ["Python", "Terraform"])

            # Verify role classification downstream works
            classified_df = classify_roles(extracted_df)
            self.assertIn("role_name", classified_df.columns)
            self.assertIn("salary_min_normalized", classified_df.columns)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


class TestDataQualityRules(unittest.TestCase):
    """Tests for Section 2.E Data-Quality Rules in validate_jobs.py."""

    def test_validation_catches_invalid_salary_ranges(self):
        """Rule 14: Min salary > Max salary must generate validation issues."""
        bad_df = pd.DataFrame([{
            "job_id": "bad_sal_001",
            "source_job_id": "1001",
            "job_title_raw": "Backend Engineer",
            "company_raw": "Tech Corp",
            "company": "Tech Corp",
            "country": "Singapore",
            "location": "Singapore",
            "location_raw": "Singapore",
            "country_normalized": "Singapore",
            "city_normalized": "Singapore",
            "state_region_normalized": "Central Region",
            "work_mode": "on_site",
            "location_normalization_status": "normalized",
            "job_description_raw": "Valid job description over 50 characters long to pass baseline checks.",
            "job_description_clean": "Valid job description over 50 characters long to pass baseline checks.",
            "requirements_raw": "Python, SQL",
            "listing_posted_date_raw": "2026-08-01",
            "closing_date_raw": "2026-08-30",
            "functional_area": "IT/Software",
            "description_type": "html_text",
            "advert_image_urls": "",
            "ocr_text_raw": "",
            "ocr_status": "not_applicable",
            "ocr_confidence": "0.0",
            "source_platform": "MyCareersFuture",
            "source_url": "https://example.com/job",
            "canonical_url": "https://example.com/job",
            "collection_batch_id": "batch_1",
            "scraped_at": "2026-08-01 10:00:00",
            "extraction_status": "success",
            "exclusion_reason": "",
            "salary_text_raw": "SGD 9,000 - 6,000",
            "salary_disclosed": True,
            "salary_type": "range",
            "salary_min_normalized": 9000.0,
            "salary_max_normalized": 6000.0,
            "salary_currency_normalized": "SGD",
            "salary_period_normalized": "monthly",
            "salary_normalization_status": "normalized",
            "salary_normalization_method": "regex_parsed",
            "clean_batch_id": "b1",
            "cleaned_at": "2026-08-01 12:00:00"
        }])

        report_runs, metrics, _ = run_validation_pipeline(pd.DataFrame(), bad_df, bad_df)
        sal_check = next((c for c in report_runs if c["name"] == "Salary Range Consistency"), None)
        self.assertIsNotNone(sal_check)
        self.assertEqual(sal_check["status"], "FAIL")
        self.assertIn("exceeds max salary", sal_check["details"])

    def test_validation_catches_missing_currency_with_disclosed_salary(self):
        """Rule 14: Numeric salary with missing currency generates validation warning."""
        no_curr_df = pd.DataFrame([{
            "job_id": "no_curr_001",
            "source_job_id": "1002",
            "job_title_raw": "Data Analyst",
            "company_raw": "Data Corp",
            "company": "Data Corp",
            "country": "India",
            "location": "Bengaluru",
            "location_raw": "Bengaluru",
            "country_normalized": "India",
            "city_normalized": "Bengaluru",
            "state_region_normalized": "Karnataka",
            "work_mode": "hybrid",
            "location_normalization_status": "normalized",
            "job_description_raw": "Valid job description over 50 characters long to pass baseline checks.",
            "job_description_clean": "Valid job description over 50 characters long to pass baseline checks.",
            "requirements_raw": "Python, SQL",
            "listing_posted_date_raw": "2026-08-01",
            "closing_date_raw": "2026-08-30",
            "functional_area": "IT/Software",
            "description_type": "html_text",
            "advert_image_urls": "",
            "ocr_text_raw": "",
            "ocr_status": "not_applicable",
            "ocr_confidence": "0.0",
            "source_platform": "Naukri",
            "source_url": "https://example.com/analyst",
            "canonical_url": "https://example.com/analyst",
            "collection_batch_id": "batch_1",
            "scraped_at": "2026-08-01 10:00:00",
            "extraction_status": "success",
            "exclusion_reason": "",
            "salary_text_raw": "50,000 - 80,000 per month",
            "salary_disclosed": True,
            "salary_type": "range",
            "salary_min_normalized": 50000.0,
            "salary_max_normalized": 80000.0,
            "salary_currency_normalized": "",
            "salary_period_normalized": "monthly",
            "salary_normalization_status": "partial",
            "salary_normalization_method": "regex_parsed",
            "clean_batch_id": "b1",
            "cleaned_at": "2026-08-01 12:00:00"
        }])

        report_runs, metrics, _ = run_validation_pipeline(pd.DataFrame(), no_curr_df, no_curr_df)
        curr_check = next((c for c in report_runs if c["name"] == "Salary Currency Disclosure"), None)
        self.assertIsNotNone(curr_check)
        self.assertEqual(curr_check["status"], "WARNING")
        self.assertIn("without normalized currency", curr_check["details"])

    def test_validation_passes_valid_regional_record(self):
        """Valid record passes all regional validation rules."""
        valid_df = pd.DataFrame([{
            "job_id": "good_001",
            "source_job_id": "1003",
            "job_title_raw": "Software Engineer",
            "company_raw": "Virtusa",
            "company": "Virtusa",
            "country": "Sri Lanka",
            "location": "Colombo",
            "location_raw": "Colombo 07",
            "country_normalized": "Sri Lanka",
            "city_normalized": "Colombo",
            "state_region_normalized": "Western Province",
            "work_mode": "hybrid",
            "location_normalization_status": "normalized",
            "job_description_raw": "Valid software engineering job description exceeding fifty characters in total length.",
            "job_description_clean": "Valid software engineering job description exceeding fifty characters in total length.",
            "requirements_raw": "Python, SQL, AWS",
            "listing_posted_date_raw": "2026-08-01",
            "closing_date_raw": "2026-08-30",
            "functional_area": "IT/Software",
            "description_type": "html_text",
            "advert_image_urls": "",
            "ocr_text_raw": "",
            "ocr_status": "not_applicable",
            "ocr_confidence": "0.0",
            "source_platform": "TopJobs",
            "source_url": "https://example.com/job",
            "canonical_url": "https://example.com/job",
            "collection_batch_id": "batch_1",
            "scraped_at": "2026-08-01 10:00:00",
            "extraction_status": "success",
            "exclusion_reason": "",
            "salary_text_raw": "LKR 250,000 - 350,000 per month",
            "salary_disclosed": True,
            "salary_type": "range",
            "salary_min_normalized": 250000.0,
            "salary_max_normalized": 350000.0,
            "salary_currency_normalized": "LKR",
            "salary_period_normalized": "monthly",
            "salary_normalization_status": "normalized",
            "salary_normalization_method": "regex_parsed",
            "clean_batch_id": "b1",
            "cleaned_at": "2026-08-01 12:00:00"
        }])

        report_runs, metrics, _ = run_validation_pipeline(pd.DataFrame(), valid_df, valid_df)
        regional_rules = [
            "Salary Range Consistency",
            "Salary Currency Disclosure",
            "Salary Pay Period Validity",
            "Country Normalization Validity",
            "Work Mode & Location Alignment",
            "Normalization Statuses Schema",
            "Source Provenance Completeness"
        ]
        for rule_name in regional_rules:
            check = next((c for c in report_runs if c["name"] == rule_name), None)
            self.assertIsNotNone(check, f"Missing rule: {rule_name}")
            self.assertEqual(check["status"], "PASS", f"Rule {rule_name} failed: {check['details']}")


if __name__ == "__main__":
    unittest.main()

