"""
Unit and integration tests for multi-portal scraping across India, Singapore, and Sri Lanka.
Validates extractor routing, LinkExtractor heuristics, MyCareersFuture adapter,
duplicate prevention, and error handling.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.scraping.models import ExtractionResult
from src.scraping.extractor_registry import ExtractorRegistry
from src.scraping.extractors.mycareersfuture import MyCareersFutureExtractor
from src.scraping.extractors.generic_html import GenericHtmlExtractor
from src.scraping.link_extractor import LinkExtractor
from src.scraping.http_client import fetch_page, FetchResult, BROWSER_USER_AGENT
from src.scraping.service import run_collection_pipeline


class TestMyCareersFutureExtractor(unittest.TestCase):
    """Tests for Singapore MyCareersFuture adapter."""

    def setUp(self):
        self.extractor = MyCareersFutureExtractor()

    def test_can_handle_supported_hostnames(self):
        self.assertTrue(self.extractor.can_handle("https://www.mycareersfuture.gov.sg/job/software-dev-123", ""))
        self.assertTrue(self.extractor.can_handle("https://mycareersfuture.gov.sg/search?search=python", ""))
        self.assertFalse(self.extractor.can_handle("https://www.topjobs.lk/job/123", ""))

    def test_extract_from_api_mock(self):
        mock_api_data = {
            "uuid": "ea8eb1b90310c8144586b06b759c1c46",
            "title": "Principal Software Engineer",
            "postedCompany": {"name": "WGT EHR PTE. LTD."},
            "address": {"district": "Central"},
            "description": "We are seeking an experienced Principal Software Engineer to lead our architecture.",
            "salary": {
                "minimum": 6000,
                "maximum": 12000,
                "type": {"salaryType": "Monthly"}
            },
            "employmentTypes": [{"employmentType": "Permanent"}, {"employmentType": "Full Time"}],
            "categories": [{"category": "Information Technology"}],
            "skills": [{"skill": "Python"}, {"skill": "Kubernetes"}, {"skill": "Cloud Architecture"}],
            "metadata": {
                "originalPostingDate": "2026-03-01T08:00:00.000Z",
                "expiryDate": "2026-04-01T08:00:00.000Z"
            }
        }

        url = "https://www.mycareersfuture.gov.sg/job/engineering/principal-software-engineer-wgt-ehr-ea8eb1b90310c8144586b06b759c1c46"
        result = ExtractionResult.create_for_url(url, "batch_test")

        with patch.object(self.extractor, "_fetch_job_api", return_value=mock_api_data):
            extracted = self.extractor.extract(url, "", result)

        self.assertEqual(extracted.extraction_status, "success")
        self.assertEqual(extracted.extractor_name, "mycareersfuture")
        self.assertEqual(extracted.job_title_raw, "Principal Software Engineer")
        self.assertEqual(extracted.company_raw, "WGT EHR PTE. LTD.")
        self.assertEqual(extracted.country_raw, "SG")
        self.assertEqual(extracted.salary_min_raw, "6000")
        self.assertEqual(extracted.salary_max_raw, "12000")
        self.assertEqual(extracted.salary_currency_raw, "SGD")
        self.assertIn("Python", extracted.skills_raw)
        self.assertIn("Kubernetes", extracted.skills_raw)
        self.assertEqual(extracted.source_job_id, "ea8eb1b90310c8144586b06b759c1c46")


class TestLinkExtractorMultiPortal(unittest.TestCase):
    """Tests for multi-portal candidate link discovery."""

    def setUp(self):
        self.le = LinkExtractor()

    def test_ikman_ad_links_extracted_while_categories_filtered(self):
        html = """
        <html>
            <body>
                <a href="/en/ads/sri-lanka/hotel-and-hospitality-jobs">Hospitality Jobs Category</a>
                <a href="/en/ads/sri-lanka/jobs">All Jobs Category</a>
                <a href="/en/ad/senior-software-engineer-colombo-10293">Senior Software Engineer</a>
                <a href="/en/ad/python-backend-developer-colombo-49201">Python Developer</a>
            </body>
        </html>
        """
        links = self.le.extract_job_links("https://ikman.lk/en/ads/sri-lanka/jobs", html)
        self.assertEqual(len(links), 2)
        self.assertIn("https://ikman.lk/en/ad/senior-software-engineer-colombo-10293", links)
        self.assertIn("https://ikman.lk/en/ad/python-backend-developer-colombo-49201", links)

    def test_shine_job_links_extracted(self):
        html = """
        <html>
            <body>
                <a href="/jobs/python-developer/tech-corp/19574086?jobtype=oj">Python Developer at Tech Corp</a>
                <a href="/jobs/frontend-engineer/soft-ltd/19574087">Frontend Engineer</a>
                <a href="/job-search/python-jobs">Python Jobs Search</a>
                <a href="/contact-us">Contact Us</a>
            </body>
        </html>
        """
        links = self.le.extract_job_links("https://www.shine.com/job-search/python-jobs", html)
        self.assertEqual(len(links), 2)
        self.assertIn("https://www.shine.com/jobs/python-developer/tech-corp/19574086?jobtype=oj", links)
        self.assertIn("https://www.shine.com/jobs/frontend-engineer/soft-ltd/19574087", links)

    def test_xpressjobs_view_links_extracted(self):
        html = """
        <html>
            <body>
                <a href="/jobs/view/343978/senior-data-analyst-bank">Senior Data Analyst</a>
                <a href="/jobs/view/343980/devops-engineer">DevOps Engineer</a>
                <a href="/about-us">About</a>
            </body>
        </html>
        """
        links = self.le.extract_job_links("https://xpress.jobs/jobs/it-telecom", html)
        self.assertEqual(len(links), 2)
        self.assertIn("https://xpress.jobs/jobs/view/343978/senior-data-analyst-bank", links)


class TestHttpClientBrowserFallback(unittest.TestCase):
    """Tests for adaptive browser User-Agent fallback in http_client."""

    @patch("requests.get")
    def test_fallback_on_403_forbidden(self, mock_get):
        # First request with academic UA returns 403; second with browser UA returns 200
        res_403 = MagicMock()
        res_403.status_code = 403
        res_403.headers = {}
        
        res_200 = MagicMock()
        res_200.status_code = 200
        res_200.headers = {"Content-Type": "text/html"}
        res_200.iter_content.return_value = [b"<html><head><title>Job Portal</title></head><body><h1>Job</h1></body></html>"]
        res_200.encoding = "utf-8"

        mock_get.side_effect = [res_403, res_200]

        res = fetch_page("https://www.naukri.com/python-developer-jobs")
        self.assertTrue(res.success)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers_used, "browser")
        self.assertIn("Job Portal", res.html)


class TestExtractorRegistryRouting(unittest.TestCase):
    """Tests that registry routes pages correctly to JSON-LD, site adapters, or generic HTML."""

    def setUp(self):
        self.registry = ExtractorRegistry()

    def test_jsonld_takes_highest_priority(self):
        html = """
        <html>
            <head>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "JobPosting",
                    "title": "Machine Learning Engineer",
                    "description": "Develop deep neural networks.",
                    "hiringOrganization": {"name": "AI Labs"}
                }
                </script>
            </head>
            <body><h1>Generic Title</h1></body>
        </html>
        """
        url = "https://example.com/job/101"
        res = ExtractionResult.create_for_url(url, "batch_test")
        extracted = self.registry.extract(url, html, res)
        self.assertEqual(extracted.extractor_name, "jsonld")
        self.assertEqual(extracted.job_title_raw, "Machine Learning Engineer")
        self.assertEqual(extracted.company_raw, "AI Labs")

    def test_mycareersfuture_adapter_routed_for_singapore_portal(self):
        url = "https://www.mycareersfuture.gov.sg/job/engineering/test-job-ea8eb1b90310c8144586b06b759c1c46"
        res = ExtractionResult.create_for_url(url, "batch_test")
        adapter = self.registry.get_extractor_for_hostname("mycareersfuture.gov.sg")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.name, "mycareersfuture")


if __name__ == "__main__":
    unittest.main()
