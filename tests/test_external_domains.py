"""
Unit and API integration tests for External Domains management.
"""

import unittest
from unittest.mock import patch, mock_open
from fastapi.testclient import TestClient

from src.api.server import app
from src.security.url_validator import (
    get_external_queue_data,
    approve_external_domain,
    reject_external_domain,
    remove_from_external_queue,
    is_approved_domain,
)


class TestExternalDomainsApi(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_get_external_domains_endpoint(self):
        response = self.client.get("/api/external-domains")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("queue", data)
        self.assertIn("pending_hostnames", data)
        self.assertIn("approved_domains", data)
        self.assertIn("blocked_domains", data)
        self.assertIn("stats", data)
        self.assertIsInstance(data["stats"]["total_queue"], int)
        self.assertIsInstance(data["stats"]["whitelist_total"], int)

    def test_approve_empty_hostname_raises_400(self):
        response = self.client.post("/api/external-domains/approve", json={"hostname": "   "})
        self.assertEqual(response.status_code, 400)

    def test_reject_empty_hostname_raises_400(self):
        response = self.client.post("/api/external-domains/reject", json={"hostname": ""})
        self.assertEqual(response.status_code, 400)

    @patch("src.api.server.approve_external_domain")
    def test_approve_domain_endpoint(self, mock_approve):
        response = self.client.post("/api/external-domains/approve", json={"hostname": "testdomain.com"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["hostname"], "testdomain.com")
        mock_approve.assert_called_once_with("testdomain.com")

    @patch("src.api.server.reject_external_domain")
    def test_reject_domain_endpoint(self, mock_reject):
        response = self.client.post(
            "/api/external-domains/reject",
            json={"hostname": "malicious-site.com", "block_domain": True},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        mock_reject.assert_called_once_with("malicious-site.com", block_domain=True)

    @patch("src.api.server.remove_from_external_queue")
    def test_remove_domain_endpoint(self, mock_remove):
        response = self.client.post(
            "/api/external-domains/remove",
            json={"hostname": "old-site.com", "external_url": "https://old-site.com/job/1"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        mock_remove.assert_called_once_with(
            hostname="old-site.com",
            target_url="https://old-site.com/job/1",
        )


if __name__ == "__main__":
    unittest.main()
