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
    evaluate_numeric_salary_amount,
    evaluate_multi_label_skills,
)
from src.evaluation.metrics import (
    compute_evaluation_metrics,
    wilson_score_interval,
    FieldMetricSummary,
)
from src.evaluation.reporter import export_field_errors_csv
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


class TestCurrencyAndPayPeriodIncompatibility(unittest.TestCase):
    """Tests for salary currency & pay-period compatibility checks and numeric MAE metrics."""

    def test_incompatible_currency_flags_error_and_excludes_numeric_mae(self):
        """Comparing amounts with incompatible currencies must be flagged and excluded from MAE."""
        # Expected SGD 8000, predicted MYR 8000
        res = evaluate_numeric_salary_amount(
            field_name="salary_min",
            reference_status="verified",
            expected_amount=8000.0,
            predicted_raw="8000",
            expected_curr="SGD",
            predicted_curr="MYR",
            expected_period="monthly",
            predicted_period="monthly",
        )
        self.assertEqual(res.status, "incompatible_currency")
        self.assertEqual(res.error_category, "incompatible_currency")
        self.assertIsNone(res.numeric_error)

    def test_incompatible_pay_period_flags_error_and_excludes_numeric_mae(self):
        """Comparing amounts with incompatible pay periods must be flagged and excluded from MAE."""
        # Expected monthly 5000, predicted hourly 5000
        res = evaluate_numeric_salary_amount(
            field_name="salary_min",
            reference_status="verified",
            expected_amount=5000.0,
            predicted_raw="5000",
            expected_curr="USD",
            predicted_curr="USD",
            expected_period="monthly",
            predicted_period="hourly",
        )
        self.assertEqual(res.status, "incompatible_pay_period")
        self.assertEqual(res.error_category, "incompatible_pay_period")
        self.assertIsNone(res.numeric_error)

    def test_compatible_amounts_compute_numeric_mae_and_exclusions(self):
        """Compatible currency and period computes absolute numeric error accurately."""
        # 1 compatible correct (within tolerance)
        r1 = evaluate_numeric_salary_amount("salary_min", "verified", 5000.0, "5000", "USD", "USD", "monthly", "monthly")
        self.assertEqual(r1.status, "correct")
        self.assertEqual(r1.numeric_error, 0.0)

        # 1 compatible incorrect with absolute error 200.0
        r2 = evaluate_numeric_salary_amount("salary_min", "verified", 5000.0, "5200", "USD", "USD", "monthly", "monthly")
        self.assertEqual(r2.status, "incorrect")
        self.assertEqual(r2.numeric_error, 200.0)

        # Build records and aggregate
        bm1 = BenchmarkRecord(
            benchmark_id="BM-SAL-01", source_url="https://example.com/1", source_platform="ex.com",
            country="Singapore", status_salary="verified", expected_salary_min=5000.0,
            expected_salary_currency="USD", expected_salary_period="monthly"
        )
        bm2 = BenchmarkRecord(
            benchmark_id="BM-SAL-02", source_url="https://example.com/2", source_platform="ex.com",
            country="Singapore", status_salary="verified", expected_salary_min=5000.0,
            expected_salary_currency="USD", expected_salary_period="monthly"
        )
        bm3 = BenchmarkRecord(
            benchmark_id="BM-SAL-03", source_url="https://example.com/3", source_platform="ex.com",
            country="Singapore", status_salary="verified", expected_salary_min=5000.0,
            expected_salary_currency="SGD", expected_salary_period="monthly"
        )

        p1 = {"source_url": "https://example.com/1", "salary_min_normalized": "5000", "salary_currency_normalized": "USD", "salary_period_normalized": "monthly"}
        p2 = {"source_url": "https://example.com/2", "salary_min_normalized": "5200", "salary_currency_normalized": "USD", "salary_period_normalized": "monthly"}
        p3 = {"source_url": "https://example.com/3", "salary_min_normalized": "5000", "salary_currency_normalized": "INR", "salary_period_normalized": "monthly"}

        results, _, _ = compare_records([bm1, bm2, bm3], [p1, p2, p3])
        metrics = compute_evaluation_metrics(results, 3, 3, 0, 0)

        sal_min_metrics = metrics.field_metrics["salary_min"]
        self.assertEqual(sal_min_metrics.eligible_references, 3)
        self.assertEqual(sal_min_metrics.comparable_count, 2)
        self.assertEqual(sal_min_metrics.excluded_incompatible_count, 1)
        self.assertEqual(sal_min_metrics.mae, 100.0)  # (0.0 + 200.0) / 2 = 100.0


