import unittest

from src.extraction.lexical import LexicalSkillExtractor
from src.extraction.taxonomy import (
    Skill,
    SkillCategory,
    SkillTaxonomy,
)


def create_test_taxonomy() -> SkillTaxonomy:
    return SkillTaxonomy(
        taxonomy_version="test",
        name="Test Taxonomy",
        description="Taxonomy used for unit tests.",
        categories=[
            SkillCategory(
                id="programming_languages",
                name="Programming Languages",
                skills=[
                    Skill(
                        id="python",
                        name="Python",
                        aliases=[
                            "python",
                            "python 3",
                            "python3",
                        ],
                    ),
                    Skill(
                        id="java",
                        name="Java",
                        aliases=["java"],
                    ),
                ],
            ),
            SkillCategory(
                id="testing",
                name="Testing",
                skills=[
                    Skill(
                        id="selenium",
                        name="Selenium",
                        aliases=["selenium"],
                    ),
                    Skill(
                        id="rest_api",
                        name="REST API",
                        aliases=[
                            "rest api",
                            "restful api",
                        ],
                    ),
                ],
            ),
        ],
    )


class LexicalSkillExtractorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.taxonomy = create_test_taxonomy()
        cls.extractor = LexicalSkillExtractor(
            cls.taxonomy
        )

    def test_extracts_exact_skill(self):
        result = self.extractor.extract(
            "job_001",
            "Experience with Python.",
        )

        skill_ids = {
            skill.skill_id
            for skill in result.skills
        }

        self.assertEqual(
            skill_ids,
            {"python"},
        )

    def test_extracts_alias(self):
        result = self.extractor.extract(
            "job_001",
            "Experience with Python3.",
        )

        skill_ids = {
            skill.skill_id
            for skill in result.skills
        }

        self.assertEqual(
            skill_ids,
            {"python"},
        )

    def test_extracts_multiple_skills(self):
        result = self.extractor.extract(
            "job_001",
            (
                "Experience with Java, Selenium "
                "and RESTful API testing."
            ),
        )

        skill_ids = {
            skill.skill_id
            for skill in result.skills
        }

        self.assertEqual(
            skill_ids,
            {
                "java",
                "selenium",
                "rest_api",
            },
        )

    def test_matching_is_case_insensitive(self):
        result = self.extractor.extract(
            "job_001",
            "PYTHON and selenium",
        )

        skill_ids = {
            skill.skill_id
            for skill in result.skills
        }

        self.assertEqual(
            skill_ids,
            {
                "python",
                "selenium",
            },
        )

    def test_duplicate_mentions_return_one_skill(self):
        result = self.extractor.extract(
            "job_001",
            "Python Python Python",
        )

        self.assertEqual(
            len(result.skills),
            1,
        )

    def test_job_id_is_preserved(self):
        result = self.extractor.extract(
            "job_123",
            "Python",
        )

        self.assertEqual(
            result.job_id,
            "job_123",
        )

    def test_non_string_text_is_rejected(self):
        with self.assertRaises(TypeError):
            self.extractor.extract(
                "job_001",
                None,
            )


if __name__ == "__main__":
    unittest.main()