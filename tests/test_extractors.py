"""
Unit tests for the job extractors and extractor registry.
"""

import unittest
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.scraping.models import ExtractionResult
from src.scraping.extractors.jsonld import JsonLdExtractor
from src.scraping.extractors.topjobs import TopjobsExtractor
from src.scraping.extractors.generic_html import GenericHtmlExtractor
from src.scraping.extractor_registry import ExtractorRegistry


class TestJobExtractors(unittest.TestCase):

    def test_jsonld_extractor_single_job(self):
        html_content = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": "Software Engineer",
                "hiringOrganization": {
                    "@type": "Organization",
                    "name": "Acme Tech"
                },
                "jobLocation": {
                    "@type": "Place",
                    "name": "Colombo, Sri Lanka"
                },
                "description": "<p>We are looking for a Software Engineer...</p>",
                "datePosted": "2026-08-25",
                "validThrough": "2026-09-25",
                "employmentType": "FULL_TIME",
                "identifier": {
                    "@type": "PropertyValue",
                    "name": "Acme Tech",
                    "value": "ACME-101"
                }
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        extractor = JsonLdExtractor()
        url = "https://example.com/jobs/101"
        self.assertTrue(extractor.can_handle(url, html_content))

        result = ExtractionResult.create_for_url(url, "batch_test")
        result = extractor.extract(url, html_content, result)

        self.assertEqual(result.extraction_status, "success")
        self.assertEqual(result.job_title_raw, "Software Engineer")
        self.assertEqual(result.company_raw, "Acme Tech")
        self.assertEqual(result.location_raw, "Colombo, Sri Lanka")
        self.assertEqual(result.job_description_raw, "<p>We are looking for a Software Engineer...</p>")
        self.assertEqual(result.posted_date_raw, "2026-08-25")
        self.assertEqual(result.closing_date_raw, "2026-09-25")
        self.assertEqual(result.employment_type_raw, "FULL_TIME")
        self.assertEqual(result.source_job_id, "ACME-101")
        self.assertEqual(result.job_id, "example.com_ACME-101")

    def test_xpressjobs_requirements_and_days_left(self):
        description = """
        <p>
            <strong>Description</strong>
        </p>

        <p>
            <strong>Job Purpose</strong>
        </p>

        <p>
            We are looking for a Senior Machine Learning Engineer
            to join our technology team.
        </p>

        <p>
            <strong>Entry Requirements</strong>
        </p>

        <p>
            <strong>Qualifications &amp; Experience</strong>
        </p>

        <ul>
            <li>Bachelor's Degree in Computer Science.</li>
            <li>3 to 5 years of relevant experience.</li>
            <li>Strong Python programming skills.</li>
        </ul>

        <p>
            <strong>
                PLEASE CLICK THE APPLY BUTTON TO SEND YOUR CV VIA XPRESSJOBS
            </strong>
        </p>
        """

        html_content = f"""
        <html>
        <head>
            <script type="application/ld+json">
            {json.dumps({
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": "Senior Machine Learning Engineer",
                "hiringOrganization": {
                    "@type": "Organization",
                    "name": "Example Company"
                },
                "description": description,
                "datePosted": "2026-08-25"
            })}
            </script>
        </head>

        <body>
            <div>
                7 Days Left to Apply
            </div>
        </body>
        </html>
        """

        extractor = JsonLdExtractor()

        url = (
            "https://xpress.jobs/jobs/view/"
            "323053/senior-machine-learning-engineer"
        )

        result = ExtractionResult.create_for_url(
            url,
            "batch_test"
        )

        result = extractor.extract(
            url,
            html_content,
            result
        )

        self.assertEqual(
            result.extraction_status,
            "success"
        )

        self.assertIn(
            "Bachelor's Degree in Computer Science",
            result.requirements_raw
        )

        self.assertIn(
            "3 to 5 years of relevant experience",
            result.requirements_raw
        )

        today = datetime.now(
            ZoneInfo("Asia/Colombo")
        ).date()

        expected_closing_date = (
            today + timedelta(days=7)
        ).strftime("%Y-%m-%d")

        self.assertEqual(
            result.closing_date_raw,
            expected_closing_date
        )

    def test_topjobs_extractor(self):
        html_content = """
        <html>
        <body>
            <span id="position">Senior Data Engineer</span>
            <span id="employer">Virtusa</span>
            <span id="adview-job-location">Colombo 02</span>
            <div id="remark">
                <p>We are looking for a Senior Data Engineer with python skills, SQL databases, cloud experience, communication skills, and team management abilities in a fast-paced environment.</p>
                <img src="/images/advertisements/ad_123.png">
            </div>
        </body>
        </html>
        """
        extractor = TopjobsExtractor()
        url = "https://www.topjobs.lk/employer/JobAdvertismentServlet?jc=1540527"
        self.assertTrue(extractor.can_handle(url, html_content))

        result = ExtractionResult.create_for_url(url, "batch_test")
        result = extractor.extract(url, html_content, result)

        self.assertEqual(result.extraction_status, "success")
        self.assertEqual(result.job_title_raw, "Senior Data Engineer")
        self.assertEqual(result.company_raw, "Virtusa")
        self.assertEqual(result.location_raw, "Colombo 02")
        self.assertIn("We are looking for a Senior Data Engineer", result.job_description_raw)
        self.assertIn("ad_123.png", result.advert_image_urls)
        self.assertEqual(result.description_type, "hybrid")
        self.assertEqual(result.source_job_id, "1540527")
        self.assertEqual(result.job_id, "topjobs.lk_1540527")

    def test_generic_html_extractor(self):
        html_content = """
        <html>
        <head>
            <title>QA Engineer Lead at WSO2</title>
            <meta name="description" content="Join our QA team as a lead engineer.">
        </head>
        <body>
            <h1>QA Lead Role</h1>
            <main>
                <p>Detailed job description about testing software products in Colombo office. We require 5+ years of experience in test automation, Selenium, CI/CD pipelines, and agile methodologies.</p>
            </main>
        </body>
        </html>
        """
        extractor = GenericHtmlExtractor()
        url = "https://wso2.com/jobs/qa-lead"
        self.assertTrue(extractor.can_handle(url, html_content))

        result = ExtractionResult.create_for_url(url, "batch_test")
        result = extractor.extract(url, html_content, result)

        # Generic extraction is evaluated as success since title and description (>100 chars) are present
        self.assertEqual(result.extraction_status, "success")
        self.assertEqual(result.job_title_raw, "QA Lead Role")  # prefer <h1> over <title>
        self.assertIn("Detailed job description", result.job_description_raw)

    def test_extractor_registry_priority(self):
        # Page with both JSON-LD and Topjobs selectors
        html_content = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": "JSON-LD Software Developer",
                "description": "JSON-LD description body"
            }
            </script>
        </head>
        <body>
            <span id="position">HTML Software Developer</span>
            <span id="employer">HTML Employer</span>
        </body>
        </html>
        """
        registry = ExtractorRegistry()
        url = "https://www.topjobs.lk/employer/JobAdvertismentServlet?jc=1540"

        result = ExtractionResult.create_for_url(url, "batch_test")
        result = registry.extract(url, html_content, result)

        # JSON-LD should be chosen because it's higher priority than Site Adapter
        self.assertEqual(result.extractor_name, "jsonld")
        self.assertEqual(result.job_title_raw, "JSON-LD Software Developer")


if __name__ == "__main__":
    unittest.main()
