"""Check the browser transport without starting Chromium or contacting a portal."""

import unittest
from unittest.mock import patch

from src.scraping.browser_fetch import fetch_page_rendered


APPROVED = "https://xpress.jobs/jobs/it-telecom"
UNAPPROVED = "https://example.com/jobs"


class TestBrowserFetch(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("socket.gethostbyname", return_value="8.8.8.8"))
        self.playwright = self.enterContext(patch("playwright.sync_api.sync_playwright"))
        self.launch = self.playwright.return_value.__enter__.return_value.chromium.launch
        self.browser = self.launch.return_value
        self.context = self.browser.new_context.return_value
        self.page = self.context.new_page.return_value
        self.page.goto.return_value.status = 200
        self.page.url = APPROVED
        self.page.content.return_value = "<p>" + ("Fixture job description. " * 20) + "</p>"

    def test_launch_enables_sandbox_and_blocks_service_workers(self):
        result = fetch_page_rendered(APPROVED)

        self.assertTrue(result.success)
        self.launch.assert_called_once_with(headless=True, chromium_sandbox=True)
        self.assertEqual(self.browser.new_context.call_args.kwargs["service_workers"], "block")
        self.assertFalse(self.browser.new_context.call_args.kwargs["accept_downloads"])
        self.context.add_init_script.assert_not_called()
        self.browser.close.assert_called_once()

    def test_launch_failure_is_reported_without_unsandboxed_retry(self):
        self.launch.side_effect = RuntimeError("Launch failed")

        result = fetch_page_rendered(APPROVED)

        self.assertEqual(result.error_type, "network_error")
        self.assertIn("sandbox enabled", result.error_message)
        self.launch.assert_called_once_with(headless=True, chromium_sandbox=True)

    def test_unapproved_host_is_rejected_before_launch(self):
        result = fetch_page_rendered(UNAPPROVED)

        self.assertEqual(result.error_type, "blocked")
        self.playwright.assert_not_called()

    def test_restricted_source_is_rejected_even_if_approved(self):
        result = fetch_page_rendered("https://www.naukri.com/software-developer-jobs")

        self.assertEqual(result.error_type, "blocked")
        self.playwright.assert_not_called()

    def test_content_at_unapproved_final_destination_is_discarded(self):
        self.page.url = UNAPPROVED

        result = fetch_page_rendered(APPROVED)

        self.assertEqual(result.error_type, "blocked")
        self.assertEqual(result.html, "")
        self.page.content.assert_not_called()
        self.browser.close.assert_called_once()
