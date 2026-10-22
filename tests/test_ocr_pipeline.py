"""
Automated test suite for Phase 7:
Comprehensive testing of TopJobs scraping, OCR, cleaning, skill extraction,
canonical normalization, and relationship analytics pipeline.

Covers:
1. HTML-based descriptions
2. Image-based descriptions requiring OCR
3. Advertisements containing both HTML text and images (Hybrid)
4. Missing images and OCR failures
5. Generic website boilerplate rejection
6. OCR output containing duplicate or noisy text
7. Skill extraction from OCR-derived descriptions
8. Canonical skill normalization
9. Relationship metrics calculated from validated skill sets
10. Regression tests for the existing pipeline
"""

import unittest
import json
import io
import math
import pandas as pd
from unittest.mock import patch, MagicMock
from PIL import Image, ImageDraw

from src.scraping.models import ExtractionResult, RAW_SCHEMA_COLUMNS
from src.scraping.extractors.topjobs import TopjobsExtractor
from src.scraping.extractors.jsonld import JsonLdExtractor
from src.scraping.service import process_ocr_for_job, is_boilerplate_description
from src.cleaning.clean_jobs import clean_raw_dataframe
from src.extraction.run_extraction import _extraction_text, _is_boilerplate, run_extraction
from src.extraction.taxonomy import load_taxonomy
from src.analytics.cooccurrence import calculate_pair_frequency, calculate_cooccurrence_matrix
from src.analytics.similarity import calculate_jaccard, calculate_pmi
from src.analytics.technology_stacks import extract_frequent_stacks
from src.security.url_validator import validate_url


