import json
from pathlib import Path

from .models import Skill, SkillCategory, SkillTaxonomy


def load_taxonomy(path: str | Path) -> SkillTaxonomy:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    categories = []

    for category_data in data["categories"]:
        skills = [
            Skill(
                id=skill_data["id"],
                name=skill_data["name"],
                aliases=skill_data.get("aliases", []),
            )
            for skill_data in category_data["skills"]
        ]

        categories.append(
            SkillCategory(
                id=category_data["id"],
                name=category_data["name"],
                skills=skills,
            )
        )

    return SkillTaxonomy(
        taxonomy_version=data["taxonomy_version"],
        name=data["name"],
        description=data["description"],
        categories=categories,
    )

def get_all_skills(taxonomy: SkillTaxonomy) -> list[Skill]:
    return [
        skill
        for category in taxonomy.categories
        for skill in category.skills
    ]


def get_skill_by_id(
    taxonomy: SkillTaxonomy,
    skill_id: str,
) -> Skill | None:
    for skill in get_all_skills(taxonomy):
        if skill.id == skill_id:
            return skill

    return None


def get_category_for_skill(
    taxonomy: SkillTaxonomy,
    skill_id: str,
) -> SkillCategory | None:
    for category in taxonomy.categories:
        if any(skill.id == skill_id for skill in category.skills):
            return category

    return None