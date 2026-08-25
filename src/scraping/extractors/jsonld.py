"""
JSON-LD Schema.org JobPosting extractor.

Extracts structured job data from pages containing Schema.org JobPosting JSON-LD.
This is the highest-priority extractor since it provides machine-readable structured data.
"""

import json
import re
import html
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
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

            # XpressJobs frequently puts the requirements inside the HTML
            # description rather than the Schema.org ``qualifications`` field.
            # Recover that section so it is not lost during extraction.
            hostname = (urllib.parse.urlparse(url).hostname or "").lower()

            if (
                hostname in {"xpress.jobs", "www.xpress.jobs"}
                and result.job_description_raw
            ):
                result.requirements_raw = self._extract_xpress_requirements(
                result.job_description_raw
            )

            # If Schema.org did not provide a closing date, use the
            # "X Days Left to Apply" value shown on the XpressJobs page.
            if not result.closing_date_raw:
                days_left = self._extract_xpress_days_left(html_content)

                if days_left is not None:
                    result.closing_date_raw = self._calculate_closing_date(days_left)
            
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

    def _extract_xpress_requirements(self, description_html):
        """Extracts the requirements section from XpressJobs job description HTML."""
        if not description_html:
            return ""

        soup = BeautifulSoup(
            description_html,
            "html.parser"
        )

        # Look for the beginning of the requirements section.
        start_node = None

        for node in soup.find_all(
            ["p", "h1", "h2", "h3", "h4", "strong"]
        ):
            text = " ".join(
                node.get_text(
                    " ",
                    strip=True
                ).split()
            ).lower()

            if (
                "entry requirements" in text
                or text == "requirements"
                or text == "qualifications & experience"
                or text == "qualifications and experience"
                or text == "qualifications/experience"
            ):
                start_node = node
                break

        if start_node is None:
            return ""

        requirements = []
        started_list = False

        # Walk forward through the HTML after the heading.
        for node in start_node.find_all_next():

            # We mainly want list items because XpressJobs
            # normally stores each requirement as <li>.
            if node.name == "li":
                text = " ".join(
                    node.get_text(
                        " ",
                        strip=True
                    ).split()
                )

                if text:
                    requirements.append(text)
                    started_list = True

                continue

            # Once the requirement list has started, stop at
            # the next major section heading.
            if started_list and node.name in {
                "h1",
                "h2",
                "h3",
                "h4",
                "p",
            }:
                text = " ".join(
                    node.get_text(
                        " ",
                        strip=True
                    ).split()
                ).lower()

                if (
                    "please click the apply" in text
                    or "how to apply" in text
                    or text in {
                        "benefits",
                        "what we offer",
                        "about the company",
                        "application process",
                    }
                ):
                    break

        # Remove duplicates while preserving order.
        unique_requirements = []
        seen = set()

        for requirement in requirements:
            if requirement not in seen:
                seen.add(requirement)
                unique_requirements.append(
                    requirement
                )

        return "\n".join(
            f"- {requirement}"
            for requirement in unique_requirements
        )

    def _extract_xpress_days_left(self, html_content):
        """Extracts the number of days left to apply from XpressJobs HTML."""
        if not html_content:
            return None

        soup = BeautifulSoup(
            html_content,
            "html.parser"
        )

        visible_text = soup.get_text(
            " ",
            strip=True
        )

        visible_text = " ".join(
            visible_text.split()
        )

        patterns = [
            r"(\d+)\s+days?\s+left\s+to\s+apply",
            r"(\d+)\s+days?\s+left",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                visible_text,
                flags=re.IGNORECASE
            )

            if match:
                try:
                    return int(match.group(1))
                except (TypeError, ValueError):
                    return None

        return None

    def _calculate_closing_date(self, days_left):
        """Calculates the closing date based on days left to apply."""
        try:
            days_left = int(days_left)
        except (TypeError, ValueError):
            return ""

        if days_left < 0:
            return ""

        today = datetime.now(
            ZoneInfo("Asia/Colombo")
        ).date()

        closing_date = (
            today + timedelta(days=days_left)
        )

        return closing_date.strftime(
            "%Y-%m-%d"
        )