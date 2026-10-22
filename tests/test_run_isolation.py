"""
Automated Test Suite: Strict Current URL-Based Data Isolation & Pipeline Provenance.

Validates that:
1. Every analysis run is strictly isolated to its submitted URLs.
2. Downstream cleaning, extraction, normalization, and relationship analytics
   use only data collected from the current run.
3. No historical records, global files, cached results, or dummy data contaminate current runs.
4. Failures and empty extractions are reported transparently without fallbacks.
5. Evidence in discovered technology stacks is 100% traceable to current run jobs.
"""

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.cleaning.clean_jobs import clean_raw_dataframe
from src.extraction.run_extraction import run_extraction
from src.analytics.run_analysis import run_analysis, load_jobs


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = PROJECT_ROOT / "config" / "skill_taxonomy.json"


def _make_raw_record(
    job_id: str,
    source_url: str,
    title: str,
    company: str,
    description: str,
    batch_id: str,
    status: str = "success",
) -> dict:
    """Helper creating a valid raw crawler schema record."""
    return {
        "job_id": job_id,
        "source_job_id": job_id,
        "job_title_raw": title,
        "company_raw": company,
        "country": "Sri Lanka",
        "location_raw": "Colombo",
        "job_description_raw": description,
        "requirements_raw": description,
        "listing_posted_date_raw": "2026-10-20",
        "closing_date_raw": "",
        "functional_area": "Software",
        "description_type": "text",
        "advert_image_urls": "",
        "ocr_text_raw": "",
        "ocr_status": "not_applicable",
        "ocr_confidence": 0.0,
        "source_platform": "topjobs",
        "source_url": source_url,
        "canonical_url": source_url,
        "collection_batch_id": batch_id,
        "scraped_at": "2026-10-20T10:00:00Z",
        "extraction_status": status,
        "exclusion_reason": "",
        "fetch_method": "requests",
        "rendering_used": "no",
        "failure_reason": "",
        "date_conversion_method": "direct",
        "date_parse_status": "success",
        "date_parse_warning": "",
        "field_provenance": "jsonld",
        "classification_status": "classified",
        "classification_explanation": "IT role",
        "classification_override": "{}",
        "manual_review_reason": "",
    }


