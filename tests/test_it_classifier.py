import unittest
import tempfile
import pathlib
from src.cleaning.it_classifier import ITClassifier


class TestITClassifier(unittest.TestCase):
    """Unit tests for the ITClassifier class."""

    def setUp(self):
        # Create a mock it_keywords file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mock_file = pathlib.Path(self.temp_dir.name) / "mock_keywords.txt"
        
        with open(self.mock_file, "w", encoding="utf-8") as f:
            f.write("## INCLUSION KEYWORDS\n")
            f.write("software\n")
            f.write("developer\n")
            f.write("engineer\n")
            f.write("qa\n")
            f.write("\n")
            f.write("## EXCLUSION KEYWORDS\n")
            f.write("graphic\n")
            f.write("sales | sales roles\n")
            f.write("operator\n")
            f.write("\n")
            f.write("## AMBIGUOUS KEYWORDS\n")
            f.write("manager\n")
            f.write("intern\n")
            f.write("trainee\n")

        self.classifier = ITClassifier(config_path=self.mock_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_keywords(self):
        self.assertIn("software", self.classifier.inclusions)
        self.assertIn("developer", self.classifier.inclusions)
        self.assertIn("graphic", self.classifier.exclusions)
        self.assertIn("sales", self.classifier.exclusions)
        self.assertIn("manager", self.classifier.ambiguous)

    def test_evaluate_it_job(self):
        is_it, is_ambig, reason = self.classifier.evaluate_title("Senior Software Engineer")
        self.assertTrue(is_it)
        self.assertFalse(is_ambig)

    def test_evaluate_non_it_job(self):
        is_it, is_ambig, reason = self.classifier.evaluate_title("Senior Graphic Designer")
        self.assertFalse(is_it)
        self.assertFalse(is_ambig)
        self.assertIn("exclusion keyword 'graphic'", reason)

    def test_evaluate_ambiguous_job(self):
        is_it, is_ambig, reason = self.classifier.evaluate_title("Trainee Software Developer")
        self.assertTrue(is_it)
        self.assertTrue(is_ambig)
        self.assertEqual(reason, "ambiguous - flagged for manual review")

        is_it, is_ambig, reason = self.classifier.evaluate_title("Project Manager")
        self.assertTrue(is_it)
        self.assertTrue(is_ambig)

    def test_evaluate_exclusion_override(self):
        # "Salesforce Developer" matches exclusion "sales" but also inclusion "developer"
        is_it, is_ambig, reason = self.classifier.evaluate_title("Salesforce Developer")
        self.assertTrue(is_it)
        self.assertFalse(is_ambig)


if __name__ == "__main__":
    unittest.main()
