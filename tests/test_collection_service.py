"""Offline collection routing checks with disposable batch outputs."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.scraping import service
from src.scraping.http_client import FetchResult


LISTING = "https://xpress.jobs/jobs/it-telecom"
DETAIL = "https://xpress.jobs/jobs/view/1234/software-engineer"
RELATED = "https://xpress.jobs/jobs/view/5678/backend-engineer"

DETAIL_HTML = """
<html><body><script type="application/ld+json">
{"@context": "https://schema.org", "@type": "JobPosting",
 "title": "Software Engineer",
 "description": "Develop and maintain Python applications for business customers.",
 "hiringOrganization": {"@type": "Organization", "name": "Fixture Employer"}}
</script></body></html>
"""


def page(url, html="", error_type=""):
    result = FetchResult()
    result.final_url = url
    result.html = html
    result.error_type = error_type
    result.success = not error_type
    return result


class TestCollectionRouting(unittest.TestCase):
    def setUp(self):
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        service_path = directory / "src" / "scraping" / "service.py"
        self.enterContext(patch.object(service, "__file__", str(service_path)))
        self.enterContext(patch("socket.gethostbyname", return_value="8.8.8.8"))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.fetch = self.enterContext(patch.object(service, "fetch_page"))
        self.render = self.enterContext(patch.object(service, "fetch_page_rendered"))
        self.render.return_value = page(LISTING, error_type="network_error")

    def test_disabled_fallback_never_renders_known_spa_listing(self):
        self.fetch.return_value = page(LISTING, "<html><body>Loading jobs</body></html>")

        service.run_collection_pipeline([LISTING], use_browser_fallback=False)

        self.render.assert_not_called()

    def test_one_vacancy_is_queued_from_a_known_listing(self):
        self.fetch.side_effect = [
            page(LISTING, f'<a href="{DETAIL}">Software Engineer</a>'),
            page(DETAIL, DETAIL_HTML),
        ]

        rows, _ = service.run_collection_pipeline([LISTING])

        self.assertEqual([call.args[0] for call in self.fetch.call_args_list], [LISTING, DETAIL])
        self.assertEqual(rows["source_url"].tolist(), [DETAIL])

    def test_detail_is_parsed_even_with_one_related_vacancy(self):
        self.fetch.return_value = page(DETAIL, DETAIL_HTML + f'<a href="{RELATED}">Backend Engineer</a>')

        rows, _ = service.run_collection_pipeline([DETAIL])

        self.fetch.assert_called_once()
        self.assertEqual(rows["source_url"].tolist(), [DETAIL])

    def test_enabled_fallback_can_discover_vacancy_on_approved_listing(self):
        self.fetch.side_effect = [
            page(LISTING, "<html><body>Loading jobs</body></html>"),
            page(DETAIL, DETAIL_HTML),
        ]
        self.render.return_value = page(LISTING, f'<a href="{DETAIL}">Software Engineer</a>')

        rows, _ = service.run_collection_pipeline([LISTING], use_browser_fallback=True)

        self.render.assert_called_once_with(LISTING)
        self.assertEqual(rows["source_url"].tolist(), [DETAIL])

    def test_rendered_detail_is_retained_without_discovered_links(self):
        url = "https://xpress.jobs/vacancy/software-engineer"
        self.fetch.return_value = page(url, "<html><body>Loading vacancy</body></html>")
        self.render.return_value = page(url, DETAIL_HTML)

        rows, _ = service.run_collection_pipeline([url], use_browser_fallback=True)

        self.render.assert_called_once_with(url)
        self.assertEqual(rows["extraction_status"].tolist(), ["success"])
        self.assertEqual(rows["job_title_raw"].tolist(), ["Software Engineer"])
        self.assertEqual(rows["fetch_method"].tolist(), ["browser"])
        self.assertEqual(rows["rendering_used"].tolist(), ["True"])

    def test_http_failure_does_not_trigger_browser_for_unapproved_host(self):
        url = "https://example.com/jobs"
        self.fetch.return_value = page(url, error_type="network_error")

        rows, _ = service.run_collection_pipeline([url], use_browser_fallback=True)

        self.render.assert_not_called()
        self.assertEqual(rows["error_type"].tolist(), ["network_error"])

    def test_terminal_http_failure_does_not_trigger_browser_for_approved_host(self):
        for error_type in ("blocked", "invalid_url", "rate_limited", "tls_error"):
            with self.subTest(error_type=error_type):
                self.render.reset_mock()
                self.fetch.return_value = page(LISTING, error_type=error_type)

                rows, _ = service.run_collection_pipeline(
                    [LISTING], use_browser_fallback=True, batch_id=f"batch_{error_type}"
                )

                self.render.assert_not_called()
                self.assertEqual(rows["error_type"].tolist(), [error_type])
