"""
Extractor registry — routes incoming pages to the best available extractor.

Extraction priority:
1. JSON-LD Schema.org JobPosting (structured data — highest quality)
2. Hostname-matched site adapter (Topjobs, etc.)
3. Generic HTML fallback (lowest priority)

Each extractor is tried in order. The first one that can_handle() succeeds
and extraction_status != "not_a_job_page" wins.
"""

import urllib.parse
from src.scraping.extractors.jsonld import JsonLdExtractor
from src.scraping.extractors.topjobs import TopjobsExtractor
from src.scraping.extractors.generic_html import GenericHtmlExtractor
from src.scraping.models import ExtractionResult


class ExtractorRegistry:
    """Registry that tries extractors in priority order."""

    def __init__(self):
        # Initialize all extractors in priority order
        self._jsonld = JsonLdExtractor()
        self._site_adapters = [
            TopjobsExtractor(),
            # Add more site adapters here as needed:
            # ItproExtractor(),
        ]
        self._generic = GenericHtmlExtractor()

        # Build hostname -> adapter lookup
        self._hostname_map = {}
        for adapter in self._site_adapters:
            for hostname in adapter.supported_hostnames:
                self._hostname_map[hostname.lower()] = adapter

    def extract(self, url: str, html: str, result: ExtractionResult) -> ExtractionResult:
        """Routes to the best extractor for this URL/content combination.

        Args:
            url: The final resolved URL.
            html: The full HTML content.
            result: Pre-populated ExtractionResult.

        Returns:
            Populated ExtractionResult.
        """
        # 1. Try JSON-LD first (highest quality)
        if self._jsonld.can_handle(url, html):
            jsonld_result = self._jsonld.extract(url, html, result)
            if jsonld_result.extraction_status in ("success", "partial"):
                return jsonld_result

        # 2. Try hostname-matched site adapter
        hostname = self._get_hostname(url)
        adapter = self._hostname_map.get(hostname)
        if adapter and adapter.can_handle(url, html):
            adapter_result = adapter.extract(url, html, result)
            if adapter_result.extraction_status in ("success", "partial"):
                return adapter_result

        # 3. Fallback to generic HTML
        if self._generic.can_handle(url, html):
            return self._generic.extract(url, html, result)

        # 4. Nothing worked
        result.extraction_status = "unsupported"
        result.extractor_name = "none"
        result.extraction_method = "none"
        result.error_message = "No extractor could handle this page"
        return result

    def get_extractor_for_hostname(self, hostname: str):
        """Returns the site adapter for a hostname, or None."""
        return self._hostname_map.get(hostname.lower())

    def list_supported_hostnames(self):
        """Returns all hostnames with dedicated adapters."""
        return list(self._hostname_map.keys())

    def _get_hostname(self, url: str) -> str:
        """Extracts and lowercases hostname from URL."""
        try:
            return urllib.parse.urlparse(url).hostname.lower() or ""
        except Exception:
            return ""
