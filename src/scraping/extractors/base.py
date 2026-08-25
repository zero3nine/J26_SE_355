"""
Abstract base class for job extractors.

Every extractor must subclass JobExtractor and implement can_handle() and extract().
"""

from abc import ABC, abstractmethod
from src.scraping.models import ExtractionResult


class JobExtractor(ABC):
    """Base class for all job extractors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of this extractor (e.g., 'topjobs', 'jsonld', 'generic_html')."""
        ...

    @property
    def supported_hostnames(self) -> list:
        """List of hostnames this extractor explicitly supports.
        Empty list means the extractor may handle any hostname (e.g., JSON-LD, generic).
        """
        return []

    @abstractmethod
    def can_handle(self, url: str, html: str) -> bool:
        """Returns True if this extractor can extract job data from the given page.

        Args:
            url: The final resolved URL.
            html: The full HTML content of the page.

        Returns:
            True if this extractor should attempt extraction.
        """
        ...

    @abstractmethod
    def extract(self, url: str, html: str, result: ExtractionResult) -> ExtractionResult:
        """Extracts job data from the page HTML.

        Must populate result fields and set extraction_status.
        Must not raise exceptions — catch internally and set error fields.

        Args:
            url: The final resolved URL.
            html: The full HTML content of the page.
            result: Pre-populated ExtractionResult to fill in.

        Returns:
            The populated ExtractionResult.
        """
        ...
