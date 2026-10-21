"""
Unit and regression tests for foreign job portal adapters, source registry governance,
and offline HTML fixtures across India, Singapore, and Malaysia.

Academic Research Component for Regional Comparative IT Labor-Market Analysis.
All tests run 100% offline using local fixtures with zero live portal dependencies.
"""

import os
import pathlib
import unittest
from unittest.mock import patch, MagicMock

from src.scraping.models import ExtractionResult
from src.scraping.source_registry import SourceRegistry, SourceConfig, get_source_registry
from src.scraping.extractors.shine import ShineExtractor
from src.scraping.extractors.timesjobs import TimesJobsExtractor
from src.scraping.extractors.mycareersfuture import MyCareersFutureExtractor
from src.scraping.extractor_registry import ExtractorRegistry
from src.scraping.link_extractor import LinkExtractor
from src.security.url_validator import validate_url, validate_redirect_url


FIXTURES_DIR = pathlib.Path(__file__).resolve().parent / "fixtures"


def load_fixture(filename: str) -> str:
    """Reads fixture file from tests/fixtures directory."""
    filepath = FIXTURES_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Fixture file missing: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


class TestSourceRegistryGovernance(unittest.TestCase):
    """Tests for configurable source registry governance and ethical access control."""

    def setUp(self):
        self.registry = get_source_registry()

    def test_registry_loads_all_target_countries(self):
        """Verify sources for India, Singapore, Malaysia, and Sri Lanka are registered."""
        sources = self.registry.list_sources()
        countries = {s.supported_country for s in sources}
        self.assertIn("India", countries)
        self.assertIn("Singapore", countries)
        self.assertIn("Malaysia", countries)
        self.assertIn("Sri Lanka", countries)

    def test_hostname_and_alias_resolution(self):
        """Verify hostnames and aliases resolve correctly to the parent source configuration."""
        # Shine aliases
        s1 = self.registry.get_source("https://www.shine.com/jobs/dev/123")
        s2 = self.registry.get_source("https://recruiter.shine.com/job/456")
        self.assertIsNotNone(s1)
        self.assertIsNotNone(s2)
        self.assertEqual(s1.source_hostname, "shine.com")
        self.assertEqual(s2.source_hostname, "shine.com")
        self.assertEqual(s1.supported_country, "India")

        # Singapore MyCareersFuture
        mcf = self.registry.get_source("https://www.mycareersfuture.gov.sg/job/tech-ea8eb1b90310c8144586b06b759c1c46")
        self.assertIsNotNone(mcf)
        self.assertEqual(mcf.supported_country, "Singapore")
        self.assertTrue(mcf.is_validated)

    def test_url_classification_detail_vs_listing(self):
        """Verify listing and detail page patterns correctly classify candidate URLs."""
        # Shine detail vs listing
        t_detail, _ = self.registry.classify_url("https://www.shine.com/jobs/python-lead/infosys/19582041")
        t_listing, _ = self.registry.classify_url("https://www.shine.com/job-search/python-jobs")
        self.assertEqual(t_detail, "detail")
        self.assertEqual(t_listing, "listing")

        # TimesJobs detail vs listing
        tj_detail, _ = self.registry.classify_url("https://www.timesjobs.com/job-detail/full-stack-12345.html")
        tj_listing, _ = self.registry.classify_url("https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch")
        self.assertEqual(tj_detail, "detail")
        self.assertEqual(tj_listing, "listing")

    def test_access_restricted_policy_detection(self):
        """Portals protected by anti-bot perimeter defenses must be flagged as access_restricted."""
        # Naukri India
        permitted_nk, status_nk, reason_nk = self.registry.check_access_permission("https://www.naukri.com/python-jobs")
        self.assertFalse(permitted_nk)
        self.assertEqual(status_nk, "access_restricted")
        self.assertIn("anti-bot", reason_nk.lower())

        # JobStreet Malaysia
        permitted_js, status_js, reason_js = self.registry.check_access_permission("https://my.jobstreet.com/jobs")
        self.assertFalse(permitted_js)
        self.assertEqual(status_js, "access_restricted")
        self.assertIn("perimeter", reason_js.lower())

    def test_rate_limiting_and_timeout_governance(self):
        """Ensure polite throttling delays and timeouts are retrievable per source."""
        shine_delay = self.registry.get_rate_limit("shine.com")
        self.assertGreaterEqual(shine_delay, 2.0)
        tj_delay = self.registry.get_rate_limit("timesjobs.com")
        self.assertGreaterEqual(tj_delay, 2.5)


