"""Temporary SQLite regressions for job import history and atomicity."""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.database.connection import database_connection
from src.database.repository import get_master_jobs, import_jobs_dataframe


class MasterImportObservationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = Path(directory.name) / "master.sqlite3"
        self.job = {
            "job_id": "job-a",
            "source_url": "https://example.com/jobs/a",
            "job_title": "Software Engineer",
            "job_description": "Python and SQL.",
            "country": "Sri Lanka",
        }

    def import_rows(self, *rows):
        return import_jobs_dataframe(pd.DataFrame(rows), db_path=self.database)

    def jobs(self, run=None):
        return get_master_jobs(db_path=self.database, import_run_id=run)

    def versions(self):
        with database_connection(self.database) as db:
            return db.execute(
                "SELECT job_id, job_description FROM job_versions ORDER BY version_id"
            ).fetchall()

    def test_replay_is_a_member_of_both_imports_without_new_versions(self):
        first = self.import_rows(self.job)["import_run_id"]
        replay = self.import_rows(self.job, self.job)
        self.assertEqual(replay["skipped_duplicates"], 2)
        self.assertEqual(replay["inserted_jobs"], 0)
        self.assertEqual(replay["updated_jobs"], 0)
        self.assertEqual(len(self.versions()), 1)

        for run in (first, replay["import_run_id"]):
            with self.subTest(run=run):
                jobs = self.jobs(run)
                self.assertEqual(jobs["job_id"].tolist(), ["job-a"])
                self.assertEqual(jobs["import_run_id"].tolist(), [run])
        self.assertEqual(self.jobs()["import_run_id"].tolist(), [first])

    def test_metadata_can_change_without_adding_content_versions(self):
        self.import_rows(dict(self.job, work_mode="remote", classification_status="it",
                              salary_text_raw="LKR 200,000 per month"))
        result = self.import_rows(dict(self.job, work_mode="hybrid", classification_status="ambiguous",
                                       salary_text_raw="LKR 250,000 per month"))
        self.assertEqual(result["updated_jobs"], 1)
        self.assertEqual(result["skipped_duplicates"], 0)
        job = self.jobs().iloc[0]
        self.assertEqual(job["work_mode"], "hybrid")
        self.assertEqual(job["classification_status"], "ambiguous")
        self.assertEqual(job["salary_min_normalized"], 250000)
        self.assertEqual(len(self.versions()), 1)

        result = self.import_rows(self.job)
        self.assertEqual(result["skipped_duplicates"], 1)
        job = self.jobs().iloc[0]
        self.assertEqual(job["work_mode"], "hybrid")
        self.assertEqual(job["classification_status"], "ambiguous")
        self.assertEqual(job["salary_min_normalized"], 250000)

    def test_old_membership_survives_updates_and_content_reversion(self):
        first = self.import_rows(self.job)["import_run_id"]
        changed = self.import_rows(dict(self.job, job_description="Go and Kubernetes."))["import_run_id"]
        reverted = self.import_rows(self.job)["import_run_id"]
        self.assertEqual(len(self.versions()), 2)
        for run in (first, changed, reverted):
            with self.subTest(run=run):
                self.assertEqual(self.jobs(run)["job_id"].tolist(), ["job-a"])

    def test_disclosure_only_replay_preserves_salary_evidence(self):
        salary = "LKR 200,000 per month"
        self.import_rows(dict(self.job, salary_text_raw=salary))

        self.import_rows(dict(self.job, salary_disclosed=True))
        self.import_rows(dict(self.job, salary_disclosed=False))

        job = self.jobs().iloc[0]
        self.assertEqual(job["salary_disclosed"], 1)
        self.assertEqual(job["salary_text_raw"], salary)
        self.assertEqual(job["salary_min_normalized"], 200000)
        self.assertEqual(job["salary_currency_normalized"], "LKR")
        self.assertEqual(job["salary_period_normalized"], "monthly")

        self.import_rows(dict(self.job, salary_text_raw="Salary not disclosed"))
        job = self.jobs().iloc[0]
        self.assertEqual(job["salary_disclosed"], 0)
        self.assertEqual(job["salary_text_raw"], "Salary not disclosed")
        self.assertIsNone(job["salary_min_normalized"])

    def test_legacy_version_can_establish_known_batch_membership(self):
        first = self.import_rows(self.job)["import_run_id"]
        self.import_rows(dict(self.job, job_description="Updated content."))
        with database_connection(self.database) as db:
            db.execute("DROP TABLE import_run_jobs")
        self.assertEqual(self.jobs(first)["job_id"].tolist(), ["job-a"])

    def test_failed_observation_write_rolls_back_new_job_and_version(self):
        self.import_rows(self.job)
        with database_connection(self.database) as db:
            db.execute(
                """CREATE TRIGGER fail_job_b_membership BEFORE INSERT ON import_run_jobs
                   WHEN NEW.job_id = 'job-b'
                   BEGIN SELECT RAISE(ABORT, 'observation write failed'); END"""
            )
        result = self.import_rows(
            dict(self.job, job_id="job-b", source_url="https://example.com/jobs/b"),
            dict(self.job, job_id="job-c", source_url="https://example.com/jobs/c"),
        )
        self.assertEqual(result["failed_rows"], 1)
        self.assertEqual(result["inserted_jobs"], 1)
        self.assertEqual(set(self.jobs()["job_id"]), {"job-a", "job-c"})
        self.assertEqual([row["job_id"] for row in self.versions()], ["job-a", "job-c"])
        self.assertEqual(self.jobs(result["import_run_id"])["job_id"].tolist(), ["job-c"])

    def test_failed_version_write_leaves_job_unchanged_and_batch_continues(self):
        self.import_rows(self.job)
        with database_connection(self.database) as db:
            db.execute(
                """CREATE TRIGGER fail_job_a_version BEFORE INSERT ON job_versions
                   WHEN NEW.job_id = 'job-a'
                   BEGIN SELECT RAISE(ABORT, 'version write failed'); END"""
            )
        result = self.import_rows(
            dict(self.job, job_description="Replacement content."),
            dict(self.job, job_id="job-b", source_url="https://example.com/jobs/b"),
        )
        self.assertEqual(result["failed_rows"], 1)
        self.assertEqual(result["inserted_jobs"], 1)
        self.assertEqual(self.jobs(result["import_run_id"])["job_id"].tolist(), ["job-b"])
        job = self.jobs().set_index("job_id").loc["job-a"]
        self.assertEqual(job["job_description"], self.job["job_description"])
        self.assertEqual([tuple(row) for row in self.versions()], [
            ("job-a", self.job["job_description"]), ("job-b", self.job["job_description"]),
        ])


if __name__ == "__main__":
    unittest.main()
