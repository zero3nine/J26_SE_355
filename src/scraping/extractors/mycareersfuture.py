"""
MyCareersFuture (Singapore) site adapter.

Extracts rich structured job data from Singapore's official national job portal
(mycareersfuture.gov.sg). Supports direct REST API hydration for 100% field accuracy,
as well as fallback to rendered DOM elements.
"""

import re
import json
import urllib.parse
import requests

from src.scraping.extractors.base import JobExtractor
from src.scraping.models import ExtractionResult, generate_job_id
from src.scraping.http_client import BROWSER_USER_AGENT


class MyCareersFutureExtractor(JobExtractor):
    """Site adapter for mycareersfuture.gov.sg (Singapore)."""

    API_JOB_ENDPOINT = "https://api.mycareersfuture.gov.sg/v2/jobs/{uuid}"
    API_SEARCH_ENDPOINT = "https://api.mycareersfuture.gov.sg/v2/search"

    @property
    def name(self) -> str:
        return "mycareersfuture"

    @property
    def supported_hostnames(self) -> list:
        return [
            "mycareersfuture.gov.sg",
            "www.mycareersfuture.gov.sg",
        ]

    def can_handle(self, url: str, html: str) -> bool:
        """Returns True for mycareersfuture.gov.sg URLs."""
        try:
            hostname = urllib.parse.urlparse(url).hostname or ""
            return hostname.lower() in self.supported_hostnames
        except Exception:
            return False

    def extract(self, url: str, html: str, result: ExtractionResult) -> ExtractionResult:
        """Extracts job posting details using official API or rendered DOM."""
        result.extractor_name = self.name
        result.source_hostname = "mycareersfuture.gov.sg"
        result.country_raw = "SG"

        # 1. Extract 32-char hex UUID from URL (e.g., /job/...-ea8eb1b90310c8144586b06b759c1c46)
        match = re.search(r'([a-f0-9]{32})', url.lower())
        job_uuid = match.group(1) if match else None

        if job_uuid:
            api_data = self._fetch_job_api(job_uuid)
            if api_data:
                return self._populate_from_api(api_data, url, result)

        # 2. Fallback: Parse from HTML if API was unreachable or URL is rendered DOM
        return self._populate_from_html(url, html, result)

    def _fetch_job_api(self, job_uuid: str) -> dict:
        """Fetches job detail directly from public REST API endpoint."""
        endpoint = self.API_JOB_ENDPOINT.format(uuid=job_uuid)
        headers = {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "application/json",
        }
        try:
            resp = requests.get(endpoint, headers=headers, timeout=12)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"  [MyCareersFuture] API fetch error: {e}")
        return {}

    def _populate_from_api(self, data: dict, url: str, result: ExtractionResult) -> ExtractionResult:
        """Populates ExtractionResult from API JSON response."""
        result.extraction_method = "site_adapter_api"
        result.source_job_id = data.get("uuid", "")
        result.job_title_raw = data.get("title", "")
        
        # Company
        posted_co = data.get("postedCompany", {}) or {}
        hiring_co = data.get("hiringCompany", {}) or {}
        result.company_raw = posted_co.get("name") or hiring_co.get("name", "")
        
        # Location & Country
        address = data.get("address", {}) or {}
        district = address.get("district", "")
        result.location_raw = f"{district}, Singapore" if district else "Singapore"
        result.country_raw = "SG"
        
        # Description
        result.job_description_raw = data.get("description", "")
        result.description_type = "html_text" if result.job_description_raw else "missing"

        # Dates
        metadata = data.get("metadata", {}) or {}
        result.posted_date_raw = metadata.get("originalPostingDate", "") or metadata.get("updatedAt", "")
        result.closing_date_raw = metadata.get("expiryDate", "")

        # Salary
        sal = data.get("salary", {}) or {}
        min_sal = sal.get("minimum")
        max_sal = sal.get("maximum")
        sal_type = (sal.get("type", {}) or {}).get("salaryType", "Monthly")
        result.salary_min_raw = str(min_sal) if min_sal is not None else ""
        result.salary_max_raw = str(max_sal) if max_sal is not None else ""
        result.salary_currency_raw = "SGD"
        result.salary_period_raw = sal_type
        if min_sal is not None and max_sal is not None:
            result.salary_text_raw = f"{min_sal} - {max_sal} SGD per {sal_type}"
        elif min_sal is not None:
            result.salary_text_raw = f"{min_sal} SGD per {sal_type}"

        # Employment type & categories
        emp_types = [e.get("employmentType", "") for e in data.get("employmentTypes", []) if isinstance(e, dict)]
        result.employment_type_raw = ", ".join(filter(None, emp_types))
        
        categories = [c.get("category", "") for c in data.get("categories", []) if isinstance(c, dict)]
        result.industry_raw = ", ".join(filter(None, categories))

        # Skills
        skills = [s.get("skill", "") for s in data.get("skills", []) if isinstance(s, dict)]
        result.skills_raw = ", ".join(filter(None, skills))

        result.job_id = generate_job_id("mycareersfuture.gov.sg", result.source_job_id, url)
        result.extraction_status = "success"
        result.extraction_confidence = 0.95
        return result

    def _populate_from_html(self, url: str, html: str, result: ExtractionResult) -> ExtractionResult:
        """Fallback extraction from HTML content."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # 1. Check for JSON-LD JobPosting
        for s in soup.find_all("script", type="application/ld+json"):
            if not s.string:
                continue
            try:
                data = json.loads(s.string)
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    from src.scraping.extractors.jsonld import JsonLdExtractor
                    return JsonLdExtractor().extract(url, html, result)
            except Exception:
                continue

        # 2. Check rendered DOM elements
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            result.job_title_raw = h1.get_text(strip=True)

        co_el = soup.find(attrs={"name": "company"}) or soup.find(class_=re.compile(r"company", re.I))
        if co_el:
            result.company_raw = co_el.get_text(strip=True)

        loc_el = soup.find(attrs={"name": "location"}) or soup.find(class_=re.compile(r"location", re.I)) or soup.find(id=re.compile(r"location", re.I))
        if loc_el:
            result.location_raw = loc_el.get_text(strip=True)
            result.country_raw = "SG"

        desc_el = soup.find(attrs={"name": "job-description"}) or soup.find(id=re.compile(r"description", re.I))
        if desc_el:
            result.job_description_raw = desc_el.get_text(separator="\n", strip=True)

        if result.job_title_raw and len(result.job_description_raw) > 50:
            result.extraction_status = "success"
            result.extraction_confidence = 0.80
        elif result.job_title_raw:
            result.extraction_status = "partial"
            result.extraction_confidence = 0.50
        else:
            result.extraction_status = "unsupported"
            result.error_message = "Could not extract job title or description from MyCareersFuture page"

        return result

    @classmethod
    def search_candidate_links(cls, query: str = "software", limit: int = 20) -> list:
        """Queries the official search endpoint to discover active job detail URLs."""
        headers = {
            "User-Agent": BROWSER_USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "limit": limit,
            "page": 0,
            "search": query,
        }
        urls = []
        try:
            resp = requests.post(cls.API_SEARCH_ENDPOINT, json=payload, headers=headers, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", []):
                    uuid = item.get("uuid")
                    title = re.sub(r'[^a-zA-Z0-9]+', '-', item.get("title", "job").lower()).strip('-')
                    if uuid:
                        urls.append(f"https://www.mycareersfuture.gov.sg/job/information-technology/{title}-{uuid}")
        except Exception as e:
            print(f"  [MyCareersFuture] search discovery error: {e}")
        return urls