class TestShineExtractorAdapter(unittest.TestCase):
    """Tests for Shine.com (India) dedicated site adapter using offline fixtures."""

    def setUp(self):
        self.extractor = ShineExtractor()

    def test_shine_detail_bengaluru_extraction(self):
        """Verify accurate extraction of Indian IT vacancy in Bengaluru with INR salary."""
        html = load_fixture("shine_detail_bengaluru.html")
        url = "https://www.shine.com/jobs/senior-python-backend-developer/infosys-limited/19582041"
        res = ExtractionResult.create_for_url(url, "batch_test_in")

        extracted = self.extractor.extract(url, html, res)

        self.assertEqual(extracted.extraction_status, "success")
        self.assertEqual(extracted.extractor_name, "shine")
        self.assertEqual(extracted.job_title_raw, "Senior Python Backend Developer")
        self.assertEqual(extracted.company_raw, "Infosys Limited")
        self.assertIn("Bengaluru", extracted.location_raw)
        self.assertEqual(extracted.country_raw, "India")
        self.assertEqual(extracted.salary_min_raw, "1500000")
        self.assertEqual(extracted.salary_max_raw, "2500000")
        self.assertEqual(extracted.salary_currency_raw, "INR")
        self.assertIn("Python", extracted.skills_raw)
        self.assertIn("Kubernetes", extracted.skills_raw)
        self.assertEqual(extracted.source_job_id, "19582041")

    def test_shine_international_multi_location_does_not_coerce_to_india(self):
        """Non-Indian vacancy on an Indian portal must not be assumed to be in India."""
        html = load_fixture("shine_detail_remote_international.html")
        url = "https://www.shine.com/jobs/staff-cloud-solutions-architect/fintech-global/19582099"
        res = ExtractionResult.create_for_url(url, "batch_test_in")

        extracted = self.extractor.extract(url, html, res)

        self.assertEqual(extracted.extraction_status, "success")
        self.assertEqual(extracted.job_title_raw, "Staff Cloud Solutions Architect")
        self.assertEqual(extracted.company_raw, "FinTech Global Pte Ltd")
        # Confirms country is recognized as Singapore, NOT coerced to India
        self.assertEqual(extracted.country_raw, "Singapore")
        self.assertEqual(extracted.work_mode_raw, "remote")
        self.assertIn("AWS", extracted.skills_raw)
        self.assertIn("Terraform", extracted.skills_raw)

    def test_shine_missing_fields_partial_status(self):
        """When fields like salary or closing date are undisclosed, do not invent values."""
        html = load_fixture("shine_detail_missing_fields.html")
        url = "https://www.shine.com/jobs/frontend-react-developer/startup-berhad/19582088"
        res = ExtractionResult.create_for_url(url, "batch_test_in")

        extracted = self.extractor.extract(url, html, res)

        self.assertIn(extracted.extraction_status, ("success", "partial"))
        self.assertEqual(extracted.job_title_raw, "Frontend React Developer")
        self.assertEqual(extracted.company_raw, "StartUp Berhad")
        self.assertEqual(extracted.country_raw, "Malaysia")
        # Salary undisclosed: must be empty, not fabricated
        self.assertEqual(extracted.salary_min_raw, "")
        self.assertEqual(extracted.salary_max_raw, "")
        self.assertEqual(extracted.closing_date_raw, "")


class TestTimesJobsExtractorAdapter(unittest.TestCase):
    """Tests for TimesJobs.com (India) dedicated site adapter using offline fixtures."""

    def setUp(self):
        self.extractor = TimesJobsExtractor()

    def test_timesjobs_detail_extraction(self):
        """Verify extraction from TimesJobs HTML structure."""
        html = load_fixture("timesjobs_detail.html")
        url = "https://www.timesjobs.com/job-detail/lead-full-stack-engineer-tata-consultancy-services-987654.html"
        res = ExtractionResult.create_for_url(url, "batch_test_tj")

        extracted = self.extractor.extract(url, html, res)

        self.assertEqual(extracted.extraction_status, "success")
        self.assertEqual(extracted.extractor_name, "timesjobs")
        self.assertEqual(extracted.job_title_raw, "Lead Full Stack Engineer")
        self.assertEqual(extracted.company_raw, "Tata Consultancy Services")
        self.assertIn("Hyderabad", extracted.location_raw)
        self.assertEqual(extracted.country_raw, "India")
        self.assertEqual(extracted.salary_min_raw, "1800000")
        self.assertEqual(extracted.salary_max_raw, "2800000")
        self.assertEqual(extracted.salary_currency_raw, "INR")
        self.assertIn("Java", extracted.skills_raw)
        self.assertIn("Kafka", extracted.skills_raw)
        self.assertEqual(extracted.source_job_id, "987654")


