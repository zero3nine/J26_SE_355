import re

from src.extraction.extractors import SkillExtractor
from src.extraction.models import ExtractedSkill, ExtractionResult
from src.extraction.taxonomy import (
    SkillTaxonomy,
    get_all_skills,
)


class LexicalSkillExtractor(SkillExtractor):
    """Extract skills using explicit lexical matching."""

    def __init__(self, taxonomy: SkillTaxonomy):
        self.taxonomy = taxonomy

    def extract(
        self,
        job_id: str,
        text: str,
    ) -> ExtractionResult:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        normalized_text = text.casefold()

        extracted_skill_ids: set[str] = set()

        for skill in get_all_skills(self.taxonomy):
            for alias in skill.aliases:
                if self._matches_alias(
                    normalized_text,
                    alias,
                ):
                    extracted_skill_ids.add(skill.id)
                    break

        skills = [
            ExtractedSkill(skill_id=skill_id)
            for skill_id in sorted(extracted_skill_ids)
        ]

        return ExtractionResult(
            job_id=job_id,
            skills=skills,
        )

    @staticmethod
    def _matches_alias(
        text: str,
        alias: str,
    ) -> bool:
        pattern = rf"(?<!\w){re.escape(alias.casefold())}(?!\w)"

        return re.search(pattern, text) is not None