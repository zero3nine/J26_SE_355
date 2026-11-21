from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ExtractedSkill:
    skill_id: str
    similarity: float | None = None
    supporting_text: str | None = None


@dataclass(frozen=True)
class ExtractionResult:
    job_id: str
    skills: Sequence[ExtractedSkill]
