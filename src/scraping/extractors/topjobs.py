"""
Topjobs.lk site-specific extractor.

Isolates Topjobs-specific HTML selectors and logic from the legacy scrape_jobs.py.
Handles Topjobs detail pages with #remark, #position, #employer selectors.
"""

import re
import json
import urllib.parse
from bs4 import BeautifulSoup
from src.scraping.extractors.base import JobExtractor
from src.scraping.models import ExtractionResult, generate_job_id


class TopjobsExtractor(JobExtractor):
    """Extractor for Topjobs.lk job detail pages."""

    @property
    def name(self) -> str:
        return "topjobs"

    @property
    def supported_hostnames(self) -> list:
        return ["topjobs.lk", "www.topjobs.lk"]

    def can_handle(self, url: str, html_content: str) -> bool:
        """Returns True if the URL is a Topjobs.lk detail page."""
        try:
            hostname = urllib.parse.urlparse(url).hostname or ""
            return hostname.lower() in self.supported_hostnames
        except Exception:
            return False

    def extract(self, url: str, html_content: str, result: ExtractionResult) -> ExtractionResult:
        """Extracts job data from a Topjobs detail page."""
        result.extractor_name = self.name
        result.extraction_method = "site_adapter"
        result.country_raw = "Sri Lanka"

        try:
            # Parse source_job_id from URL query params
            parsed_url = urllib.parse.urlparse(url)
            queries = urllib.parse.parse_qs(parsed_url.query)
            source_job_id = queries.get("jc", [None])[0] or ""
            result.source_job_id = source_job_id
            result.source_platform = "topjobs.lk"

            # Generate job_id
            result.job_id = generate_job_id("topjobs.lk", source_job_id, url)

            # Parse HTML
            soup = BeautifulSoup(html_content, "lxml")

            # 1. Title, Company, Location
            title_el = soup.find(id="position") or soup.find(class_="job-title")
            result.job_title_raw = title_el.get_text(strip=True) if title_el else ""

            company_el = soup.find(id="employer") or soup.find(class_="ad-company-name")
            result.company_raw = company_el.get_text(strip=True) if company_el else ""

            location_el = soup.find(id="adview-job-location") or soup.find(class_="adview-job-location")
            result.location_raw = location_el.get_text(strip=True) if location_el else ""

            # 2. Extract Description & Flyer Images from #remark div
            remark_div = soup.find(id="remark") or soup.find(class_="job-holder")

            if remark_div:
                # Preserve raw HTML content
                result.job_description_raw = str(remark_div)

                # Scan for images inside remark
                image_urls = []
                for img in remark_div.find_all("img"):
                    src = img.get("src", "")
                    if not src:
                        continue
                    # Filter utility/styling/loading images
                    if any(term in src.lower() for term in [
                        "local.jpg", "application.png", "loading.gif", "info.png"
                    ]):
                        continue
                    # Make absolute URL
                    abs_src = urllib.parse.urljoin("https://www.topjobs.lk", src)
                    image_urls.append(abs_src)

                result.advert_image_urls = json.dumps(image_urls)

                # Classify description type
                plain_text = " ".join(remark_div.get_text().split()).strip()
                has_text = len(plain_text) > 100
                has_images = len(image_urls) > 0

                if has_text and has_images:
                    result.description_type = "hybrid"
                elif has_images:
                    result.description_type = "image"
                elif has_text:
                    result.description_type = "html_text"
                else:
                    result.description_type = "missing"

                # OCR status for image-based descriptions
                if has_images:
                    result.ocr_status = "not_permitted"  # Permission unverified
                else:
                    result.ocr_status = "not_required"
            else:
                result.job_description_raw = ""
                result.description_type = "missing"
                result.ocr_status = "not_required"

            # 3. Determine extraction quality
            has_title = bool(result.job_title_raw.strip())

            if not has_title:
                result.extraction_status = "partial"
                result.extraction_confidence = 0.2
                result.error_message = "Failed to extract job title"
            elif result.description_type == "missing":
                result.extraction_status = "partial"
                result.extraction_confidence = 0.4
                result.manual_review_reason = "Missing job description body"
            elif result.description_type == "image":
                result.extraction_status = "partial"
                result.extraction_confidence = 0.5
                result.manual_review_reason = "Image-only advertisement — OCR not permitted"
            else:
                result.extraction_status = "success"
                result.extraction_confidence = 0.85

            return result

        except Exception as e:
            result.extraction_status = "parse_error"
            result.error_type = "parse_error"
            result.error_message = f"Topjobs extraction failed: {e}"
            return result


def parse_topjobs_listing_page(url, headers):
    """Fetches and parses the Topjobs functional area listing page.

    This is the original listing-page parser from scrape_jobs.py, preserved
    for backward compatibility with the Topjobs listing page mode.

    Returns:
        dict: Mapping of jc_id -> metadata dict.
    """
    import requests

    print(f"Fetching listing page: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching listing page: {e}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 3:
        print("Warning: Listing page does not contain expected tables structure.")
        return {}

    listing_table = tables[2]
    rows = listing_table.find_all("tr")
    metadata = {}

    for row in rows:
        row_id = row.get("id", "")
        if not row_id.startswith("tr"):
            continue

        cells = row.find_all(["td", "th"])
        if len(cells) < 7:
            continue

        source_job_id = cells[1].get_text(strip=True)
        if not source_job_id:
            continue

        title_company_cell = cells[2]
        title_el = title_company_cell.find("h2")
        company_el = title_company_cell.find("h1")

        title = title_el.get_text(strip=True) if title_el else ""
        company = company_el.get_text(strip=True) if company_el else ""

        ac_span = title_company_cell.find("span", id=lambda x: x and x.startswith("hdnAC"))
        ec_span = title_company_cell.find("span", id=lambda x: x and x.startswith("hdnEC"))
        jc_span = title_company_cell.find("span", id=lambda x: x and x.startswith("hdnJC"))

        ac = ac_span.get_text(strip=True) if ac_span else ""
        ec = ec_span.get_text(strip=True) if ec_span else ""
        jc = jc_span.get_text(strip=True) if jc_span else ""

        onclick = row.get("onclick", "")
        rid_val = row_id.replace("tr", "")
        if (not ac or not jc) and onclick:
            match = re.search(
                r"createAlert\('([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'",
                onclick
            )
            if match:
                rid, ac_val, jc_val, ec_val = match.groups()
                ac = ac_val
                jc = jc_val
                ec = ec_val
                rid_val = rid

        if not jc:
            jc = source_job_id

        detail_url = (
            f"https://www.topjobs.lk/employer/JobAdvertismentServlet"
            f"?rid={rid_val}&ac={ac}&jc={jc}&ec={ec}"
            f"&pg=applicant/vacancybyfunctionalarea.jsp"
        )

        opening_date = cells[4].get_text(strip=True)
        closing_date = cells[5].get_text(strip=True)
        location = cells[6].get_text(strip=True)

        metadata[jc] = {
            "source_job_id": jc,
            "job_title_raw": title,
            "company_raw": company,
            "listing_posted_date_raw": opening_date,
            "closing_date_raw": closing_date,
            "location_raw": location,
            "detail_url": detail_url,
        }

    print(f"Extracted listing metadata for {len(metadata)} vacancies.")
    return metadata
