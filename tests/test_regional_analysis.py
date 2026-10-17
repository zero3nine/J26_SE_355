"""
Unit and Integration Tests for Comparative Regional IT Labor-Market Analysis Engine.
Project: IT Job Market Intelligence Tool (J26_SE_355).

Tests:
1. Denominator consistency and cross-country rules.
2. Unique skill counting per advertisement (anti-inflation guarantee).
3. Independent eligibility rules (skill demand does NOT require disclosed salary).
4. Missing, undisclosed, and ambiguous salary handling (no zero inference).
5. Currency and pay-period isolation and monthly conversion.
6. Small sample size flags (N < 10) and empty group handling.
7. Skill-gap calculations with two-proportion z-tests.
8. Deterministic multidimensional profile similarity (Cosine, Jaccard, Spearman).
9. Sensitivity analysis across validation regimes.
"""

import math
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

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


class TestRegionalAnalysisEngine(unittest.TestCase):
    """Test suite for the regional analysis engine using isolated synthetic fixtures."""

    def setUp(self):
        """Build controlled synthetic job records across target regional markets."""
        self.config = EligibilityConfig()

        # Synthetic multi-market dataset
        self.synthetic_df = pd.DataFrame([
            # Sri Lanka (LK)
            {
                "job_id": "lk_1",
                "source_url": "https://example.lk/job1",
                "source_platform": "itpro.lk",
                "country": "Sri Lanka",
                "job_title_raw": "Senior Python Backend Engineer",
                "company": "Colombo Tech",
                "location_raw": "Colombo",
                "work_mode": "hybrid",
                "job_description": "We need Python, Docker, AWS, PostgreSQL, Git and Agile.",
                "is_it": True,
                "classification_status": "it",
                "source_validation_status": "validated",
                "is_benchmark_verified": True,
                "skills": ["python", "docker", "aws", "postgresql", "git", "agile"],
                "role_id": "software_engineer",
                "role_name": "Software Engineer / Developer",
                "salary_disclosed": True,
                "salary_text_raw": "LKR 300,000 - 450,000",
                "salary_type": "range",
                "salary_min_raw": "300000",
                "salary_max_raw": "450000",
                "salary_min_normalized": 300000.0,
                "salary_max_normalized": 450000.0,
                "salary_currency_normalized": "LKR",
                "salary_period_normalized": "monthly",
                "salary_monthly_min": 300000.0,
                "salary_monthly_max": 450000.0,
                "salary_monthly_midpoint": 375000.0,
                "salary_normalization_status": "normalized",
                "salary_normalization_method": "regex_parsed",
            },
            {
                "job_id": "lk_2",
                "source_url": "https://example.lk/job2",
                "source_platform": "itpro.lk",
                "country": "Sri Lanka",
                "job_title_raw": "QA Automation Engineer",
                "company": "Kandy Solutions",
                "location_raw": "Kandy",
                "work_mode": "remote",
                "job_description": "Selenium, Python, Git, and test automation experience required.",
                "is_it": True,
                "classification_status": "it",
                "source_validation_status": "validated",
                "is_benchmark_verified": True,
                "skills": ["python", "selenium", "git", "test_automation"],
                "role_id": "qa_test_engineer",
                "role_name": "QA / Test Engineer",
                "salary_disclosed": False,  # Undisclosed salary!
                "salary_text_raw": "Competitive",
                "salary_type": "undisclosed",
                "salary_min_raw": "",
                "salary_max_raw": "",
                "salary_min_normalized": None,
                "salary_max_normalized": None,
                "salary_currency_normalized": "",
                "salary_period_normalized": "unspecified",
                "salary_monthly_min": None,
                "salary_monthly_max": None,
                "salary_monthly_midpoint": None,
                "salary_normalization_status": "undisclosed",
                "salary_normalization_method": "not_applicable",
            },
            {
                "job_id": "lk_3",
                "source_url": "https://example.lk/job3",
                "source_platform": "topjobs.lk",
                "country": "Sri Lanka",
                "job_title_raw": "Frontend React Developer",
                "company": "Apex Lanka",
                "location_raw": "Colombo",
                "work_mode": "on_site",
                "job_description": "React, JavaScript, TypeScript, HTML, CSS.",
                "is_it": True,
                "classification_status": "it",
                "source_validation_status": "validated",
                "is_benchmark_verified": False,
                "skills": ["javascript", "typescript", "react", "html", "css"],
                "role_id": "software_engineer",
                "role_name": "Software Engineer / Developer",
                "salary_disclosed": False,
                "salary_text_raw": "",
                "salary_type": "undisclosed",
                "salary_min_raw": "",
                "salary_max_raw": "",
                "salary_min_normalized": None,
                "salary_max_normalized": None,
                "salary_currency_normalized": "",
                "salary_period_normalized": "unspecified",
                "salary_monthly_min": None,
                "salary_monthly_max": None,
                "salary_monthly_midpoint": None,
                "salary_normalization_status": "undisclosed",
                "salary_normalization_method": "not_applicable",
            },
            # India (IN)
            {
                "job_id": "in_1",
                "source_url": "https://example.in/job1",
                "source_platform": "shine.com",
                "country": "India",
                "job_title_raw": "Lead Python Architect",
                "company": "Bangalore Cloud",
                "location_raw": "Bangalore",
                "work_mode": "hybrid",
                "job_description": "Python, AWS, Microservices, Docker, Kubernetes.",
                "is_it": True,
                "classification_status": "it",
                "source_validation_status": "validated",
                "is_benchmark_verified": True,
                "skills": ["python", "aws", "docker", "kubernetes"],
                "role_id": "software_architect",
                "role_name": "Software Architect",
                "salary_disclosed": True,
                "salary_text_raw": "24 - 36 LPA",
                "salary_type": "range",
                "salary_min_raw": "24",
                "salary_max_raw": "36 LPA",
                "salary_min_normalized": 2400000.0,
                "salary_max_normalized": 3600000.0,
                "salary_currency_normalized": "INR",
                "salary_period_normalized": "annual",
                "salary_monthly_min": 200000.0,
                "salary_monthly_max": 300000.0,
                "salary_monthly_midpoint": 250000.0,
                "salary_normalization_status": "normalized",
                "salary_normalization_method": "regex_parsed",
            },
            {
                "job_id": "in_2",
                "source_url": "https://example.in/job2",
                "source_platform": "shine.com",
                "country": "India",
                "job_title_raw": "Java Backend Developer",
                "company": "Pune Infosys",
                "location_raw": "Pune",
                "work_mode": "on_site",
                "job_description": "Java, Spring Boot, MySQL, Git.",
                "is_it": True,
                "classification_status": "it",
                "source_validation_status": "validated",
                "is_benchmark_verified": True,
                "skills": ["java", "spring_boot", "mysql", "git"],
                "role_id": "software_engineer",
                "role_name": "Software Engineer / Developer",
                "salary_disclosed": True,
                "salary_text_raw": "12 LPA",
                "salary_type": "fixed",
                "salary_min_raw": "12 LPA",
                "salary_max_raw": "12 LPA",
                "salary_min_normalized": 1200000.0,
                "salary_max_normalized": 1200000.0,
                "salary_currency_normalized": "INR",
                "salary_period_normalized": "annual",
                "salary_monthly_min": 100000.0,
                "salary_monthly_max": 100000.0,
                "salary_monthly_midpoint": 100000.0,
                "salary_normalization_status": "normalized",
                "salary_normalization_method": "regex_parsed",
            },
            # Singapore (SG)
            {
                "job_id": "sg_1",
                "source_url": "https://example.gov.sg/job1",
                "source_platform": "www.mycareersfuture.gov.sg",
                "country": "Singapore",
                "job_title_raw": "Senior Software Engineer (Python/Go)",
                "company": "SG Fintech Ltd",
                "location_raw": "Singapore Central",
                "work_mode": "hybrid",
                "job_description": "Python, Golang, AWS, Docker, CI/CD, Git.",
                "is_it": True,
                "classification_status": "it",
                "source_validation_status": "validated",
                "is_benchmark_verified": True,
                "skills": ["python", "golang", "aws", "docker", "cicd", "git"],
                "role_id": "software_engineer",
                "role_name": "Software Engineer / Developer",
                "salary_disclosed": True,
                "salary_text_raw": "8000 - 12000 SGD",
                "salary_type": "range",
                "salary_min_raw": "8000",
                "salary_max_raw": "12000",
                "salary_min_normalized": 8000.0,
                "salary_max_normalized": 12000.0,
                "salary_currency_normalized": "SGD",
                "salary_period_normalized": "monthly",
                "salary_monthly_min": 8000.0,
                "salary_monthly_max": 12000.0,
                "salary_monthly_midpoint": 10000.0,
                "salary_normalization_status": "normalized",
                "salary_normalization_method": "jsonld_structured",
            },
            # Malaysia (MY)
            {
                "job_id": "my_1",
                "source_url": "https://example.com.my/job1",
                "source_platform": "my.jobstreet.com",
                "country": "Malaysia",
                "job_title_raw": "Data Analyst (SQL/Python)",
                "company": "KL Analytics",
                "location_raw": "Kuala Lumpur",
                "work_mode": "hybrid",
                "job_description": "SQL, Python, Tableau, Power BI, Excel.",
                "is_it": True,
                "classification_status": "it",
                "source_validation_status": "validated",
                "is_benchmark_verified": True,
                "skills": ["sql", "python", "tableau", "power_bi"],
                "role_id": "data_analyst",
                "role_name": "Data Analyst",
                "salary_disclosed": True,
                "salary_text_raw": "RM 6,000 - 8,500",
                "salary_type": "range",
                "salary_min_raw": "6000",
                "salary_max_raw": "8500",
                "salary_min_normalized": 6000.0,
                "salary_max_normalized": 8500.0,
                "salary_currency_normalized": "MYR",
                "salary_period_normalized": "monthly",
                "salary_monthly_min": 6000.0,
                "salary_monthly_max": 8500.0,
                "salary_monthly_midpoint": 7250.0,
                "salary_normalization_status": "normalized",
                "salary_normalization_method": "regex_parsed",
            },
            # Invalid Non-IT Record (to verify filtering)
            {
                "job_id": "non_it_1",
                "source_url": "https://example.com/nonit",
                "source_platform": "general.com",
                "country": "Sri Lanka",
                "job_title_raw": "Executive Assistant to Managing Director",
                "company": "Hotel Grand",
                "location_raw": "Colombo",
                "work_mode": "on_site",
                "job_description": "Secretarial duties, diary scheduling, event planning.",
                "is_it": False,
                "classification_status": "non_it",
                "source_validation_status": "unverified",
                "is_benchmark_verified": False,
                "skills": [],
                "role_id": "unclassified",
                "role_name": "Unclassified",
                "salary_disclosed": False,
                "salary_text_raw": "",
                "salary_type": "undisclosed",
                "salary_min_raw": "",
                "salary_max_raw": "",
                "salary_min_normalized": None,
                "salary_max_normalized": None,
                "salary_currency_normalized": "",
                "salary_period_normalized": "unspecified",
                "salary_monthly_min": None,
                "salary_monthly_max": None,
                "salary_monthly_midpoint": None,
                "salary_normalization_status": "undisclosed",
                "salary_normalization_method": "not_applicable",
            },
            # Invalid Geographic Record (Outside target countries)
            {
                "job_id": "us_1",
                "source_url": "https://example.com/us1",
                "source_platform": "indeed.com",
                "country": "United States",
                "job_title_raw": "Software Engineer",
                "company": "US Corp",
                "location_raw": "San Francisco",
                "work_mode": "remote",
                "job_description": "Python, AWS.",
                "is_it": True,
                "classification_status": "it",
                "source_validation_status": "unverified",
                "is_benchmark_verified": False,
                "skills": ["python", "aws"],
                "role_id": "software_engineer",
                "role_name": "Software Engineer / Developer",
                "salary_disclosed": True,
                "salary_text_raw": "$120,000",
                "salary_type": "fixed",
                "salary_min_raw": "120000",
                "salary_max_raw": "120000",
                "salary_min_normalized": 120000.0,
                "salary_max_normalized": 120000.0,
                "salary_currency_normalized": "USD",
                "salary_period_normalized": "annual",
                "salary_monthly_min": 10000.0,
                "salary_monthly_max": 10000.0,
                "salary_monthly_midpoint": 10000.0,
                "salary_normalization_status": "normalized",
                "salary_normalization_method": "regex_parsed",
            },
        ])

    def test_country_normalization_and_geographic_filtering(self):
        """Test country name standardizer and geographic exclusion."""
        self.assertEqual(normalize_country_name("LK"), "Sri Lanka")
        self.assertEqual(normalize_country_name("in"), "India")
        self.assertEqual(normalize_country_name("Singapore"), "Singapore")
        self.assertEqual(normalize_country_name("MYS"), "Malaysia")
        self.assertEqual(normalize_country_name("", platform="www.shine.com"), "India")
        self.assertEqual(normalize_country_name("", platform="itpro.lk"), "Sri Lanka")
        self.assertEqual(normalize_country_name("", platform="mycareersfuture.gov.sg"), "Singapore")

        # In dataset: 7 valid target IT records + 1 non-IT (Sri Lanka) + 1 US record
        eligible_geo, counts, _ = filter_records_with_provenance(
            self.synthetic_df, self.config, task="geographic"
        )
        # US record excluded by non_target_country, non-IT excluded by classified_non_it
        self.assertEqual(counts.get("non_target_country", 0), 1)
        self.assertNotIn("us_1", eligible_geo["job_id"].values)

    def test_separate_eligibility_rules_preserves_undisclosed_salary_for_skills(self):
        """CRITICAL: Test that skill demand does NOT require a disclosed salary."""
        # Record lk_2 has undisclosed salary
        eligible_skill, counts_skill, _ = filter_records_with_provenance(
            self.synthetic_df, self.config, task="skill"
        )
        self.assertIn("lk_2", eligible_skill["job_id"].values)
        self.assertNotIn("salary_undisclosed", counts_skill)

        # But for salary task, lk_2 must be excluded
        eligible_salary, counts_salary, _ = filter_records_with_provenance(
            self.synthetic_df, self.config, task="salary"
        )
        self.assertNotIn("lk_2", eligible_salary["job_id"].values)
        self.assertGreater(counts_salary.get("salary_undisclosed", 0), 0)

    def test_exclusion_funnel_records_provenance(self):
        """Test that exclusion funnel audits attrition at every analytical stage."""
        funnel = build_exclusion_funnel(self.synthetic_df, self.config)
        self.assertEqual(len(funnel), 6)
        stages = funnel["stage"].tolist()
        self.assertIn("Raw Input Records", stages)
        self.assertIn("Geographic Filtering", stages)
        self.assertIn("Skill-Demand Analysis", stages)
        self.assertIn("Salary Analysis", stages)

        # Check total raw count matches
        raw_row = funnel[funnel["task"] == "raw"].iloc[0]
        self.assertEqual(raw_row["input_records"], len(self.synthetic_df))
        self.assertEqual(raw_row["eligible_records"], len(self.synthetic_df))

    def test_unique_skill_counting_per_advertisement(self):
        """Test that an ad mentioning a canonical skill multiple times is counted at most ONCE."""
        # Create an ad with repeated 'python' entries
        dup_skill_df = pd.DataFrame([{
            "job_id": "dup_1",
            "source_url": "https://example.lk/dup",
            "source_platform": "itpro.lk",
            "country": "Sri Lanka",
            "job_title_raw": "Python Developer Python Engineer",
            "company": "Test",
            "location_raw": "Colombo",
            "work_mode": "on_site",
            "job_description": "Python Python 3 Python",
            "is_it": True,
            "classification_status": "it",
            "source_validation_status": "validated",
            "is_benchmark_verified": True,
            "skills": ["python", "python", "python"],  # duplicates in list
            "role_id": "software_engineer",
            "role_name": "Software Engineer / Developer",
            "salary_disclosed": False,
            "salary_text_raw": "",
            "salary_type": "undisclosed",
            "salary_min_raw": "",
            "salary_max_raw": "",
            "salary_min_normalized": None,
            "salary_max_normalized": None,
            "salary_currency_normalized": "",
            "salary_period_normalized": "unspecified",
            "salary_monthly_min": None,
            "salary_monthly_max": None,
            "salary_monthly_midpoint": None,
            "salary_normalization_status": "undisclosed",
            "salary_normalization_method": "not_applicable",
        }])

        demands = calculate_skill_demand_percentages(dup_skill_df, self.config)
        python_row = demands[(demands["country"] == "Sri Lanka") & (demands["skill_id"] == "python")]
        self.assertEqual(len(python_row), 1)
        # Mention count must be exactly 1, NOT 3
        self.assertEqual(int(python_row.iloc[0]["mention_count"]), 1)
        self.assertEqual(float(python_row.iloc[0]["demand_pct"]), 100.0)

    def test_correct_denominators_across_countries(self):
        """Test that each country uses its own total eligible ads as the denominator."""
        demands = calculate_skill_demand_percentages(self.synthetic_df, self.config)
        self.assertFalse(demands.empty)

        # In synthetic_df:
        # Sri Lanka has 3 valid IT ads (lk_1, lk_2, lk_3)
        # Python appears in lk_1 and lk_2 -> 2/3 = 66.67%
        # India has 2 valid IT ads (in_1, in_2)
        # Python appears in in_1 -> 1/2 = 50.0%
        # Singapore has 1 ad (sg_1) -> Python appears -> 1/1 = 100.0%
        # Malaysia has 1 ad (my_1) -> Python appears -> 1/1 = 100.0%

        lk_py = demands[(demands["country"] == "Sri Lanka") & (demands["skill_id"] == "python")].iloc[0]
        self.assertEqual(int(lk_py["eligible_ads_denominator"]), 3)
        self.assertEqual(int(lk_py["mention_count"]), 2)
        self.assertEqual(float(lk_py["demand_pct"]), 66.67)

        in_py = demands[(demands["country"] == "India") & (demands["skill_id"] == "python")].iloc[0]
        self.assertEqual(int(in_py["eligible_ads_denominator"]), 2)
        self.assertEqual(int(in_py["mention_count"]), 1)
        self.assertEqual(float(in_py["demand_pct"]), 50.0)

    def test_wilson_confidence_interval_bounds(self):
        """Test Wilson score confidence interval calculations."""
        # 0 mentions out of 100 -> lower is 0.0, upper is small positive
        low, high = calculate_wilson_ci(0, 100)
        self.assertEqual(low, 0.0)
        self.assertGreater(high, 0.0)
        self.assertLess(high, 5.0)

        # 50 out of 100 -> centered around 50%
        low, high = calculate_wilson_ci(50, 100)
        self.assertLess(low, 50.0)
        self.assertGreater(high, 50.0)
        self.assertAlmostEqual((low + high) / 2.0, 50.0, delta=1.0)

        # Small sample flag verification
        cfg = EligibilityConfig(small_sample_threshold=10)
        demands = calculate_skill_demand_percentages(self.synthetic_df, cfg)
        # Sri Lanka has 3 ads (< 10), so small_sample_flag must be True
        lk_rows = demands[demands["country"] == "Sri Lanka"]
        self.assertTrue(lk_rows["small_sample_flag"].all())

    def test_skill_gaps_and_two_proportion_z_test(self):
        """Test skill-gap percentage point calculations and significance tests."""
        demands = calculate_skill_demand_percentages(self.synthetic_df, self.config)
        gaps = calculate_skill_gaps(demands, focal_country="Sri Lanka")
        self.assertFalse(gaps.empty)

        # Python in LK = 66.67%, in IN = 50.0% -> gap = +16.67 pp
        py_gap_in = gaps[(gaps["comparator_country"] == "India") & (gaps["skill_id"] == "python")].iloc[0]
        self.assertEqual(float(py_gap_in["gap_pp"]), 16.67)
        # Because samples are small (3 and 2), small_sample_warning must be True
        self.assertTrue(bool(py_gap_in["small_sample_warning"]))
        self.assertIn("Indeterminate", py_gap_in["evidence_status"])

    def test_salary_analysis_never_infers_zero_and_preserves_currencies(self):
        """Test salary calculations strictly preserve currency isolation and do not infer missing salaries."""
        country_sal, role_sal, rates = analyze_regional_salaries(self.synthetic_df, self.config)

        # 4 currencies represented: LKR, INR, SGD, MYR
        currencies = set(country_sal["currency"].unique())
        self.assertIn("LKR", currencies)
        self.assertIn("INR", currencies)
        self.assertIn("SGD", currencies)
        self.assertIn("MYR", currencies)

        # Verify Sri Lanka has exactly 1 disclosed salary in synthetic data (lk_1 = 375,000 midpoint)
        lk_row = country_sal[country_sal["country"] == "Sri Lanka"].iloc[0]
        self.assertEqual(int(lk_row["disclosed_salary_count"]), 1)
        self.assertEqual(float(lk_row["median_salary"]), 375000.0)
        self.assertNotEqual(float(lk_row["median_salary"]), 0.0)
        # Undisclosed lk_2 and lk_3 MUST NOT drag median to 0!

        # Verify India: in_1 = 250,000/mo, in_2 = 100,000/mo -> median = 175,000 INR/mo
        in_row = country_sal[country_sal["country"] == "India"].iloc[0]
        self.assertEqual(int(in_row["disclosed_salary_count"]), 2)
        self.assertEqual(float(in_row["median_salary"]), 175000.0)
        self.assertEqual(float(in_row["iqr_salary"]), 75000.0)

    def test_monthly_equivalent_period_conversions(self):
        """Test annual, hourly, and monthly pay period standardizations."""
        # Annual: 120,000 / year -> 10,000 / month
        min_m, max_m, mid_m = _compute_monthly_equivalents(120000.0, 144000.0, "annual")
        self.assertEqual(min_m, 10000.0)
        self.assertEqual(max_m, 12000.0)
        self.assertEqual(mid_m, 11000.0)

        # Hourly: $50 / hr * 160 hrs = $8,000 / month
        min_m, max_m, mid_m = _compute_monthly_equivalents(50.0, 60.0, "hourly", hours_per_month=160.0)
        self.assertEqual(min_m, 8000.0)
        self.assertEqual(max_m, 9600.0)
        self.assertEqual(mid_m, 8800.0)

        # Unspecified period -> cannot normalize
        min_m, max_m, mid_m = _compute_monthly_equivalents(5000.0, 7000.0, "unspecified")
        self.assertIsNone(min_m)
        self.assertIsNone(mid_m)

    def test_role_comparisons_and_unclassified_tracking(self):
        """Test role distributions and unclassified reporting."""
        role_counts, role_skills, unclass = compare_regional_roles(self.synthetic_df, self.config)
        self.assertFalse(role_counts.empty)
        self.assertFalse(unclass.empty)

        # Check Sri Lanka role counts: software_engineer (2), qa_test_engineer (1)
        lk_roles = role_counts[role_counts["country"] == "Sri Lanka"]
        self.assertEqual(len(lk_roles), 2)
        se_row = lk_roles[lk_roles["role_id"] == "software_engineer"].iloc[0]
        self.assertEqual(int(se_row["job_count"]), 2)

    def test_country_similarity_metrics(self):
        """Test Cosine, Jaccard, and Spearman profile similarities."""
        demands = calculate_skill_demand_percentages(self.synthetic_df, self.config)
        sims = calculate_country_similarities(demands)
        self.assertFalse(sims.empty)

        # All cosine values must be bounded between 0.0 and 1.0
        self.assertTrue((sims["cosine_similarity"] >= 0.0).all())
        self.assertTrue((sims["cosine_similarity"] <= 1.0).all())

        # Metric limitations note must be present
        self.assertTrue(sims["metric_limitations"].str.contains("proportional skill priority").all())

    def test_sensitivity_analysis_scenarios(self):
        """Test sensitivity analysis across 5 validation regimes."""
        summary, details = run_regional_sensitivity_analysis(self.synthetic_df, self.config)
        self.assertEqual(len(summary), 5)
        keys = summary["scenario_key"].tolist()
        self.assertIn("1_baseline", keys)
        self.assertIn("2_verified_sources_only", keys)
        self.assertIn("3_benchmark_verified_only", keys)
        self.assertIn("4_unambiguous_roles_only", keys)
        self.assertIn("5_salary_disclosed_subsample", keys)

        # Baseline mean shift must be 0.0
        base_row = summary[summary["scenario_key"] == "1_baseline"].iloc[0]
        self.assertEqual(float(base_row["mean_abs_demand_shift_pp"]), 0.0)

    def test_zero_dependency_markdown_table_formatter(self):
        """Test that _df_to_markdown works cleanly without tabulate dependency."""
        sample_df = pd.DataFrame([{"col1": "val1", "col2": 123}, {"col1": "val2", "col2": 456}])
        md = _df_to_markdown(sample_df)
        self.assertIn("| col1 | col2 |", md)
        self.assertIn("| --- | --- |", md)
        self.assertIn("| val1 | 123 |", md)


if __name__ == "__main__":
    unittest.main()
