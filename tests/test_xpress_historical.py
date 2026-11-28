import json
import unittest
from datetime import date

from tools.stage_xpress_history import stage_detail


AS_OF = date(2026, 11, 28)


def detail(**changes):
    return json.dumps({
        "jobId": 188419,
        "jobTitle": "Application Support Engineer",
        "createdDate": "2025-06-05T07:01:14.647",
        "jobItem": {
            "jobId": 188419,
            "jobTitle": "Application Support Engineer",
            "organizationName": "Example employer",
            "locations": "Colombo, Western Province; Work From Home / Hybrid, Remote Work",
            "expiryDateOnWebsite": "2025-06-26T00:00:00",
            "jobType": "Full-Time",
        },
        "sectors": [{"friendlyName": "it"}],
        "jobInfo": (
            "<p>Maintain Python services and troubleshoot production issues. Use SQL to investigate system errors "
            "and work with other engineers to document and deploy software fixes.</p>"
            "<p>Contact employer@example.com for more details.</p>"
        ),
    } | changes).encode()


class XpressHistoryTests(unittest.TestCase):
    def test_preserves_original_creation_date_and_publisher_identity(self):
        row, reason = stage_detail("188419", detail(), AS_OF)
        self.assertEqual(reason, "")
        self.assertEqual(row["source_url"], "https://xpress.jobs/jobs/view/188419")
        self.assertEqual(row["posted_date_raw"], "2025-06-05")
        self.assertEqual(row["country_raw"], "Sri Lanka")
        self.assertNotIn("employer@example.com", row["job_description_raw"])

    def test_missing_and_future_dates_do_not_use_expiry(self):
        for value in ("", "2027-05-27T04:05:30"):
            with self.subTest(value=value):
                self.assertEqual(stage_detail("188419", detail(createdDate=value), AS_OF), (None, "date"))

    def test_remote_only_and_mixed_market_locations_require_review(self):
        for location in ("Remote Work", "Colombo, Western Province; Dubai, United Arab Emirates",
                         "Colombo, Western Province, United Arab Emirates"):
            with self.subTest(location=location):
                job = json.loads(detail())
                job["jobItem"]["locations"] = location
                self.assertEqual(stage_detail("188419", json.dumps(job).encode(), AS_OF), (None, "location"))

    def test_rejects_different_ad_and_image_only_response(self):
        self.assertEqual(stage_detail("188418", detail(), AS_OF), (None, "identity"))
        self.assertEqual(stage_detail("188419", detail(jobInfo="<img src='advert.png'>"), AS_OF), (None, "text"))
