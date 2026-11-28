"""Regional skill demand uses one completed extraction cohort."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.analytics.regional_analysis import (
    EligibilityConfig,
    calculate_skill_demand_percentages,
    load_regional_market_data_from_db,
)
from src.database import connection
from src.database.repository import get_master_jobs, import_jobs_dataframe, save_extraction_results


class RegionalMatchedCohortTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = Path(directory.name) / "master.sqlite3"
        self.enterContext(patch.object(connection, "DB_PATH", self.database))
        import_jobs_dataframe(pd.DataFrame([
            {
                "job_id": job_id,
                "source_url": f"https://example.com/jobs/{job_id}",
                "job_title": "Software Engineer",
                "job_description": "A test job advertisement",
                "country": country,
                "posting_date": "2026-09-20",
            }
            for job_id, country in (
                ("mentions", "Sri Lanka"), ("successful-zero", "Sri Lanka"),
                ("legacy-only", "Sri Lanka"), ("outside-region", "United Kingdom"),
            )
        ]), db_path=self.database)

        jobs = get_master_jobs(db_path=self.database).set_index("job_id", drop=False)
        old_run = self.save_run(
            jobs.loc[["successful-zero", "legacy-only"]], '["python"]', '["python"]',
        )
        self.run = self.save_run(
            jobs.loc[["mentions", "successful-zero", "outside-region"]],
            ['["python"]', "[]", '["python"]'], ['["sql"]', "[]", '["python"]'],
        )
        with connection.database_connection(self.database) as db:
            db.execute("UPDATE extraction_runs SET started_at = ? WHERE run_id = ?", ("2026-09-01", old_run))
            db.execute("UPDATE extraction_runs SET started_at = ? WHERE run_id = ?", ("2026-09-20", self.run))

    def save_run(self, jobs, lexical, semantic):
        result = jobs.assign(lexical_skills=lexical, semantic_skills=semantic)
        return save_extraction_results(
            result, semantic_threshold=0.62, model_name="cohort fixture",
            db_path=self.database,
        )[0]

    def test_skill_rows_and_denominator_follow_selected_run_and_method(self):
        config = EligibilityConfig(require_at_least_n_skills=0)
        for method, expected in (
            ("lexical", {"python": 50, "sql": 0}),
            ("semantic", {"python": 0, "sql": 50}),
            ("combined", {"python": 50, "sql": 50}),
        ):
            with self.subTest(method=method):
                records = load_regional_market_data_from_db(run_id=self.run, method=method)
                self.assertEqual(set(records["job_id"]), {"mentions", "successful-zero"})
                self.assertEqual(records.set_index("job_id").loc["successful-zero", "skills"], [])
                demand = calculate_skill_demand_percentages(records, config).set_index("skill_id")
                self.assertEqual(set(demand["eligible_ads_denominator"]), {2})
                self.assertEqual(demand.loc[list(expected), "demand_pct"].to_dict(), expected)

    def test_view_defaults_to_latest_matched_run_and_reports_measured_scope(self):
        before = self.database.read_bytes()
        app = AppTest.from_string(
            "from src.analytics.regional_dashboard_view import render_regional_analysis_view\n"
            "render_regional_analysis_view()",
            default_timeout=20,
        ).run()
        self.assertFalse(app.exception)
        selector = next(item for item in app.selectbox if item.label == "Extraction run")
        self.assertEqual(selector.value, self.run)
        self.assertIn("Legacy data (unverified cohort)", selector.options)
        self.assertTrue(any("2 eligible advertisements" in item.value for item in app.caption))
        self.assertTrue(any("Sri Lanka (N=2)" in item.value for item in app.caption))
        selector.set_value("legacy").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Legacy skill demand" in item.value for item in app.info))
        self.assertEqual(self.database.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
