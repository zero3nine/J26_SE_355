import unittest

import torch

from src.extraction.semantic import SemanticSkillExtractor
from src.extraction.taxonomy import (
    Skill,
    SkillCategory,
    SkillTaxonomy,
)


class FakeEmbedder:

    def encode(self, texts):
        if isinstance(texts, str):
            texts = [texts]

        embeddings = []

        for text in texts:
            text = text.lower()

            if "python" in text:
                embeddings.append([1.0, 0.0, 0.0])
            elif "java" in text:
                embeddings.append([0.0, 1.0, 0.0])
            elif "selenium" in text:
                embeddings.append([0.0, 0.0, 1.0])
            else:
                embeddings.append([0.0, 0.0, 0.0])

        return torch.tensor(
            embeddings,
            dtype=torch.float32,
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
                        aliases=["python"],
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
                ],
            ),
        ],
    )


class SemanticSkillExtractorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.taxonomy = create_test_taxonomy()

        cls.extractor = SemanticSkillExtractor(
            taxonomy=cls.taxonomy,
            embedder=FakeEmbedder(),
            threshold=0.5,
        )

    def test_extract_returns_job_id(self):
        result = self.extractor.extract(
            "job_001",
            "Python",
        )

        self.assertEqual(
            result.job_id,
            "job_001",
        )

    def test_extracts_semantically_matching_skill(self):
        result = self.extractor.extract(
            "job_001",
            "Python",
        )

        skill_ids = {
            skill.skill_id
            for skill in result.skills
        }

        self.assertIn(
            "python",
            skill_ids,
        )

    def test_non_string_text_is_rejected(self):
        with self.assertRaises(TypeError):
            self.extractor.extract(
                "job_001",
                None,
            )

    def test_invalid_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            SemanticSkillExtractor(
                taxonomy=self.taxonomy,
                embedder=FakeEmbedder(),
                threshold=1.5,
            )


if __name__ == "__main__":
    unittest.main()