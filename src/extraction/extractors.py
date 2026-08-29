from abc import ABC, abstractmethod

from .models import ExtractionResult


class SkillExtractor(ABC):

    @abstractmethod
    def extract(
        self,
        job_id: str,
        text: str,
    ) -> ExtractionResult:
        """Extract canonical skills from job description text."""
        raise NotImplementedError