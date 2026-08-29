"""
Generic HTML fallback extractor.

Attempts to extract job information from any web page using standard HTML elements:
- <title>, <h1>, Open Graph tags
- <meta name="description">
- <main>, <article>, semantic containers
- Tracks provenance, confidence scores, and validation warnings.
"""

import re
import json
import urllib.parse
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
        """Extracts job data from generic HTML with validation and confidence scoring."""
        result.extractor_name = self.name
        result.extraction_method = "generic_html"

        try:
            soup = BeautifulSoup(html_content, "html.parser")
            provenance = {}

            # 1. Extract job title
            title, title_evidence, title_conf, title_warnings = self._extract_title_with_scoring(soup, url)
            result.job_title_raw = title
            provenance["job_title"] = {
                "value": title,
                "method": "generic_html",
                "evidence": title_evidence,
                "confidence_score": title_conf,
                "warnings": title_warnings
            }

            # 2. Extract company
            company, company_evidence, company_conf, company_warnings = self._extract_company_with_scoring(soup, url)
            result.company_raw = company
            provenance["company"] = {
                "value": company,
                "method": "generic_html",
                "evidence": company_evidence,
                "confidence_score": company_conf,
                "warnings": company_warnings
            }

            # 3. Extract location
            location, location_evidence, location_conf, location_warnings = self._extract_location_with_scoring(soup)
            result.location_raw = location
            provenance["location"] = {
                "value": location,
                "method": "generic_html",
                "evidence": location_evidence,
                "confidence_score": location_conf,
                "warnings": location_warnings
            }

            # 4. Extract description
            description, desc_evidence, desc_conf, desc_warnings = self._extract_description_with_scoring(soup)
            result.job_description_raw = description
            provenance["description"] = {
                "value": description,
                "method": "generic_html",
                "evidence": desc_evidence,
                "confidence_score": desc_conf,
                "warnings": desc_warnings
            }

            # 5. Extract dates
            posted_date, date_evidence, date_conf, date_warnings = self._extract_date_with_scoring(soup)
            result.posted_date_raw = posted_date
            provenance["posted_date"] = {
                "value": posted_date,
                "method": "generic_html",
                "evidence": date_evidence,
                "confidence_score": date_conf,
                "warnings": date_warnings
            }

            # 6. Generate job_id from URL
            result.job_id = generate_job_id(result.source_hostname, "", url)

            # Store serialized provenance
            result.field_provenance = json.dumps(provenance)

            # Classify description type
            if description and len(description.strip()) > 100:
                result.description_type = "html_text"
            else:
                result.description_type = "missing"

            # 7. Determine overall extraction status and confidence
            # Overall confidence is an average of title and description confidence
            overall_confidence = (title_conf + desc_conf) / 2.0
            result.extraction_confidence = float(f"{overall_confidence:.2f}")

            has_title = bool(title.strip()) and "invalid" not in "".join(title_warnings)
            has_description = len(description.strip()) > 100 if description else False

            # Require description to contain body text and not just nav warnings
            if "nav_dominated" in desc_warnings:
                has_description = False

            if has_title and has_description:
                if overall_confidence >= 0.5:
                    result.extraction_status = "success"
                else:
                    result.extraction_status = "manual_review"
                    result.manual_review_reason = "Low confidence generic extraction"
            elif has_title:
                result.extraction_status = "partial"
                result.manual_review_reason = "Generic extraction — description too short or missing"
            else:
                result.extraction_status = "unsupported"
                result.manual_review_reason = "Generic extraction could not find valid job title or description"

            return result

        except Exception as e:
            result.extraction_status = "parse_error"
            result.error_type = "parse_error"
            result.error_message = f"Generic HTML extraction failed: {e}"
            return result

    def _extract_title_with_scoring(self, soup, url):
        """Extracts title and evaluates confidence/warnings."""
        title = ""
        evidence = ""
        confidence = 0.0
        warnings = []

        # Heuristic 1: h1 tag
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            title = h1.get_text(strip=True)
            evidence = "h1 tag"
            confidence = 0.8
        else:
            # Heuristic 2: Open Graph title
            og_title = soup.find("meta", attrs={"property": "og:title"})
            if og_title and og_title.get("content", "").strip():
                title = og_title["content"].strip()
                evidence = "og:title meta tag"
                confidence = 0.7
            else:
                # Heuristic 3: <title> tag
                title_tag = soup.find("title")
                if title_tag and title_tag.get_text(strip=True):
                    text = title_tag.get_text(strip=True)
                    # Clean common suffixes like " | Company Name"
                    for sep in [" | ", " - ", " – ", " — "]:
                        if sep in text:
                            text = text.split(sep)[0].strip()
                            break
                    title = text
                    evidence = "title tag"
                    confidence = 0.5

        # Validation: Reject generic title words
        title_clean = title.strip().lower()
        if not title_clean:
            confidence = 0.0
            warnings.append("empty_title")
        else:
            generic_terms = {"jobs", "careers", "home", "search", "login", "register", "vacancy", "vacancies"}
            # Check if title is purely a generic term or job board title
            if title_clean in generic_terms:
                confidence = 0.1
                warnings.append("generic_title")
            
            # Check if title matches portal branding
            hostname = urllib.parse.urlparse(url).hostname or ""
            domain_parts = hostname.lower().split(".")
            for part in domain_parts:
                if len(part) > 3 and part in title_clean:
                    # e.g. "topjobs" or "itpro" in title -> reduce confidence
                    confidence = max(0.1, confidence - 0.3)
                    warnings.append("contains_portal_branding")

        return title, evidence, confidence, warnings

    def _extract_company_with_scoring(self, soup, url):
        """Extracts company and evaluates confidence/warnings."""
        company = ""
        evidence = ""
        confidence = 0.0
        warnings = []

        # Heuristic 1: itemprop="hiringOrganization"
        org = soup.find(attrs={"itemprop": "hiringOrganization"})
        if org:
            name_el = org.find(attrs={"itemprop": "name"})
            if name_el:
                company = name_el.get_text(strip=True)
                evidence = "itemprop hiringOrganization name"
                confidence = 0.8
            else:
                company = org.get_text(strip=True)
                evidence = "itemprop hiringOrganization text"
                confidence = 0.6
        else:
            # Heuristic 2: og:site_name
            og_site = soup.find("meta", attrs={"property": "og:site_name"})
            if og_site and og_site.get("content", "").strip():
                company = og_site["content"].strip()
                evidence = "og:site_name meta tag"
                confidence = 0.6

        # Validation: check if company is portal branding
        company_clean = company.strip().lower()
        if company_clean:
            hostname = urllib.parse.urlparse(url).hostname or ""
            domain_parts = hostname.lower().split(".")
            for part in domain_parts:
                if len(part) > 3 and part == company_clean:
                    # Portal brand detected as company
                    confidence = 0.1
                    warnings.append("portal_branding_as_company")
        else:
            confidence = 0.0
            warnings.append("empty_company")

        return company, evidence, confidence, warnings

    def _extract_location_with_scoring(self, soup):
        """Extracts location and evaluates confidence."""
        location = ""
        evidence = ""
        confidence = 0.0
        warnings = []

        loc = soup.find(attrs={"itemprop": "jobLocation"})
        if loc:
            addr = loc.find(attrs={"itemprop": "address"})
            if addr:
                location = addr.get_text(strip=True)
                evidence = "itemprop jobLocation address"
                confidence = 0.8
            else:
                location = loc.get_text(strip=True)
                evidence = "itemprop jobLocation text"
                confidence = 0.6
        else:
            # Check meta tags
            meta_loc = soup.find("meta", attrs={"name": "geo.placename"})
            if meta_loc and meta_loc.get("content", "").strip():
                location = meta_loc["content"].strip()
                evidence = "geo.placename meta tag"
                confidence = 0.5
            else:
                warnings.append("no_location_evidence")

        return location, evidence, confidence, warnings

    def _extract_description_with_scoring(self, soup):
        """Extracts description and evaluates confidence/warnings."""
        description = ""
        evidence = ""
        confidence = 0.0
        warnings = []

        # Heuristic 1: itemprop="description"
        desc = soup.find(attrs={"itemprop": "description"})
        if desc and len(desc.get_text(strip=True)) > 50:
            description = str(desc)
            evidence = "itemprop description tag"
            confidence = 0.9
        else:
            # Heuristic 2: <main> tag
            main = soup.find("main")
            if main and len(main.get_text(strip=True)) > 50:
                description = str(main)
                evidence = "main tag"
                confidence = 0.75
            else:
                # Heuristic 3: <article> tag
                article = soup.find("article")
                if article and len(article.get_text(strip=True)) > 50:
                    description = str(article)
                    evidence = "article tag"
                    confidence = 0.7
                else:
                    # Heuristic 4: og:description / meta description
                    og_desc = soup.find("meta", attrs={"property": "og:description"}) or soup.find("meta", attrs={"name": "description"})
                    if og_desc and og_desc.get("content", "").strip():
                        description = og_desc["content"].strip()
                        evidence = "description meta tag"
                        confidence = 0.4
                    else:
                        # Heuristic 5: Fallback first large content div
                        for div in soup.find_all(["div", "section"], limit=20):
                            text = div.get_text(strip=True)
                            if len(text) > 200:
                                description = str(div)
                                evidence = "large content div fallback"
                                confidence = 0.3
                                break

        # Validation: Check if description is dominated by navigation/footer
        desc_text = BeautifulSoup(description, "html.parser").get_text()
        desc_clean = desc_text.strip().lower()

        if not desc_clean:
            confidence = 0.0
            warnings.append("empty_description")
        else:
            if len(desc_clean) < 100:
                confidence = max(0.1, confidence - 0.3)
                warnings.append("description_too_short")
            
            # Simple heuristic: density of links in description
            # If description contains many links, it might be navigation/footer
            links_text_len = sum(len(a.get_text(strip=True)) for a in BeautifulSoup(description, "html.parser").find_all("a"))
            if len(desc_clean) > 0 and (links_text_len / len(desc_clean)) > 0.4:
                confidence = 0.1
                warnings.append("nav_dominated")

        return description, evidence, confidence, warnings

    def _extract_date_with_scoring(self, soup):
        """Extracts date and evaluates confidence."""
        date_val = ""
        evidence = ""
        confidence = 0.0
        warnings = []

        # Heuristic 1: meta date published
        meta_names = ["datePublished", "date", "article:published_time", "pubdate", "publish-date"]
        for name in meta_names:
            tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
            if tag and tag.get("content", "").strip():
                date_val = tag["content"].strip()
                evidence = f"meta tag {name}"
                confidence = 0.8
                break

        if not date_val:
            # Check schema/itemprop
            date_el = soup.find(attrs={"itemprop": "datePosted"})
            if date_el and date_el.get("content", "").strip():
                date_val = date_el["content"].strip()
                evidence = "itemprop datePosted content"
                confidence = 0.8
            elif date_el:
                date_val = date_el.get_text(strip=True)
                evidence = "itemprop datePosted text"
                confidence = 0.6
            else:
                warnings.append("no_date_evidence")

        return date_val, evidence, confidence, warnings

