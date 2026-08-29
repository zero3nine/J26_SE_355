"""
JSON-LD Schema.org JobPosting extractor.

Extracts structured job data from pages containing Schema.org JobPosting JSON-LD.
This is the highest-priority extractor since it provides machine-readable structured data.
"""

import json
import re
import html
from bs4 import BeautifulSoup
from src.scraping.extractors.base import JobExtractor
from src.scraping.models import ExtractionResult, generate_job_id


class JsonLdExtractor(JobExtractor):
    """Extracts job data from Schema.org JobPosting JSON-LD blocks."""

    @property
    def name(self) -> str:
        return "jsonld"

    def can_handle(self, url: str, html_content: str) -> bool:
        """Returns True if the page contains a JSON-LD block with JobPosting."""
        if not html_content:
            return False
        # Quick check before parsing
        if "application/ld+json" not in html_content:
            return False
        if "JobPosting" not in html_content:
            return False
        return True

    def extract(self, url: str, html_content: str, result: ExtractionResult) -> ExtractionResult:
        """Extracts job data from JSON-LD JobPosting blocks."""
        result.extractor_name = self.name
        result.extraction_method = "jsonld"

        try:
            soup = BeautifulSoup(html_content, "html.parser")
            scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

            if not scripts:
                result.extraction_status = "not_a_job_page"
                result.error_message = "No JSON-LD blocks found"
                return result

            job_posting = None

            for script in scripts:
                text = script.string
                if not text:
                    continue
                try:
                    data = json.loads(text)
                except (json.JSONDecodeError, ValueError):
                    continue

                # Find JobPosting in the data
                job_posting = self._find_job_posting(data)
                if job_posting:
                    break

            if not job_posting:
                result.extraction_status = "not_a_job_page"
                result.error_message = "No JobPosting found in JSON-LD blocks"
                return result

            # Extract fields from the JobPosting object
            result.job_title_raw = self._get_str(job_posting, "title", "")
            result.company_raw = self._extract_company(job_posting)
            result.location_raw = self._extract_location(job_posting)
            result.job_description_raw = self._get_str(job_posting, "description", "")
            result.posted_date_raw = self._get_str(job_posting, "datePosted", "")
            result.closing_date_raw = self._get_str(job_posting, "validThrough", "")
            result.employment_type_raw = self._extract_employment_type(job_posting)
            result.industry_raw = self._get_str(job_posting, "industry", "")
            result.skills_raw = self._extract_list_field(job_posting, "skills")
            result.qualifications_raw = self._extract_list_field(job_posting, "qualifications")

            # Extract identifiers
            identifier = job_posting.get("identifier")
            if isinstance(identifier, dict):
                result.source_job_id = str(identifier.get("value", ""))
            elif isinstance(identifier, str):
                result.source_job_id = identifier

            # Generate job_id
            result.job_id = generate_job_id(
                result.source_hostname, result.source_job_id, url
            )

            # Classify description type
            if result.job_description_raw:
                result.description_type = "jsonld"
            else:
                result.description_type = "missing"

            # Determine extraction quality
            has_title = bool(result.job_title_raw.strip())
            has_description = bool(result.job_description_raw.strip())
            has_company = bool(result.company_raw.strip())

            if has_title and has_description:
                result.extraction_status = "success"
                result.extraction_confidence = 0.9
                if not has_company:
                    result.extraction_confidence = 0.7
            elif has_title:
                result.extraction_status = "partial"
                result.extraction_confidence = 0.5
            else:
                result.extraction_status = "partial"
                result.extraction_confidence = 0.3
                result.manual_review_reason = "Job title missing from JSON-LD"

            return result

        except Exception as e:
            result.extraction_status = "parse_error"
            result.error_type = "parse_error"
            result.error_message = f"JSON-LD extraction failed: {e}"
            return result

    def _find_job_posting(self, data):
        """Recursively searches for a JobPosting object in JSON-LD data."""
        if isinstance(data, dict):
            # Check @type
            type_val = data.get("@type", "")
            if isinstance(type_val, list):
                if "JobPosting" in type_val:
                    return data
            elif type_val == "JobPosting":
                return data

            # Check @graph
            graph = data.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    found = self._find_job_posting(item)
                    if found:
                        return found

        elif isinstance(data, list):
            for item in data:
                found = self._find_job_posting(item)
                if found:
                    return found

        return None

    def _get_str(self, obj, key, default=""):
        """Safely gets a string value from a dict."""
        val = obj.get(key, default)
        if isinstance(val, dict):
            for text_key in ["innerText", "outerText", "textContent", "value", "@value"]:
                if text_key in val and val[text_key]:
                    val = val[text_key]
                    break
        if isinstance(val, str):
            return val.strip()
        if isinstance(val, list):
            return ", ".join(str(v) for v in val)
        if val is not None:
            return str(val).strip()
        return default

    def _extract_company(self, job_posting):
        """Extracts company name from hiringOrganization."""
        org = job_posting.get("hiringOrganization")
        if isinstance(org, dict):
            return self._get_str(org, "name", "")
        if isinstance(org, str):
            return org.strip()
        return ""

    def _extract_location(self, job_posting):
        """Extracts location from jobLocation."""
        loc = job_posting.get("jobLocation")
        if isinstance(loc, dict):
            address = loc.get("address")
            if isinstance(address, dict):
                parts = [
                    address.get("streetAddress", ""),
                    address.get("addressLocality", ""),
                    address.get("addressRegion", ""),
                    address.get("addressCountry", ""),
                ]
                return ", ".join(p.strip() for p in parts if p and p.strip())
            name = loc.get("name", "")
            if name:
                return str(name).strip()
        if isinstance(loc, list) and loc:
            locations = []
            for item in loc:
                if isinstance(item, dict):
                    name = item.get("name", "")
                    if name:
                        locations.append(str(name).strip())
            return "; ".join(locations)
        if isinstance(loc, str):
            return loc.strip()
        return ""

    def _extract_employment_type(self, job_posting):
        """Extracts employment type."""
        et = job_posting.get("employmentType")
        if isinstance(et, list):
            return ", ".join(str(v) for v in et)
        if isinstance(et, str):
            return et.strip()
        return ""

    def _extract_list_field(self, job_posting, key):
        """Extracts a field that could be string, list, or object."""
        val = job_posting.get(key)
        if isinstance(val, list):
            return ", ".join(str(v) for v in val)
        if isinstance(val, str):
            return val.strip()
        return ""
