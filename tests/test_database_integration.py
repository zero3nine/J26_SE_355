"""
Automated tests for Master Job Collection and Extracted Skill SQLite Database integration.
Tests schema initialization, taxonomy seeding, extraction persistence, parameterized queries,
and end-to-end analytical pipeline consumption using isolated temporary databases.
"""
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.database.connection import (
    get_connection,
    initialize_database,
    database_connection,
)
from src.database.repository import (
    seed_skills_taxonomy,
    import_jobs_dataframe,
    record_extraction_run,
    store_extracted_skills,
    get_extracted_skills_dataset,
    get_master_jobs,
    get_database_summary,
)
from src.extraction.run_extraction import run_extraction
from src.analytics.run_analysis import (
    load_jobs,
    load_jobs_from_database,
    run_analysis,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = PROJECT_ROOT / "config" / "skill_taxonomy.json"


class TestDatabaseIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_master.sqlite3"
        self.output_dir = Path(self.temp_dir.name) / "analytics_out"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_initialization_and_schema(self):
        """Verify schema creation and pragmas in an isolated temporary database."""
        initialize_database(db_path=self.db_path)
        self.assertTrue(self.db_path.exists())

        with database_connection(db_path=self.db_path) as conn:
            cur = conn.cursor()
            tables = {
                r[0]
                for r in cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            expected_tables = {
                "jobs",
                "job_versions",
                "import_runs",
                "extraction_runs",
                "skills",
                "extracted_skills",
            }
            self.assertTrue(expected_tables.issubset(tables))

            # Foreign keys pragma verification
            fk_status = cur.execute("PRAGMA foreign_keys").fetchone()[0]
            self.assertEqual(fk_status, 1)

    def test_seed_skills_taxonomy_idempotency(self):
        """Verify safe, repeatable seeding of skills table from skill_taxonomy.json."""
        initialize_database(db_path=self.db_path)

        seeded_first = seed_skills_taxonomy(
            taxonomy_path=TAXONOMY_PATH, db_path=self.db_path
        )
        self.assertGreaterEqual(seeded_first, 60)

        summary_first = get_database_summary(db_path=self.db_path)
        self.assertEqual(summary_first["canonical_skills"], seeded_first)

        # Idempotency check: re-seeding must not duplicate rows
        seeded_second = seed_skills_taxonomy(
            taxonomy_path=TAXONOMY_PATH, db_path=self.db_path
        )
        summary_second = get_database_summary(db_path=self.db_path)
        self.assertEqual(summary_second["canonical_skills"], seeded_first)

        with database_connection(db_path=self.db_path) as conn:
            row = conn.execute(
                "SELECT canonical_name, category, aliases_json FROM skills WHERE canonical_name = 'Python'"
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["canonical_name"], "Python")
            self.assertEqual(row["category"], "Programming Languages")
            aliases = json.loads(row["aliases_json"])
            self.assertIn("python", aliases)

    def test_job_import_extraction_and_persistence(self):
        """Verify jobs import, extraction execution, and persistence into extracted_skills."""
        initialize_database(db_path=self.db_path)
        seed_skills_taxonomy(taxonomy_path=TAXONOMY_PATH, db_path=self.db_path)

        sample_jobs = pd.DataFrame([
            {
                "job_id": "test_job_1",
                "source_url": "https://example.com/jobs/1",
                "job_title": "Senior Python Developer",
                "company_name": "Alpha Tech",
                "location": "Colombo",
                "country": "Sri Lanka",
                "posting_date": "2026-10-01",
                "job_description": "We are seeking a Senior Python Developer with strong Django, PostgreSQL, and Docker experience.",
                "source_platform": "test_portal",
                "skill_provenance": "description",
            },
            {
                "job_id": "test_job_2",
                "source_url": "https://example.com/jobs/2",
                "job_title": "Full Stack Engineer",
                "company_name": "Beta Labs",
                "location": "Kandy",
                "country": "Sri Lanka",
                "posting_date": "2026-10-02",
                "job_description": "Join our agile team working with React, TypeScript, Node.js, and AWS cloud infrastructure.",
                "source_platform": "test_portal",
                "skill_provenance": "description",
            },
        ])

        # Import jobs into database
        import_res = import_jobs_dataframe(sample_jobs, source_name="unit_test", db_path=self.db_path)
        self.assertEqual(import_res["inserted_jobs"], 2)

        # Run extraction with persistence
        extracted_df = run_extraction(
            input_path=sample_jobs,
            taxonomy_path=TAXONOMY_PATH,
            semantic_threshold=0.45,
            persist_to_db=True,
            db_path=self.db_path,
        )
        self.assertIn("extraction_run_id", extracted_df.columns)
        run_id = extracted_df["extraction_run_id"].iloc[0]

        summary = get_database_summary(db_path=self.db_path)
        self.assertEqual(summary["jobs"], 2)
        self.assertEqual(summary["extraction_runs"], 1)
        self.assertGreater(summary["skill_mentions"], 0)

        # Verify extracted_skills rows and foreign key integrity
        with database_connection(db_path=self.db_path) as conn:
            mentions = conn.execute(
                """SELECT es.*, s.canonical_name 
                   FROM extracted_skills es
                   LEFT JOIN skills s ON es.canonical_skill_id = s.skill_id
                   WHERE es.run_id = ?""",
                (run_id,)
            ).fetchall()
            self.assertGreater(len(mentions), 0)

            for m in mentions:
                self.assertIn(m["job_id"], ["test_job_1", "test_job_2"])
                self.assertEqual(m["run_id"], run_id)
                self.assertIn(m["method"], ["lexical", "semantic"])
                self.assertEqual(m["original_span"], "description")
                self.assertGreater(m["confidence"], 0.0)

    def test_analysis_pipeline_reads_from_database(self):
        """Verify the analytical pipeline consumes jobs and extracted skills directly from SQLite."""
        initialize_database(db_path=self.db_path)
        seed_skills_taxonomy(taxonomy_path=TAXONOMY_PATH, db_path=self.db_path)

        jobs_data = pd.DataFrame([
            {
                "job_id": "job_dev_1",
                "source_url": "https://example.com/dev/1",
                "job_title": "Backend Python Engineer",
                "company_name": "DevCorp",
                "location": "Remote",
                "country": "Sri Lanka",
                "posting_date": "2026-10-01",
                "job_description": "Looking for Python, Django, PostgreSQL, and Docker developer.",
                "source_platform": "dev_portal",
                "skill_provenance": "description",
            },
            {
                "job_id": "job_dev_2",
                "source_url": "https://example.com/dev/2",
                "job_title": "Python Microservices Engineer",
                "company_name": "CloudWorks",
                "location": "Colombo",
                "country": "Sri Lanka",
                "posting_date": "2026-10-02",
                "job_description": "We need Python, FastAPI, Docker, and PostgreSQL skills.",
                "source_platform": "dev_portal",
                "skill_provenance": "description",
            },
        ])
        import_jobs_dataframe(jobs_data, source_name="unit_test", db_path=self.db_path)
        run_extraction(
            input_path=jobs_data,
            taxonomy_path=TAXONOMY_PATH,
            semantic_threshold=0.45,
            persist_to_db=True,
            db_path=self.db_path,
        )

        # 1. Test get_extracted_skills_dataset
        df_dataset = get_extracted_skills_dataset(db_path=self.db_path)
        self.assertEqual(len(df_dataset), 2)
        self.assertIn("lexical_skills", df_dataset.columns)
        self.assertIn("semantic_skills", df_dataset.columns)

        # 2. Test load_jobs with db_path
        jobs_list, report, records = load_jobs(
            input_path=self.db_path,
            skill_mode="combined",
            normalize=True,
            return_records=True,
        )
        self.assertEqual(len(jobs_list), 2)
        self.assertIn("Python", jobs_list[0])
        self.assertIn("PostgreSQL", jobs_list[0])
        self.assertEqual(report["jobs_with_selected_skills"], 2)

        # 3. Test run_analysis end-to-end directly from SQLite database
        analysis_report = run_analysis(
            input_path=self.db_path,
            output_dir=self.output_dir,
            skill_mode="combined",
        )
        self.assertEqual(analysis_report["status"], "complete")
        self.assertGreater(analysis_report["unique_skills"], 0)
        self.assertTrue(analysis_report["association_rules_generated"])
        self.assertTrue(analysis_report["technology_stacks_generated"])

        combined_dir = self.output_dir / "combined"
        self.assertTrue((combined_dir / "cooccurrence_matrix.csv").exists())
        self.assertTrue((combined_dir / "jaccard_similarity.csv").exists())
        self.assertTrue((combined_dir / "pmi_scores.csv").exists())
        self.assertTrue((combined_dir / "association_rules.csv").exists())
        self.assertTrue((combined_dir / "technology_stacks.csv").exists())

    def test_empty_database_guard(self):
        """Verify load_jobs and run_analysis safely handle an empty database without throwing exceptions."""
        initialize_database(db_path=self.db_path)

        jobs_list, report = load_jobs(input_path=self.db_path, skill_mode="combined")
        self.assertEqual(jobs_list, [])
        self.assertEqual(report["status"], "empty_database")
        self.assertEqual(report["jobs_with_selected_skills"], 0)


if __name__ == "__main__":
    unittest.main()
