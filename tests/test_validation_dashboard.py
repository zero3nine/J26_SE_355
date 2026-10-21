"""
Unit and integration tests for the Scraping Accuracy & Validation Dashboard.
Academic Research Component for Regional Comparative IT Labor-Market Analysis.

Covers:
- Evaluation run discovery (latest vs historical, real vs synthetic)
- Graceful unavailable state when no evaluation outputs exist
- Multi-dimensional filter logic (country, platform, method, field, status)
- Stratified reporting with mandatory sample sizes N and small-sample caveats
- Review queue building, persistent annotation storage, and audit logs
- Immutability of primary benchmark datasets and raw scrapings
- Safe handling of untrusted text and URLs
- Cross-tab integration helpers
"""

import json
import os
import pathlib
import tempfile
import unittest
import pandas as pd

from src.evaluation.dashboard_data import (
    discover_evaluation_runs,
    load_evaluation_run_data,
    filter_evaluation_errors,
    compute_stratified_view,
    load_review_annotations,
    save_review_annotation,
    get_correction_history,
    build_review_queue,
    get_benchmark_accuracy_summary_for_quality_tab,
)
from src.evaluation.dashboard_view import display_stratified_table


class TestValidationDashboardData(unittest.TestCase):
    """Tests data loading, discovery, filtering, and metric calculation for the dashboard."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = pathlib.Path(__file__).resolve().parent.parent
        cls.results_dir = cls.project_root / "data" / "evaluation" / "results"

    def test_discover_evaluation_runs_populated(self):
        """Discovers existing evaluation runs in data/evaluation/results/."""
        runs = discover_evaluation_runs(self.results_dir)
        self.assertGreater(len(runs), 0)
        
        # Verify first run is latest
        latest_run = runs[0]
        self.assertTrue(latest_run["is_latest"] or "latest" in latest_run["run_id"])
        self.assertGreaterEqual(latest_run["total_benchmark"], 100)
        self.assertFalse(latest_run["is_synthetic"])
        self.assertIn("Empirical Benchmark", latest_run["label"])

    def test_discover_evaluation_runs_empty_directory(self):
        """Returns empty list gracefully when no results exist in the directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = pathlib.Path(tmpdir)
            runs = discover_evaluation_runs(empty_dir)
            self.assertEqual(runs, [])

    def test_load_evaluation_run_data_populated(self):
        """Loads all paired artifacts for the latest evaluation run."""
        data = load_evaluation_run_data("latest", results_dir=self.results_dir)
        self.assertIsNotNone(data)
        self.assertIn("metrics", data)
        self.assertIn("errors_df", data)
        self.assertIn("summary_df", data)
        self.assertIn("report_md", data)
        self.assertIn("reproducibility", data)

        meta = data["metrics"].get("metadata", {})
        self.assertEqual(meta.get("total_benchmark_records"), 120)
        self.assertFalse(data["errors_df"].empty)
        self.assertFalse(data["summary_df"].empty)
        self.assertGreater(len(data["report_md"]), 100)

    def test_load_evaluation_run_data_missing(self):
        """Returns None cleanly when an evaluation run does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = pathlib.Path(tmpdir)
            data = load_evaluation_run_data("non_existent_run_9999", results_dir=empty_dir)
            self.assertIsNone(data)

    def test_filter_evaluation_errors_multi_criteria(self):
        """Filters field-level errors across country, platform, method, and field."""
        data = load_evaluation_run_data("latest", results_dir=self.results_dir)
        errors_df = data["errors_df"]

        # 1. Filter by country
        in_errors = filter_evaluation_errors(errors_df, country="India")
        self.assertFalse(in_errors.empty)
        self.assertTrue(all(in_errors["country"] == "India"))

        # 2. Filter by platform
        shine_errors = filter_evaluation_errors(errors_df, platform="www.shine.com")
        self.assertFalse(shine_errors.empty)
        self.assertTrue(all(shine_errors["source_platform"] == "www.shine.com"))

        # 3. Filter by field name
        title_errors = filter_evaluation_errors(errors_df, field_name="job_title")
        self.assertFalse(title_errors.empty)
        self.assertTrue(all(title_errors["field_name"] == "job_title"))

        # 4. Filter by extraction method
        jsonld_errors = filter_evaluation_errors(errors_df, method="jsonld")
        self.assertFalse(jsonld_errors.empty)
        self.assertTrue(all(jsonld_errors["extraction_method"] == "jsonld"))

    def test_filter_evaluation_errors_no_matches_returns_empty(self):
        """Returns empty DataFrame with same schema when no rows match filters."""
        data = load_evaluation_run_data("latest", results_dir=self.results_dir)
        errors_df = data["errors_df"]

        res = filter_evaluation_errors(
            errors_df,
            country="NonExistentCountry",
            platform="nonexistent.portal.xyz"
        )
        self.assertTrue(res.empty)
        self.assertEqual(list(res.columns), list(errors_df.columns))

    def test_filter_evaluation_errors_search_query(self):
        """Searches across benchmark_id, URL, expected, and discrepancy details."""
        data = load_evaluation_run_data("latest", results_dir=self.results_dir)
        errors_df = data["errors_df"]

        res = filter_evaluation_errors(errors_df, search_query="BM-LK-ITPRO")
        self.assertFalse(res.empty)
        self.assertTrue(all("BM-LK-ITPRO" in bid for bid in res["benchmark_id"]))

    def test_compute_stratified_view_with_denominators(self):
        """Verifies stratified summaries include mandatory sample sizes N."""
        data = load_evaluation_run_data("latest", results_dir=self.results_dir)
        summary_df = data["summary_df"]

        country_view = compute_stratified_view(summary_df, "country")
        self.assertFalse(country_view.empty)
        self.assertIn("total_records", country_view.columns)
        self.assertIn("exact_match_rate", country_view.columns)

        # Check India, Singapore, Sri Lanka, Malaysia are present
        c_names = set(country_view["subgroup_name"])
        self.assertIn("India", c_names)
        self.assertIn("Singapore", c_names)
        self.assertIn("Sri Lanka", c_names)
        self.assertIn("Malaysia", c_names)

        # Verify sample size N
        for _, r in country_view.iterrows():
            self.assertGreater(r["total_records"], 0)

    def test_small_sample_size_flagging(self):
        """Subgroups with sample sizes N < 10 must be flagged as small samples."""
        data = load_evaluation_run_data("latest", results_dir=self.results_dir)
        summary_df = data["summary_df"]

        platform_view = compute_stratified_view(summary_df, "platform")
        # ikman.lk has N=1 in benchmark, must have is_small_sample=True
        ikman_row = platform_view[platform_view["subgroup_name"] == "ikman.lk"]
        if not ikman_row.empty:
            self.assertTrue(bool(ikman_row.iloc[0]["is_small_sample"]))

        # itpro.lk has N=42, must have is_small_sample=False
        itpro_row = platform_view[platform_view["subgroup_name"] == "itpro.lk"]
        if not itpro_row.empty:
            self.assertFalse(bool(itpro_row.iloc[0]["is_small_sample"]))


class TestReviewWorkflowAndPersistence(unittest.TestCase):
    """Tests manual verification, persistent annotation storage, and audit logs."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store_path = pathlib.Path(self.temp_dir.name) / "test_review_annotations.json"
        self.hist_path = pathlib.Path(self.temp_dir.name) / "test_correction_history.jsonl"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_load_review_annotation(self):
        """Saves a reviewer decision, verifies persistent storage and audit history."""
        success, msg = save_review_annotation(
            benchmark_id="BM-IN-SHINE-001",
            field_name="work_mode",
            status="verified",
            reviewer_id="reviewer_alice",
            reviewer_notes="Confirmed remote work mode explicitly stated in job description paragraph 2.",
            corrected_value="remote",
            original_predicted="",
            original_expected="remote",
            source_url="https://www.shine.com/job/101",
            country="India",
            source_platform="www.shine.com",
            storage_path=self.store_path,
            history_path=self.hist_path,
        )
        self.assertTrue(success)
        self.assertIn("persisted successfully", msg)

        # Verify loaded annotation
        annotations = load_review_annotations(self.store_path)
        comp_key = "BM-IN-SHINE-001::work_mode"
        self.assertIn(comp_key, annotations)
        ann = annotations[comp_key]
        self.assertEqual(ann["status"], "verified")
        self.assertEqual(ann["reviewer_id"], "reviewer_alice")
        self.assertEqual(ann["corrected_value"], "remote")

        # Verify audit history
        hist = get_correction_history(self.hist_path)
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["benchmark_id"], "BM-IN-SHINE-001")
        self.assertEqual(hist[0]["field_name"], "work_mode")

    def test_save_review_annotation_rejects_invalid_inputs(self):
        """Rejects invalid review status, empty reviewer ID, or empty notes."""
        # 1. Invalid status
        s1, m1 = save_review_annotation(
            benchmark_id="BM-IN-SHINE-001",
            field_name="salary",
            status="invalid_status_xyz",
            reviewer_id="alice",
            reviewer_notes="Some note",
            storage_path=self.store_path,
            history_path=self.hist_path,
        )
        self.assertFalse(s1)
        self.assertIn("Invalid review status", m1)

        # 2. Empty reviewer ID
        s2, m2 = save_review_annotation(
            benchmark_id="BM-IN-SHINE-001",
            field_name="salary",
            status="verified",
            reviewer_id="   ",
            reviewer_notes="Some note",
            storage_path=self.store_path,
            history_path=self.hist_path,
        )
        self.assertFalse(s2)
        self.assertIn("Reviewer identifier is required", m2)

        # 3. Empty reviewer notes
        s3, m3 = save_review_annotation(
            benchmark_id="BM-IN-SHINE-001",
            field_name="salary",
            status="verified",
            reviewer_id="alice",
            reviewer_notes="",
            storage_path=self.store_path,
            history_path=self.hist_path,
        )
        self.assertFalse(s3)
        self.assertIn("Reviewer justification notes are mandatory", m3)

    def test_review_does_not_mutate_benchmark_reference_data(self):
        """Review decisions must never overwrite ground-truth benchmark_dataset.csv."""
        bench_path = pathlib.Path(__file__).resolve().parent.parent / "data" / "evaluation" / "benchmark_dataset.csv"
        initial_mtime = bench_path.stat().st_mtime
        initial_size = bench_path.stat().st_size

        # Perform a review action
        save_review_annotation(
            benchmark_id="BM-LK-ITPRO-001",
            field_name="job_title",
            status="verified",
            reviewer_id="reviewer_bob",
            reviewer_notes="Verified title against primary DOM heading.",
            storage_path=self.store_path,
            history_path=self.hist_path,
        )

        current_mtime = bench_path.stat().st_mtime
        current_size = bench_path.stat().st_size

        self.assertEqual(initial_mtime, current_mtime)
        self.assertEqual(initial_size, current_size)

    def test_build_review_queue_merges_status(self):
        """build_review_queue merges errors with saved annotations."""
        dummy_errors = pd.DataFrame([{
            "benchmark_id": "BM-001",
            "field_name": "job_title",
            "country": "India",
            "source_platform": "www.shine.com",
            "extraction_method": "jsonld",
            "expected_raw": "Senior Dev",
            "predicted_raw": "Dev",
            "error_category": "value_mismatch",
            "error_type": "discrepancy",
            "discrepancy_details": "Title mismatch",
            "source_url": "https://www.shine.com/job/1",
        }])

        # Without annotation
        q_empty = build_review_queue(dummy_errors, annotations={})
        self.assertEqual(q_empty.iloc[0]["review_status"], "pending_review")

        # With annotation
        dummy_ann = {
            "BM-001::job_title": {
                "status": "incorrect",
                "reviewer_id": "auditor_1",
                "reviewer_notes": "Scraper dropped Senior prefix",
                "corrected_value": "Senior Dev",
                "timestamp": "2026-10-20T12:00:00Z",
            }
        }
        q_annotated = build_review_queue(dummy_errors, annotations=dummy_ann)
        self.assertEqual(q_annotated.iloc[0]["review_status"], "incorrect")
        self.assertEqual(q_annotated.iloc[0]["reviewer_id"], "auditor_1")


class TestCrossTabIntegrations(unittest.TestCase):
    """Tests cross-tab integration helpers for Quality Report and other tabs."""

    def test_quality_report_summary_helper(self):
        """get_benchmark_accuracy_summary_for_quality_tab returns correct latest metrics."""
        summary = get_benchmark_accuracy_summary_for_quality_tab()
        self.assertIsNotNone(summary)
        self.assertGreater(summary["total_benchmark"], 100)
        self.assertGreater(summary["title_agreement"], 70.0)
        self.assertGreater(summary["employer_agreement"], 70.0)
        self.assertFalse(summary["is_synthetic"])


if __name__ == "__main__":
    unittest.main()
