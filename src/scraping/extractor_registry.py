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
import json
from src.scraping.extractors.jsonld import JsonLdExtractor
from src.scraping.extractors.topjobs import TopjobsExtractor
from src.scraping.extractors.generic_html import GenericHtmlExtractor
from src.scraping.models import ExtractionResult
from src.security.url_validator import is_approved_domain
from src.scraping.browser_fetch import fetch_page_rendered


class ExtractorRegistry:
    """Registry that tries extractors in priority order, with browser rendering fallback."""

    def __init__(self):
        # Initialize all extractors in priority order
        self._jsonld = JsonLdExtractor()
        self._site_adapters = [
            TopjobsExtractor(),
        ]
        self._generic = GenericHtmlExtractor()

        # Build hostname -> adapter lookup
        self._hostname_map = {}
        for adapter in self._site_adapters:
            for hostname in adapter.supported_hostnames:
                self._hostname_map[hostname.lower()] = adapter

        # Rendered HTML Cache (URL -> (rendered_html, final_url))
        self._render_cache = {}

    def extract(self, url: str, html: str, result: ExtractionResult, use_browser_fallback: bool = False) -> ExtractionResult:
        """Routes to the best extractor for this URL/content combination, with fallback.

        Args:
            url: The final resolved URL.
            html: The full HTTP HTML content.
            result: Pre-populated ExtractionResult.
            use_browser_fallback: Whether to use Playwright fallback if HTTP HTML is insufficient.

        Returns:
            Populated ExtractionResult.
        """
        result.fetch_method = "http"
        result.rendering_used = "False"

        # 1. Try JSON-LD first (highest quality)
        if self._jsonld.can_handle(url, html):
            jsonld_result = self._jsonld.extract(url, html, result)
            if jsonld_result.extraction_status == "success":
                return jsonld_result

        # 2. Try hostname-matched site adapter
        hostname = self._get_hostname(url)
        adapter = self._hostname_map.get(hostname)
        if adapter and adapter.can_handle(url, html):
            adapter_result = adapter.extract(url, html, result)
            if adapter_result.extraction_status == "success":
                return adapter_result

        # 3. Fallback to generic HTML
        if self._generic.can_handle(url, html):
            generic_result = self._generic.extract(url, html, result)
            # If HTTP HTML got success, return it immediately
            if generic_result.extraction_status == "success":
                return generic_result

        # 4. Check if HTTP HTML is insufficient and browser rendering is approved/enabled
        is_insufficient = (
            result.extraction_status not in ("success", "partial") or
            not result.job_title_raw.strip() or
            not result.job_description_raw.strip() or
            len(result.job_description_raw.strip()) < 100
        )

        if is_insufficient and use_browser_fallback:
            print(f"  → HTTP HTML insufficient. Triggering browser fallback for approved domain '{hostname}'...")
            rendered_html = ""
            final_rendered_url = url
            
            # Use cache or render
            if url in self._render_cache:
                rendered_html, final_rendered_url = self._render_cache[url]
                print("  → Using cached rendered DOM.")
            else:
                rendered_html = ""
                final_rendered_url = url
                fetch_result = fetch_page_rendered(url)
                if fetch_result.success:
                    rendered_html = fetch_result.html
                    final_rendered_url = fetch_result.final_url or url
                    self._render_cache[url] = (rendered_html, final_rendered_url)
                else:
                    print(f"  → Browser fallback failed: {fetch_result.error_message}")
                    result.failure_reason = f"Browser rendering failed: {fetch_result.error_message}"

            if rendered_html:
                # Re-run extraction on rendered HTML
                result.fetch_method = "browser"
                result.rendering_used = "True"
                result.final_url = final_rendered_url
                
                # Re-extract layers
                # 1. JSON-LD
                if self._jsonld.can_handle(final_rendered_url, rendered_html):
                    jsonld_res = self._jsonld.extract(final_rendered_url, rendered_html, result)
                    if jsonld_res.extraction_status == "success":
                        return jsonld_res
                
                # 2. Adapter
                adapter = self._hostname_map.get(self._get_hostname(final_rendered_url))
                if adapter and adapter.can_handle(final_rendered_url, rendered_html):
                    adapter_res = adapter.extract(final_rendered_url, rendered_html, result)
                    if adapter_res.extraction_status == "success":
                        return adapter_res
                
                # 3. Generic
                return self._generic.extract(final_rendered_url, rendered_html, result)

        # 5. Nothing worked/insufficient
        if result.extraction_status not in ("success", "partial"):
            result.extraction_status = "unsupported"
            result.extractor_name = "none"
            result.extraction_method = "none"
            result.error_message = "No extractor could reliably handle this page"
            
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
