import unittest

from src.extraction import SkillExtractor


class TestExtractor(SkillExtractor):

    def extract(
        self,
        job_id: str,
        text: str,
    ):
        raise NotImplementedError


class SkillExtractorInterfaceTests(unittest.TestCase):

    def test_extractor_is_abstract(self):
        self.assertTrue(
            hasattr(SkillExtractor, "extract")
        )

    def test_test_implementation_can_be_defined(self):
        extractor = TestExtractor()

        self.assertIsInstance(
            extractor,
            SkillExtractor,
        )


if __name__ == "__main__":
    unittest.main()