"""
Generic HTML fallback extractor.

Attempts to extract job information from any web page using standard HTML elements:
- <title>, <h1>, Open Graph tags
- <meta name="description">
- <main>, <article>, semantic containers
- Conservative — returns "unsupported" when confidence is too low.
"""

import re
from bs4 import BeautifulSoup
from src.scraping.extractors.base import JobExtractor
from src.scraping.models import ExtractionResult, generate_job_id


class GenericHtmlExtractor(JobExtractor):
    """Conservative generic HTML extractor for unknown job pages."""

    @property
    def name(self) -> str:
        return "generic_html"

    def can_handle(self, url: str, html_content: str) -> bool:
        """Always returns True — this is the fallback extractor."""
        return bool(html_content)

    def extract(self, url: str, html_content: str, result: ExtractionResult) -> ExtractionResult:
        """Extracts basic job data from generic HTML."""
        result.extractor_name = self.name
        result.extraction_method = "generic_html"

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # 1. Extract title
            title = self._extract_title(soup)
            result.job_title_raw = title

            # 2. Extract company
            company = self._extract_company(soup)
            result.company_raw = company

            # 3. Extract location
            location = self._extract_location(soup)
            result.location_raw = location

            # 4. Extract description
            description = self._extract_description(soup)
            result.job_description_raw = description

            # 5. Extract dates
            result.posted_date_raw = self._extract_meta(soup, ["datePublished", "date", "article:published_time"])

            # 6. Generate job_id from URL
            result.job_id = generate_job_id(result.source_hostname, "", url)

            # Classify description type
            if description and len(description.strip()) > 100:
                result.description_type = "html_text"
            else:
                result.description_type = "missing"

            # 7. Determine extraction quality
            has_title = bool(title.strip())
            has_description = len(description.strip()) > 100 if description else False

            if has_title and has_description:
                result.extraction_status = "success"
                result.extraction_confidence = 0.5  # Generic = lower confidence
            elif has_title:
                result.extraction_status = "partial"
                result.extraction_confidence = 0.3
                result.manual_review_reason = "Generic extraction — description too short or missing"
            else:
                result.extraction_status = "unsupported"
                result.extraction_confidence = 0.1
                result.manual_review_reason = "Generic extraction could not find job title or description"

            return result

        except Exception as e:
            result.extraction_status = "parse_error"
            result.error_type = "parse_error"
            result.error_message = f"Generic HTML extraction failed: {e}"
            return result

    def _extract_title(self, soup):
        """Extracts a page title using multiple strategies."""
        # Try Open Graph title first
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content", "").strip():
            return og_title["content"].strip()

        # Try first h1
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            return h1.get_text(strip=True)

        # Try <title> tag
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            # Clean common suffixes like " | Company Name" or " - Website"
            text = title_tag.get_text(strip=True)
            for sep in [" | ", " - ", " – ", " — "]:
                if sep in text:
                    text = text.split(sep)[0].strip()
                    break
            return text

        return ""

    def _extract_company(self, soup):
        """Extracts company name using metadata and semantic hints."""
        # Try og:site_name
        og_site = soup.find("meta", attrs={"property": "og:site_name"})
        if og_site and og_site.get("content", "").strip():
            return og_site["content"].strip()

        # Try itemprop="hiringOrganization"
        org = soup.find(attrs={"itemprop": "hiringOrganization"})
        if org:
            name = org.find(attrs={"itemprop": "name"})
            if name:
                return name.get_text(strip=True)
            return org.get_text(strip=True)

        return ""

    def _extract_location(self, soup):
        """Extracts location from metadata."""
        # Try itemprop="jobLocation"
        loc = soup.find(attrs={"itemprop": "jobLocation"})
        if loc:
            addr = loc.find(attrs={"itemprop": "address"})
            if addr:
                return addr.get_text(strip=True)
            return loc.get_text(strip=True)

        return ""

    def _extract_description(self, soup):
        """Extracts the main content body."""
        # Try itemprop="description"
        desc = soup.find(attrs={"itemprop": "description"})
        if desc and len(desc.get_text(strip=True)) > 50:
            return str(desc)

        # Try <main> element
        main = soup.find("main")
        if main and len(main.get_text(strip=True)) > 50:
            return str(main)

        # Try <article> element
        article = soup.find("article")
        if article and len(article.get_text(strip=True)) > 50:
            return str(article)

        # Try og:description
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content", "").strip():
            return og_desc["content"].strip()

        # Try meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content", "").strip():
            return meta_desc["content"].strip()

        # Fallback: first large content div (with >200 chars of text)
        for div in soup.find_all(["div", "section"], limit=20):
            text = div.get_text(strip=True)
            if len(text) > 200:
                return str(div)

        return ""

    def _extract_meta(self, soup, names):
        """Extracts content from meta tags by name/property."""
        for name in names:
            tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
            if tag and tag.get("content", "").strip():
                return tag["content"].strip()
        return ""
