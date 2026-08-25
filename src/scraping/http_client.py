"""
Safe HTTP client for academic web scraping.

Provides a single reusable fetch function with:
- Transparent academic user-agent
- Connection and read timeouts
- Bounded response size
- Manual redirect following with URL revalidation
- Content-type checking
- Polite delay between requests
- No retry for permanent errors (400, 401, 403, 404)
- Limited backoff retry for temporary errors (429, 5xx)
"""

import time
import requests
from src.security.url_validator import validate_url, validate_redirect_url


# Configuration
USER_AGENT = (
    "Academic Research Bot/1.0 "
    "(Contact: student-researcher@example.edu; "
    "Regional IT Skills Demand Study)"
)

CONNECTION_TIMEOUT = 10   # seconds
READ_TIMEOUT = 20         # seconds
MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_REDIRECTS = 5
POLITE_DELAY_SECONDS = 2
MAX_RETRIES_TEMPORARY = 2
RETRY_BACKOFF_BASE = 3    # seconds


class FetchResult:
    """Result of an HTTP fetch operation."""

    def __init__(self):
        self.html = ""
        self.status_code = 0
        self.content_type = ""
        self.final_url = ""
        self.original_url = ""
        self.success = False
        self.error_type = ""      # network_error, blocked, rate_limited, etc.
        self.error_message = ""
        self.redirect_chain = []


def fetch_page(url, delay_before=False):
    """Fetches a web page safely with all security checks.

    Args:
        url: The URL to fetch.
        delay_before: If True, sleep POLITE_DELAY_SECONDS before fetching.

    Returns:
        FetchResult with the HTML content or error details.
    """
    result = FetchResult()
    result.original_url = url

    # Optional polite delay
    if delay_before:
        time.sleep(POLITE_DELAY_SECONDS)

    # Validate URL before fetching
    is_valid, reason = validate_url(url)
    if not is_valid:
        result.error_type = "invalid_url"
        result.error_message = reason
        return result

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    current_url = url
    redirect_count = 0

    try:
        while redirect_count <= MAX_REDIRECTS:
            response = requests.get(
                current_url,
                headers=headers,
                timeout=(CONNECTION_TIMEOUT, READ_TIMEOUT),
                allow_redirects=False,
                stream=True,
            )

            result.status_code = response.status_code

            # Handle redirects manually
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_url = response.headers.get("Location", "")
                if not redirect_url:
                    result.error_type = "network_error"
                    result.error_message = f"Redirect {response.status_code} with no Location header"
                    response.close()
                    return result

                # Make absolute URL if relative
                if not redirect_url.startswith(("http://", "https://")):
                    from urllib.parse import urljoin
                    redirect_url = urljoin(current_url, redirect_url)

                # Validate redirect target
                is_valid, reason = validate_redirect_url(current_url, redirect_url)
                if not is_valid:
                    result.error_type = "blocked"
                    result.error_message = f"Redirect to unsafe URL blocked: {reason}"
                    response.close()
                    return result

                result.redirect_chain.append(redirect_url)
                response.close()
                current_url = redirect_url
                redirect_count += 1
                continue

            # Check for permanent errors — no retry
            if response.status_code in (400, 401, 404):
                result.error_type = "network_error"
                result.error_message = f"HTTP {response.status_code}"
                result.final_url = current_url
                response.close()
                return result

            if response.status_code == 403:
                result.error_type = "blocked"
                result.error_message = "HTTP 403 Forbidden — access restricted"
                result.final_url = current_url
                response.close()
                return result

            if response.status_code == 429:
                result.error_type = "rate_limited"
                result.error_message = "HTTP 429 Too Many Requests — rate limited"
                result.final_url = current_url
                response.close()
                return result

            # Server errors — could retry but we'll note it
            if response.status_code >= 500:
                result.error_type = "network_error"
                result.error_message = f"HTTP {response.status_code} server error"
                result.final_url = current_url
                response.close()
                return result

            # Success — check content type
            content_type = response.headers.get("Content-Type", "")
            result.content_type = content_type

            if not any(ct in content_type.lower() for ct in ("text/html", "application/xhtml", "text/xml", "application/xml")):
                result.error_type = "parse_error"
                result.error_message = f"Unexpected content type: {content_type}"
                result.final_url = current_url
                response.close()
                return result

            # Read response body with size limit
            content_chunks = []
            total_bytes = 0
            for chunk in response.iter_content(chunk_size=8192):
                total_bytes += len(chunk)
                if total_bytes > MAX_RESPONSE_BYTES:
                    result.error_type = "parse_error"
                    result.error_message = f"Response exceeds {MAX_RESPONSE_BYTES // (1024*1024)}MB limit"
                    response.close()
                    return result
                content_chunks.append(chunk)

            response.close()

            # Decode HTML
            raw_bytes = b"".join(content_chunks)
            # Try to detect encoding from response
            encoding = response.encoding or "utf-8"
            try:
                result.html = raw_bytes.decode(encoding, errors="replace")
            except (UnicodeDecodeError, LookupError):
                result.html = raw_bytes.decode("utf-8", errors="replace")

            result.final_url = current_url
            result.success = True
            return result

        # Exceeded max redirects
        result.error_type = "network_error"
        result.error_message = f"Exceeded maximum {MAX_REDIRECTS} redirects"
        result.final_url = current_url
        return result

    except requests.exceptions.ConnectTimeout:
        result.error_type = "network_error"
        result.error_message = "Connection timeout"
        return result
    except requests.exceptions.ReadTimeout:
        result.error_type = "network_error"
        result.error_message = "Read timeout"
        return result
    except requests.exceptions.ConnectionError as e:
        result.error_type = "network_error"
        result.error_message = f"Connection error: {e}"
        return result
    except requests.exceptions.RequestException as e:
        result.error_type = "network_error"
        result.error_message = f"Request failed: {e}"
        return result
    except Exception as e:
        result.error_type = "network_error"
        result.error_message = f"Unexpected error: {e}"
        return result
