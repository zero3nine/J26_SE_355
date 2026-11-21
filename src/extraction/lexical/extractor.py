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

        original_indices = None
        if len(normalized_text) != len(text):
            original_indices = [
                index for index, character in enumerate(text) for _ in character.casefold()
            ]
        matches = {}

        for skill in get_all_skills(self.taxonomy):
            for alias in skill.aliases:
                pattern = rf"(?<!\w){re.escape(alias.casefold())}(?!\w)"
                match = re.search(pattern, normalized_text)
                if match is not None:
                    start, end = match.span()
                    if original_indices is not None:
                        start, end = original_indices[start], original_indices[end - 1] + 1
                    matches[skill.id] = text[start:end]
                    break

        skills = [
            ExtractedSkill(skill_id=skill_id, supporting_text=fragment)
            for skill_id, fragment in sorted(matches.items())
        ]

        return ExtractionResult(
            job_id=job_id,
            skills=skills,
        )