class TestMultiLabelSkillsEvaluation(unittest.TestCase):
    """Tests for multi-label canonical skill extraction: micro, macro, and per-label."""

    def test_multi_label_skills_micro_and_macro_calculation(self):
        """Micro and macro metrics correctly distinguish overall token vs label-balanced precision/recall."""
        bm1 = BenchmarkRecord(
            benchmark_id="BM-SK-01", source_url="https://example.com/s1", source_platform="ex.com",
            country="Singapore", status_skills="verified", expected_skills="Python, SQL, AWS"
        )
        bm2 = BenchmarkRecord(
            benchmark_id="BM-SK-02", source_url="https://example.com/s2", source_platform="ex.com",
            country="Singapore", status_skills="verified", expected_skills="Python, Docker"
        )

        # Ad 1 predicted: Python, SQL (missed AWS) -> TP=2, FP=0, FN=1
        # Ad 2 predicted: Python, Docker, React (extra React) -> TP=2, FP=1, FN=0
        p1 = {"source_url": "https://example.com/s1", "skills_raw": "Python, SQL"}
        p2 = {"source_url": "https://example.com/s2", "skills_raw": "Python, Docker, React"}

        results, _, _ = compare_records([bm1, bm2], [p1, p2])
        metrics = compute_evaluation_metrics(results, 2, 2, 0, 0)
        sk = metrics.skill_metrics

        self.assertIsNotNone(sk)
        self.assertEqual(sk.ads_with_verified_skills, 2)
        # Total TP = 4, Total FP = 1, Total FN = 1
        # Micro P = 4 / (4 + 1) = 0.80, Micro R = 4 / (4 + 1) = 0.80
        self.assertEqual(sk.micro_precision, 0.8)
        self.assertEqual(sk.micro_recall, 0.8)
        self.assertEqual(sk.micro_f1, 0.8)

        # Check per-label support
        self.assertIn("python", sk.per_label_metrics)
        self.assertEqual(sk.per_label_metrics["python"]["support"], 2)
        self.assertEqual(sk.per_label_metrics["python"]["precision"], 1.0)
        self.assertEqual(sk.per_label_metrics["python"]["recall"], 1.0)


class TestCoverageVsCorrectnessSeparation(unittest.TestCase):
    """Tests establishing that coverage (completeness) and correctness (precision) are decoupled."""

    def test_low_coverage_high_correctness_does_not_appear_reliable(self):
        """A scraper extracting only 1 field correctly must not show high overall reliability."""
        bm = BenchmarkRecord(
            benchmark_id="BM-COV-01", source_url="https://example.com/cov", source_platform="ex.com",
            country="Sri Lanka",
            status_job_title="verified", expected_job_title_raw="Data Engineer",
            status_company="verified", expected_company_raw="SysCorp",
            status_location="verified", expected_location_raw="Colombo",
            status_posted_date="verified", expected_posted_date="2026-10-15",
        )
        # Prediction only captured job_title, left all others completely missing
        pred = {
            "source_url": "https://example.com/cov",
            "job_title_raw": "Data Engineer",
            "company_raw": "",
            "location_raw": "",
            "posted_date_raw": ""
        }

        results, _, _ = compare_records([bm], [pred])
        metrics = compute_evaluation_metrics(results, 1, 1, 0, 0)

        # Job title: 100% coverage, 100% correctness
        jt = metrics.field_metrics["job_title"]
        self.assertEqual(jt.extraction_coverage, 1.0)
        self.assertEqual(jt.extraction_correctness, 1.0)

        # Company: 0% coverage, 0% correctness
        cmp = metrics.field_metrics["company"]
        self.assertEqual(cmp.extraction_coverage, 0.0)
        self.assertEqual(cmp.extraction_correctness, 0.0)
        self.assertEqual(cmp.missing_predictions, 1)


