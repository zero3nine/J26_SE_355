"""Public boundary, cohort arithmetic, exports, and publication regressions."""
import csv
import io
import json
import sqlite3
import tempfile
import unittest
import os
import subprocess
import sys
import shutil
from pathlib import Path
from contextlib import closing
from urllib.parse import urlencode
from wsgiref.util import setup_testing_defaults

from public_dashboard.app import create_app
from public_dashboard.data import read_snapshot, summarize, timeline
from public_dashboard.publication import publish, synthetic_records
from tools.publish_dashboard import from_master


def record(job_id, posted="2025-01-10", country="Sri Lanka", role="Software development", lexical=None, semantic=None):
    return {"job_id": job_id, "posting_date": posted, "country": country, "role": role,
            "source": "Fixture portal", "lexical": lexical or [], "semantic": semantic or []}


class PublicDashboardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "public.sqlite3"
        self.records = [record("a", lexical=["Python"], semantic=["Python", "Django"]),
                        record("b"), record("c", country="Singapore", semantic=["Java"])]
        self.meta = {"title": "Fixture", "provenance": "Unit-test synthetic records", "is_synthetic": True}
        publish(self.records, self.path, self.meta)
        self.app = create_app(self.path)

    def request(self, path="/api/analysis", query=None, method="GET"):
        environ = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, QUERY_STRING=urlencode(query or {}), REQUEST_METHOD=method)
        response = {}
        def start(status, headers):
            response.update(status=status, headers=dict(headers))
        response["body"] = b"".join(self.app(environ, start))
        return response

    def test_zero_skill_jobs_share_denominator_and_methods_use_same_cohort(self):
        data = json.loads(self.request(query={"country": "Sri Lanka"})["body"])
        self.assertEqual(data["summary"]["jobs"], 2)
        self.assertEqual(data["skills"][0]["rate"], 50)
        comparison = {r["skill"]: r for r in data["comparison"]}
        self.assertEqual(comparison["Python"]["difference"], 0)
        self.assertEqual(comparison["Django"]["difference"], 50)

    def test_public_database_is_sanitized_and_reader_cannot_initialize_master(self):
        with closing(sqlite3.connect(self.path)) as conn:
            columns = [r[1] for r in conn.execute("PRAGMA table_info(jobs)")]
            self.assertEqual(columns, ["id", "posted", "country", "role", "source"])
            self.assertNotEqual(conn.execute("SELECT id FROM jobs LIMIT 1").fetchone()[0], "a")
        missing = Path(self.directory.name) / "absent.sqlite3"
        app = create_app(missing)
        environ = {}; setup_testing_defaults(environ); environ["PATH_INFO"] = "/api/options"
        captured = []
        list(app(environ, lambda s, h: captured.append(s)))
        self.assertTrue(captured[0].startswith("503"))
        self.assertFalse(missing.exists())

    def test_sparse_period_is_never_reintroduced_as_zero(self):
        rows = [record(str(i), posted=month, semantic=["Python"])
                for month, n, offset in [("2025-01-01", 5, 0), ("2025-02-01", 1, 5), ("2025-03-01", 5, 6)]
                for i in range(offset, offset+n)]
        publish(rows, self.path, self.meta)
        meta, jobs = read_snapshot(self.path)
        points = summarize(meta, jobs, {"min_jobs": "5"})["timeline"]
        self.assertEqual([p["rates"]["Python"] for p in points], [100, None, 100])

    def test_zero_mentions_and_unobserved_month_are_distinct(self):
        publish([record("a", semantic=["Python"]), record("b", posted="2025-02-01"),
                 record("c", posted="2025-04-01", semantic=["Python"])], self.path, self.meta)
        meta, jobs = read_snapshot(self.path)
        data = summarize(meta, jobs, {"min_jobs": "1"})
        self.assertEqual([p["rates"]["Python"] for p in data["timeline"]], [100, 0, None, 100])
        self.assertTrue(all(r["change"] is None for r in data["skills"]))

    def test_filters_apply_to_counts_and_market_comparison_lifts_only_country(self):
        data = json.loads(self.request(query={"country": "Sri Lanka", "skill": "Python"})["body"])
        self.assertEqual(data["summary"]["jobs"], 2)
        self.assertEqual({r["country"] for r in data["markets"]}, {"Sri Lanka", "Singapore"})
        self.assertEqual(data["relationships"][0]["confidence"], 100)
        self.assertEqual(data["relationships"][0]["lift"], 2)

    def test_unknown_filters_dates_and_methods_fail_clearly(self):
        for query in [{"method": "hybrid"}, {"start": "not-a-date"}, {"min_jobs": "0"},
                      {"country": "' OR 1=1"}, {"unexpected": "value"},
                      {"start": "2025-01-11", "end": "2025-01-10"}]:
            with self.subTest(query=query):
                self.assertTrue(self.request(query=query)["status"].startswith("400"))

    def test_read_only_routes_and_static_allowlist(self):
        self.assertTrue(self.request(method="POST")["status"].startswith("405"))
        for path in ["/../data/master_jobs.sqlite3", "/data/master_jobs.sqlite3", "/app.py", "/admin"]:
            self.assertTrue(self.request(path)["status"].startswith("404"))
        home = self.request("/")
        self.assertTrue(home["status"].startswith("200"))
        self.assertIn("Content-Security-Policy", home["headers"])
        self.assertEqual(self.request("/", method="HEAD")["body"], b"")

    def test_csv_has_scope_and_synthetic_provenance_but_no_private_records(self):
        response = self.request("/api/export", {"country": "Sri Lanka", "view": "skills"})
        rows = list(csv.DictReader(io.StringIO(response["body"].decode("utf-8-sig"))))
        self.assertTrue(response["status"].startswith("200"))
        self.assertEqual(rows[0]["synthetic"], "True")
        self.assertIn('"country": "Sri Lanka"', rows[0]["scope"])
        self.assertNotIn("job_id", rows[0])
        self.assertNotIn("source_url", rows[0])

    def test_csv_protects_spreadsheet_formula_labels(self):
        publish([record("formula", semantic=["=HYPERLINK(1)"])], self.path, self.meta)
        data = self.request("/api/export")["body"].decode("utf-8-sig")
        self.assertIn("'=HYPERLINK(1)", data)

    def test_invalid_publication_preserves_previous_snapshot(self):
        original = self.path.read_bytes()
        invalid = [record("a"), record("a")]
        with self.assertRaises(ValueError):
            publish(invalid, self.path, self.meta)
        self.assertEqual(self.path.read_bytes(), original)
        invalid = record("a"); del invalid["lexical"]
        with self.assertRaises(ValueError):
            publish([invalid], self.path, self.meta)

    def test_empty_scope_is_valid_and_not_an_api_error(self):
        publish([record("a"), record("b", country="Singapore", role="Quality assurance")], self.path, self.meta)
        response = self.request(query={"country": "Sri Lanka", "role": "Quality assurance"})
        data = json.loads(response["body"])
        self.assertEqual(data["summary"]["jobs"], 0)
        self.assertEqual(data["skills"], [])

    def test_forecasts_are_published_offline_and_not_reused_for_another_scope(self):
        records = [record(f"{month}-{i}", posted=f"2024-{month:02d}-01", semantic=["Python"])
                   for month in range(1, 13) for i in range(5)]
        records += [record(f"2025-{month}-{i}", posted=f"2025-{month:02d}-01", semantic=["Python"])
                    for month in range(1, 7) for i in range(5)]
        publish(records, self.path, self.meta)
        full = json.loads(self.request()["body"])
        self.assertEqual(len(full["forecast"]["rows"]), 3)
        self.assertEqual(full["forecast"]["rows"][0]["mae"], 0)
        export = self.request("/api/export", {"view": "forecasts", "skill": "Python"})
        self.assertEqual(len(list(csv.DictReader(io.StringIO(export["body"].decode("utf-8-sig"))))), 3)
        scoped = json.loads(self.request(query={"source": "Fixture portal"})["body"])
        self.assertEqual(scoped["forecast"]["rows"], [])

    def test_demo_is_deterministic_diverse_and_includes_zero_skill_jobs(self):
        a, b = synthetic_records(), synthetic_records()
        self.assertEqual(a, b)
        self.assertEqual(len({r["country"] for r in a}), 4)
        self.assertEqual(len({r["role"] for r in a}), 5)
        self.assertTrue(any(not r["lexical"] and not r["semantic"] for r in a))

    def test_demo_is_reproducible_across_process_hash_seeds(self):
        command = [sys.executable, "-c", "import hashlib,json; from public_dashboard.publication import synthetic_records; print(hashlib.sha256(json.dumps(synthetic_records(),sort_keys=True).encode()).hexdigest())"]
        hashes = [subprocess.check_output(command, env={**os.environ, "PYTHONHASHSEED": seed}, text=True).strip()
                  for seed in ("1", "42")]
        self.assertEqual(hashes[0], hashes[1])

    def test_master_export_requires_reviewed_completion_and_keeps_zero_results(self):
        master = Path(self.directory.name) / "master.sqlite3"
        cohort = Path(self.directory.name) / "cohort.csv"
        with closing(sqlite3.connect(master)) as conn:
            conn.executescript("""
                CREATE TABLE extraction_runs (run_id TEXT, model_name TEXT, model_version TEXT,
                    semantic_threshold REAL, taxonomy_version TEXT);
                INSERT INTO extraction_runs VALUES ('run-1','model','v1',0.58,'tax-1');
                CREATE TABLE jobs (job_id TEXT, posting_date TEXT, country TEXT, source_platform TEXT,
                    job_title TEXT, job_description TEXT, classification_status TEXT);
                INSERT INTO jobs VALUES ('a','2025-01-10','Sri Lanka','Fixture','Software Engineer','Private text','it');
                INSERT INTO jobs VALUES ('b','2025-01-10','Sri Lanka','Fixture','Software Engineer','Private text','it');
                CREATE TABLE skills (skill_id INTEGER, canonical_name TEXT);
                INSERT INTO skills VALUES (1,'Python');
                CREATE TABLE extracted_skills (job_id TEXT, run_id TEXT, method TEXT, skill_name TEXT, canonical_skill_id INTEGER);
                INSERT INTO extracted_skills VALUES ('a','run-1','semantic','python_id',1);
            """)
        original = master.read_bytes()
        cohort.write_text("job_id,lexical_completed,semantic_completed\na,true,true\nb,true,true\n", encoding="utf-8")
        rows, metadata = from_master(master, "run-1", cohort)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["semantic"], ["Python"])
        self.assertEqual(rows[1]["semantic"], [])
        self.assertEqual(metadata["extraction_run"]["run_id"], "run-1")
        self.assertEqual(master.read_bytes(), original)
        cohort.write_text("job_id,lexical_completed,semantic_completed\na,true,false\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            from_master(master, "run-1", cohort)

    def test_production_files_run_without_repository_or_admin_packages(self):
        root = Path(self.directory.name) / "isolated"
        package = root / "public_dashboard"
        package.mkdir(parents=True)
        source = Path(__file__).resolve().parents[1] / "public_dashboard"
        for name in ("__init__.py", "app.py", "data.py"):
            shutil.copyfile(source / name, package / name)
        command = [sys.executable, "-I", "-c",
                   "import sys; sys.path.insert(0,'.'); "
                   "from public_dashboard.app import create_app; "
                   "assert not any(x in sys.modules for x in ['streamlit','pandas','sentence_transformers','src.database.connection']); "
                   "assert callable(create_app()); print('isolated runtime ok')"]
        self.assertIn("isolated runtime ok", subprocess.check_output(command, cwd=root, text=True))


if __name__ == "__main__":
    unittest.main()
