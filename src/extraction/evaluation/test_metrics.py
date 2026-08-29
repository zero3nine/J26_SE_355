import unittest

from src.extraction.evaluation.metrics import calculate_metrics


class MetricsTests(unittest.TestCase):

    def test_perfect_predictions(self):
        ground_truth = {
            ("job_1", "python"),
            ("job_1", "sql"),
        }

        predicted = {
            ("job_1", "python"),
            ("job_1", "sql"),
        }

        metrics = calculate_metrics(
            predicted,
            ground_truth,
        )

        self.assertEqual(
            metrics.true_positives,
            2,
        )

        self.assertEqual(
            metrics.false_positives,
            0,
        )

        self.assertEqual(
            metrics.false_negatives,
            0,
        )

        self.assertEqual(
            metrics.precision,
            1.0,
        )

        self.assertEqual(
            metrics.recall,
            1.0,
        )

        self.assertEqual(
            metrics.f1,
            1.0,
        )

    def test_partial_predictions(self):
        ground_truth = {
            ("job_1", "python"),
            ("job_1", "sql"),
        }

        predicted = {
            ("job_1", "python"),
            ("job_1", "docker"),
        }

        metrics = calculate_metrics(
            predicted,
            ground_truth,
        )

        self.assertEqual(
            metrics.true_positives,
            1,
        )

        self.assertEqual(
            metrics.false_positives,
            1,
        )

        self.assertEqual(
            metrics.false_negatives,
            1,
        )

        self.assertAlmostEqual(
            metrics.precision,
            0.5,
        )

        self.assertAlmostEqual(
            metrics.recall,
            0.5,
        )

        self.assertAlmostEqual(
            metrics.f1,
            0.5,
        )

    def test_no_predictions(self):
        ground_truth = {
            ("job_1", "python"),
        }

        predicted = set()

        metrics = calculate_metrics(
            predicted,
            ground_truth,
        )

        self.assertEqual(
            metrics.true_positives,
            0,
        )

        self.assertEqual(
            metrics.false_positives,
            0,
        )

        self.assertEqual(
            metrics.false_negatives,
            1,
        )

        self.assertEqual(
            metrics.precision,
            0.0,
        )

        self.assertEqual(
            metrics.recall,
            0.0,
        )

        self.assertEqual(
            metrics.f1,
            0.0,
        )

    def test_no_ground_truth(self):
        predicted = {
            ("job_1", "python"),
        }

        ground_truth = set()

        metrics = calculate_metrics(
            predicted,
            ground_truth,
        )

        self.assertEqual(
            metrics.true_positives,
            0,
        )

        self.assertEqual(
            metrics.false_positives,
            1,
        )

        self.assertEqual(
            metrics.false_negatives,
            0,
        )

        self.assertEqual(
            metrics.precision,
            0.0,
        )

        self.assertEqual(
            metrics.recall,
            0.0,
        )

        self.assertEqual(
            metrics.f1,
            0.0,
        )


if __name__ == "__main__":
    unittest.main()