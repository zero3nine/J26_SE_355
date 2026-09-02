"""
JSON-LD Schema.org JobPosting extractor.

Extracts structured job data from pages containing Schema.org JobPosting JSON-LD.
This is the highest-priority extractor since it provides machine-readable structured data.
"""

import json
import re
import html
from unittest import result
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
            result.country_raw = self._extract_country(job_posting)
            result.job_description_raw = self._get_str(job_posting, "description", "")
            result.posted_date_raw = self._get_str(job_posting, "datePosted", "")
            result.closing_date_raw = self._get_str(job_posting, "validThrough", "")
            result.employment_type_raw = self._extract_employment_type(job_posting)
            result.industry_raw = self._get_str(job_posting, "industry", "")

            # XpressJobs frequently puts the requirements inside the HTML
            # description rather than the Schema.org ``qualifications`` field.
            # Recover that section so it is not lost during extraction.
            hostname = (urllib.parse.urlparse(url).hostname or "").lower()

            if (
                hostname in {"xpress.jobs", "www.xpress.jobs"}
                and result.job_description_raw
            ):
                (
                result.job_description_raw,
                result.requirements_raw, 
            ) = self._split_xpress_description(
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
            return self._extract_place_text(loc)

        if isinstance(loc, list) and loc:
            locations = []
            for item in loc:
                if isinstance(item, dict):
                    text = self._extract_place_text(item)
                    if text:
                        locations.append(text)
            return "; ".join(locations)

        if isinstance(loc, str):
            return loc.strip()

        return ""

    def _extract_place_text(self, place):
        """Extracts a readable location string from a single Schema.org Place object.

        Prefers the structured PostalAddress (streetAddress/addressLocality/
        addressRegion/addressCountry) since that's what most XpressJobs
        postings actually provide; falls back to a plain "name" field for
        sites that use that shape instead.
        """
        address = place.get("address")
        if isinstance(address, dict):
            parts = [
                address.get("streetAddress", ""),
                address.get("addressLocality", ""),
                address.get("addressRegion", ""),
                address.get("addressCountry", ""),
            ]
            text = ", ".join(p.strip() for p in parts if p and p.strip())
            if text:
                return text
        elif isinstance(address, str) and address.strip():
            return address.strip()

        name = place.get("name", "")
        if name:
            return str(name).strip()

        return ""

    def _extract_country(self, job_posting):
        """Extracts country code(s) from jobLocation address entries.

        XpressJobs sometimes lists multiple jobLocation entries for one
        posting (e.g. a specific city/country plus a generic "Island Wide"
        catch-all) — this collects every distinct addressCountry value found
        instead of assuming just one.
        """
        loc = job_posting.get("jobLocation")
        countries = []

        def add_country(place):
            if not isinstance(place, dict):
                return
            address = place.get("address")
            if isinstance(address, dict):
                country = address.get("addressCountry", "")
                if country and str(country).strip():
                    countries.append(str(country).strip())

        if isinstance(loc, dict):
            add_country(loc)
        elif isinstance(loc, list):
            for item in loc:
                add_country(item)

        # De-duplicate while preserving order.
        seen = set()
        unique_countries = []
        for c in countries:
            if c not in seen:
                seen.add(c)
                unique_countries.append(c)

        return "; ".join(unique_countries)

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

    def _split_xpress_description(self, description_html):
        """Splits the XpressJobs job description into description and requirements."""
        if not description_html:
            return "", ""

        original_html = description_html
        soup = BeautifulSoup(description_html, "html.parser")

        heading_keywords = (
            "requirements",
            "qualification",   # catches both "qualification" and "qualifications"
            "prerequisites",
            "experience required",
            "entry requirements",
            "required skills",
            "preferred skills",
            "key skills",
        )

        start_node = None
        matched_keyword = None

        for node in soup.find_all(["p", "h1", "h2", "h3", "h4", "strong", "li"]):
            text = " ".join(node.get_text(" ", strip=True).split()).lower()
            for kw in heading_keywords:
                if kw in text:
                    start_node = node
                    matched_keyword = kw
                    break
            if start_node:
                break

        # No requirements section found — leave the description untouched.
        if start_node is None:
            return original_html, ""

        heading_container = start_node
        if start_node.parent and start_node.parent.name in ("p", "li"):
            heading_container = start_node.parent

        description_parts = []
        for element in soup.contents:
            if element is heading_container:
                break
            if hasattr(element, "get_text"):
                text = element.get_text(" ", strip=True)
                if text:
                    description_parts.append(text)

        stop_phrases = (
            "please click the apply",
            "how to apply",
            "benefits",
            "what we offer",
            "about the company",
            "application process",
        )

        def clean_line(line):
            # Strip leading bullet markers (-, *, •, ●, en/em dash, etc.)
            return re.sub(r"^[\s\-\u2013\u2014\u2022\u25CF\u25AA\*]+", "", line).strip()

        requirements = []

        # 1) Text living in the SAME block as the heading — this covers the
        #    common "<p>Requirements:<br>- item1<br>- item2</p>" pattern and
        #    "<p><strong>Requirements:</strong> single line of prose</p>".
        #    Using "\n" as the get_text separator turns <br> and block
        #    children into real line breaks instead of squashing them.
        heading_lines = [
            l for l in heading_container.get_text("\n", strip=True).split("\n") if l.strip()
        ]
        for i, line in enumerate(heading_lines):
            lowered = line.strip().lower()
            if i == 0 and matched_keyword in lowered and len(lowered) < len(matched_keyword) + 15:
                # This line is essentially just the label itself
                # ("Requirements", "Requirements:", "Key Requirements -").
                # Try to salvage trailing text after a colon/dash on the same line.
                remainder = re.split(r"[:\-\u2013\u2014]\s*", line, maxsplit=1)
                if len(remainder) == 2 and remainder[1].strip():
                    requirements.append(clean_line(remainder[1]))
                continue
            requirements.append(clean_line(line))

        # 2) Walk forward through the rest of the description for further
        #    bullet/paragraph content, stopping at the next section.
        started = bool(requirements)
        for node in heading_container.find_all_next():
            if node.name in ("li", "p"):
                block_text = node.get_text("\n", strip=True)
                if not block_text:
                    continue
                lowered_block = block_text.lower()
                if any(p in lowered_block for p in stop_phrases):
                    break
                for line in block_text.split("\n"):
                    line = clean_line(line)
                    if line:
                        requirements.append(line)
                        started = True
                continue

            if started and node.name in {"h1", "h2", "h3", "h4"}:
                break

        # Remove duplicates while preserving order.
        unique_requirements = []
        seen = set()
        for requirement in requirements:
            if requirement and requirement not in seen:
                seen.add(requirement)
                unique_requirements.append(requirement)

        requirements_text = "\n".join(f"• {r}" for r in unique_requirements)

        # Safety net: if we found a "Requirements" heading but still
        # couldn't parse any actual requirement lines out of it, don't
        # throw the content away — return the original, untouched
        # description instead of a description missing that section.
        if not requirements_text.strip():
            return original_html, ""

        description_text = "\n\n".join(description_parts)
        return description_text, requirements_text

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