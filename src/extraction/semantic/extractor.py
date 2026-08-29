import re

from sentence_transformers.util import cos_sim

from src.extraction.extractors import SkillExtractor
from src.extraction.models import ExtractedSkill, ExtractionResult
from src.extraction.taxonomy import (
    Skill,
    SkillTaxonomy,
    get_all_skills,
)

from .embedder import SemanticEmbedder


class SemanticSkillExtractor(SkillExtractor):
    """Extract skills using semantic similarity."""

    DEFAULT_THRESHOLD = 0.50

    def __init__(
        self,
        taxonomy: SkillTaxonomy,
        embedder: SemanticEmbedder | None = None,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        if not 0 <= threshold <= 1:
            raise ValueError(
                "threshold must be between 0 and 1"
            )

        self.taxonomy = taxonomy
        self.embedder = embedder or SemanticEmbedder()
        self.threshold = threshold

        self.skills = get_all_skills(taxonomy)

        self.skill_texts = [
            self._build_skill_text(skill)
            for skill in self.skills
        ]

        self.skill_embeddings = self.embedder.encode(
            self.skill_texts
        )

    @staticmethod
    def _build_skill_text(skill: Skill) -> str:
        """Create semantic representation of a taxonomy skill."""

        aliases = ", ".join(skill.aliases)

        return (
            f"Skill: {skill.name}. "
            f"Known terms: {aliases}."
        )

    @staticmethod
    def _split_into_candidates(
        text: str,
    ) -> list[str]:
        """Split job description into meaningful text candidates."""

        candidates = re.split(
            r"(?<=[.!?])\s+|\n+|•|·",
            text,
        )

        return [
            candidate.strip()
            for candidate in candidates
            if candidate.strip()
        ]

    def extract(
        self,
        job_id: str,
        text: str,
    ) -> ExtractionResult:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        candidates = self._split_into_candidates(text)

        if not candidates:
            return ExtractionResult(
                job_id=job_id,
                skills=[],
            )

        candidate_embeddings = self.embedder.encode(
            candidates
        )

        similarities = cos_sim(
            candidate_embeddings,
            self.skill_embeddings,
        )

        extracted_skills: dict[str, float] = {}

        for candidate_index, _candidate in enumerate(candidates):
            for skill_index, skill in enumerate(self.skills):
                similarity = similarities[
                    candidate_index,
                    skill_index,
                ].item()

                if similarity >= self.threshold:
                    existing = extracted_skills.get(skill.id)

                    if existing is None or similarity > existing:
                        extracted_skills[skill.id] = similarity

        skills = [
            ExtractedSkill(skill_id=skill_id, confidence=confidence)
            for skill_id, confidence in sorted(extracted_skills.items())
        ]

        return ExtractionResult(
            job_id=job_id,
            skills=skills,
        )