class TestMyCareersFutureAdapter(unittest.TestCase):
    """Tests for MyCareersFuture (Singapore) dedicated site adapter."""

    def setUp(self):
        self.extractor = MyCareersFutureExtractor()

    def test_mycareersfuture_dom_fallback_extraction(self):
        """Verify extraction from rendered DOM elements when API is offline/bypassed."""
        html = load_fixture("mycareersfuture_detail.html")
        url = "https://www.mycareersfuture.gov.sg/job/security/senior-cyber-security-specialist-ea8eb1b90310c8144586b06b759c1c46"
        res = ExtractionResult.create_for_url(url, "batch_test_sg")

        # Force DOM fallback by providing empty API response
        with patch.object(self.extractor, "_fetch_job_api", return_value={}):
            extracted = self.extractor.extract(url, html, res)

        self.assertIn(extracted.extraction_status, ("success", "partial"))
        self.assertEqual(extracted.job_title_raw, "Senior Cyber Security Specialist")
        self.assertIn("Central", extracted.location_raw)


class TestExtractorRegistryAccessGovernance(unittest.TestCase):
    """Tests that ExtractorRegistry halts access-restricted portals with diagnostic errors."""

    def setUp(self):
        self.registry = ExtractorRegistry()

    def test_naukri_access_restricted_returns_blocked_status(self):
        """Naukri URL must be marked as blocked without making live network requests."""
        html = load_fixture("access_restricted_naukri.html")
        url = "https://www.naukri.com/job-listings-python-dev-12345"
        res = ExtractionResult.create_for_url(url, "batch_test")

        extracted = self.registry.extract(url, html, res)

        self.assertEqual(extracted.extraction_status, "blocked")
        self.assertEqual(extracted.error_type, "blocked")
        self.assertIn("anti-bot", extracted.error_message.lower())

    def test_jobstreet_access_restricted_returns_blocked_status(self):
        """JobStreet Malaysia URL must be marked as blocked with perimeter defense reason."""
        url = "https://my.jobstreet.com/job/123456"
        res = ExtractionResult.create_for_url(url, "batch_test")

        extracted = self.registry.extract(url, "<html>Challenge</html>", res)

        self.assertEqual(extracted.extraction_status, "blocked")
        self.assertEqual(extracted.error_type, "blocked")
        self.assertIn("perimeter", extracted.error_message.lower())


class TestLinkExtractorForeignPortals(unittest.TestCase):
    """Tests that LinkExtractor discovers detail links and filters navigation on foreign listings."""

    def setUp(self):
        self.le = LinkExtractor()

    def test_shine_search_listing_extracts_detail_links_and_filters_categories(self):
        """Verify candidate vacancy links are extracted while categories/filters are omitted."""
        html = load_fixture("shine_search_listing.html")
        base_url = "https://www.shine.com/job-search/python-jobs"

        links = self.le.extract_job_links(base_url, html)

        self.assertGreaterEqual(len(links), 4)
        self.assertTrue(any("19582001" in link for link in links))
        self.assertTrue(any("19582002" in link for link in links))
        self.assertTrue(any("19582003" in link for link in links))
        self.assertTrue(any("19582004" in link for link in links))

        # Check navigation / category links are filtered out
        self.assertFalse(any("privacy-policy" in link for link in links))
        self.assertFalse(any("login" in link for link in links))
        self.assertFalse(any("category" in link for link in links))


class TestURLSecurityAndRedirectRevalidation(unittest.TestCase):
    """Tests SSRF protection, redirect target validation, and non-standard schemes."""

    def test_foreign_redirect_to_private_ip_is_blocked(self):
        """Redirecting from an approved foreign domain to internal/metadata IPs must be blocked."""
        is_valid, reason = validate_redirect_url(
            "https://www.shine.com/job/101",
            "http://169.254.169.254/latest/meta-data/"
        )
        self.assertFalse(is_valid)
        self.assertIn("SSRF", reason)

    def test_foreign_redirect_to_localhost_is_blocked(self):
        """Redirecting to localhost must be blocked."""
        is_valid, reason = validate_redirect_url(
            "https://mycareersfuture.gov.sg/job/1",
            "http://127.0.0.1/internal"
        )
        self.assertFalse(is_valid)
        self.assertIn("SSRF", reason)

    def test_foreign_redirect_to_dangerous_scheme_is_blocked(self):
        """Redirecting to file:// or javascript: must be strictly rejected."""
        is_valid, reason = validate_redirect_url(
            "https://timesjobs.com/job/1",
            "file:///etc/passwd"
        )
        self.assertFalse(is_valid)
        self.assertIn("Dangerous URL scheme", reason)


if __name__ == "__main__":
    unittest.main()
