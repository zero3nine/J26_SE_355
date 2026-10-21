"""
Configurable Source Registry for Regional IT Job Portals.
Academic Research Component for Regional Comparative IT Labor-Market Analysis.

Manages metadata, extraction strategy, validation status, URL patterns,
and ethical access policies across India, Singapore, Malaysia, and Sri Lanka.
"""

from __future__ import annotations

import json
import pathlib
import re
import urllib.parse
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


VALIDATION_STATUSES = {
    "validated",           # Independently evaluated against ground-truth benchmark
    "pilot_tested",        # Integration verified with offline regression fixtures / sample batch
    "access_restricted",   # Perimeter anti-bot challenge / Cloudflare / CAPTCHA wall (scraping prohibited)
    "unsupported",         # No functional adapter or out-of-scope portal
    "pending_evaluation",  # Added to pipeline but accuracy not yet measured
}


@dataclass
class SourceConfig:
    """Configuration and empirical governance metadata for a single job portal."""
    source_hostname: str
    aliases: List[str] = field(default_factory=list)
    display_name: str = ""
    supported_country: str = "Unspecified"
    target_market: str = ""
    validation_status: str = "pending_evaluation"
    extraction_strategy: str = "generic_html"
    adapter_name: str = "generic_html"
    adapter_version: str = "1.0.0"
    requires_browser_rendering: bool = False
    polite_delay_seconds: float = 2.0
    timeout_seconds: int = 15
    listing_patterns: List[str] = field(default_factory=list)
    detail_patterns: List[str] = field(default_factory=list)
    field_mappings: Dict[str, Any] = field(default_factory=dict)
    access_policy: Dict[str, Any] = field(default_factory=dict)
    last_successful_test: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_access_restricted(self) -> bool:
        return self.validation_status == "access_restricted"

    @property
    def is_validated(self) -> bool:
        return self.validation_status == "validated"


class SourceRegistry:
    """Manages portal configurations, URL routing, access compliance, and adapter discovery."""

    _DEFAULT_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent.parent / "config" / "source_registry.json"

    def __init__(self, config_path: Optional[pathlib.Path] = None):
        self.config_path = config_path or self._DEFAULT_CONFIG_PATH
        self._sources: Dict[str, SourceConfig] = {}
        self._hostname_lookup: Dict[str, str] = {}  # alias/host -> primary_hostname
        self._load_registry()

    def _load_registry(self):
        """Loads and parses source configurations from the JSON registry."""
        if not self.config_path.exists():
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load source registry from {self.config_path}: {e}")
            return

        for item in data.get("sources", []):
            cfg = SourceConfig(**item)
            primary_host = cfg.source_hostname.lower().strip()
            self._sources[primary_host] = cfg
            self._hostname_lookup[primary_host] = primary_host
            for alias in cfg.aliases:
                self._hostname_lookup[alias.lower().strip()] = primary_host

    def _extract_hostname(self, url_or_hostname: str) -> str:
        """Extracts cleaned lowercase hostname from a URL or raw hostname."""
        if not url_or_hostname:
            return ""
        s = url_or_hostname.strip().lower()
        if "://" in s or s.startswith("//"):
            try:
                parsed = urllib.parse.urlparse(s)
                return parsed.hostname or ""
            except Exception:
                return ""
        # Remove any path or query if passed as plain hostname/path
        return s.split("/")[0].split(":")[0]

    def get_source(self, url_or_hostname: str) -> Optional[SourceConfig]:
        """Finds source configuration for a given URL or hostname."""
        host = self._extract_hostname(url_or_hostname)
        if not host:
            return None

        # Exact match or alias match
        primary = self._hostname_lookup.get(host)
        if primary and primary in self._sources:
            return self._sources[primary]

        # Domain suffix match (e.g., job.shine.com -> shine.com)
        for registered_host, primary_key in self._hostname_lookup.items():
            if host.endswith("." + registered_host):
                return self._sources.get(primary_key)

        return None

    def is_supported(self, url_or_hostname: str) -> bool:
        """Returns True if the portal is recognized in the registry."""
        src = self.get_source(url_or_hostname)
        return src is not None

    def is_validated(self, url_or_hostname: str) -> bool:
        """Returns True if the source has passed independent ground-truth evaluation."""
        src = self.get_source(url_or_hostname)
        return src.is_validated if src else False

    def check_access_permission(self, url_or_hostname: str) -> Tuple[bool, str, str]:
        """Evaluates whether automated scraping is ethically and technically permitted.

        Returns:
            Tuple[is_permitted (bool), status (str), explanation (str)]
        """
        src = self.get_source(url_or_hostname)
        if not src:
            return False, "unsupported", "Portal is not recognized in the research source registry."

        if src.is_access_restricted:
            reason = src.access_policy.get(
                "restriction_reason",
                "Automated access is restricted by portal bot-management / perimeter security challenge."
            )
            return False, "access_restricted", reason

        return True, src.validation_status, "Automated research collection permitted under polite rate limits."

    def classify_url(self, url: str) -> Tuple[str, Optional[SourceConfig]]:
        """Classifies a URL into 'detail', 'listing', 'access_restricted', or 'unsupported'.

        Returns:
            Tuple[classification_type (str), source_config (Optional[SourceConfig])]
        """
        src = self.get_source(url)
        if not src:
            return "unsupported", None

        if src.is_access_restricted:
            return "access_restricted", src

        # Check detail patterns
        for pat in src.detail_patterns:
            if re.search(pat, url, re.IGNORECASE):
                return "detail", src

        # Check listing patterns
        for pat in src.listing_patterns:
            if re.search(pat, url, re.IGNORECASE):
                return "listing", src

        # Fallback heuristic: query or trailing structure
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower()
        if any(kw in path for kw in ["/search", "/jobs", "/category", "/browse"]) or parsed.query:
            return "listing", src

        return "unknown", src

    def get_rate_limit(self, url_or_hostname: str, default: float = 2.0) -> float:
        """Returns the configured politeness standby delay in seconds for the portal."""
        src = self.get_source(url_or_hostname)
        if src and src.polite_delay_seconds:
            return src.polite_delay_seconds
        return default

    def get_country(self, url_or_hostname: str) -> str:
        """Returns the primary target country/market associated with the portal."""
        src = self.get_source(url_or_hostname)
        if src:
            return src.supported_country
        return "Unspecified"

    def requires_browser_rendering(self, url_or_hostname: str) -> bool:
        """Returns True if the portal requires Playwright DOM rendering."""
        src = self.get_source(url_or_hostname)
        if src:
            return src.requires_browser_rendering
        return False

    def list_sources(
        self,
        country: Optional[str] = None,
        validation_status: Optional[str] = None
    ) -> List[SourceConfig]:
        """Lists sources filtered by country or validation status."""
        results = list(self._sources.values())
        if country:
            results = [s for s in results if s.supported_country.lower() == country.lower()]
        if validation_status:
            results = [s for s in results if s.validation_status.lower() == validation_status.lower()]
        return results

    def to_dict(self) -> Dict[str, Any]:
        """Serializes current source registry to dictionary."""
        return {
            "sources": [asdict(s) for s in self._sources.values()]
        }


# Global singleton instance for clean cross-module access
_registry_instance: Optional[SourceRegistry] = None


def get_source_registry() -> SourceRegistry:
    """Returns the shared SourceRegistry singleton."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = SourceRegistry()
    return _registry_instance