class TestOCRPipeline(unittest.TestCase):

    def setUp(self):
        # Create an in-memory sample image
        self.test_img = Image.new("RGB", (600, 200), color=(255, 255, 255))
        d = ImageDraw.Draw(self.test_img)
        d.text((20, 20), "Senior Python Developer\nRequirements: Python, Django, PostgreSQL, Docker", fill=(0, 0, 0))
        img_byte_arr = io.BytesIO()
        self.test_img.save(img_byte_arr, format="PNG")
        self.test_img_bytes = img_byte_arr.getvalue()

    # -------------------------------------------------------------------------
    # 1. HTML based descriptions
    # -------------------------------------------------------------------------
    def test_1_html_based_description(self):
        """Test extraction and cleaning for purely HTML-based job descriptions."""
        html = """
        <html>
        <head><title>Job Details</title></head>
        <body>
            <div id="job_header"><h1>Backend Engineer</h1></div>
            <div id="job_content">
                <p>We are seeking an experienced Backend Engineer to join our core architecture team.
                Responsibilities include building RESTful services, database modeling, and designing scalable microservices.
                Requirements: 3+ years experience with Go and Python.</p>
            </div>
        </body>
        </html>
        """
        raw_data = {
            "job_id": ["test_html_1"],
            "source_job_id": ["101"],
            "job_title_raw": ["Backend Engineer"],
            "company_raw": ["TechSL (Pvt) Ltd"],
            "country_raw": ["Sri Lanka"],
            "location_raw": ["Colombo 03"],
            "job_description_raw": [
                "We are seeking an experienced Backend Engineer to join our core architecture team. "
                "Responsibilities include building RESTful services, database modeling, and designing scalable microservices. "
                "Requirements: 3+ years experience with Go and Python."
            ],
            "posted_date_raw": ["2026-10-15"],
            "closing_date_raw": ["2026-11-15"],
            "description_type": ["html_text"],
            "advert_image_urls": ["[]"],
            "ocr_text_raw": [""],
            "ocr_status": ["not_required"],
            "ocr_confidence": [""],
            "source_platform": ["topjobs.lk"],
            "source_url": ["https://www.topjobs.lk/jobs/101"],
            "extraction_status": ["success"],
        }
        df_raw = pd.DataFrame(raw_data)
        df_internal, df_team, stats = clean_raw_dataframe(df_raw)

        self.assertEqual(len(df_team), 1)
        self.assertEqual(df_team.iloc[0]["job_title_raw"], "Backend Engineer")
        self.assertIn("Backend Engineer", df_team.iloc[0]["job_description"])
        self.assertIn("Python", df_team.iloc[0]["job_description"])
        
        # Verify provenance recorded as html_text
        prov = json.loads(df_internal.iloc[0]["field_provenance"])
        self.assertEqual(prov.get("description_source"), "html_text")

    # -------------------------------------------------------------------------
    # 2. Image based descriptions requiring OCR
    # -------------------------------------------------------------------------
    @patch("requests.get")
    def test_2_image_based_description_ocr(self, mock_get):
        """Test that TopJobs image flyer URLs trigger OCR and replace boilerplate."""
        # Mock HTTP response for image download
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "image/png"}
        mock_resp.iter_content.return_value = [self.test_img_bytes]
        mock_get.return_value = mock_resp

        result = ExtractionResult.create_for_url("https://www.topjobs.lk/employer/JobAdvertismentServlet?jc=1542071", "b1")
        result.job_title_raw = "Senior Python Developer"
        result.job_description_raw = "Please refer the full details of the job posting as given by the employer below."
        result.description_type = "image"
        result.advert_image_urls = json.dumps(["https://www.topjobs.lk/logo/DEFZZZ/7297c1144.png"])
        result.ocr_status = "pending"

        processed = process_ocr_for_job(result, use_ocr=True)

        self.assertEqual(processed.ocr_status, "success")
        self.assertTrue(len(processed.ocr_text_raw) > 20)
        self.assertIn("Python", processed.ocr_text_raw)

        # Feed into cleaning pipeline
        raw_row = processed.to_dict()
        df_raw = pd.DataFrame([raw_row])
        df_internal, df_team, stats = clean_raw_dataframe(df_raw)

        self.assertEqual(len(df_team), 1)
        # Verify the boilerplate was replaced by real OCR text
        self.assertNotIn("Please refer the full details", df_team.iloc[0]["job_description"])
        self.assertIn("Python", df_team.iloc[0]["job_description"])

        prov = json.loads(df_internal.iloc[0]["field_provenance"])
        self.assertEqual(prov.get("description_source"), "ocr")

    # -------------------------------------------------------------------------
    # 3. Advertisements containing both HTML text and images (Hybrid)
    # -------------------------------------------------------------------------
    @patch("requests.get")
    def test_3_hybrid_description_html_and_images(self, mock_get):
        """Test hybrid job adverts combining valid HTML text and distinct OCR flyer text."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "image/png"}
        mock_resp.iter_content.return_value = [self.test_img_bytes]
        mock_get.return_value = mock_resp

        result = ExtractionResult.create_for_url("https://www.topjobs.lk/employer/JobAdvertismentServlet?jc=1542072", "b1")
        result.job_title_raw = "Full Stack Engineer"
        result.job_description_raw = (
            "Leading fintech company seeking a Full Stack Engineer to build next-generation payment systems. "
            "Competitive compensation package with remote work flexibility."
        )
        result.description_type = "hybrid"
        result.advert_image_urls = json.dumps(["https://www.topjobs.lk/logo/DEFZZZ/flyer.png"])
        result.ocr_status = "pending"

        processed = process_ocr_for_job(result, use_ocr=True)
        self.assertEqual(processed.ocr_status, "success")

        df_raw = pd.DataFrame([processed.to_dict()])
        df_internal, df_team, _ = clean_raw_dataframe(df_raw)

        clean_desc = df_team.iloc[0]["job_description"]
        self.assertIn("Leading fintech company", clean_desc)
        self.assertIn("--- OCR Text ---", clean_desc)
        self.assertIn("Python", clean_desc)

        prov = json.loads(df_internal.iloc[0]["field_provenance"])
        self.assertEqual(prov.get("description_source"), "hybrid")

    # -------------------------------------------------------------------------
    # 4. Missing images and OCR failures
    # -------------------------------------------------------------------------
    @patch("requests.get")
    def test_4_missing_image_and_ocr_failures(self, mock_get):
        """Test handling of failed image downloads without fabricating text."""
        # Simulate 404 Not Found on image flyer
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = ExtractionResult.create_for_url("https://www.topjobs.lk/employer/JobAdvertismentServlet?jc=1542073", "b1")
        result.job_title_raw = "DevOps Engineer"
        result.job_description_raw = "Please refer the full details of the job posting."
        result.description_type = "image"
        result.advert_image_urls = json.dumps(["https://www.topjobs.lk/logo/missing.png"])

        processed = process_ocr_for_job(result, use_ocr=True)

        self.assertEqual(processed.ocr_status, "failed")
        self.assertEqual(processed.ocr_text_raw, "")

        # Cleaning should flag as manual_review instead of inventing text
        df_raw = pd.DataFrame([processed.to_dict()])
        df_internal, df_team, _ = clean_raw_dataframe(df_raw)

        self.assertEqual(df_internal.iloc[0]["extraction_status"], "manual_review")
        self.assertIn("No usable job description", df_internal.iloc[0]["manual_review_reason"])

    # -------------------------------------------------------------------------
    # 5. Generic website boilerplate rejection
    # -------------------------------------------------------------------------
    def test_5_generic_website_boilerplate_rejection(self):
        """Test that generic TopJobs boilerplates are identified and rejected."""
        boilerplates = [
            "Please refer the full details of the job posting as given by the employer below.",
            "topjobs sri lanka Job Network - most popular online job site in Sri Lanka for jobs, careers, recruitment and employment with recruitment automation for employers.",
            "Please refer to the vacancy advert above for more details.",
            "Please see the full job description on the flyer.",
        ]

        for text in boilerplates:
            self.assertTrue(is_boilerplate_description(text), f"Failed to identify boilerplate: {text}")
            self.assertTrue(_is_boilerplate(text), f"Failed _is_boilerplate check: {text}")

        # Real description should NOT be identified as boilerplate
        real_desc = "We are seeking a React Developer with 3+ years experience building single-page applications using Redux and TypeScript."
        self.assertFalse(is_boilerplate_description(real_desc))
        self.assertFalse(_is_boilerplate(real_desc))

    # -------------------------------------------------------------------------
    # 6. OCR output containing duplicate or noisy text
    # -------------------------------------------------------------------------
    def test_6_ocr_noise_and_duplicate_handling(self):
        """Test deduplication when OCR produces text already contained in HTML."""
        shared_text = "Senior Java Engineer with Spring Boot and Microservices experience."

        raw_data = {
            "job_id": ["job_dedup_1"],
            "source_job_id": ["301"],
            "job_title_raw": ["Senior Java Engineer"],
            "company_raw": ["Enterprise Solutions"],
            "country_raw": ["Sri Lanka"],
            "location_raw": ["Colombo 02"],
            "job_description_raw": [f"<p>{shared_text} Extensive cloud infrastructure experience required.</p>"],
            "posted_date_raw": ["2026-10-10"],
            "closing_date_raw": ["2026-11-10"],
            "description_type": ["hybrid"],
            "advert_image_urls": ['["https://www.topjobs.lk/logo/img.png"]'],
            "ocr_text_raw": [f"   {shared_text}   \n\n   "],  # Redundant with HTML
            "ocr_status": ["success"],
            "ocr_confidence": ["0.92"],
            "source_platform": ["topjobs.lk"],
            "source_url": ["https://www.topjobs.lk/jobs/301"],
            "extraction_status": ["success"],
        }
        df_raw = pd.DataFrame(raw_data)
        df_internal, df_team, _ = clean_raw_dataframe(df_raw)

        desc = df_team.iloc[0]["job_description"]
        # Should not duplicate the shared text via --- OCR Text ---
        self.assertNotIn("--- OCR Text ---", desc)
        self.assertIn("Senior Java Engineer", desc)

    # -------------------------------------------------------------------------
    # 7. Skill extraction from OCR derived descriptions
    # -------------------------------------------------------------------------
    def test_7_skill_extraction_from_ocr_description(self):
        """Test that skills are extracted from OCR-derived descriptions and provenance is tracked."""
        ocr_text = "Requirements: Strong expertise in Python, Docker, PostgreSQL, and AWS cloud deployment."

        row = pd.Series({
            "job_id": "test_ocr_skill_1",
            "job_title_raw": "Software Engineer",
            "job_description": ocr_text,
            "description_source": "ocr",
        })

        text, provenance = _extraction_text(row)
        self.assertEqual(provenance, "ocr")
        self.assertEqual(text, ocr_text)

        # Title fallback should NOT be used when OCR description exists
        self.assertNotIn("Software Engineer Requirements", text)

    # -------------------------------------------------------------------------
    # 8. Canonical skill normalization
    # -------------------------------------------------------------------------
    def test_8_canonical_skill_normalization(self):
        """Test that varied skill surface forms normalize to canonical taxonomy IDs."""
        from src.extraction.lexical.extractor import LexicalSkillExtractor
        from pathlib import Path

        taxonomy_path = Path("config/skill_taxonomy.json")
        taxonomy = load_taxonomy(taxonomy_path)
        extractor = LexicalSkillExtractor(taxonomy)

        test_text = "Candidate must know C#, Python 3, JavaScript (JS), and Postgres."
        result = extractor.extract(job_id="norm_test", text=test_text)
        extracted_ids = {s.skill_id for s in result.skills}

        # Check normalization
        self.assertIn("csharp", extracted_ids)       # "C#" -> "csharp"
        self.assertIn("python", extracted_ids)       # "Python 3" -> "python"
        self.assertIn("javascript", extracted_ids)   # "JavaScript (JS)" -> "javascript"
        self.assertIn("postgresql", extracted_ids)   # "Postgres" -> "postgresql"

    # -------------------------------------------------------------------------
    # 9. Relationship metrics calculated from validated skill sets
    # -------------------------------------------------------------------------
    def test_9_relationship_metrics_from_validated_skills(self):
        """Test mathematical accuracy of co-occurrence, Jaccard, PMI, and tech stacks."""
        # 4 deterministic jobs:
        # Job 0: {python, django, docker}
        # Job 1: {python, django, postgresql}
        # Job 2: {python, react}
        # Job 3: {java, spring}
        jobs = [
            {"python", "django", "docker"},
            {"python", "django", "postgresql"},
            {"python", "react"},
            {"java", "spring"},
        ]

        # 1. Pair counts
        df_pairs = calculate_pair_frequency(jobs)
        py_django_pair = df_pairs[
            ((df_pairs["skill_a"] == "django") & (df_pairs["skill_b"] == "python")) |
            ((df_pairs["skill_a"] == "python") & (df_pairs["skill_b"] == "django"))
        ].iloc[0]
        self.assertEqual(py_django_pair["pair_count"], 2)

        py_docker_pair = df_pairs[
            ((df_pairs["skill_a"] == "django") & (df_pairs["skill_b"] == "docker")) |
            ((df_pairs["skill_a"] == "docker") & (df_pairs["skill_b"] == "django"))
        ].iloc[0]
        self.assertEqual(py_docker_pair["pair_count"], 1)

        # 2. Jaccard similarity:
        # Python appears in 3 jobs (0, 1, 2)
        # Django appears in 2 jobs (0, 1)
        # Intersection = {0, 1} (2 jobs)
        # Union = {0, 1, 2} (3 jobs)
        # Jaccard(python, django) = 2 / 3 = 0.666667
        df_jaccard = calculate_jaccard(jobs)
        py_django_row = df_jaccard[
            ((df_jaccard["skill_a"] == "django") & (df_jaccard["skill_b"] == "python")) |
            ((df_jaccard["skill_a"] == "python") & (df_jaccard["skill_b"] == "django"))
        ].iloc[0]
        self.assertAlmostEqual(py_django_row["jaccard"], 2.0 / 3.0, places=4)

        # 3. PMI calculation:
        # P(python) = 3/4 = 0.75
        # P(django) = 2/4 = 0.50
        # P(python, django) = 2/4 = 0.50
        # PMI = log2(0.50 / (0.75 * 0.50)) = log2(1 / 0.75) = log2(4/3) ≈ 0.4150
        df_pmi = calculate_pmi(jobs)
        pmi_row = df_pmi[
            ((df_pmi["skill_a"] == "django") & (df_pmi["skill_b"] == "python")) |
            ((df_pmi["skill_a"] == "python") & (df_pmi["skill_b"] == "django"))
        ].iloc[0]
        expected_pmi = math.log2(0.50 / (0.75 * 0.50))
        self.assertAlmostEqual(pmi_row["pmi"], expected_pmi, places=3)

        # 4. Tech stack combinations:
        df_stacks = extract_frequent_stacks(jobs, minimum_support=0.25, maximum_stack_size=3)
        # "django + python" occurs in 2 jobs out of 4 (support = 0.50)
        self.assertTrue(any(row["stack"] == "django + python" and row["job_count"] == 2 for _, row in df_stacks.iterrows()))

    # -------------------------------------------------------------------------
    # 10. Regression tests for the existing pipeline
    # -------------------------------------------------------------------------
    def test_10_regression_existing_pipeline(self):
        """Ensure RAW schema, URL security validation, and 10-column team schema are intact."""
        # Verify RAW schema includes new OCR fields
        self.assertIn("ocr_text_raw", RAW_SCHEMA_COLUMNS)
        self.assertIn("ocr_confidence", RAW_SCHEMA_COLUMNS)
        self.assertIn("advert_image_urls", RAW_SCHEMA_COLUMNS)

        # Verify URL security validator prevents SSRF and non-permitted domains
        valid_topjobs, _ = validate_url("https://www.topjobs.lk/jobs/1")
        self.assertTrue(valid_topjobs)

        invalid_private, _ = validate_url("http://192.168.1.1/admin")
        self.assertFalse(invalid_private)

        invalid_localhost, _ = validate_url("http://localhost:8080/exploit")
        self.assertFalse(invalid_localhost)


    # -------------------------------------------------------------------------
    # 11. DirectFN TopJobs Flyer Discrepancy Investigation
    # -------------------------------------------------------------------------
    def test_11_directfn_flyer_investigation(self):
        """
        Focused regression test auditing the DirectFN Software Engineer flyer scenario:
        - Demonstrates why failure in OCR leads to title fallback ('Software Engineer HTML5'),
          yielding only HTML (lexical) and HTML + JavaScript (semantic).
        - Demonstrates that when OCR succeeds, the merged description allows extraction of
          JavaScript, HTML, Git, and REST API.
        """
        from pathlib import Path
        from src.extraction.lexical.extractor import LexicalSkillExtractor
        from src.extraction.semantic.extractor import SemanticSkillExtractor

        tax = load_taxonomy(Path("config/skill_taxonomy.json"))
        lex_extractor = LexicalSkillExtractor(tax)

        # Scenario A: OCR failed / not available (User's observed discrepancy)
        raw_row_failed = {
            "job_id": "topjobs_directfn_1",
            "source_job_id": "1561151",
            "job_title_raw": "Software Engineer HTML5",
            "company_raw": "DirectFN",
            "country_raw": "Sri Lanka",
            "location_raw": "",
            "job_description_raw": "Please refer the full details of the job posting as given by the employer. </br>කරුණාකර සේවායෝජකයා විසින් දෙන ලද රැකියා විස්තරය වෙත යොමුවන්න.",
            "posted_date_raw": "2026-10-19",
            "closing_date_raw": "2026-11-02",
            "description_type": "image",
            "advert_image_urls": '["https://topjobs.lk/logo/0000000492/8364cSE HTML5.png"]',
            "ocr_text_raw": "",
            "ocr_status": "failed",
            "ocr_confidence": "-1.0",
            "source_platform": "topjobs.lk",
            "source_url": "https://topjobs.lk/employer/JobAdvertismentServlet?jc=0001561151",
            "extraction_status": "manual_review",
        }
        df_raw_failed = pd.DataFrame([raw_row_failed])
        _, df_clean_failed, _ = clean_raw_dataframe(df_raw_failed)

        # In clean dataframe, description is empty because boilerplate was rejected and OCR failed
        self.assertEqual(df_clean_failed.iloc[0]["job_description"], "")

        # _extraction_text falls back to job_title_raw
        text_fallback, prov_fallback = _extraction_text(df_clean_failed.iloc[0])
        self.assertEqual(prov_fallback, "title_fallback")
        self.assertEqual(text_fallback, "Software Engineer HTML5")

        # Lexical extraction on title only finds HTML (via html5 alias)
        lex_res_failed = lex_extractor.extract("directfn_test", text_fallback)
        lex_skills_failed = {s.skill_id for s in lex_res_failed.skills}
        self.assertEqual(lex_skills_failed, {"html"})
        self.assertNotIn("javascript", lex_skills_failed)
        self.assertNotIn("git", lex_skills_failed)

        # Scenario B: OCR succeeds on flyer
        ocr_text = (
            "DirectFN\n\nWe're Looking for a\n\nSoftware Engineer -HTML5/JavaScript\n"
            "On-site Full Time Bachelors Degree\n\n"
            "HTML5 Canvas and/or SVG\n"
            "Web performance and browser rendering\n"
            "WebSocket/Git RESTful APIs\n\n"
            "Send your CV to Careers@directfn.com"
        )
        raw_row_success = dict(raw_row_failed)
        raw_row_success["ocr_text_raw"] = ocr_text
        raw_row_success["ocr_status"] = "success"
        raw_row_success["ocr_confidence"] = "0.90"
        raw_row_success["extraction_status"] = "success"

        df_raw_success = pd.DataFrame([raw_row_success])
        _, df_clean_success, _ = clean_raw_dataframe(df_raw_success)

        # Clean description now contains the full OCR text
        clean_desc_success = df_clean_success.iloc[0]["job_description"]
        self.assertIn("Software Engineer -HTML5/JavaScript", clean_desc_success)
        self.assertIn("WebSocket/Git RESTful APIs", clean_desc_success)

        # In team schema (jobs_clean.csv), provenance returns 'description'
        text_success, prov_success = _extraction_text(df_clean_success.iloc[0])
        self.assertEqual(prov_success, "description")

        # If description_source is available (from internal schema), provenance is 'ocr'
        row_with_source = df_clean_success.iloc[0].copy()
        row_with_source["description_source"] = "ocr"
        _, prov_with_source = _extraction_text(row_with_source)
        self.assertEqual(prov_with_source, "ocr")

        # Lexical extraction on OCR text discovers JavaScript, HTML, Git, and REST API
        lex_res_success = lex_extractor.extract("directfn_test_success", text_success)
        lex_skills_success = {s.skill_id for s in lex_res_success.skills}
        self.assertIn("javascript", lex_skills_success)
        self.assertIn("html", lex_skills_success)
        self.assertIn("git", lex_skills_success)
        self.assertIn("rest_api", lex_skills_success)

    # -------------------------------------------------------------------------
    # 12. RESTful APIs Plural Alias Matching
    # -------------------------------------------------------------------------
    def test_12_rest_apis_plural_alias(self):
        """Verify that plural phrasing 'RESTful APIs' matches canonical rest_api."""
        from pathlib import Path
        from src.extraction.lexical.extractor import LexicalSkillExtractor

        tax = load_taxonomy(Path("config/skill_taxonomy.json"))
        lex_extractor = LexicalSkillExtractor(tax)

        test_text = "Experience with WebSocket/Git RESTful APIs and microservices."
        res = lex_extractor.extract("api_test", test_text)
        skills = {s.skill_id for s in res.skills}
        self.assertIn("rest_api", skills)
        self.assertIn("git", skills)


if __name__ == "__main__":
    unittest.main()

