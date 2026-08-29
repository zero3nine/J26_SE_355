from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ExtractedSkill:
    skill_id: str


@dataclass(frozen=True)
class ExtractionResult:
    job_id: str
    skills: Sequence[ExtractedSkill]