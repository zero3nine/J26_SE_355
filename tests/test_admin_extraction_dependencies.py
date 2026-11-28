"""Check that the admin pages handle an install without semantic extraction."""

import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import app_shared
from src.database import connection, repository


ROOT = Path(__file__).resolve().parents[1]


class AdminExtractionDependenciesTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(directory)
        database = self.root / "master.sqlite3"
        repository.import_jobs_dataframe(pd.DataFrame([{
            "job_id": "fixture",
            "source_url": "https://example.com/job",
            "job_title": "Software Engineer",
            "job_description": "Python and SQL development",
        }]), source_name="Fixture", db_path=database)
        self.enterContext(patch.object(connection, "DB_PATH", database))
        self.enterContext(patch.object(app_shared, "current_dir", self.root))

    def test_extraction_actions_are_disabled_without_semantic_packages(self):
        ground_truth = BytesIO(b"job_id,skill_id\nfixture,python\n")
        with (
            patch.dict(sys.modules, {"sentence_transformers": None}),
            patch("streamlit.file_uploader", return_value=ground_truth),
        ):
            for filename, labels in (
                ("5_Extract_Skills.py", [
                    "Run Lexical + Semantic Extraction",
                    "Calibrate semantic threshold",
                    "Evaluate extraction",
                ]),
                ("11_Skill_Relationship_Analysis.py", ["Run Skill Extraction on Master Jobs Now"]),
            ):
                with self.subTest(page=filename):
                    page = AppTest.from_file(str(ROOT / "pages" / filename)).run()
                    self.assertFalse(page.exception)
                    for label in labels:
                        self.assertTrue(next(button for button in page.button if button.label == label).disabled)
                    self.assertTrue(any("ADMIN_INSTALL_EXTRACTION=true" in info.value for info in page.info))
