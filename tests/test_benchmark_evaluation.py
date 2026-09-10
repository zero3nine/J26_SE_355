"""
Unit and integration tests for the Information Extraction Benchmark Evaluation Framework.
Academic Research Component for Regional Comparative IT Labor-Market Analysis.

Tests:
- Valid and invalid benchmark records.
- Missing expected values.
- Ambiguous reference labels.
- Duplicate benchmark IDs.
- Missing predictions.
- Extra predictions.
- Incorrect field values.
- Deterministic output.
- Prevention of accidental benchmark modification.
- Local fixtures and synthetic test records (no live portals).
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from src.evaluation.schema import (
    BenchmarkRecord,
    ALLOWED_STATUSES,
    ALLOWED_COUNTRIES,
    validate_benchmark_records,
    load_benchmark_dataset,
    BENCHMARK_SCHEMA_COLUMNS,
)
from src.evaluation.comparator import (
    compare_single_record,
    compare_records,
    normalize_text_for_comparison,
    normalize_company_name,
    normalize_date_to_iso,
)
from src.evaluation.metrics import compute_evaluation_metrics
from src.evaluation.evaluate_scraping import main as cli_main


class TestBenchmarkSchemaValidation(unittest.TestCase):
    """Tests for benchmark record schema constraints and validation rules."""

    def _create_minimal_record(self, **kwargs) -> BenchmarkRecord:
        base = {
            "benchmark_id": "BM-LK-TEST-001",
            "source_url": "https://itpro.lk/job/101/software-engineer",
            "source_platform": "itpro.lk",
            "country": "Sri Lanka",
            "collection_context": "unit_test_fixture",
            "extraction_method": "jsonld",
            "expected_job_title_raw": "Senior Software Engineer",
            "expected_company_raw": "Virtusa",
            "expected_location_raw": "Colombo, Sri Lanka",
            "expected_country_normalized": "Sri Lanka",
            "expected_city_normalized": "Colombo",
            "expected_work_mode": "hybrid",
            "status_job_title": "verified",
            "status_company": "verified",
            "status_location": "verified",
            "status_work_mode": "verified",
            "status_posted_date": "verified",
            "status_closing_date": "unavailable",
            "status_description": "verified",
            "status_salary": "verified",
            "status_skills": "not_reviewed",
            "verification_timestamp": "2026-10-20T10:00:00Z",
            "verified_by": "test_auditor",
        }
        base.update(kwargs)
        return BenchmarkRecord(**base)

    def test_valid_benchmark_records(self):
        """Verify valid records pass schema validation."""
        rec = self._create_minimal_record()
        errors = validate_benchmark_records([rec])
        self.assertEqual(len(errors), 0, f"Expected 0 errors, got: {errors}")

    def test_invalid_benchmark_missing_id(self):
        """Verify missing benchmark_id triggers validation failure."""
        rec = self._create_minimal_record(benchmark_id="")
        errors = validate_benchmark_records([rec])
        self.assertTrue(any("benchmark_id" in e for e in errors))

    def test_invalid_benchmark_malformed_url(self):
        """Verify malformed URL triggers validation error."""
        rec = self._create_minimal_record(source_url="not_a_valid_url")
        errors = validate_benchmark_records([rec])
        self.assertTrue(any("Invalid URL format" in e for e in errors))

    def test_invalid_benchmark_unsupported_country(self):
        """Verify unsupported country name is rejected."""
        rec = self._create_minimal_record(country="Narnia")
        errors = validate_benchmark_records([rec])
        self.assertTrue(any("Invalid country" in e for e in errors))

    def test_invalid_benchmark_unknown_status(self):
        """Verify non-standard verification status is strictly rejected."""
        rec = self._create_minimal_record(status_job_title="semi_verified")
        errors = validate_benchmark_records([rec])
        self.assertTrue(any("status_job_title" in e for e in errors))

    def test_duplicate_benchmark_ids(self):
        """Verify duplicate benchmark_id values are detected and flagged."""
        rec1 = self._create_minimal_record(benchmark_id="BM-DUPLICATE-ID")
        rec2 = self._create_minimal_record(benchmark_id="BM-DUPLICATE-ID")
        errors = validate_benchmark_records([rec1, rec2])
        self.assertTrue(any("Duplicate benchmark_id" in e for e in errors))


class TestComparatorFieldEvaluation(unittest.TestCase):
    """Tests for field-by-field evaluation and normalization rules."""

    def test_missing_expected_values_correct_absence(self):
        """When source field is unavailable and prediction is empty, count as correct_absence."""
        bm = BenchmarkRecord(
            benchmark_id="BM-TEST-001",
            source_url="https://example.com/ad/1",
            source_platform="example.com",
            country="Singapore",
            status_salary="unavailable",
            expected_salary_disclosed=False,
            status_closing_date="unavailable",
            expected_closing_date=""
        )
        # Prediction correctly left salary and closing date empty
        pred = {
            "source_url": "https://example.com/ad/1",
            "salary_disclosed": "False",
            "salary_min_raw": "",
            "salary_text_raw": "",
            "closing_date_raw": ""
        }
        res = compare_single_record(bm, pred)
        self.assertEqual(res.field_results["salary"].status, "correct_absence")
        self.assertEqual(res.field_results["closing_date"].status, "correct_absence")

    def test_missing_expected_values_over_extraction(self):
        """When source field is unavailable but prediction hallucinates a value, flag as over_extracted."""
        bm = BenchmarkRecord(
            benchmark_id="BM-TEST-002",
            source_url="https://example.com/ad/2",
            source_platform="example.com",
            country="Sri Lanka",
            status_salary="unavailable",
            expected_salary_disclosed=False,
            status_closing_date="unavailable",
            expected_closing_date=""
        )
        # Prediction falsely claims disclosed salary and closing date
        pred = {
            "source_url": "https://example.com/ad/2",
            "salary_disclosed": "True",
            "salary_min_raw": "100000",
            "closing_date_raw": "2026-12-31"
        }
        res = compare_single_record(bm, pred)
        self.assertEqual(res.field_results["salary"].status, "over_extracted")
        self.assertEqual(res.field_results["closing_date"].status, "over_extracted")

    def test_ambiguous_reference_labels_excluded_from_strict_metrics(self):
        """Ambiguous reference fields must be excluded from strict accuracy denominators."""
        bm = BenchmarkRecord(
            benchmark_id="BM-TEST-003",
            source_url="https://example.com/ad/3",
            source_platform="example.com",
            country="India",
            status_location="ambiguous",
            expected_location_raw="All India / Remote / APAC",
            status_job_title="verified",
            expected_job_title_raw="Data Scientist"
        )
        pred = {
            "source_url": "https://example.com/ad/3",
            "job_title_raw": "Data Scientist",
            "location_raw": "Bangalore"
        }
        res = compare_single_record(bm, pred)
        self.assertEqual(res.field_results["location_raw"].status, "ambiguous_excluded")
        self.assertEqual(res.field_results["job_title"].status, "correct")

        # Check metrics computation excludes ambiguous from verified count
        metrics = compute_evaluation_metrics([res], 1, 1, 0, 0)
        self.assertEqual(metrics.field_metrics["location_raw"].ambiguous_total, 1)
        self.assertEqual(metrics.field_metrics["location_raw"].verified_total, 0)

    def test_missing_predictions(self):
        """When benchmark record has no prediction, verified fields are marked missing_prediction."""
        bm = BenchmarkRecord(
            benchmark_id="BM-TEST-004",
            source_url="https://example.com/ad/4",
            source_platform="example.com",
            country="Singapore",
            status_job_title="verified",
            expected_job_title_raw="Cloud Architect",
            status_salary="unavailable"
        )
        # No matching predictions provided
        results, unmatched_bm, extra = compare_records([bm], [])
        self.assertEqual(len(unmatched_bm), 1)
        self.assertEqual(results[0].field_results["job_title"].status, "missing_prediction")
        self.assertEqual(results[0].field_results["salary"].status, "correct_absence")

    def test_extra_predictions(self):
        """Extra predictions not in benchmark must be recorded without corrupting metrics."""
        bm = BenchmarkRecord(
            benchmark_id="BM-TEST-005",
            source_url="https://example.com/ad/5",
            source_platform="example.com",
            country="Malaysia",
            status_job_title="verified",
            expected_job_title_raw="DevOps Engineer"
        )
        preds = [
            {"source_url": "https://example.com/ad/5", "job_title_raw": "DevOps Engineer"},
            {"source_url": "https://example.com/ad/999_extra", "job_title_raw": "Spam Ad"}
        ]
        results, unmatched_bm, extra = compare_records([bm], preds)
        self.assertEqual(len(extra), 1)
        self.assertEqual(extra[0]["source_url"], "https://example.com/ad/999_extra")
        self.assertEqual(results[0].field_results["job_title"].status, "correct")

    def test_incorrect_field_values_detected(self):
        """Incorrect values in title, company, salary are identified with diff details."""
        bm = BenchmarkRecord(
            benchmark_id="BM-TEST-006",
            source_url="https://example.com/ad/6",
            source_platform="example.com",
            country="Malaysia",
            status_job_title="verified",
            expected_job_title_raw="Backend Developer",
            status_company="verified",
            expected_company_raw="Fintech Berhad",
            status_salary="verified",
            expected_salary_disclosed=True,
            expected_salary_min=8000.0,
            expected_salary_max=12000.0,
            expected_salary_currency="MYR",
            expected_salary_period="monthly"
        )
        pred = {
            "source_url": "https://example.com/ad/6",
            "job_title_raw": "Frontend Developer",  # Wrong title
            "company_raw": "Travel Agency",         # Wrong company
            "salary_disclosed": "True",
            "salary_min_normalized": "4000",        # Wrong salary
            "salary_max_normalized": "6000",
            "salary_currency_normalized": "MYR",
            "salary_period_normalized": "monthly"
        }
        res = compare_single_record(bm, pred)
        self.assertEqual(res.field_results["job_title"].status, "incorrect")
        self.assertEqual(res.field_results["company"].status, "incorrect")
        self.assertEqual(res.field_results["salary"].status, "incorrect")
        self.assertIn("min 4000.0 != 8000.0", res.field_results["salary"].details)

    def test_field_normalization_rules(self):
        """Verify case, corporate suffix, and date normalization rules."""
        # 1. Company corporate suffix removal
        c1 = normalize_company_name("Virtusa Private Limited")
        c2 = normalize_company_name("virtusa pvt ltd")
        self.assertEqual(c1, c2)

        # 2. Date ISO normalization
        d1 = normalize_date_to_iso("2026-10-19T19:43:20+05:30")
        d2 = normalize_date_to_iso("2026-10-19")
        self.assertEqual(d1, "2026-10-19")
        self.assertEqual(d2, "2026-10-19")

        # 3. Text whitespace and case normalization
        t1 = normalize_text_for_comparison("Senior   Software\nEngineer ")
        t2 = normalize_text_for_comparison("senior software engineer")
        self.assertEqual(t1, t2)


class TestEvaluationPipelineIntegrity(unittest.TestCase):
    """Tests for deterministic execution and prevention of benchmark modification."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.bm_path = Path(self.temp_dir.name) / "benchmark.csv"
        self.pred_path = Path(self.temp_dir.name) / "predictions.csv"
        self.out_dir = Path(self.temp_dir.name) / "results"

        # Create valid synthetic benchmark CSV
        records = [
            BenchmarkRecord(
                benchmark_id="BM-FIXTURE-001",
                source_url="https://example.com/job/1",
                source_platform="example.com",
                country="Sri Lanka",
                status_job_title="verified",
                expected_job_title_raw="Software Engineer",
                status_company="verified",
                expected_company_raw="Tech Corp",
                status_location="verified",
                expected_location_raw="Colombo",
                expected_country_normalized="Sri Lanka",
                expected_city_normalized="Colombo",
                expected_work_mode="on_site",
                status_work_mode="verified",
                status_posted_date="verified",
                expected_posted_date="2026-10-19",
                status_closing_date="unavailable",
                status_description="verified",
                expected_description_snippet="Full stack development",
                expected_description_min_len=20,
                status_salary="verified",
                expected_salary_disclosed=False,
                status_skills="not_reviewed",
            )
        ]
        with open(self.bm_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=BENCHMARK_SCHEMA_COLUMNS)
            writer.writeheader()
            for r in records:
                writer.writerow(r.to_dict())

        # Create matching predictions CSV
        with open(self.pred_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "job_id", "source_url", "job_title_raw", "company_raw",
                "location_raw", "country_normalized", "city_normalized",
                "work_mode", "posted_date_raw", "job_description_raw",
                "salary_disclosed"
            ])
            writer.writeheader()
            writer.writerow({
                "job_id": "job_1",
                "source_url": "https://example.com/job/1",
                "job_title_raw": "Software Engineer",
                "company_raw": "Tech Corp",
                "location_raw": "Colombo",
                "country_normalized": "Sri Lanka",
                "city_normalized": "Colombo",
                "work_mode": "on_site",
                "posted_date_raw": "2026-10-19",
                "job_description_raw": "Full stack development in Python and React",
                "salary_disclosed": "False"
            })

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_deterministic_output(self):
        """Verify identical inputs yield identical metrics across multiple runs."""
        bms = load_benchmark_dataset(self.bm_path)
        with open(self.pred_path, "r", encoding="utf-8") as f:
            preds = list(csv.DictReader(f))

        res1, unmatched1, extra1 = compare_records(bms, preds)
        m1 = compute_evaluation_metrics(res1, len(bms), len(preds), len(unmatched1), len(extra1), "2026-10-20T10:00:00Z")

        res2, unmatched2, extra2 = compare_records(bms, preds)
        m2 = compute_evaluation_metrics(res2, len(bms), len(preds), len(unmatched2), len(extra2), "2026-10-20T10:00:00Z")

        self.assertEqual(m1.exact_match_rate, m2.exact_match_rate)
        self.assertEqual(m1.macro_f1, m2.macro_f1)
        self.assertEqual(m1.to_dict(), m2.to_dict())

    def test_prevention_of_accidental_benchmark_modification(self):
        """Verify evaluation never alters benchmark file content or checksum."""
        # Calculate SHA-256 before evaluation
        with open(self.bm_path, "rb") as f:
            hash_before = hashlib.sha256(f.read()).hexdigest()

        # Run evaluation via CLI
        code = cli_main([
            "--benchmark", str(self.bm_path),
            "--predictions", str(self.pred_path),
            "--output-dir", str(self.out_dir),
            "--quiet"
        ])
        self.assertEqual(code, 0)

        # Calculate SHA-256 after evaluation
        with open(self.bm_path, "rb") as f:
            hash_after = hashlib.sha256(f.read()).hexdigest()

        self.assertEqual(hash_before, hash_after, "Benchmark file was mutated during evaluation!")

    def test_cli_prevents_evaluating_benchmark_against_itself(self):
        """CLI must reject passing benchmark path as predictions."""
        code = cli_main([
            "--benchmark", str(self.bm_path),
            "--predictions", str(self.bm_path),  # Illegal self-evaluation
            "--output-dir", str(self.out_dir),
            "--quiet"
        ])
        self.assertEqual(code, 1)

    def test_cli_zero_matches_returns_exit_code_two(self):
        """CLI returns exit code 2 when zero benchmark records match predictions."""
        # Create non-matching predictions file
        mismatch_pred = Path(self.temp_dir.name) / "mismatch.csv"
        with open(mismatch_pred, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["source_url", "job_title_raw"])
            writer.writeheader()
            writer.writerow({"source_url": "https://unrelated.com/job/999", "job_title_raw": "Unrelated"})

        code = cli_main([
            "--benchmark", str(self.bm_path),
            "--predictions", str(mismatch_pred),
            "--output-dir", str(self.out_dir),
            "--quiet"
        ])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
