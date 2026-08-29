"""
Generic Link Extractor.

Extracts candidate job detail page URLs from a job portal's listing/main page HTML
using generic heuristics (URL patterns, path depth, link text analysis) and security validations.
"""

import urllib.parse
from bs4 import BeautifulSoup
from src.security.url_validator import validate_url
from src.cleaning.it_classifier import ITClassifier


class LinkExtractor:
    """Extracts job detail links from any listing page dynamically."""

    def __init__(self, classifier=None):
        self.classifier = classifier or ITClassifier()

    def extract_job_links(self, base_url: str, html_content: str, max_links: int = 30) -> list:
        """Parses HTML content to find job vacancy detail links.

        Args:
            base_url: The URL of the listing page.
            html_content: The HTML content of the listing page.
            max_links: Maximum number of links to return.

        Returns:
            List of absolute, verified, candidate job detail URLs.
        """
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        parsed_base = urllib.parse.urlparse(base_url)
        base_hostname = parsed_base.hostname.lower() if parsed_base.hostname else ""

        candidate_links = []
        seen_urls = set()

        # Find all <a> tags with href
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href:
                continue

            # Resolve relative URLs
            absolute_url = urllib.parse.urljoin(base_url, href)

            # Basic clean
            parsed_url = urllib.parse.urlparse(absolute_url)
            scheme = parsed_url.scheme.lower()
            hostname = parsed_url.hostname.lower() if parsed_url.hostname else ""

            # 1. Scope Checks
            if scheme not in ("http", "https"):
                continue

            # Check if same host
            is_same_host = hostname.endswith(base_hostname) or base_hostname.endswith(hostname)
            
            # If not same host, check if it's an approved external domain
            from src.security.url_validator import is_approved_domain
            is_approved_ext = is_approved_domain(hostname)

            # Remove fragment/hash
            clean_url = urllib.parse.urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                parsed_url.query,
                ""
            ))

            if clean_url in seen_urls:
                continue

            # 2. Exclude static assets
            path = parsed_url.path.lower()
            if any(path.endswith(ext) for ext in [
                ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg",
                ".pdf", ".zip", ".gz", ".doc", ".docx", ".xls", ".xlsx"
            ]):
                continue

            # 3. Exclude obvious system/utility routes
            system_patterns = [
                "/login", "/logout", "/register", "/signup", "/signin",
                "/cart", "/checkout", "/account", "/settings", "/profile",
                "/contact", "/about", "/privacy", "/terms", "/faq",
                "/cookies", "/help", "/feedback", "/blog", "/news"
            ]
            if any(pat in path for pat in system_patterns):
                continue

            # 4. Check Link Text & Attributes
            link_text = a_tag.get_text(separator=" ", strip=True)
            link_title = a_tag.get("title", "").strip()
            combined_text = (link_text + " " + link_title).lower()

            # Ignore common pagination/navigation words
            navigation_words = {
                "home", "next", "previous", "prev", "back", "more", "search",
                "apply", "share", "view", "download", "print", "contact",
                "about", "privacy", "terms", "jobs", "careers", "careers at",
                "login", "register", "all", "filter", "sort", "categories"
            }
            if len(link_text) < 3 or link_text.lower() in navigation_words:
                continue

            # 5. Job URL & Text Heuristics Scoring
            score = 0

            # Heuristic A: URL Path Keywords
            job_path_keywords = [
                "/job/", "/jobs/", "/vacancy/", "/vacancies/", "/careers/",
                "/career/", "/detail/", "/post/", "/opportunity/", "/listing/",
                "/show/", "/view/", "jobadvertismentservlet"
            ]
            if any(kw in path for kw in job_path_keywords):
                score += 10

            # Heuristic B: URL Query Parameters
            query_params = urllib.parse.parse_qs(parsed_url.query.lower())
            job_query_params = ["jc", "job_id", "vacancy_id", "rid", "ac", "id"]
            if any(qp in query_params for qp in job_query_params):
                score += 8

            # Heuristic C: Link Text contains job keywords or general title indicators
            if any(inc in combined_text for inc in self.classifier.inclusions):
                score += 6
            elif any(amb in combined_text for amb in self.classifier.ambiguous):
                score += 4

            # Heuristic D: Path depth
            path_segments = [s for s in path.split("/") if s]
            if len(path_segments) >= 2:
                score += 2

            # 6. Final Filter & Security Validation
            if score >= 4:
                is_valid, _ = validate_url(clean_url)
                if is_valid:
                    if is_same_host or is_approved_ext:
                        seen_urls.add(clean_url)
                        candidate_links.append(clean_url)
                    else:
                        # Legitimate external link that is not approved yet
                        self._add_to_external_queue(base_url, clean_url, link_text)

            # Cap links
            if len(candidate_links) >= max_links:
                break

        return candidate_links

    def _add_to_external_queue(self, source_url, target_url, anchor_text):
        """Records an external candidate link in the review queue."""
        import json
        import pathlib
        project_root = pathlib.Path(__file__).resolve().parent.parent.parent
        queue_path = project_root / "data" / "external_links_queue.json"
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        
        queue = []
        if queue_path.exists():
            try:
                with open(queue_path, "r", encoding="utf-8") as f:
                    queue = json.load(f)
            except Exception:
                queue = []
        
        # Check if already in queue
        exists = any(item["external_url"] == target_url for item in queue)
        if not exists:
            src_host = urllib.parse.urlparse(source_url).hostname or ""
            dst_host = urllib.parse.urlparse(target_url).hostname or ""
            
            queue.append({
                "source_url": source_url,
                "external_url": target_url,
                "source_hostname": src_host,
                "destination_hostname": dst_host,
                "anchor_text": anchor_text,
                "discovery_reason": "Scored as job detail page",
                "review_status": "pending"
            })
            
            with open(queue_path, "w", encoding="utf-8") as f:
                json.dump(queue, f, indent=4)
