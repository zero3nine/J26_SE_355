"""
Unit tests for the centralized URL validator.
"""

import unittest
import socket
from unittest.mock import patch
from src.security.url_validator import validate_url, validate_redirect_url


class TestUrlValidator(unittest.TestCase):

    def test_valid_http_https_urls(self):
        # Valid hostnames that resolve should pass
        is_ok, reason = validate_url("https://www.google.com")
        self.assertTrue(is_ok)
        self.assertEqual(reason, "")

        is_ok, reason = validate_url("http://example.com/some/path?query=123")
        self.assertTrue(is_ok)
        self.assertEqual(reason, "")

    def test_invalid_scheme(self):
        # Only http/https allowed
        is_ok, reason = validate_url("ftp://ftp.example.com/file.txt")
        self.assertFalse(is_ok)
        self.assertTrue("Invalid scheme" in reason or "Dangerous URL scheme" in reason)

        is_ok, reason = validate_url("file:///etc/passwd")
        self.assertFalse(is_ok)
        self.assertIn("Dangerous URL scheme", reason)

        is_ok, reason = validate_url("javascript:alert(1)")
        self.assertFalse(is_ok)
        self.assertIn("Dangerous URL scheme", reason)

    def test_embedded_credentials(self):
        is_ok, reason = validate_url("https://user:pass@example.com/path")
        self.assertFalse(is_ok)
        self.assertIn("Credentials in URL", reason)

    def test_non_standard_ports(self):
        is_ok, reason = validate_url("https://example.com:8080/path")
        self.assertFalse(is_ok)
        self.assertIn("Non-standard port", reason)

        # Ports 80 and 443 are allowed explicitly
        is_ok, reason = validate_url("https://example.com:443/path")
        self.assertTrue(is_ok)

    def test_unsafe_local_and_private_ips(self):
        # Loopback and private IPs must be blocked
        self.assertFalse(validate_url("http://127.0.0.1/")[0])
        self.assertFalse(validate_url("http://192.168.0.1/")[0])
        self.assertFalse(validate_url("http://10.0.0.1/")[0])
        self.assertFalse(validate_url("http://172.16.0.1/")[0])
        self.assertFalse(validate_url("http://localhost/")[0])

        # Metadata services
        self.assertFalse(validate_url("http://169.254.169.254/")[0])

    @patch("socket.gethostbyname")
    def test_ssrf_resolution_check(self, mock_gethostbyname):
        # Hostname resolves to private IP -> reject
        mock_gethostbyname.return_value = "10.0.0.5"
        is_ok, reason = validate_url("https://some-internal-domain.com")
        self.assertFalse(is_ok)
        self.assertIn("resolves to private/local IP", reason)

        # Hostname resolves to public IP -> accept
        mock_gethostbyname.return_value = "8.8.8.8"
        is_ok, reason = validate_url("https://some-public-domain.com")
        self.assertTrue(is_ok)


if __name__ == "__main__":
    unittest.main()
