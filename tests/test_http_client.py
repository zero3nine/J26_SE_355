"""Offline transport regressions; no live sources or research data are used."""

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from src.scraping import http_client, service


URL = "https://example.com/jobs"
TARGET = "https://example.com/detail"


def response(status=200, headers=None, chunks=None):
    result = MagicMock()
    result.status_code = status
    result.headers = headers if headers is not None else {"Content-Type": "text/html"}
    result.iter_content.return_value = chunks if chunks is not None else [b"<html>Job</html>"]
    result.encoding = "utf-8"
    return result


class TestHttpClient(unittest.TestCase):
    def setUp(self):
        self.validate = self.enterContext(patch.object(http_client, "validate_url", return_value=(True, "")))
        self.redirect = self.enterContext(patch.object(http_client, "validate_redirect_url", return_value=(True, "")))
        self.get = self.enterContext(patch.object(http_client.requests, "get"))
        self.sleep = self.enterContext(patch.object(http_client.time, "sleep"))

    def assert_verified_requests(self):
        for request in self.get.call_args_list:
            self.assertIs(request.kwargs["verify"], True)
            self.assertIs(request.kwargs["allow_redirects"], False)
            self.assertIs(request.kwargs["stream"], True)
            self.assertEqual(request.kwargs["timeout"], (http_client.CONNECTION_TIMEOUT, http_client.READ_TIMEOUT))

    def test_tls_failure_stops_without_retry(self):
        for browser_ua in (False, True):
            with self.subTest(browser_ua=browser_ua):
                self.get.reset_mock()
                self.get.side_effect = requests.exceptions.SSLError("certificate verify failed")
                result = http_client.fetch_page(URL, force_browser_ua=browser_ua)
                self.assertFalse(result.success)
                self.assertEqual(result.html, "")
                self.assertEqual(self.get.call_count, 1)
                self.assert_verified_requests()
                self.assertEqual(result.error_type, "tls_error")
                self.assertIn("certificate", result.error_message)
                self.assertIn("trust configuration", result.error_message)
                self.assertEqual(result.final_url, URL)
        self.sleep.assert_not_called()

    def test_tls_failure_at_redirect_target_stops(self):
        redirect = response(302, {"Location": TARGET})
        self.get.side_effect = [redirect, requests.exceptions.SSLError("hostname mismatch")]
        result = http_client.fetch_page(URL)
        self.assertFalse(result.success)
        self.assertEqual(result.error_type, "tls_error")
        self.assertEqual(result.final_url, TARGET)
        self.assertEqual(result.redirect_chain, [TARGET])
        self.assertEqual(self.get.call_count, 2)
        self.assert_verified_requests()
        self.redirect.assert_called_once_with(URL, TARGET)
        redirect.close.assert_called_once()
        self.sleep.assert_not_called()

    def test_verified_redirect_success_and_delay(self):
        redirect = response(302, {"Location": "/detail"})
        page = response()
        self.get.side_effect = [redirect, page]
        result = http_client.fetch_page(URL, delay_before=True, polite_delay=4)
        self.assertTrue(result.success)
        self.assertEqual(result.html, "<html>Job</html>")
        self.assertEqual(result.final_url, TARGET)
        self.validate.assert_called_once_with(URL)
        self.redirect.assert_called_once_with(URL, TARGET)
        self.sleep.assert_called_once_with(4)
        self.assert_verified_requests()
        redirect.close.assert_called_once()
        page.close.assert_called_once()

    def test_invalid_url_makes_no_request(self):
        self.validate.return_value = (False, "unsafe URL")
        result = http_client.fetch_page(URL)
        self.assertEqual(result.error_type, "invalid_url")
        self.get.assert_not_called()

    def test_unsafe_redirect_is_not_fetched(self):
        self.redirect.return_value = (False, "private address")
        page = response(302, {"Location": "https://127.0.0.1/"})
        self.get.return_value = page
        result = http_client.fetch_page(URL)
        self.assertEqual(result.error_type, "blocked")
        self.assertEqual(self.get.call_count, 1)
        page.close.assert_called_once()

    def test_response_limit_is_preserved(self):
        page = response(chunks=[b"1234", b"5"])
        self.get.return_value = page
        with patch.object(http_client, "MAX_RESPONSE_BYTES", 4):
            result = http_client.fetch_page(URL)
        self.assertFalse(result.success)
        self.assertEqual(result.error_type, "parse_error")
        self.assertEqual(result.html, "")
        page.close.assert_called_once()

    def test_temporary_status_still_retries_with_verification(self):
        temporary = response(503, {})
        self.get.side_effect = [temporary, response()]
        result = http_client.fetch_page(URL)
        self.assertTrue(result.success)
        self.assertEqual(self.get.call_count, 2)
        self.assert_verified_requests()
        self.sleep.assert_called_once_with(6)
        temporary.close.assert_called_once()

    def test_user_agent_fallback_stays_verified(self):
        blocked = response(403, {})
        self.get.side_effect = [blocked, response()]
        result = http_client.fetch_page(URL)
        self.assertTrue(result.success)
        self.assertEqual(result.headers_used, "browser")
        self.assertEqual(self.get.call_count, 2)
        self.assert_verified_requests()


class TestCollectionTlsFailure(unittest.TestCase):
    def test_tls_failure_is_logged_without_browser_or_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Redirect only service output paths into a temporary project layout.
            fake_file = root / "src" / "scraping" / "service.py"
            with patch.object(service, "__file__", str(fake_file)), \
                 patch.object(service, "validate_url", return_value=(True, "")), \
                 patch.object(http_client, "validate_url", return_value=(True, "")), \
                 patch.object(http_client.requests, "get", side_effect=requests.exceptions.SSLError("certificate verify failed")) as get, \
                 patch.object(service, "get_source_registry") as registry_factory, \
                 patch.object(service, "fetch_page_rendered") as browser, \
                 patch.object(service, "ExtractorRegistry") as extractor, \
                 patch.object(service, "process_ocr_for_job") as ocr:
                browser.return_value.success = False
                registry_factory.return_value.check_access_permission.return_value = (True, "permitted", "")
                registry_factory.return_value.get_country.return_value = "Unspecified"
                registry_factory.return_value.get_rate_limit.return_value = 2
                frame, _ = service.run_collection_pipeline([URL], use_browser_fallback=True, use_ocr=True)
            browser.assert_not_called()
            extractor.return_value.extract.assert_not_called()
            ocr.assert_not_called()
            self.assertEqual(get.call_count, 1)
            self.assertEqual(frame.iloc[0]["error_type"], "tls_error")
            self.assertEqual(frame.iloc[0]["extraction_status"], "tls_error")
            with (root / "logs" / "failed_urls.csv").open(encoding="utf-8", newline="") as file:
                failures = list(csv.DictReader(file))
            self.assertEqual(failures[0]["error_type"], "tls_error")
            self.assertIn("trust configuration", failures[0]["error_message"])
            manifest = json.loads((root / "data" / "raw" / "collection_manifest.json").read_text(encoding="utf-8"))[0]
            self.assertEqual(manifest["requests_completed"], 0)
            self.assertEqual(manifest["failed_urls"], 1)
            self.assertEqual(manifest["browser_fallback_used"], 0)


if __name__ == "__main__":
    unittest.main()
