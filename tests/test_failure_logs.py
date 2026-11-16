"""
Unit and API integration tests for Failure Logs & Exclusions.
"""

import unittest
from fastapi.testclient import TestClient

from src.api.server import app, compile_failure_logs


class TestFailureLogsApi(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_get_failure_logs_session_scope(self):
        response = self.client.get("/api/failure-logs?scope=session")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["scope"], "session")
        self.assertIn("records", data)
        self.assertIn("stats", data)
        self.assertIn("available_batches", data)

    def test_get_failure_logs_historical_scope(self):
        response = self.client.get("/api/failure-logs?scope=historical")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["scope"], "historical")
        self.assertGreater(data["stats"]["total_records"], 0)
        self.assertTrue(len(data["records"]) > 0)

        # Check required fields match Streamlit specification
        rec = data["records"][0]
        self.assertIn("url", rec)
        self.assertIn("source_hostname", rec)
        self.assertIn("extractor_name", rec)
        self.assertIn("error_type", rec)
        self.assertIn("error_message", rec)
        self.assertIn("timestamp", rec)
        self.assertIn("retryable", rec)

    def test_export_failure_logs_csv(self):
        response = self.client.get("/api/failure-logs/export-csv?scope=historical")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn("jobs_failures_", response.headers["content-disposition"])
        lines = response.text.split("\n")
        header = lines[0].strip()
        self.assertEqual(
            header,
            "url,source_hostname,extractor_name,error_type,error_message,timestamp,retryable",
        )

    def test_clear_session_endpoint(self):
        response = self.client.post("/api/failure-logs/clear-session")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")


if __name__ == "__main__":
    unittest.main()

