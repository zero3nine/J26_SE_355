import unittest
from unittest.mock import MagicMock, patch
import json
import tempfile
import shutil
import pathlib
from datetime import datetime, timezone

from src.cleaning.clean_jobs import normalize_date_reproducible, clean_job_description_body
from src.scraping.extractor_registry import ExtractorRegistry
from src.scraping.models import ExtractionResult
from src.scraping.link_extractor import LinkExtractor


class TestEnhancements(unittest.TestCase):
    """Unit tests for academic scraper enhancement tasks."""

    def test_date_normalization(self):
        """Task 7: Test timezone-aware date baseline and relative conversion."""
        # Baseline collected_at
        baseline = "2026-08-29T10:00:00Z"
        
        # Test today
        date, method, status, warn = normalize_date_reproducible("Today", baseline)
        self.assertEqual(date, "2026-08-29")
        self.assertEqual(method, "relative")
        
        # Test yesterday
        date, method, status, warn = normalize_date_reproducible("Yesterday", baseline)
        self.assertEqual(date, "2026-08-28")
        self.assertEqual(method, "relative")
        
        # Test days ago
        date, method, status, warn = normalize_date_reproducible("3 days ago", baseline)
        self.assertEqual(date, "2026-08-26")
        
        # Test absolute date
        date, method, status, warn = normalize_date_reproducible("2026-05-15", baseline)
        self.assertEqual(date, "2026-05-15")
        self.assertEqual(method, "absolute")

    def test_description_cleaning_preserves_formatting(self):
        """Task 8: Test HTML description cleaning preserves bullets and paragraphs."""
        raw_html = """
        <div>
            <h1>Lead QA Engineer</h1>
            <p>We are looking for a senior developer.</p>
            <script>console.log('remove me');</script>
            <ul>
                <li>5+ years experience</li>
                <li>Python expertise</li>
            </ul>
        </div>
        """
        cleaned = clean_job_description_body(raw_html)
        self.assertIn("Lead QA Engineer", cleaned)
        self.assertIn("We are looking for a senior developer.", cleaned)
        self.assertNotIn("console.log", cleaned)
        # Verify bullet points are kept
        self.assertIn("• 5+ years experience", cleaned)
        self.assertIn("• Python expertise", cleaned)

    @patch("src.scraping.extractor_registry.is_approved_domain")
    def test_playwright_fallback_routing(self, mock_is_approved):
        """Task 2: Test Playwright browser fallback is triggered for approved domains when HTTP is insufficient."""
        mock_is_approved.return_value = True
        
        registry = ExtractorRegistry()
        # Mock the browser rendering function so it doesn't spin up a real browser
        registry._render_page_with_playwright = MagicMock(return_value=("<html><h1>Mock Rendered Title</h1><div itemprop='description'>This is a very long description that has more than 100 characters to make it look sufficient.</div></html>", "https://approved.com/job/1"))
        
        result = ExtractionResult.create_for_url("https://approved.com/job/1", "test_batch")
        
        # Initial HTTP content has insufficient description (too short)
        http_html = "<html><h1>Mock Title</h1><body>Too short</body></html>"
        
        final_result = registry.extract("https://approved.com/job/1", http_html, result, use_browser_fallback=True)
        
        self.assertEqual(final_result.fetch_method, "browser")
        self.assertEqual(final_result.rendering_used, "True")
        self.assertEqual(final_result.job_title_raw, "Mock Rendered Title")
        registry._render_page_with_playwright.assert_called_once()

    @patch("src.security.url_validator.is_approved_domain")
    @patch("src.scraping.link_extractor.validate_url")
    def test_external_links_queuing(self, mock_validate, mock_is_approved):
        """Task 3: Test that unapproved external vacancy links are queued rather than followed."""
        mock_validate.return_value = (True, "")
        # Host is not approved
        mock_is_approved.return_value = False
        
        extractor = LinkExtractor()
        
        # Mock _add_to_external_queue to verify it gets called
        extractor._add_to_external_queue = MagicMock()
        
        html = '<html><a href="https://external-jobs.com/detail/python-dev">Apply on Company Site</a></html>'
        
        # Base url is on a different domain
        candidates = extractor.extract_job_links("https://my-portal.lk/jobs", html)
        
        # The link is external and unapproved, so it must not be in candidates, but must be queued
        self.assertNotIn("https://external-jobs.com/detail/python-dev", candidates)
        extractor._add_to_external_queue.assert_called_once_with(
            "https://my-portal.lk/jobs",
            "https://external-jobs.com/detail/python-dev",
            "Apply on Company Site"
        )
