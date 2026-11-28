"""Browser-based rendering fetch for JavaScript-rendered (SPA) job sites.
Some job portals (e.g. xpress.jobs) return a near empty HTML shell on a plain
HTTP GET, the actual job content is injected client-side by JavaScript after
page load. requests/BeautifulSoup can never see that content. This module uses
Playwright to load the page in a real (headless) browser, wait for it to
render, and return the fully-rendered HTML so the existing extractor chain can work on it normally."""

import sys
import time
import pathlib
import asyncio

from src.security.url_validator import is_approved_domain, validate_url
from src.scraping.http_client import MAX_RESPONSE_BYTES, POLITE_DELAY_SECONDS
from src.scraping.models import get_hostname
from src.scraping.source_registry import get_source_registry

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

RENDER_TIMEOUT_MS = 25_000       # Max time to wait for the page to render
NAVIGATION_TIMEOUT_MS = 45_000   # Max time for the initial navigation
NAVIGATION_RETRY_DELAY_SECONDS = 5  # Pause before retrying a stalled navigation

class FetchResult:
    """Mirrors http_client.FetchResult so callers can treat both interchangeably."""

    def __init__(self):
        self.html = ""
        self.status_code = 0
        self.content_type = "text/html"
        self.final_url = ""
        self.original_url = ""
        self.success = False
        self.error_type = ""
        self.error_message = ""
        self.redirect_chain = []


def _load_js_rendered_domains():
    """Loads the set of hostnames that require browser rendering."""
    config_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "config"
    filepath = config_dir / "js_rendered_domains.txt"
    domains = {"xpress.jobs", "www.xpress.jobs", "mycareersfuture.gov.sg", "www.mycareersfuture.gov.sg"}
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            domains.update({
                line.strip().lower()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            })
    return domains


def requires_js_rendering(hostname: str) -> bool:
    """Returns True if this hostname is configured to need browser rendering."""
    clean_host = (hostname or "").lower()
    domains = _load_js_rendered_domains()
    return clean_host in domains or any(clean_host.endswith("." + d) for d in domains)


def _validate_browser_destination(url: str) -> tuple[str, str]:
    is_valid, reason = validate_url(url)
    if not is_valid:
        return "invalid_url", reason
    if not is_approved_domain(get_hostname(url)):
        return "blocked", "Browser rendering requires an approved domain."
    permitted, status, reason = get_source_registry().check_access_permission(url)
    if not permitted and status == "access_restricted":
        return "blocked", reason
    return "", ""


def fetch_page_rendered(url, delay_before=False, wait_for_selector=None):
    """Fetches a page using a headless browser, waiting for JS to render content.

    Chromium runs with its sandbox enabled. The destination checks apply to
    the submitted URL and the URL used for extraction. Browser network
    requests also require an environment-level egress policy.

    Args:
        url: The URL to fetch.
        delay_before: If True, sleep POLITE_DELAY_SECONDS before fetching.
        wait_for_selector: Optional CSS selector to explicitly wait for.

    Returns:
        FetchResult with the rendered HTML content or error details.
    """
    result = FetchResult()
    result.original_url = url

    if delay_before:
        time.sleep(POLITE_DELAY_SECONDS)

    result.error_type, result.error_message = _validate_browser_destination(url)
    if result.error_type:
        return result

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        result.error_type = "network_error"
        result.error_message = (
            "playwright is not installed. Run: pip install playwright "
            "&& playwright install chromium"
        )
        return result

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True, chromium_sandbox=True)
            except Exception as exc:
                result.error_type = "network_error"
                result.error_message = f"Could not launch Chromium with its sandbox enabled: {exc}"
                return result

            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    service_workers="block",
                    accept_downloads=False,
                )
                page = context.new_page()
                page.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
                page.set_default_timeout(RENDER_TIMEOUT_MS)

                response = None
                last_error = None
                for attempt in range(2):
                    try:
                        response = page.goto(url, wait_until="domcontentloaded")
                        break
                    except Exception as e:
                        last_error = e
                        if attempt == 0:
                            time.sleep(NAVIGATION_RETRY_DELAY_SECONDS)

                if response is None:
                    result.error_type = "network_error"
                    result.error_message = (
                        f"Browser rendering failed after retry: {last_error}"
                    )
                    return result

                result.status_code = response.status
                result.final_url = page.url

                if result.status_code == 403:
                    result.error_type = "blocked"
                    result.error_message = "HTTP 403 Forbidden — access restricted"
                    return result
                if result.status_code == 429:
                    result.error_type = "rate_limited"
                    result.error_message = "HTTP 429 Too Many Requests — rate limited"
                    return result
                if result.status_code >= 400:
                    result.error_type = "network_error"
                    result.error_message = f"HTTP {result.status_code}"
                    return result

                # Wait for client-side JavaScript hydration
                if wait_for_selector:
                    try:
                        page.wait_for_selector(wait_for_selector, timeout=8000)
                    except Exception:
                        pass
                else:
                    # Give client-side frameworks (Next.js, Vue, React) time to finish AJAX hydration
                    try:
                        page.wait_for_function(
                            "() => document.documentElement.innerHTML.includes('JobPosting')",
                            timeout=5000,
                        )
                    except Exception:
                        try:
                            page.wait_for_load_state("networkidle", timeout=5000)
                        except Exception:
                            page.wait_for_timeout(2000)

                result.final_url = page.url
                if result.final_url != url:
                    result.error_type, result.error_message = _validate_browser_destination(result.final_url)
                    if result.error_type:
                        return result

                html = page.content()

                if len(html.strip()) < 300:
                    result.error_type = "js_render_incomplete"
                    result.error_message = (
                        "Navigated OK but page body remained nearly empty after render timeout."
                    )
                    return result

                if len(html.encode("utf-8")) > MAX_RESPONSE_BYTES:
                    result.error_type = "parse_error"
                    result.error_message = (
                        f"Rendered response exceeds {MAX_RESPONSE_BYTES // (1024*1024)}MB limit"
                    )
                    return result

                result.html = html
                result.content_type = "text/html"
                result.success = True
                return result
            finally:
                browser.close()

    except Exception as e:
        result.error_type = "network_error"
        result.error_message = f"Browser rendering failed: {e}"
        return result