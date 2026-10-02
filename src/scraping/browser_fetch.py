"""
Browser-based rendering fetch for JavaScript-rendered (SPA) job sites.

Some job portals (e.g. xpress.jobs) return an near-empty HTML shell on a plain
HTTP GET — the actual job content is injected client-side by JavaScript after
page load. requests/BeautifulSoup can never see that content. This module uses
Playwright to load the page in a real (headless) browser, wait for it to
render, and return the fully-rendered HTML so the existing extractor chain
(JSON-LD -> site adapter -> generic HTML) can work on it normally.

Only used for hostnames listed in config/js_rendered_domains.txt — plain
http_client.fetch_page() remains the default for every other site, since it is
faster, lighter, and sufficient for server-rendered pages.
"""

import sys
import time
import pathlib
import asyncio

from src.security.url_validator import validate_url
from src.scraping.http_client import BROWSER_USER_AGENT, POLITE_DELAY_SECONDS, MAX_RESPONSE_BYTES

# Playwright's sync API needs an event loop that supports spawning
# subprocesses (it launches the browser as a subprocess). On Windows, the
# default event loop for background threads is Selector, which does NOT
# support subprocess creation — that's what raises NotImplementedError
# when this runs inside Streamlit (which executes user scripts in a
# background thread rather than the main thread). Proactor does support
# subprocesses from any thread, so we select it explicitly here.
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


def fetch_page_rendered(url, delay_before=False, wait_for_selector=None):
    """Fetches a page using a headless browser, waiting for JS to render content.

    Uses modern browser configuration with anti-detection headers, and waits for
    client-side SPA hydration (JSON-LD or DOM job cards).

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

    # Reuse the same centralized SSRF/security validation as the plain HTTP path
    is_valid, reason = validate_url(url)
    if not is_valid:
        result.error_type = "invalid_url"
        result.error_message = reason
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
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
            try:
                context = browser.new_context(
                    user_agent=BROWSER_USER_AGENT,
                    viewport={"width": 1280, "height": 800},
                )
                context.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")
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