class TestStrictRunIsolation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_first_url_submission(self):
        """Test 1: Submit URL A and verify all downstream outputs derive strictly from URL A."""
        run_id = "run_test_01"
        url_a = "https://example.com/job/python-backend"
        raw_records = [
            _make_raw_record(
                job_id="job_py_01",
                source_url=url_a,
                title="Python Backend Developer",
                company="Alpha Corp",
                description="We are seeking an experienced Python Backend Developer skilled in Django and PostgreSQL for building scalable REST APIs and cloud services.",
                batch_id=run_id,
            )
        ]
        df_raw = pd.DataFrame(raw_records)

        # 1. Clean
        df_internal, df_clean, _ = clean_raw_dataframe(df_raw)
        self.assertEqual(len(df_clean), 1)
        self.assertEqual(df_clean.iloc[0]["source_url"], url_a)

        # 2. Extract
        df_extracted = run_extraction(
            input_path=df_clean,
            taxonomy_path=TAXONOMY_PATH,
            semantic_threshold=0.45,
            batch_id=run_id,
        )
        self.assertEqual(len(df_extracted), 1)
        lexical = json.loads(df_extracted.iloc[0]["lexical_skills"])
        self.assertIn("python", lexical)
        self.assertIn("django", lexical)
        self.assertIn("postgresql", lexical)
        self.assertNotIn("java", lexical)

        # 3. Analytics
        out_dir = self.output_root / run_id
        report = run_analysis(input_path=df_extracted, output_dir=out_dir, skill_mode="combined", run_id=run_id)
        self.assertEqual(report["run_id"], run_id)
        self.assertEqual(report["jobs_with_selected_skills"], 1)

        # Verify output files exist in run-isolated directory
        freq_csv = out_dir / "combined" / "skill_frequency.csv"
        self.assertTrue(freq_csv.exists())
        df_freq = pd.read_csv(freq_csv)
        skills_found = set(df_freq["skill"].tolist())
        self.assertTrue({"Python", "Django", "PostgreSQL"}.issubset(skills_found))
        self.assertNotIn("Java", skills_found)

    def test_02_second_url_submission_isolates_from_first(self):
        """Test 2: Submit URL B after URL A and verify analysis contains ONLY records from URL B."""
        # Run A: Python job
        run_a = "run_test_02_A"
        raw_a = pd.DataFrame([
            _make_raw_record(
                job_id="job_a",
                source_url="https://example.com/job/python",
                title="Python Dev",
                company="Alpha Corp",
                description="We are seeking an experienced Python Backend Developer skilled in Django and PostgreSQL for building scalable REST APIs.",
                batch_id=run_a,
            )
        ])
        _, clean_a, _ = clean_raw_dataframe(raw_a)
        extracted_a = run_extraction(clean_a, TAXONOMY_PATH, 0.45, batch_id=run_a)
        out_a = self.output_root / run_a
        run_analysis(extracted_a, out_a, "combined", run_id=run_a)

        # Run B: Java job submitted after Run A
        run_b = "run_test_02_B"
        url_b = "https://example.com/job/java-specialist"
        raw_b = pd.DataFrame([
            _make_raw_record(
                job_id="job_b",
                source_url=url_b,
                title="Java Specialist",
                company="Beta Tech",
                description="Looking for a skilled Java Software Engineer with extensive experience in Spring Boot, MySQL database design, and microservices.",
                batch_id=run_b,
            )
        ])
        _, clean_b, _ = clean_raw_dataframe(raw_b)
        extracted_b = run_extraction(clean_b, TAXONOMY_PATH, 0.45, batch_id=run_b)
        out_b = self.output_root / run_b
        report_b = run_analysis(extracted_b, out_b, "combined", run_id=run_b)

        # Assert Run B contains only Java/MySQL/Spring Boot and ZERO Python/Django
        self.assertEqual(report_b["run_id"], run_b)
        self.assertEqual(report_b["total_rows_in_csv"], 1)

        df_freq_b = pd.read_csv(out_b / "combined" / "skill_frequency.csv")
        skills_b = set(df_freq_b["skill"].tolist())
        self.assertTrue({"Java", "MySQL"}.issubset(skills_b))
        self.assertNotIn("Python", skills_b)
        self.assertNotIn("Django", skills_b)
        self.assertNotIn("PostgreSQL", skills_b)

    def test_03_multiple_urls_submission(self):
        """Test 3: Submit URLs A and B together and verify current run combines ONLY those two."""
        run_id = "run_test_03_AB"
        url_1 = "https://example.com/job/dev1"
        url_2 = "https://example.com/job/dev2"
        raw_records = [
            _make_raw_record("job_1", url_1, "Go Developer", "Gopher Ltd", "Seeking a Senior Golang Backend Developer experienced in building distributed systems, microservices, and Docker containerization.", run_id),
            _make_raw_record("job_2", url_2, "Cloud Engineer", "Sky Inc", "Looking for an AWS Cloud Solutions Engineer with hands-on experience in Docker, Kubernetes cluster orchestration, and infrastructure.", run_id),
        ]
        df_raw = pd.DataFrame(raw_records)
        _, df_clean, _ = clean_raw_dataframe(df_raw)
        self.assertEqual(len(df_clean), 2)
        self.assertEqual(set(df_clean["source_url"]), {url_1, url_2})

        df_extracted = run_extraction(df_clean, TAXONOMY_PATH, 0.45, batch_id=run_id)
        self.assertEqual(len(df_extracted), 2)

        out_dir = self.output_root / run_id
        report = run_analysis(df_extracted, out_dir, "combined", run_id=run_id)
        self.assertEqual(report["jobs_with_selected_skills"], 2)

        df_freq = pd.read_csv(out_dir / "combined" / "skill_frequency.csv")
        skills = set(df_freq["skill"].tolist())
        self.assertIn("Docker", skills)
        self.assertIn("AWS", skills)
        # Verify no external jobs
        self.assertNotIn("PHP", skills)
        self.assertNotIn("Ruby", skills)

    def test_04_historical_data_isolation(self):
        """Test 4: Prepopulate historical files on disk; verify they never leak into new run."""
        # Create a historical file with 20 unrelated skills
        historical_dir = self.output_root / "historical_global"
        historical_dir.mkdir(parents=True, exist_ok=True)
        hist_csv = historical_dir / "jobs_extracted.csv"
        pd.DataFrame([
            {
                "job_id": f"hist_{i}",
                "job_title_raw": "Blockchain Engineer",
                "company": "Crypto Global",
                "country": "Sri Lanka",
                "location_raw": "Colombo",
                "job_description": "We are seeking a blockchain engineer experienced in Solidity, Rust smart contracts, and Web3 decentralized architecture.",
                "posted_date": "2026-09-01",
                "source_platform": "topjobs",
                "source_url": "https://example.com/old/job",
                "scraped_at": "2026-09-01T00:00:00Z",
                "skill_provenance": "description",
                "lexical_skills": json.dumps(["solidity", "rust"]),
                "semantic_skills": json.dumps([]),
            }
            for i in range(10)
        ]).to_csv(hist_csv, index=False)

        # Now run a new isolated submission with a single JavaScript posting
        new_run_id = "run_fresh_isolated"
        new_raw = pd.DataFrame([
            _make_raw_record(
                "fresh_1",
                "https://example.com/fresh-react",
                "React Frontend Engineer",
                "Modern Web Ltd",
                "We are hiring a Frontend Web Developer proficient in JavaScript, React, HTML, and CSS to build responsive and modern user interfaces.",
                new_run_id,
            )
        ])
        _, clean_df, _ = clean_raw_dataframe(new_raw)
        extracted_df = run_extraction(clean_df, TAXONOMY_PATH, 0.45, batch_id=new_run_id)

        new_out_dir = self.output_root / new_run_id
        report = run_analysis(extracted_df, new_out_dir, "combined", run_id=new_run_id)

        # Assert no historical skills (Solidity, Rust) leaked in
        df_freq = pd.read_csv(new_out_dir / "combined" / "skill_frequency.csv")
        new_skills = set(df_freq["skill"].tolist())
        self.assertTrue({"JavaScript", "React"}.issubset(new_skills))
        self.assertNotIn("Solidity", new_skills)
        self.assertNotIn("Rust", new_skills)
        self.assertEqual(report["total_rows_in_csv"], 1)

    def test_05_extraction_isolation(self):
        """Test 5: Extraction & normalization use only cleaned descriptions from current run."""
        run_id = "run_test_05"
        raw_df = pd.DataFrame([
            _make_raw_record(
                "job_csharp",
                "https://example.com/csharp-job",
                "Senior .NET Developer",
                "DotNet Corp",
                "Senior C# .NET Developer needed with extensive enterprise expertise in .NET Core, Azure cloud, and SQL Server databases.",
                run_id,
            )
        ])
        _, clean_df, _ = clean_raw_dataframe(raw_df)
        extracted_df = run_extraction(clean_df, TAXONOMY_PATH, 0.45, batch_id=run_id)

        self.assertEqual(len(extracted_df), 1)
        self.assertEqual(extracted_df.iloc[0]["job_id"], "job_csharp")
        self.assertEqual(extracted_df.iloc[0]["collection_batch_id"], run_id)

        # Verify distinct boundary: C# recognized, not confused with C or C++
        lexical = json.loads(extracted_df.iloc[0]["lexical_skills"])
        self.assertIn("csharp", lexical)
        self.assertNotIn("c", lexical)
        self.assertNotIn("cpp", lexical)

    def test_06_relationship_isolation_and_statistical_correctness(self):
        """Test 6: Jaccard, PMI, and co-occurrence are derived purely from current run transactions."""
        run_id = "run_test_06"
        # 3 jobs:
        # Job 1: Python, Docker
        # Job 2: Python, Docker, AWS
        # Job 3: Java, Spring Boot
        records = [
            _make_raw_record("j1", "http://a.com/1", "Dev 1", "Corp", "Python software developer proficient in Docker containers, Linux, and backend application development for enterprise platforms.", run_id),
            _make_raw_record("j2", "http://a.com/2", "Dev 2", "Corp", "Senior Python cloud engineer with hands-on experience in Docker containers, AWS deployment, and scalable backend infrastructure.", run_id),
            _make_raw_record("j3", "http://a.com/3", "Dev 3", "Corp", "Enterprise Java Software Engineer specializing in Spring Boot framework, RESTful web services, and relational database systems.", run_id),
        ]
        _, clean_df, _ = clean_raw_dataframe(pd.DataFrame(records))
        extracted_df = run_extraction(clean_df, TAXONOMY_PATH, 0.45, batch_id=run_id)

        out_dir = self.output_root / run_id
        report = run_analysis(extracted_df, out_dir, "combined", run_id=run_id)

        # Load computed tables
        df_freq = pd.read_csv(out_dir / "combined" / "skill_frequency.csv")
        freq_map = dict(zip(df_freq["skill"], df_freq["job_count"]))
        self.assertEqual(freq_map["Python"], 2)
        self.assertEqual(freq_map["Docker"], 2)
        self.assertEqual(freq_map["AWS"], 1)
        self.assertEqual(freq_map["Java"], 1)

        # Jaccard verification
        df_jac = pd.read_csv(out_dir / "combined" / "jaccard_similarity.csv")
        py_doc = df_jac[(df_jac["skill_a"] == "Python") & (df_jac["skill_b"] == "Docker")]
        if py_doc.empty:
            py_doc = df_jac[(df_jac["skill_a"] == "Docker") & (df_jac["skill_b"] == "Python")]
        self.assertFalse(py_doc.empty)
        # Python and Docker co-occur in 2 jobs; union = 2 jobs -> Jaccard = 2/2 = 1.00
        self.assertAlmostEqual(float(py_doc.iloc[0]["jaccard"]), 1.0, places=2)

        # Java and Python never co-occur
        ja_py = df_jac[((df_jac["skill_a"] == "Java") & (df_jac["skill_b"] == "Python")) |
                       ((df_jac["skill_a"] == "Python") & (df_jac["skill_b"] == "Java"))]
        self.assertTrue(ja_py.empty or float(ja_py.iloc[0]["jaccard"]) == 0.0)

    def test_07_failed_url_reporting(self):
        """Test 7: Failed URL reports failure without substituting old or dummy data."""
        run_id = "run_test_07_failed"
        failed_records = [
            _make_raw_record(
                "job_fail",
                "https://invalid-nonexistent-job-site.com/job/404",
                "",
                "",
                "",
                run_id,
                status="network_error",
            )
        ]
        df_raw = pd.DataFrame(failed_records)
        df_internal, df_clean, stats = clean_raw_dataframe(df_raw)

        # Clean dataframe must be empty because failed status is excluded
        self.assertTrue(df_clean.empty)

        # Extraction on empty clean dataframe returns empty dataframe
        df_extracted = run_extraction(df_clean, TAXONOMY_PATH, 0.45, batch_id=run_id)
        self.assertTrue(df_extracted.empty)

        # Analysis on empty dataframe reports insufficient_data cleanly
        out_dir = self.output_root / run_id
        report = run_analysis(df_extracted, out_dir, "combined", run_id=run_id)
        self.assertEqual(report["status"], "insufficient_data")
        self.assertEqual(report["jobs_with_selected_skills"], 0)

    def test_08_empty_skill_extraction(self):
        """Test 8: Display clear empty state when no skills are extracted from descriptions."""
        run_id = "run_test_08_empty"
        records = [
            _make_raw_record(
                "rec_empty_1",
                "https://example.com/job/receptionist",
                "Office Receptionist",
                "Office Services Ltd",
                "This role is for a receptionist handling office visitors, front desk correspondence, and general phone inquiries in Colombo.",
                run_id,
            )
        ]
        _, df_clean, _ = clean_raw_dataframe(pd.DataFrame(records))
        self.assertEqual(len(df_clean), 1)

        df_extracted = run_extraction(df_clean, TAXONOMY_PATH, 0.45, batch_id=run_id)
        self.assertEqual(len(df_extracted), 1)

        out_dir = self.output_root / run_id
        report = run_analysis(df_extracted, out_dir, "combined", run_id=run_id)
        self.assertEqual(report["status"], "insufficient_data")
        self.assertEqual(report["jobs_with_selected_skills"], 0)
        self.assertEqual(report["unique_skills"], 0)

        # Verify empty schema CSVs were generated
        freq_csv = out_dir / "combined" / "skill_frequency.csv"
        self.assertTrue(freq_csv.exists())
        self.assertTrue(pd.read_csv(freq_csv).empty)

    def test_09_cache_isolation_and_threshold_change(self):
        """Test 9: Changing semantic threshold triggers recalculation without returning stale cache."""
        run_id = "run_test_09"
        records = [
            _make_raw_record(
                "job_sem_1",
                "https://example.com/job/ml",
                "Machine Learning Engineer",
                "AI Labs",
                "We are seeking a Machine Learning Engineer to work on deep learning models, natural language processing, predictive analytics, and statistical algorithms.",
                run_id,
            )
        ]
        _, clean_df, _ = clean_raw_dataframe(pd.DataFrame(records))
        self.assertEqual(len(clean_df), 1)

        # Run extraction at strict high threshold 0.85
        df_ext_high = run_extraction(clean_df, TAXONOMY_PATH, 0.85, batch_id=run_id)
        sem_high = json.loads(df_ext_high.iloc[0]["semantic_skills"])

        # Run extraction at relaxed threshold 0.35
        df_ext_low = run_extraction(clean_df, TAXONOMY_PATH, 0.35, batch_id=run_id)
        sem_low = json.loads(df_ext_low.iloc[0]["semantic_skills"])

        # Low threshold should capture equal or more semantic skill matches
        self.assertGreaterEqual(len(sem_low), len(sem_high))

    def test_10_evidence_traceability(self):
        """Test 10: Verify each discovered skill relationship/stack traces back to real jobs."""
        run_id = "run_test_10_trace"
        records = [
            _make_raw_record("rec_101", "https://ex.com/1", "Lead Python Engineer", "Acme", "We are hiring a Lead Python Engineer with expertise in Django, PostgreSQL database management, and Docker containerization for SaaS platforms.", run_id),
            _make_raw_record("rec_102", "https://ex.com/2", "Senior Backend Software Engineer", "Acme", "Senior Backend Software Engineer proficient in Python, Django, PostgreSQL, and Docker container platforms for scalable enterprise services.", run_id),
        ]
        _, clean_df, _ = clean_raw_dataframe(pd.DataFrame(records))
        self.assertEqual(len(clean_df), 2)
        extracted_df = run_extraction(clean_df, TAXONOMY_PATH, 0.45, batch_id=run_id)

        out_dir = self.output_root / run_id
        report = run_analysis(extracted_df, out_dir, "combined", run_id=run_id)

        self.assertEqual(report["status"], "complete")
        path_stacks = out_dir / "combined" / "technology_stacks.csv"
        self.assertTrue(path_stacks.exists())
        df_stacks = pd.read_csv(path_stacks)
        self.assertFalse(df_stacks.empty)

        # Inspect supporting_jobs field
        self.assertIn("supporting_jobs", df_stacks.columns)
        first_stack = df_stacks.iloc[0]
        supp_jobs = json.loads(first_stack["supporting_jobs"])
        self.assertGreater(len(supp_jobs), 0)

        # Verify the supporting jobs belong strictly to the current run
        supporting_ids = {j["job_id"] for j in supp_jobs}
        self.assertTrue(supporting_ids.issubset({"rec_101", "rec_102"}))
        for j in supp_jobs:
            self.assertEqual(j["company"], "Acme")


if __name__ == "__main__":
    unittest.main()
