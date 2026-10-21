import csv
import tempfile
import unittest
from pathlib import Path

from src.extraction.evaluation import load_ground_truth


class GroundTruthLoaderTests(unittest.TestCase):

    def test_load_ground_truth(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "ground_truth.csv"

            with path.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as file:
                writer = csv.writer(file)

                writer.writerow([
                    "job_id",
                    "skill_id",
                ])

                writer.writerow([
                    "job_001",
                    "python",
                ])

                writer.writerow([
                    "job_001",
                    "sql",
                ])

            result = load_ground_truth(path)

            self.assertEqual(len(result), 2)

            self.assertEqual(
                result[0].job_id,
                "job_001",
            )

            self.assertEqual(
                result[0].skill_id,
                "python",
            )

    def test_missing_file_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            load_ground_truth(
                "does_not_exist.csv"
            )

    def test_invalid_columns_raise_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.csv"

            with path.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as file:
                writer = csv.writer(file)

                writer.writerow([
                    "wrong_column",
                ])

                writer.writerow([
                    "something",
                ])

            with self.assertRaises(ValueError):
                load_ground_truth(path)


if __name__ == "__main__":
    unittest.main()