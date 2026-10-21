import unittest
from pathlib import Path

from src.extraction.taxonomy import (
    get_all_skills,
    get_category_for_skill,
    get_skill_by_id,
    load_taxonomy,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TAXONOMY_PATH = (
    PROJECT_ROOT
    / "config"
    / "skill_taxonomy.json"
)


class TaxonomyLoaderTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.taxonomy = load_taxonomy(TAXONOMY_PATH)

    def test_taxonomy_loads(self):
        self.assertEqual(
            self.taxonomy.taxonomy_version,
            "0.1.0",
        )

    def test_taxonomy_has_categories(self):
        self.assertGreater(
            len(self.taxonomy.categories),
            0,
        )

    def test_taxonomy_has_skills(self):
        skills = get_all_skills(self.taxonomy)

        self.assertGreater(
            len(skills),
            0,
        )

    def test_python_skill_exists(self):
        skill = get_skill_by_id(
            self.taxonomy,
            "python",
        )

        self.assertIsNotNone(skill)
        self.assertEqual(skill.name, "Python")

    def test_python_category(self):
        category = get_category_for_skill(
            self.taxonomy,
            "python",
        )

        self.assertIsNotNone(category)
        self.assertEqual(
            category.id,
            "programming_languages",
        )

    def test_skill_ids_are_unique(self):
        skills = get_all_skills(self.taxonomy)

        skill_ids = [skill.id for skill in skills]

        self.assertEqual(
            len(skill_ids),
            len(set(skill_ids)),
        )


if __name__ == "__main__":
    unittest.main()