class TestZeroDenominatorAndEmptySubsets(unittest.TestCase):
    """Tests verifying robust zero-denominator handling and edge conditions."""

    def test_wilson_score_interval_zero_trials(self):
        """Wilson interval returns (0.0, 0.0) for zero trials without division error."""
        lo, hi = wilson_score_interval(0, 0)
        self.assertEqual((lo, hi), (0.0, 0.0))

    def test_field_summary_zero_eligible_references(self):
        """Field with zero verified references produces zeroed rates without throwing exceptions."""
        s = FieldMetricSummary(field_name="niche_field")
        s.compute_statistics()
        self.assertEqual(s.exact_agreement_rate, 0.0)
        self.assertEqual(s.normalized_agreement_rate, 0.0)
        self.assertEqual(s.extraction_coverage, 0.0)
        self.assertEqual(s.extraction_correctness, 0.0)
        self.assertEqual(s.precision, 0.0)
        self.assertEqual(s.recall, 0.0)
        self.assertEqual(s.f1_score, 0.0)

    def test_empty_results_metrics_computation(self):
        """Metrics aggregator handles empty result lists without crashing."""
        metrics = compute_evaluation_metrics([], 0, 0, 0, 0)
        self.assertEqual(metrics.total_benchmark_records, 0)
        self.assertEqual(metrics.matched_records_count, 0)
        self.assertEqual(metrics.exact_match_rate, 0.0)


class TestPartialReferenceLabels(unittest.TestCase):
    """Tests for records where ground truth consists of partial reference labels."""

    def test_partial_reference_labels_handling(self):
        """Record with mixture of verified, unavailable, and not_reviewed statuses."""
        bm = BenchmarkRecord(
            benchmark_id="BM-PARTIAL-01", source_url="https://example.com/part", source_platform="ex.com",
            country="India",
            status_job_title="verified", expected_job_title_raw="QA Lead",
            status_salary="unavailable", expected_salary_disclosed=False,
            status_skills="not_reviewed"
        )
        pred = {
            "source_url": "https://example.com/part",
            "job_title_raw": "QA Lead",
            "salary_disclosed": "False",
            "skills_raw": "Java, Selenium"
        }
        res = compare_single_record(bm, pred)
        self.assertEqual(res.field_results["job_title"].status, "correct")
        self.assertEqual(res.field_results["salary"].status, "correct_absence")
        self.assertEqual(res.field_results["skills"].status, "not_reviewed")


class TestFieldLevelErrorReportGeneration(unittest.TestCase):
    """Tests generating and verifying the field-level error CSV report."""

    def test_field_errors_csv_schema_and_content(self):
        """Error CSV must identify benchmark ID, URL, country, method, field, expected, predicted, category, type."""
        bm = BenchmarkRecord(
            benchmark_id="BM-ERR-01", source_url="https://example.com/err", source_platform="ex.com",
            country="Malaysia", extraction_method="generic_html",
            status_job_title="verified", expected_job_title_raw="Lead Developer",
            status_work_mode="verified", expected_work_mode="remote"
        )
        pred = {
            "source_url": "https://example.com/err",
            "job_title_raw": "Intern",      # Incorrect
            "work_mode": ""                 # Missing
        }
        results, _, _ = compare_records([bm], [pred])
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "errors.csv"
            export_field_errors_csv(results, csv_path)
            self.assertTrue(csv_path.exists())

            with open(csv_path, "r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                self.assertGreaterEqual(len(reader), 2)
                row0 = reader[0]
                self.assertIn("benchmark_id", row0)
                self.assertIn("source_url", row0)
                self.assertIn("country", row0)
                self.assertIn("extraction_method", row0)
                self.assertIn("field_name", row0)
                self.assertIn("expected_value", row0)
                self.assertIn("predicted_value", row0)
                self.assertIn("error_category", row0)
                self.assertIn("error_type", row0)
                self.assertIn("error_status", row0)


if __name__ == "__main__":
    unittest.main()
