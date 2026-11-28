"""Offline Streamlit checks for the matched research cohort controls."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import app_shared
from src.database import connection, repository


ROOT = Path(__file__).resolve().parents[1]


class MatchedResearchPagesTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.db = self.root / "master.sqlite3"
        jobs = pd.DataFrame([
            {
                "job_id": str(index),
                "source_url": f"https://example.com/{index}",
                "job_title": "Software Engineer",
                "job_description": "Software engineering",
                "posting_date": "2026-01-15",
                "country": "Sri Lanka" if index < 6 else "Singapore",
                "source_platform": "Fixture",
            }
            for index in range(7)
        ])
        repository.import_jobs_dataframe(jobs, source_name="Fixture", db_path=self.db)
        current = repository.get_master_jobs(db_path=self.db)
        cohort = current[current["job_id"].ne("6")].copy()
        for method in ("lexical", "semantic"):
            cohort[f"{method}_skills"] = cohort["job_id"].map(
                lambda job_id: '["python"]' if job_id == "0" else "[]",
            )
        self.run_id, _, _ = repository.save_extraction_results(
            cohort, semantic_threshold=0.5, model_name="fixture", db_path=self.db,
        )
        legacy_id = repository.record_extraction_run("legacy", db_path=self.db)
        legacy = current[current["job_id"].eq("6")].assign(skills='["java"]')
        repository.store_extracted_skills(legacy, legacy_id, "lexical", "skills", db_path=self.db)

    def test_temporal_uses_matched_denominator_and_filters(self):
        with patch.object(connection, "DB_PATH", self.db):
            page = AppTest.from_file(str(ROOT / "pages/13_Temporal_Analysis.py")).run()
            self.assertFalse(page.exception)
            self.assertNotIn("Singapore", next(x for x in page.selectbox if x.label == "Country").options)
            run = next(x for x in page.selectbox if x.label == "Extraction run")
            self.assertEqual(run.value, self.run_id)
            counts = next(x.value for x in page.dataframe if "Eligible jobs" in x.value.columns)
            self.assertEqual(counts["Eligible jobs"].tolist(), [6])
            run.select("legacy").run()
            self.assertFalse(page.exception)
            self.assertIn("Singapore", next(x for x in page.selectbox if x.label == "Country").options)

    def test_role_keeps_zero_skill_jobs_in_the_selected_run(self):
        with patch.object(connection, "DB_PATH", self.db), patch.object(app_shared, "current_dir", self.root):
            page = AppTest.from_file(str(ROOT / "pages/14_Role_Skill_Analysis.py")).run()
            self.assertFalse(page.exception)
            self.assertEqual(set(page.session_state.role_classified_df["job_id"]), set(map(str, range(6))))
            run = next(x for x in page.selectbox if x.label == "Extraction run")
            self.assertEqual(run.value, self.run_id)
            self.assertIn("Legacy data (unverified cohort)", run.options)
            run.select("legacy").run()
            self.assertFalse(page.exception)
            self.assertEqual(set(page.session_state.role_classified_df["job_id"]), {"6"})


if __name__ == "__main__":
    unittest.main()
