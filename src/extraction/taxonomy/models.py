from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    aliases: List[str]


@dataclass(frozen=True)
class SkillCategory:
    id: str
    name: str
    skills: List[Skill]


@dataclass(frozen=True)
class SkillTaxonomy:
    taxonomy_version: str
    name: str
    description: str
    categories: List[SkillCategory]