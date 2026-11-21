"""Saved workflow artifacts can be reopened without an active Streamlit session."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src.cleaning.clean_jobs import clean_raw_dataframe
from src.scraping.batches import (
    list_saved_batches,
    load_saved_batch,
    save_appended_batch,
    save_historical_batch,
)


class SavedBatchTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def write_csv(self, directory, filename, rows):
        target = self.root / "data" / directory / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(target, index=False)

    def test_reopens_historical_raw_and_paired_cleaned_artifacts(self):
        batch_id = "hist_20261120_111111_abc123"
        save_historical_batch(self.root, batch_id, pd.DataFrame([
            {"job_id": "001", "job_title_raw": "Software Engineer", "collection_batch_id": batch_id},
        ]))
        cleaned = [{"job_id": "001", "job_description": "Builds Python applications"}]
        self.write_csv("processed/batches", f"jobs_clean_internal_{batch_id}.csv", [
            {"job_id": "001", "job_description_clean": "Builds Python applications", "extraction_status": "success"},
            {"job_id": "002", "job_description_clean": "", "extraction_status": "excluded"},
        ])
        self.write_csv("processed/batches", f"jobs_clean_{batch_id}.csv", cleaned)

        self.assertEqual(list_saved_batches(self.root), [batch_id])
        batch = load_saved_batch(self.root, batch_id)
        self.assertEqual(batch.raw["job_id"].tolist(), ["001"])
        self.assertEqual(batch.cleaned["job_id"].tolist(), ["001"])
        self.assertEqual(batch.cleaned_internal["job_id"].tolist(), ["001", "002"])
        self.assertIsNone(batch.warning)

    def test_appended_batch_reopens_original_scope_and_parent(self):
        before = "hist_previous"
        batch_id = "batch_current"
        self.write_csv("raw/batches", f"jobs_raw_{batch_id}.csv", [
            {"job_id": "second", "job_title_raw": "Software Engineer", "collection_batch_id": batch_id},
        ])
        combined = pd.DataFrame([
            {"job_id": "first", "job_title_raw": "Data Engineer", "collection_batch_id": before},
            {"job_id": "second", "job_title_raw": "Software Engineer", "collection_batch_id": batch_id},
        ])
        save_appended_batch(self.root, batch_id, before, combined)

        self.assertEqual(list_saved_batches(self.root), [batch_id])
        batch = load_saved_batch(self.root, batch_id)
        pd.testing.assert_frame_equal(batch.raw, combined)
        self.assertEqual(batch.parent_batch_id, before)

    def test_partial_cleaned_output_still_allows_raw_recovery(self):
        batch_id = "batch_partial"
        self.write_csv("raw/batches", f"jobs_raw_{batch_id}.csv", [
            {"job_id": "first", "job_title_raw": "Data Engineer"},
        ])
        self.write_csv("processed/batches", f"jobs_clean_{batch_id}.csv", [
            {"job_id": "first"},
        ])

        batch = load_saved_batch(self.root, batch_id)
        self.assertEqual(len(batch.raw), 1)
        self.assertIsNone(batch.cleaned)
        self.assertIn("incomplete", batch.warning)

    def test_reopened_batch_can_resume_cleaning(self):
        batch_id = "hist_research"
        save_historical_batch(self.root, batch_id, pd.DataFrame([{
            "job_id": "007",
            "job_title_raw": "Software Engineer",
            "job_description_raw": "Develop Python applications and maintain internal production systems.",
            "source_url": "https://example.com/offline-job",
            "extraction_status": "success",
            "classification_status": "it",
            "collection_batch_id": batch_id,
        }]))

        raw = load_saved_batch(self.root, batch_id).raw
        internal, cleaned, _ = clean_raw_dataframe(raw)
        self.assertEqual(cleaned["job_id"].tolist(), ["007"])
        self.assertEqual(internal["collection_batch_id"].tolist(), [batch_id])
        output = self.root / "data/processed/batches"
        output.mkdir(parents=True)
        internal.to_csv(output / f"jobs_clean_internal_{batch_id}.csv", index=False)
        cleaned.to_csv(output / f"jobs_clean_{batch_id}.csv", index=False)
        self.assertEqual(load_saved_batch(self.root, batch_id).cleaned["job_id"].tolist(), ["007"])

    def test_missing_artifact_and_invalid_batch_id_fail_clearly(self):
        with self.assertRaisesRegex(ValueError, "Missing raw"):
            load_saved_batch(self.root, "batch_missing")
        with self.assertRaisesRegex(ValueError, "Invalid batch ID"):
            load_saved_batch(self.root, "../outside")

    def test_live_batch_is_only_visible_after_the_worker_finishes(self):
        from src.scraping import service

        def check_while_collecting(*_progress):
            self.assertEqual(list_saved_batches(self.root), [])

        with patch.object(service, "__file__", str(self.root / "src/scraping/service.py")), patch.object(
            service, "validate_url", return_value=(False, "Fixture URL rejected")
        ):
            service.run_collection_pipeline(
                ["https://example.com/offline-fixture"], batch_id="batch_running",
                progress_callback=check_while_collecting,
            )

        self.assertEqual(list_saved_batches(self.root), ["batch_running"])
