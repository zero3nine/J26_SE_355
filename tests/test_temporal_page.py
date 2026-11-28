"""Streamlit regression checks for temporal research controls."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.database import connection, repository


PAGE = Path(__file__).resolve().parents[1] / "pages" / "13_Temporal_Analysis.py"


class TemporalPageTests(unittest.TestCase):
    def test_empty_representation_keeps_matched_comparison_and_diagnostics(self):
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "master.sqlite3"
            jobs = pd.DataFrame([
                {"job_id": str(index), "source_url": f"https://example.com/{index}",
                 "job_title": "Software Engineer", "job_description": "Software engineering",
                 "posting_date": "2026-01-15", "country": "Sri Lanka",
                 "source_platform": "Fixture"}
                for index in range(5)
            ])
            repository.import_jobs_dataframe(jobs, source_name="Fixture", db_path=db_path)
            cohort = repository.get_master_jobs(db_path=db_path).assign(
                lexical_skills='["python"]', semantic_skills="[]",
            )
            repository.save_extraction_results(cohort, semantic_threshold=0.5, model_name="fixture", db_path=db_path)

            with patch.object(connection, "DB_PATH", db_path):
                page = AppTest.from_file(str(PAGE)).run()
                representation = next(item for item in page.selectbox if item.label == "Skill representation")
                representation.select("semantic").run()

            self.assertFalse(page.exception)
            metrics = {item.label: item.value for item in page.metric}
            self.assertEqual(metrics.get("Top-10 Jaccard overlap"), "0.0%")
            self.assertEqual(metrics.get("Trend classification agreement"), "—")
            self.assertEqual(metrics.get("Missing or invalid dates in selected scope"), "0")
            comparison = next(item.value for item in page.dataframe if "Semantic mean demand (%)" in item.value)
            self.assertEqual(comparison["Semantic mean demand (%)"].tolist(), [0.0])
            self.assertTrue(comparison["Trend classification agrees"].isna().all())

    def test_legacy_analytics_and_audit_exclude_synthetic_jobs(self):
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "master.sqlite3"
            jobs = pd.DataFrame({
                "job_id": ["real", "bundled", "custom"],
                "source_url": ["https://example.com/real", "https://example.com/synthetic-temporal-test/fixture",
                               "https://example.com/custom-demo"],
                "source_platform": ["Reviewed portal", "Bundled fixture", "Custom fixture"],
                "job_title": "Software Engineer",
                "posting_date": "2026-01-15",
                "data_provenance": ["empirical", "unreviewed", "synthetic"],
            })
            repository.import_jobs_dataframe(jobs, source_name="Fixture", db_path=db_path)
            current = repository.get_master_jobs(db_path=db_path).assign(skills='["python"]')
            run_id = repository.record_extraction_run("legacy", db_path=db_path)
            repository.store_extracted_skills(current, run_id, "lexical", "skills", db_path=db_path)

            with patch.object(connection, "DB_PATH", db_path):
                page = AppTest.from_file(str(PAGE)).run()

            self.assertFalse(page.exception)
            metrics = {item.label: item.value for item in page.metric}
            self.assertEqual(metrics["Jobs in selected scope"], "1")
            self.assertEqual(metrics["Stored skill mentions"], "1")
            self.assertEqual(next(item for item in page.selectbox if item.label == "Source platform").options,
                             ["All", "Reviewed portal"])
            audit = next(item.value for item in page.dataframe if "manual_verification_status" in item.value)
            self.assertEqual(audit["job_id"].tolist(), ["real"])

    def test_forecast_backtests_all_displayed_horizons_after_trailing_zeroes(self):
        with TemporaryDirectory() as directory:
            db_path = Path(directory) / "master.sqlite3"
            periods = pd.date_range("2025-01-01", periods=12, freq="MS")
            jobs = pd.DataFrame({
                "job_id": [f"job-{month:02d}" for month in range(12)],
                "source_url": [f"https://example.com/forecast/{month}" for month in range(12)],
                "source_platform": "Fixture portal", "job_title": "Software Engineer",
                "posting_date": periods.strftime("%Y-%m-%d"),
            })
            repository.import_jobs_dataframe(jobs, source_name="Fixture", db_path=db_path)
            cohort = repository.get_master_jobs(db_path=db_path).assign(
                lexical_skills=lambda frame: frame["job_id"].map(
                    {f"job-{month:02d}": '["python"]' for month in range(8)},
                ).fillna("[]"),
                semantic_skills="[]",
            )
            repository.save_extraction_results(cohort, semantic_threshold=0.5, model_name="fixture", db_path=db_path)

            with patch.object(connection, "DB_PATH", db_path):
                page = AppTest.from_file(str(PAGE)).run()
                minimum_jobs = next(item for item in page.number_input if item.label == "Minimum eligible jobs per period")
                minimum_jobs.set_value(1).run()
                generate = next(item for item in page.button if item.label == "Generate forecasts and evaluate baselines")
                generate.click().run()

            self.assertFalse(page.exception)
            forecast = next(item.value for item in page.dataframe if "last_value_baseline" in item.value)
            self.assertEqual(forecast.iloc[0]["period"], pd.Timestamp("2026-01-01"))
            self.assertEqual(forecast["last_value_baseline"].tolist(), [0.0] * 3)
            evaluation = next(item.value for item in page.dataframe if "MAE" in item.value)
            self.assertEqual(evaluation["horizon"].unique().tolist(), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
