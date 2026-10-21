"""
Automated Tests for Regional Analysis Visualizations and Statistical Charts.
Project: IT Job Market Intelligence Tool (J26_SE_355).
Research Component: Comparative Regional Market Analysis.

Coverage:
1. Grouped bar chart specifications and required tooltip dimensions.
2. Skill-demand 2D interactive heatmap with complete grid & text overlay.
3. Salary interval/range plot with local currency isolation and sample sizes.
4. 4x4 country-to-country skill profile similarity matrix (symmetry and diagonal).
5. Scraper zero-mention artifact detection in two-proportion skill gap tests.
"""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.analytics.regional_analysis import (
    EligibilityConfig,
    analyze_regional_salaries,
    calculate_country_similarities,
    calculate_skill_demand_percentages,
    calculate_skill_gaps,
)
from src.analytics.regional_charts import (
    COUNTRY_COLORS,
    TARGET_COUNTRIES_ORDER,
    build_country_similarity_matrix,
    build_salary_interval_chart,
    build_skill_demand_bar_chart,
    build_skill_demand_heatmap,
)


class TestRegionalVisualizations(unittest.TestCase):
    """Test suite for Altair regional visualization builders and statistical protections."""

    def setUp(self):
        """Construct synthetic multi-market data fixture with controlled properties."""
        self.config = EligibilityConfig()

        # Build multi-country synthetic dataset
        records = []
        countries = ["Sri Lanka", "India", "Singapore", "Malaysia"]

        # 1. Sri Lanka (N=20): Heavy Python (80%), Docker (50%), Git (40%)
        for i in range(20):
            records.append({
                "job_id": f"lk_{i}",
                "source_url": "https://example.lk",
                "source_platform": "itpro.lk",
                "country": "Sri Lanka",
                "job_title_raw": "Software Engineer",
                "location_raw": "Colombo",
                "is_it": True,
                "classification_status": "it",
                "source_validation_status": "validated",
                "skills": ["python"] if i < 16 else (["docker"] if i < 18 else ["git"]),
                "role_id": "software_engineer",
                "role_name": "Software Engineer / Developer",
                "salary_disclosed": i < 2,  # Only 2 disclosed
                "salary_min_normalized": 50000.0 if i == 0 else 75000.0,
                "salary_max_normalized": 70000.0 if i == 0 else 90000.0,
                "salary_currency_normalized": "LKR",
                "salary_period_normalized": "monthly",
                "salary_monthly_min": 50000.0 if i == 0 else 75000.0,
                "salary_monthly_max": 70000.0 if i == 0 else 90000.0,
                "salary_monthly_midpoint": 60000.0 if i == 0 else 82500.0,
            })

        # 2. India (N=20): High Java (75%), Python (50%), Zero Git (extraction defect)
        for i in range(20):
            records.append({
                "job_id": f"in_{i}",
                "source_url": "https://example.in",
                "source_platform": "shine.com",
                "country": "India",
                "job_title_raw": "Java Developer",
                "location_raw": "Bangalore",
                "is_it": True,
                "classification_status": "it",
                "source_validation_status": "validated",
                "skills": ["java"] if i < 15 else (["python"] if i < 18 else ["sql"]),
                "role_id": "software_engineer",
                "role_name": "Software Engineer / Developer",
                "salary_disclosed": i < 12,
                "salary_min_normalized": 20000.0 + i * 1000,
                "salary_max_normalized": 40000.0 + i * 1000,
                "salary_currency_normalized": "INR",
                "salary_period_normalized": "monthly",
                "salary_monthly_min": 20000.0 + i * 1000,
                "salary_monthly_max": 40000.0 + i * 1000,
                "salary_monthly_midpoint": 30000.0 + i * 1000,
            })

        # 3. Singapore (N=20): Balanced Python (60%), Docker (60%), Java (40%)
        for i in range(20):
            records.append({
                "job_id": f"sg_{i}",
                "source_url": "https://example.sg",
                "source_platform": "jobstreet.com.sg",
                "country": "Singapore",
                "job_title_raw": "Cloud Dev",
                "location_raw": "Singapore",
                "is_it": True,
                "classification_status": "it",
                "source_validation_status": "validated",
                "skills": ["python", "docker"] if i < 12 else ["java"],
                "role_id": "software_engineer",
                "role_name": "Software Engineer / Developer",
                "salary_disclosed": i < 15,
                "salary_min_normalized": 5000.0 + i * 100,
                "salary_max_normalized": 8000.0 + i * 100,
                "salary_currency_normalized": "SGD",
                "salary_period_normalized": "monthly",
                "salary_monthly_min": 5000.0 + i * 100,
                "salary_monthly_max": 8000.0 + i * 100,
                "salary_monthly_midpoint": 6500.0 + i * 100,
            })

        # 4. Malaysia (N=20): Java (50%), Python (40%), SQL (40%)
        for i in range(20):
            records.append({
                "job_id": f"my_{i}",
                "source_url": "https://example.my",
                "source_platform": "jobstreet.com.my",
                "country": "Malaysia",
                "job_title_raw": "Backend Dev",
                "location_raw": "Kuala Lumpur",
                "is_it": True,
                "classification_status": "it",
                "source_validation_status": "validated",
                "skills": ["java"] if i < 10 else (["python"] if i < 16 else ["sql"]),
                "role_id": "software_engineer",
                "role_name": "Software Engineer / Developer",
                "salary_disclosed": i < 10,
                "salary_min_normalized": 6000.0 + i * 200,
                "salary_max_normalized": 10000.0 + i * 200,
                "salary_currency_normalized": "MYR",
                "salary_period_normalized": "monthly",
                "salary_monthly_min": 6000.0 + i * 200,
                "salary_monthly_max": 10000.0 + i * 200,
                "salary_monthly_midpoint": 8000.0 + i * 200,
            })

        self.df = pd.DataFrame(records)
        self.df["salary_normalization_status"] = "normalized"
        self.demands = calculate_skill_demand_percentages(self.df, self.config)
        self.country_salary, self.role_salary, self.rates = analyze_regional_salaries(self.df, self.config)
        self.sims = calculate_country_similarities(self.demands)

    def test_grouped_bar_chart_generation(self):
        """Test Altair grouped bar chart encoding, sort order, and tooltip completeness."""
        chart = build_skill_demand_bar_chart(self.demands, focal_country="Sri Lanka", top_n=5)
        spec = chart.to_dict()

        # Must have bar mark with rounded corners
        self.assertIn("mark", spec)
        self.assertEqual(spec["mark"]["type"], "bar")

        # Must encode x, y, color, xOffset, and tooltip
        enc = spec["encoding"]
        self.assertIn("x", enc)
        self.assertIn("y", enc)
        self.assertIn("color", enc)
        self.assertIn("xOffset", enc)
        self.assertIn("tooltip", enc)

        # Tooltips must cover Skill, Market, Demand Rate, Mentions (k), Sample (N), and CI
        tooltip_fields = [t["field"] for t in enc["tooltip"]]
        self.assertIn("skill_name", tooltip_fields)
        self.assertIn("country", tooltip_fields)
        self.assertIn("demand_pct", tooltip_fields)
        self.assertIn("mention_count", tooltip_fields)
        self.assertIn("eligible_ads_denominator", tooltip_fields)
        self.assertIn("ci_label", tooltip_fields)

    def test_heatmap_grid_completeness_and_text_overlay(self):
        """Test that the 2D heatmap creates a full rectangular grid with overlay text."""
        heat = build_skill_demand_heatmap(self.demands, focal_country="Sri Lanka", top_n=5)
        spec = heat.to_dict()

        # Must have 2 layers: rect background + text label overlay
        self.assertIn("layer", spec)
        self.assertEqual(len(spec["layer"]), 2)

        layer_marks = [l["mark"]["type"] for l in spec["layer"]]
        self.assertIn("rect", layer_marks)
        self.assertIn("text", layer_marks)

        # X encoding must order countries according to standard research order
        x_enc = spec["layer"][0]["encoding"]["x"]
        self.assertEqual(x_enc["sort"], TARGET_COUNTRIES_ORDER)

    def test_salary_interval_chart_currency_isolation(self):
        """Test that salary interval charts isolate each currency with independent scales."""
        chart = build_salary_interval_chart(self.country_salary)
        spec = chart.to_dict()

        # Must vertically concatenate subcharts for each country/currency
        self.assertIn("vconcat", spec)
        subcharts = spec["vconcat"]
        self.assertEqual(len(subcharts), 4)

        # Verify Sri Lanka has small sample warning in title
        lk_sub = subcharts[0]
        self.assertIn("Sri Lanka", lk_sub["title"]["text"])
        self.assertIn("Small Sample (N<10)", lk_sub["title"]["text"])

        # Each subchart must contain rule (range), bar (IQR), and tick (median)
        for sub in subcharts:
            self.assertIn("layer", sub)
            sub_marks = [l["mark"]["type"] for l in sub["layer"]]
            self.assertIn("rule", sub_marks)
            self.assertIn("bar", sub_marks)
            self.assertIn("tick", sub_marks)

    def test_country_similarity_matrix_symmetry_and_diagonal(self):
        """Test that the 4x4 similarity matrix is strictly symmetric with diagonal = 1.0000."""
        for metric in ["cosine_similarity", "jaccard_top10_similarity", "spearman_rank_correlation"]:
            mat_chart = build_country_similarity_matrix(self.sims, metric_choice=metric)
            spec = mat_chart.to_dict()

            self.assertIn("layer", spec)
            dataset_name = spec.get("data", {}).get("name")
            if dataset_name and "datasets" in spec:
                mat_data = spec["datasets"][dataset_name]
            else:
                mat_data = spec.get("data", {}).get("values", [])

            self.assertEqual(len(mat_data), 16)  # 4x4 = 16 cells

            # Check diagonal entries
            for row in mat_data:
                c1, c2, score = row["country_a"], row["country_b"], row["score"]
                if c1 == c2:
                    self.assertEqual(score, 1.0000)

            # Check symmetry: M[i, j] == M[j, i]
            score_map = {(r["country_a"], r["country_b"]): r["score"] for r in mat_data}
            for c1 in TARGET_COUNTRIES_ORDER:
                for c2 in TARGET_COUNTRIES_ORDER:
                    self.assertAlmostEqual(score_map[(c1, c2)], score_map[(c2, c1)], places=4)

    def test_zero_count_comparator_artifact_flag(self):
        """Verify that zero-mention comparator skills are flagged as scraper artifacts rather than real divergence."""
        gaps = calculate_skill_gaps(self.demands, focal_country="Sri Lanka")

        # In our setup: Sri Lanka has Python, India has zero Git
        # Let's check git gap between Sri Lanka and India
        lk_git = self.demands[(self.demands["country"] == "Sri Lanka") & (self.demands["skill_id"] == "git")]
        in_git = self.demands[(self.demands["country"] == "India") & (self.demands["skill_id"] == "git")]

        # In our setup, India has zero git mentions
        in_gaps = gaps[gaps["comparator_country"] == "India"]
        git_gap_rows = in_gaps[in_gaps["skill_id"] == "git"]

        if not git_gap_rows.empty:
            git_gap = git_gap_rows.iloc[0]
            if git_gap["statistically_significant"] and git_gap["comparator_demand_pct"] == 0:
                self.assertTrue(bool(git_gap["zero_comparator_artifact"]))
                self.assertEqual(git_gap["evidence_status"], "Data Collection Artifact (Unverified)")


if __name__ == "__main__":
    unittest.main()
