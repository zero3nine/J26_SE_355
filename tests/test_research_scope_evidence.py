"""Regression checks for scoped role audits and relationship evidence."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import app_shared
from src.analytics.evidence import build_source_evidence
from src.analytics.run_analysis import run_analysis, run_comprehensive_analysis
from src.database import connection, repository


class ResearchScopeEvidenceTests(unittest.TestCase):
    def test_role_audit_keeps_its_own_run_when_another_session_writes_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "master.sqlite3"
            repository.import_jobs_dataframe(pd.DataFrame([
                {
                    "job_id": str(index), "source_url": f"https://example.com/{index}",
                    "job_title": "Software Engineer" if index < 6 else "Data Engineer",
                    "job_description": "Software engineering and data pipelines",
                }
                for index in range(12)
            ]), source_name="Fixture", db_path=database)
            jobs = repository.get_master_jobs(db_path=database)
            run_ids = []
            for skills in ('["python"]', '["javascript"]'):
                cohort = jobs.assign(lexical_skills=skills, semantic_skills=skills)
                run_id, _, _ = repository.save_extraction_results(
                    cohort, semantic_threshold=0.5, model_name="fixture", db_path=database,
                )
                run_ids.append(run_id)

            page_path = Path(__file__).resolve().parents[1] / "pages/14_Role_Skill_Analysis.py"
            with patch.object(connection, "DB_PATH", database), patch.object(app_shared, "current_dir", root):
                sessions = []
                for run_id in run_ids:
                    page = AppTest.from_file(page_path).run()
                    next(item for item in page.selectbox if item.label == "Extraction run").select(run_id).run()
                    self.assertFalse(page.exception)
                    self.assertTrue(page.session_state.audit_result["summary"]["passed"])
                    sessions.append(page)

                for page in sessions:
                    next(item for item in page.button if item.label == "Re-run output audit").click().run()
                    self.assertFalse(page.exception)
                    self.assertTrue(page.session_state.audit_result["summary"]["passed"])

    def test_evidence_requires_every_skill_in_the_sample_excerpt(self):
        jobs = pd.DataFrame([
            {
                "job_id": "inferred", "job_description": "We need an experienced engineer.",
                "lexical_skills": "[]", "semantic_skills": '["python", "javascript"]',
            },
        ])
        pairs = pd.DataFrame([{"skill_a": "JavaScript", "skill_b": "Python", "pair_count": 1}])
        stacks = pd.DataFrame([{"stack": "JavaScript + Python", "job_count": 1}])
        evidence = build_source_evidence(jobs, pairs, stacks)
        self.assertEqual(len(evidence), 2)
        for record in evidence:
            self.assertEqual(record["supporting_ads_count"], 1)
            self.assertEqual(record["verification_status"], "Inferred by semantic extraction")

    def test_evidence_csv_exports_untrusted_text_as_literal(self):
        jobs = pd.DataFrame([{
            "job_id": "posting", "company": "=2+2", "job_description": "Use Python and JavaScript.",
            "lexical_skills": '["python", "javascript"]', "semantic_skills": "[]",
        }])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            run_comprehensive_analysis(jobs, output)
            export = pd.read_csv(output / "source_evidence.csv")
            self.assertEqual(export["company"].unique().tolist(), ["'=2+2"])
            self.assertEqual(export["supporting_job_ids"].unique().tolist(), ['["posting"]'])

    def test_both_evidence_types_use_the_selected_method(self):
        jobs = pd.DataFrame([
            {
                "job_id": "semantic", "job_description": "Use JavaScript and Python.",
                "lexical_skills": "[]", "semantic_skills": '["python", "javascript"]',
            },
            {
                "job_id": "lexical", "job_description": "Use JavaScript and Python.",
                "lexical_skills": '["python", "javascript"]', "semantic_skills": "[]",
            },
        ])
        pairs = pd.DataFrame([{"skill_a": "JavaScript", "skill_b": "Python", "pair_count": 1}])
        stacks = pd.DataFrame([{"stack": "JavaScript + Python", "job_count": 1}])
        evidence = build_source_evidence(jobs, pairs, stacks, skill_mode="lexical_skills")
        self.assertEqual(len(evidence), 2)
        for record in evidence:
            self.assertEqual(record["supporting_ads_count"], 1)
            self.assertEqual(record["supporting_job_ids"], ["lexical"])
            self.assertEqual(record["sample_job_id"], "lexical")
            self.assertEqual(record["verification_status"], "Verified in Original Text")

    def test_dashboard_pair_drilldown_excludes_jobs_that_only_match_in_semantic_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            jobs = pd.DataFrame([
                {
                    "job_id": str(index), "job_title_raw": title,
                    "job_description": "Work with JavaScript and Python.",
                    "lexical_skills": '["python", "javascript"]' if index < 2 else "[]",
                    "semantic_skills": '["python", "javascript"]',
                }
                for index, title in enumerate(["Lexical Job One", "Lexical Job Two", "Only Semantic Job"])
            ])
            report = run_analysis(jobs, output, skill_mode="lexical_skills", include_jobs_without_skills=True)
            self.assertEqual(report["jobs_in_analysis"], 3)
            self.assertEqual(report["jobs_with_selected_skills"], 2)
            stacks = pd.read_csv(output / "lexical_skills" / "technology_stacks.csv")
            self.assertAlmostEqual(stacks.loc[0, "support"], 2 / 3, places=6)
            page = AppTest.from_string(f"""
from pathlib import Path
import pandas as pd
from src.analytics.dashboard import render_section2_skill_relationships

render_section2_skill_relationships(
    Path({str(output / 'lexical_skills')!r}),
    {{'skill_mode': 'lexical_skills'}},
    pd.DataFrame({jobs.to_dict('records')!r}),
)
""").run()

            self.assertFalse(page.exception)
            display = "\n".join(item.value for item in page.markdown)
            self.assertIn("Lexical Job One", display)
            self.assertIn("Lexical Job Two", display)
            self.assertNotIn("Only Semantic Job", display)
