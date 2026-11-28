import json
import unittest
from datetime import date

from src.scraping.extractors.jsonld import JsonLdExtractor
from src.scraping.itpro_feed import normalize_feed
from src.scraping.models import ExtractionResult
from tools.stage_itpro_archive import stage_capture


AS_OF = date(2026, 11, 28)


def advert(**overrides):
    row = {
        "id": "15918",
        "url_title": "full-stack-engineer",
        "title": "Full Stack Engineer",
        "company": "Example employer",
        "location": "Colombo",
        "category_name": "Software Engineering",
        "type_name": "Full time",
        "created_on": "2026-09-28 09:30:00",
        "description": (
            "<p>Build with Python &amp;amp; SQL. Requirements</p><ul><li>Build and test Python services with SQL "
            "databases and review production changes with the engineering team.</li>"
            "<li>Maintain API documentation and own releases for internal tools.</li></ul>"
            "<script>exclude-this</script><p>Contact jobs@example.com or 077 123 4567.</p>"
        ),
    }
    return row | overrides


class ITProFeedTests(unittest.TestCase):
    def test_normalizes_documented_feed_without_executing_script(self):
        rows, exclusions = normalize_feed("var jobs = " + json.dumps([advert()]) + ";", AS_OF)
        self.assertEqual(exclusions, {})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_url"], "https://itpro.lk/job/15918/full-stack-engineer")
        self.assertEqual(rows[0]["source_job_id"], "15918")
        self.assertEqual(rows[0]["posted_date_raw"], "2026-09-28")
        self.assertIn("Python services", rows[0]["job_description_raw"])
        self.assertIn("Python & SQL", rows[0]["job_description_raw"])
        self.assertNotIn("exclude-this", rows[0]["job_description_raw"])
        self.assertNotIn("jobs@example.com", rows[0]["job_description_raw"])
        self.assertNotIn("077 123 4567", rows[0]["job_description_raw"])

    def test_excludes_invalid_late_and_out_of_scope_rows(self):
        rows, exclusions = normalize_feed(
            json.dumps([
                advert(),
                advert(url_title="alternate-slug"),
                advert(id="20", created_on="2026-12-01 00:00:00"),
                advert(id="21", created_on="not a date"),
                advert(id="22", title="Payroll Officer", category_name="Management and Business"),
                advert(id="23", description="Please see the vacancy"),
                advert(id="24", url_title="../not-a-vacancy"),
            ]),
            AS_OF,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(exclusions, {"duplicate": 1, "date": 2, "role": 1, "text": 1, "identity": 1})

    def test_rejects_script_beyond_the_documented_wrapper(self):
        with self.assertRaises(ValueError):
            normalize_feed("var jobs = []; anotherCall();", AS_OF)

    def test_archived_itpro_description_can_contain_literal_line_breaks(self):
        html = (
            '<script type="application/ld+json">{"@type":"JobPosting",'
            '"title":"Software Engineer","datePosted":"2024-11-10",'
            '"description":"Build Python-backed data pipelines.\n'
            'Maintain the job queue and storage services."}</script>'
        )
        for host in ("itpro.lk", "www.itpro.lk", "example.org"):
            with self.subTest(host=host):
                url = f"https://{host}/job/1561/software-engineer"
                result = JsonLdExtractor().extract(url, html, ExtractionResult.create_for_url(url, "archive-fixture"))
                if host == "example.org":
                    self.assertEqual(result.extraction_status, "not_a_job_page")
                else:
                    self.assertEqual(result.posted_date_raw, "2024-11-10")
                    self.assertIn("storage services", result.job_description_raw)

    def test_archive_keeps_posting_date_and_replay_date_separate(self):
        archive = "https://web.archive.org/web/20250323174352id_/https://itpro.lk/job/1561/software-engineer/"
        posting = {
            "@type": "JobPosting",
            "title": "Software Engineer",
            "datePosted": "2024-11-10",
            "description": advert()["description"],
            "hiringOrganization": {"name": "Example employer"},
            "identifier": {"value": "1561"},
        }

        def body(**changes):
            content = json.dumps(posting | changes).replace("<", "\\u003c")
            return f'<script type="application/ld+json">{content}</script>'.encode()

        row, reason = stage_capture(archive, body())
        self.assertEqual(reason, "")
        self.assertEqual(row["source_url"], "https://itpro.lk/job/1561/software-engineer")
        self.assertEqual(row["posted_date_raw"], "2024-11-10")
        self.assertEqual(row["capture_timestamp"], "2025-03-23T17:43:52+00:00")
        self.assertEqual(stage_capture(archive, body(datePosted="")), (None, "posting date"))
        self.assertEqual(
            stage_capture(archive, body(datePosted="2025-03-24")),
            (None, "posting date after capture"),
        )
        self.assertEqual(
            stage_capture(archive, body(identifier={"value": "1562"})),
            (None, "vacancy identity"),
        )
        self.assertEqual(
            stage_capture(archive.replace("https://itpro.lk/", "https://example.org/"), body()),
            (None, "replay URL"),
        )
