"""Transactional extraction persistence tests using temporary SQLite databases."""

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.database import repository
from src.database.connection import database_connection
from src.database.extraction_cohort import get_matched_extraction_dataset, list_matched_extraction_runs


class ExtractionPersistenceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.db_path = Path(directory.name) / "master.sqlite3"
        repository.import_jobs_dataframe(
            pd.DataFrame([
                {"job_id": "a", "source_url": "https://example.com/a", "job_title": "Engineer",
                 "job_description": "Working with Python"},
                {"job_id": "b", "source_url": "https://example.com/b", "job_title": "Engineer",
                 "job_description": "General duties"},
            ]),
            source_name="Fixture",
            db_path=self.db_path,
        )
        jobs = repository.get_master_jobs(db_path=self.db_path)
        self.results = jobs.assign(
            lexical_skills=jobs["job_id"].map({"a": '["python"]', "b": "[]"}),
            semantic_skills=jobs["job_id"].map({"a": '["python"]', "b": "[]"}),
            skill_provenance="description",
        )
        self.results.attrs["extraction_metadata"] = {"semantic_scores": {"a": {"python": 0.74}}}

    def save_results(self):
        return repository.save_extraction_results(
            self.results,
            semantic_threshold=0.62,
            model_name="test-model",
            source_batch_id="test-batch",
            db_path=self.db_path,
        )

    def test_save_records_successful_inputs_even_without_mentions(self):
        run_id, lexical, semantic = self.save_results()
        self.assertEqual((lexical, semantic), (1, 1))
        with database_connection(self.db_path) as conn:
            run = conn.execute("SELECT * FROM extraction_runs WHERE run_id = ?", (run_id,)).fetchone()
            self.assertEqual((run["semantic_threshold"], run["model_name"], run["source_batch_id"]),
                             (0.62, "test-model", "test-batch"))
            self.assertTrue(run["completed_at"])
            self.assertEqual(len(conn.execute("SELECT * FROM extracted_skills").fetchall()), 2)
            self.assertEqual(conn.execute(
                "SELECT confidence FROM extracted_skills WHERE method = 'semantic'"
            ).fetchone()[0], 0.74)
            completed = conn.execute(
                """SELECT job_id, input_sha256, lexical_completed, semantic_completed
                   FROM extraction_run_jobs WHERE run_id = ? ORDER BY job_id""",
                (run_id,),
            ).fetchall()
            self.assertEqual([tuple(row) for row in completed], [
                ("a", hashlib.sha256(b"Engineer Working with Python").hexdigest(), 1, 1),
                ("b", hashlib.sha256(b"Engineer General duties").hexdigest(), 1, 1),
            ])

    def test_matched_reader_retains_zero_skill_job_and_detects_removed_input(self):
        run_id, _, _ = self.save_results()
        with database_connection(self.db_path) as conn:
            runs = list_matched_extraction_runs(conn)
            self.assertEqual(list(runs[["run_id", "job_count"]].itertuples(index=False, name=None)), [(run_id, 2)])
            cohort = get_matched_extraction_dataset(conn, run_id)
            self.assertEqual(cohort["job_id"].tolist(), ["a", "b"])
            self.assertEqual(cohort["semantic_skills"].map(json.loads).tolist(), [["Python"], []])
            conn.execute("DELETE FROM jobs WHERE job_id = 'b'")
            with self.assertRaisesRegex(ValueError, "no longer match"):
                get_matched_extraction_dataset(conn, run_id)

    def test_second_method_failure_rolls_back_and_allows_retry(self):
        with database_connection(self.db_path) as conn:
            conn.execute(
                """CREATE TRIGGER reject_semantic BEFORE INSERT ON extracted_skills
                   WHEN NEW.method = 'semantic' BEGIN
                       SELECT RAISE(ABORT, 'injected semantic failure');
                   END"""
            )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "injected semantic failure"):
            self.save_results()
        with database_connection(self.db_path) as conn:
            for table in ("extraction_runs", "extraction_run_jobs", "extracted_skills", "skills"):
                self.assertEqual(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)
            conn.execute("DROP TRIGGER reject_semantic")
        self.assertEqual(self.save_results()[1:], (1, 1))

    def test_stale_master_result_is_rejected(self):
        repository.import_jobs_dataframe(
            pd.DataFrame([{
                "job_id": "a", "source_url": "https://example.com/a", "job_title": "Engineer",
                "job_description": "Working with Java",
            }]),
            source_name="Updated fixture",
            db_path=self.db_path,
        )
        with self.assertRaisesRegex(ValueError, "changed since extraction"):
            self.save_results()
        with database_connection(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM extraction_runs").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
