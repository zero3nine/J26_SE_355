import unittest
from datetime import date

from tools.stage_itpro_tracker import stage_snapshots


def advert(day=12, **changes):
    return {
        "source": "ITPro.lk",
        "link": "https://itpro.lk/job/13003/software-engineer/",
        "title": "Software Engineer",
        "company": "Example employer",
        "datePosted": [2026, 4, 10, 8, 9, 10],
        "scrapedDate": [2026, 4, day],
        "description": (
            "Build and test web services using Python and SQL. Deploy the application to a managed Kubernetes "
            "cluster and review changes with the platform engineering team. Contact developer@example.com."
        ),
    } | changes


def snapshot(revision, day, *adverts):
    return (revision * 40, date(2026, 4, day), adverts)


class ITProTrackerTests(unittest.TestCase):
    def test_requires_stable_timestamp_across_distinct_observation_days(self):
        rows, counts = stage_snapshots([
            snapshot("a", 12, advert()),
            snapshot("b", 13, advert(13, link="https://itpro.lk/job/13003/new-slug")),
        ])
        self.assertEqual(counts, {})
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["source_job_id"], "13003")
        self.assertEqual(row["posted_date_raw"], "2026-04-10")
        self.assertEqual(row["tracker_first_commit"], "a" * 40)
        self.assertEqual(row["tracker_confirming_commit"], "b" * 40)
        self.assertNotIn("developer@example.com", row["job_description_raw"])

    def test_rejects_repeated_fallback_and_conflicting_dates(self):
        rows, counts = stage_snapshots([
            snapshot("a", 12, advert(), advert(link="https://itpro.lk/job/13004/developer")),
            snapshot("b", 12, advert()),
            snapshot("c", 13, advert(13, datePosted=[2026, 4, 12, 9, 0, 0],
                                      link="https://itpro.lk/job/13004/developer")),
        ])
        self.assertEqual(rows, [])
        self.assertEqual(counts, {"single observation day": 1, "conflicting timestamps": 1})

    def test_rejects_non_itpro_wrong_origin_and_impossible_dates(self):
        rows, counts = stage_snapshots([
            snapshot("a", 12, advert(source="TopJobs.lk"),
                     advert(link="https://itpro.lk.example.org/job/13003/engineer"),
                     advert(datePosted=[2026, 4, 31, 0, 0, 0]),
                     advert(datePosted=[2026, 4, 20, 0, 0, 0]),
                     advert(scrapedDate=[2026, 3, 1])),
        ])
        self.assertEqual(rows, [])
        self.assertEqual(counts, {"other source": 1, "identity": 1, "dates": 3})
