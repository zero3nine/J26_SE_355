import unittest

from src.extraction import (
    ExtractedSkill,
    ExtractionResult,
)


class ExtractionModelTests(unittest.TestCase):

    def test_extracted_skill(self):
        skill = ExtractedSkill(
            skill_id="python",
        )

        self.assertEqual(
            skill.skill_id,
            "python",
        )

    def test_extraction_result(self):
        result = ExtractionResult(
            job_id="job_001",
            skills=[
                ExtractedSkill("python"),
                ExtractedSkill("sql"),
            ],
        )

        self.assertEqual(
            result.job_id,
            "job_001",
        )

        self.assertEqual(
            len(result.skills),
            2,
        )

        self.assertEqual(
            result.skills[0].skill_id,
            "python",
        )