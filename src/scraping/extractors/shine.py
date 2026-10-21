"""
Shine.com (India) dedicated site adapter.
Academic Research Component for Regional Comparative IT Labor-Market Analysis.

Extracts structured job vacancies from India's leading tech portal (shine.com).
Supports:
- Schema.org JSON-LD structured parsing when available
- Shine HTML DOM parsing across legacy and current widget layouts
- Indian compensation structures (Lakhs INR per annum, monthly, undisclosed)
- Multi-location Indian cities and international/remote postings
- Preserves raw values, provenance, and reports explicit extraction statuses
"""

from __future__ import annotations

import re
import json
import urllib.parse
from bs4 import BeautifulSoup
from typing import Optional, Tuple

from src.scraping.extractors.base import JobExtractor
from src.scraping.models import ExtractionResult, generate_job_id
from src.cleaning.location_normalizer import normalize_country


class ShineExtractor(JobExtractor):
    """Dedicated site adapter for shine.com (India)."""

    ADAPTER_VERSION = "1.2.0"

    @property
    def name(self) -> str:
        return "shine"

    @property
    def supported_hostnames(self) -> list:
        return [
            "shine.com",
            "www.shine.com",
            "recruiter.shine.com",
            "resume.shine.com",
        ]

    def can_handle(self, url: str, html: str) -> bool:
        """Returns True for shine.com URLs."""
        try:
            hostname = urllib.parse.urlparse(url).hostname or ""
            return hostname.lower() in self.supported_hostnames
        except Exception:
            return False

    def extract(self, url: str, html: str, result: ExtractionResult) -> ExtractionResult:
        """Extracts job posting details from Shine.com HTML content."""
        result.extractor_name = self.name
        result.source_platform = "www.shine.com"
        result.source_hostname = "shine.com"
        result.country_raw = "India"  # Initial default, refined by location

        if not html or not html.strip():
            result.extraction_status = "network_error"
            result.error_message = "Empty HTML content provided to ShineExtractor"
            return result

        soup = BeautifulSoup(html, "html.parser")

        # 1. Attempt JSON-LD extraction if present and well-formed
        has_extracted_jsonld = self._try_extract_jsonld(soup, url, result)
        if has_extracted_jsonld and result.job_title_raw and len(result.job_description_raw) > 50:
            result.extraction_method = "jsonld"
            result.extraction_status = "success"
            result.extraction_confidence = 0.95
            return result

        # 2. Extract directly from Shine DOM structure
        return self._extract_from_dom(soup, url, result)

    def _try_extract_jsonld(self, soup: BeautifulSoup, url: str, result: ExtractionResult) -> bool:
        """Extracts Schema.org JobPosting data from <script type='application/ld+json'>."""
        for tag in soup.find_all("script", type="application/ld+json"):
            if not tag.string:
                continue
            try:
                data = json.loads(tag.string)
            except Exception:
                continue

            # Support single JobPosting or graph list
            items = data.get("@graph", [data]) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for item in items:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    result.job_title_raw = str(item.get("title", "")).strip()
                    
                    # Company
                    hiring_org = item.get("hiringOrganization", {})
                    if isinstance(hiring_org, dict):
                        result.company_raw = str(hiring_org.get("name", "")).strip()
                    elif isinstance(hiring_org, str):
                        result.company_raw = hiring_org.strip()

                    # Description
                    desc = item.get("description", "")
                    if desc:
                        clean_desc = BeautifulSoup(desc, "html.parser").get_text(separator="\n", strip=True)
                        result.job_description_raw = clean_desc
                        result.description_type = "html_text"

                    # Dates
                    result.posted_date_raw = str(item.get("datePosted", "")).strip()
                    result.closing_date_raw = str(item.get("validThrough", "")).strip()
                    result.employment_type_raw = str(item.get("employmentType", "")).strip()

                    # Location
                    job_loc = item.get("jobLocation", {})
                    if isinstance(job_loc, dict):
                        addr = job_loc.get("address", {})
                        if isinstance(addr, dict):
                            locality = addr.get("addressLocality", "")
                            region = addr.get("addressRegion", "")
                            country = addr.get("addressCountry", "")
                            loc_parts = [p for p in [locality, region, country] if p]
                            result.location_raw = ", ".join(loc_parts)
                            if country:
                                result.country_raw = country

                    # Base Salary
                    base_sal = item.get("baseSalary", {})
                    if isinstance(base_sal, dict):
                        val = base_sal.get("value", {})
                        if isinstance(val, dict):
                            result.salary_min_raw = str(val.get("minValue", ""))
                            result.salary_max_raw = str(val.get("maxValue", ""))
                            result.salary_currency_raw = str(base_sal.get("currency", "INR"))
                            result.salary_period_raw = str(val.get("unitText", "YEAR")).lower()

                    # Skills
                    skills = item.get("skills", "")
                    if isinstance(skills, list):
                        result.skills_raw = ", ".join(str(s).strip() for s in skills if s)
                    elif isinstance(skills, str):
                        result.skills_raw = skills.strip()

                    # Job ID
                    result.source_job_id = str(item.get("identifier", {}).get("value", "") or "")
                    if not result.source_job_id:
                        result.source_job_id = self._extract_job_id_from_url(url)

                    result.job_id = generate_job_id("shine.com", result.source_job_id, url)
                    return True

        return False

    def _extract_from_dom(self, soup: BeautifulSoup, url: str, result: ExtractionResult) -> ExtractionResult:
        """Extracts fields using Shine's specific CSS selectors and DOM structure."""
        result.extraction_method = "site_adapter"

        # 1. Job Title
        title_el = (
            soup.find("h1", class_=re.compile(r"jobTitle|heading", re.I)) or
            soup.find(class_=re.compile(r"jobTitle|job_title", re.I)) or
            soup.find("h1")
        )
        if title_el:
            result.job_title_raw = title_el.get_text(strip=True)

        # 2. Company Name
        co_el = (
            soup.find("a", class_=re.compile(r"jobCard_jobCard_cName|company", re.I)) or
            soup.find("span", class_=re.compile(r"company_name|cName", re.I)) or
            soup.find(class_=re.compile(r"company-name|employer-name", re.I))
        )
        if co_el:
            result.company_raw = co_el.get_text(strip=True)

        # 3. Job ID from URL
        result.source_job_id = self._extract_job_id_from_url(url)
        result.job_id = generate_job_id("shine.com", result.source_job_id, url)

        # 4. Meta Information: Experience, Location, Salary from badge lists
        list_items = soup.find_all("li", class_=re.compile(r"jobCard_jobCard_lists_item|list_item", re.I))
        if not list_items:
            # Fallback for alternative Shine layouts
            list_items = soup.find_all(class_=re.compile(r"jobDetailWidget|jobInfo|job-info", re.I))

        for li in list_items:
            text = li.get_text(strip=True)
            class_str = " ".join(li.get("class", [])).lower()
            # Location
            if (any(loc_kw in text.lower() for loc_kw in ["bangalore", "bengaluru", "hyderabad", "pune", "mumbai", "delhi", "noida", "gurgaon", "chennai", "kolkata", "singapore", "malaysia", "kuala lumpur", "remote"])
                    or "loc" in class_str or "city" in class_str):
                result.location_raw = text

            # Salary
            if (any(sal_kw in text.lower() for sal_kw in ["lakh", "lpa", "₹", "rs", "inr", "sgd", "myr", "$", "per annum", "per month", "undisclosed", "not disclosed"])
                    or "sal" in class_str):
                result.salary_text_raw = text

            # Work Mode
            if "work from home" in text.lower() or "remote" in text.lower():
                result.work_mode_raw = "remote"
            elif "hybrid" in text.lower():
                result.work_mode_raw = "hybrid"

        # Dedicated Location element lookup if not captured in list
        if not result.location_raw:
            loc_el = soup.find(class_=re.compile(r"job_location|location|city", re.I))
            if loc_el:
                result.location_raw = loc_el.get_text(strip=True)

        # Analyze country from location (never assume Indian portal = India if explicitly foreign/remote)
        if result.location_raw:
            loc_lower = result.location_raw.lower()
            if "singapore" in loc_lower:
                result.country_raw = "Singapore"
            elif "malaysia" in loc_lower or "kuala lumpur" in loc_lower:
                result.country_raw = "Malaysia"
            elif "india" in loc_lower or any(c in loc_lower for c in ["bengaluru", "bangalore", "hyderabad", "pune", "mumbai", "delhi", "chennai", "noida", "gurgaon", "karnataka", "telangana"]):
                result.country_raw = "India"
            else:
                norm_c = normalize_country(result.location_raw)
                if norm_c and norm_c not in ("Unspecified", ""):
                    result.country_raw = norm_c

        # Parse Salary amounts if present
        if result.salary_text_raw:
            self._parse_salary_text(result.salary_text_raw, result)

        # 5. Skills Chips
        skill_els = (
            soup.find_all("li", class_=re.compile(r"jobCard_skillList_item|skill", re.I)) or
            soup.find_all("span", class_=re.compile(r"skill|tag", re.I))
        )
        skills_found = [s.get_text(strip=True) for s in skill_els if s.get_text(strip=True) and len(s.get_text(strip=True)) < 35]
        if skills_found:
            # Deduplicate preserving order
            seen_sk = set()
            clean_sk = []
            for sk in skills_found:
                if sk.lower() not in seen_sk and sk.lower() not in ("skills", "key skills", "apply"):
                    seen_sk.add(sk.lower())
                    clean_sk.append(sk)
            result.skills_raw = ", ".join(clean_sk)

        # 6. Job Description
        desc_el = (
            soup.find(id=re.compile(r"job_desc|description", re.I)) or
            soup.find(class_=re.compile(r"jobDesc|jobDescription|job-detail-content", re.I)) or
            soup.find("div", class_=re.compile(r"JobDetailWidget", re.I))
        )
        if desc_el:
            result.job_description_raw = desc_el.get_text(separator="\n", strip=True)
            result.description_type = "html_text"

        # 7. Posted date
        date_el = soup.find(class_=re.compile(r"posted|date", re.I))
        if date_el and "posted" in date_el.get_text().lower():
            result.posted_date_raw = date_el.get_text(strip=True)

        # Determine extraction status
        if result.job_title_raw and (len(result.job_description_raw) >= 50 or result.company_raw):
            result.extraction_status = "success"
            result.extraction_confidence = 0.90 if len(result.job_description_raw) >= 50 else 0.70
        elif result.job_title_raw:
            result.extraction_status = "partial"
            result.extraction_confidence = 0.50
        else:
            result.extraction_status = "unsupported"
            result.error_message = "Could not identify job title from Shine page structure"

        return result

    def _extract_job_id_from_url(self, url: str) -> str:
        """Extracts numeric job identifier from Shine URL pattern."""
        match = re.search(r'/(\d{6,10})(?:[/?#]|$)', url)
        if match:
            return match.group(1)
        return ""

    def _parse_salary_text(self, text: str, result: ExtractionResult):
        """Parses Indian compensation text into min, max, currency, and period."""
        clean = text.replace(",", "").strip()

        if any(un in clean.lower() for un in ["not disclosed", "undisclosed", "best in industry"]):
            result.salary_min_raw = ""
            result.salary_max_raw = ""
            result.salary_currency_raw = ""
            result.salary_period_raw = ""
            return

        # Pattern 1: '5 - 10 Lakhs PA' or '5 to 10 Lakhs' or '5.5 - 8.5 LPA'
        lakhs_match = re.search(r'([\d.]+)\s*(?:-|to)\s*([\d.]+)\s*(?:lakhs?|lacs?|lpa)', clean, re.I)
        if lakhs_match:
            try:
                min_lakh = float(lakhs_match.group(1)) * 100000
                max_lakh = float(lakhs_match.group(2)) * 100000
                result.salary_min_raw = str(int(min_lakh))
                result.salary_max_raw = str(int(max_lakh))
                result.salary_currency_raw = "INR"
                result.salary_period_raw = "annual"
                return
            except ValueError:
                pass

        # Pattern 2: Single Lakh amount: 'Up to 12 Lakhs PA'
        single_lakh = re.search(r'(?:up to|upto|max)?\s*([\d.]+)\s*(?:lakhs?|lacs?|lpa)', clean, re.I)
        if single_lakh:
            try:
                amt = float(single_lakh.group(1)) * 100000
                result.salary_min_raw = str(int(amt))
                result.salary_currency_raw = "INR"
                result.salary_period_raw = "annual"
                return
            except ValueError:
                pass

        # Pattern 3: Explicit numeric currency: '₹ 600000 - 1200000'
        num_match = re.search(r'(?:₹|rs\.?|inr)\s*(\d{4,8})\s*(?:-|to)\s*(\d{4,8})', clean, re.I)
        if num_match:
            result.salary_min_raw = num_match.group(1)
            result.salary_max_raw = num_match.group(2)
            result.salary_currency_raw = "INR"
            result.salary_period_raw = "annual" if int(result.salary_min_raw) > 100000 else "monthly"
            return

        # Pattern 4: International currency: 'SGD 10000 - 16000' or 'USD 80000 - 120000'
        intl_match = re.search(r'(sgd|usd|myr|eur|gbp)\s*([\d.]+)\s*(?:-|to)\s*([\d.]+)', clean, re.I)
        if intl_match:
            result.salary_currency_raw = intl_match.group(1).upper()
            result.salary_min_raw = str(int(float(intl_match.group(2))))
            result.salary_max_raw = str(int(float(intl_match.group(3))))
            result.salary_period_raw = "monthly" if "month" in clean.lower() else "annual"
            return
