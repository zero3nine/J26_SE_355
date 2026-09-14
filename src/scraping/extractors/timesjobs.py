"""
TimesJobs.com (India) dedicated site adapter.
Academic Research Component for Regional Comparative IT Labor-Market Analysis.

Extracts structured job vacancies from TimesJobs (timesjobs.com).
Supports:
- TimesJobs detailed job posting layouts
- Indian IT compensation formats (INR, Lakhs per annum)
- Technical skill chips extraction
- Preserves raw values, provenance, and reports explicit extraction statuses
"""

from __future__ import annotations

import re
import urllib.parse
from bs4 import BeautifulSoup
from typing import Optional

from src.scraping.extractors.base import JobExtractor
from src.scraping.models import ExtractionResult, generate_job_id
from src.cleaning.location_normalizer import normalize_country


class TimesJobsExtractor(JobExtractor):
    """Dedicated site adapter for timesjobs.com (India)."""

    ADAPTER_VERSION = "1.0.0"

    @property
    def name(self) -> str:
        return "timesjobs"

    @property
    def supported_hostnames(self) -> list:
        return [
            "timesjobs.com",
            "www.timesjobs.com",
        ]

    def can_handle(self, url: str, html: str) -> bool:
        """Returns True for timesjobs.com URLs."""
        try:
            hostname = urllib.parse.urlparse(url).hostname or ""
            return hostname.lower() in self.supported_hostnames
        except Exception:
            return False

    def extract(self, url: str, html: str, result: ExtractionResult) -> ExtractionResult:
        """Extracts job posting details from TimesJobs HTML content."""
        result.extractor_name = self.name
        result.source_platform = "www.timesjobs.com"
        result.source_hostname = "timesjobs.com"
        result.country_raw = "India"
        result.extraction_method = "site_adapter"

        if not html or not html.strip():
            result.extraction_status = "network_error"
            result.error_message = "Empty HTML content provided to TimesJobsExtractor"
            return result

        soup = BeautifulSoup(html, "html.parser")

        # 1. Job Title
        title_el = (
            soup.find("h1", class_=re.compile(r"heading-tr|job-title", re.I)) or
            soup.find("h1", class_=re.compile(r"heading", re.I)) or
            soup.find("h1")
        )
        if title_el:
            result.job_title_raw = title_el.get_text(strip=True)

        # 2. Company Name
        co_el = (
            soup.find("h2", class_=re.compile(r"heading-sub|company-name|sub-heading", re.I)) or
            soup.find("span", class_=re.compile(r"company-name", re.I)) or
            soup.find(class_=re.compile(r"hiring-company|employer", re.I))
        )
        if co_el:
            result.company_raw = co_el.get_text(strip=True)

        # 3. Job ID from URL or page
        result.source_job_id = self._extract_job_id(url, soup)
        result.job_id = generate_job_id("timesjobs.com", result.source_job_id, url)

        # 4. Basic Info: Location, Experience, Salary
        info_items = soup.find_all("li", class_=re.compile(r"job-basic-info|basic-info", re.I))
        if not info_items:
            basic_div = soup.find(class_=re.compile(r"job-basic-info|c-job-details", re.I))
            if basic_div:
                info_items = basic_div.find_all("li")

        for item in info_items:
            text = item.get_text(strip=True)
            # Location
            if any(loc_kw in text.lower() for loc_kw in ["location", "bengaluru", "bangalore", "hyderabad", "pune", "mumbai", "delhi", "chennai", "noida", "gurgaon"]):
                clean_loc = re.sub(r'(?i)location\s*[:\-]?', '', text).strip()
                result.location_raw = clean_loc
            # Salary
            if any(sal_kw in text.lower() for sal_kw in ["rs", "₹", "inr", "lakh", "lpa", "salary"]):
                clean_sal = re.sub(r'(?i)salary\s*[:\-]?', '', text).strip()
                result.salary_text_raw = clean_sal

        # Location fallback
        if not result.location_raw:
            loc_span = soup.find("span", class_=re.compile(r"location|city", re.I))
            if loc_span:
                result.location_raw = loc_span.get_text(strip=True)

        # Country normalization
        if result.location_raw:
            loc_lower = result.location_raw.lower()
            if "singapore" in loc_lower:
                result.country_raw = "Singapore"
            elif "malaysia" in loc_lower or "kuala lumpur" in loc_lower:
                result.country_raw = "Malaysia"
            elif "india" in loc_lower or any(c in loc_lower for c in ["bengaluru", "bangalore", "hyderabad", "pune", "delhi", "mumbai", "chennai", "noida", "gurgaon"]):
                result.country_raw = "India"
            else:
                norm_c = normalize_country(result.location_raw)
                if norm_c and norm_c not in ("Unspecified", "", result.location_raw):
                    result.country_raw = norm_c

        # Parse Salary if available
        if result.salary_text_raw:
            self._parse_salary_text(result.salary_text_raw, result)

        # 5. Key Skills
        skill_els = (
            soup.find_all("span", class_=re.compile(r"more-skills-sections|skill-tag|key-skills", re.I)) or
            soup.find_all("a", class_=re.compile(r"srp-skills|skill", re.I))
        )
        skills_found = [s.get_text(strip=True) for s in skill_els if s.get_text(strip=True) and len(s.get_text(strip=True)) < 30]
        if skills_found:
            seen_sk = set()
            clean_sk = []
            for sk in skills_found:
                cleaned = re.sub(r'[,\n\r\t]+', '', sk).strip()
                if cleaned and cleaned.lower() not in seen_sk and cleaned.lower() not in ("skills", "key skills", "apply"):
                    seen_sk.add(cleaned.lower())
                    clean_sk.append(cleaned)
            result.skills_raw = ", ".join(clean_sk)

        # 6. Job Description
        desc_el = (
            soup.find(class_=re.compile(r"job-description|job-desc|jobDetail", re.I)) or
            soup.find(id=re.compile(r"jobDescription|job-description", re.I))
        )
        if desc_el:
            result.job_description_raw = desc_el.get_text(separator="\n", strip=True)
            result.description_type = "html_text"

        # 7. Posted date
        date_el = soup.find(class_=re.compile(r"posted-date|postedDate|date", re.I))
        if date_el:
            result.posted_date_raw = date_el.get_text(strip=True)

        # Extraction status
        if result.job_title_raw and (len(result.job_description_raw) >= 50 or result.company_raw):
            result.extraction_status = "success"
            result.extraction_confidence = 0.85
        elif result.job_title_raw:
            result.extraction_status = "partial"
            result.extraction_confidence = 0.50
        else:
            result.extraction_status = "unsupported"
            result.error_message = "Could not identify job title from TimesJobs structure"

        return result

    def _extract_job_id(self, url: str, soup: BeautifulSoup) -> str:
        """Extracts job identifier from URL or DOM."""
        match = re.search(r'[-_/](\d{4,10})\.html', url)
        if match:
            return match.group(1)
        id_input = soup.find("input", id=re.compile(r"jobId|job_id", re.I))
        if id_input and id_input.get("value"):
            return id_input["value"].strip()
        return ""

    def _parse_salary_text(self, text: str, result: ExtractionResult):
        """Parses Indian salary compensation text."""
        clean = text.replace(",", "").strip()
        if any(un in clean.lower() for un in ["not disclosed", "undisclosed", "as per industry"]):
            result.salary_min_raw = ""
            result.salary_max_raw = ""
            return

        lakhs_match = re.search(r'([\d.]+)\s*(?:-|to)\s*([\d.]+)\s*(?:lakhs?|lacs?|lpa)', clean, re.I)
        if lakhs_match:
            try:
                result.salary_min_raw = str(int(float(lakhs_match.group(1)) * 100000))
                result.salary_max_raw = str(int(float(lakhs_match.group(2)) * 100000))
                result.salary_currency_raw = "INR"
                result.salary_period_raw = "annual"
                return
            except ValueError:
                pass
