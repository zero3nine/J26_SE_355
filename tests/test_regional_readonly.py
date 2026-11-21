"""Regression tests for regional reads of the master database."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.analytics.regional_analysis import load_regional_market_data_from_db
from src.database import connection
from src.database.repository import import_jobs_dataframe


class RegionalReadOnlyTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = Path(directory.name) / "master.sqlite3"
        self.enterContext(patch.object(connection, "DB_PATH", self.database))
        self.migration = self.enterContext(patch(
            "src.database.repository.migrate_csv_data_to_master_db"
        ))

    def test_open_and_refresh_preserve_curated_jobs_and_extraction(self):
        import_jobs_dataframe(pd.DataFrame([{
            "job_id": "curated",
            "source_url": "https://example.com/job",
            "country": "Sri Lanka",
            "job_title": "Software Engineer",
        }]), db_path=self.database)
        with connection.database_connection(db_path=self.database) as db:
            db.execute(
                "INSERT INTO extraction_runs(run_id, run_type, started_at) "
                "VALUES ('reviewed', 'both', '2026-01-01')"
            )
            db.execute(
                "INSERT INTO extracted_skills(job_id, run_id, method, skill_name, created_at) "
                "VALUES ('curated', 'reviewed', 'lexical', 'Python', '2026-01-01')"
            )

        def rows():
            with connection.database_connection(db_path=self.database) as db:
                return [db.execute(f"SELECT * FROM {table}").fetchall()
                        for table in ("jobs", "job_versions", "extracted_skills", "regional_analysis_runs")]

        before = rows()
        database_bytes = self.database.read_bytes()
        for _ in range(2):
            result = load_regional_market_data_from_db()
            self.assertEqual(result["job_id"].tolist(), ["curated"])
            self.assertEqual(result["skills"].tolist(), [["Python"]])
        self.assertEqual(rows(), before)
        self.assertEqual(self.database.read_bytes(), database_bytes)
        self.migration.assert_not_called()

    def test_absent_master_returns_empty_without_initializing_database(self):
        self.assertTrue(load_regional_market_data_from_db().empty)
        self.assertFalse(self.database.exists())
        self.migration.assert_not_called()


if __name__ == "__main__":
    unittest.main()
