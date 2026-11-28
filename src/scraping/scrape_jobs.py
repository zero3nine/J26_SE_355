"""Compatibility CLI for collecting URLs from the repository's urls.txt."""

import argparse
import hashlib
import pathlib
import time
import urllib.parse


MAX_REQUESTS = 120
MAX_RUN_SECONDS = 300


def get_canonical_url(url):
    """Normalizes URL by sorting parameters and removing unnecessary session IDs."""
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    # Remove jsessionid from paths if present
    path = parsed.path
    if ";jsessionid=" in path:
        path = path.split(";jsessionid=")[0]

    # Retain core topjobs parameters
    clean_params = {}
    for p in ['rid', 'ac', 'jc', 'ec', 'pg']:
        if p in params:
            clean_params[p] = params[p][0]

    query = urllib.parse.urlencode(sorted(clean_params.items()))
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, query, parsed.fragment))

def create_job_id(source_platform, source_job_id, url=None):
    """Generates job_id from platform + source_job_id, or URL hash as fallback."""
    if source_job_id and source_job_id.strip():
        return f"{source_platform}_{source_job_id.strip()}"
    elif url:
        canonical = get_canonical_url(url)
        return f"{source_platform}_hash_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"
    else:
        return f"{source_platform}_unknown_{int(time.time() * 1000)}"

def evaluate_it_job_status(title):
    """Applies IT inclusion/exclusion rules to determine if a job is in scope."""
    if not title:
        return True, True, "ambiguous - empty title"

    title_lower = title.lower()

    # Explicit exclusions
    exclusions = [
        ("graphic", "graphic designer"),
        ("multimedia", "multimedia roles"),
        ("creative designer", "creative designer"),
        ("video editor", "video editor"),
        ("3d", "3d animator/designer"),
        ("printing machine", "printing machine operator"),
        ("operator", "non-IT operator"),
        ("sales", "sales roles"),
        ("marketing", "marketing roles"),
        ("coordinator", "administrative coordinator"),
        ("co-ordinator", "administrative coordinator"),
        ("admin", "administrative roles"),
    ]

    for word, label in exclusions:
        if word in title_lower:
            # Exceptions (e.g., "salesforce developer" is IT, but "sales executive" is not)
            if "developer" in title_lower or "engineer" in title_lower or "analyst" in title_lower:
                continue
            return False, False, f"Non-IT role: {label}"

    # Explicit inclusions
    inclusions = [
        "software", "developer", "engineer", "qa", "quality assurance", "test",
        "full stack", "fullstack", "frontend", "front-end", "backend", "back-end",
        "devops", "sre", "cloud", "data science", "data scientist", "data engineer",
        "machine learning", "ml", "ai", "artificial intelligence", "cybersecurity", "security",
        "database", "dba", "network", "sysadmin", "systems administrator", "it support",
        "helpdesk", "analyst", "architect"
    ]

    is_included = any(word in title_lower for word in inclusions)

    # Check for ambiguity
    ambiguous_keywords = ["ui/ux", "product designer", "designer", "intern", "trainee", "associate", "manager", "director"]
    is_ambiguous = False
    if is_included:
        if any(word in title_lower for word in ["designer", "manager", "director", "coordinator"]):
            is_ambiguous = True
    else:
        # Not explicitly included, but might be ambiguous (e.g. "Project Manager", "IT Executive")
        if any(word in title_lower for word in ["manager", "executive", "intern", "associate", "consultant", "analyst"]):
            is_ambiguous = True

    if is_ambiguous:
        return True, True, "ambiguous - flagged for manual review"
    elif is_included:
        return True, False, ""
    else:
        return False, False, "Non-IT role: does not match IT inclusion criteria"


def run_scraping_pipeline(
    urls, progress_callback=None, enable_ocr=False, batch_id=None, *, max_requests=MAX_REQUESTS
):
    """Run the guarded collector and return its raw rows and batch ID."""
    from src.scraping.service import run_collection_pipeline

    return run_collection_pipeline(
        urls,
        max_requests=min(max_requests, MAX_REQUESTS),
        max_time_seconds=MAX_RUN_SECONDS,
        use_browser_fallback=False,
        use_ocr=enable_ocr,
        progress_callback=progress_callback,
        batch_id=batch_id,
        crawl_all_pages=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Collect research job ads from urls.txt")
    parser.add_argument("--test-limit", type=int, help="Cap submitted URLs and crawl requests for a test")
    args = parser.parse_args()
    if args.test_limit is not None and args.test_limit < 0:
        parser.error("--test-limit must be non-negative")

    urls_file = pathlib.Path(__file__).resolve().parents[2] / "urls.txt"
    if not urls_file.is_file():
        parser.exit(1, f"Error: {urls_file} does not exist.\n")

    with urls_file.open(encoding="utf-8") as file:
        urls = list(dict.fromkeys(
            url for line in file if (url := line.strip()) and not url.startswith("#")
        ))

    max_requests = MAX_REQUESTS
    if args.test_limit is not None:
        urls = urls[:args.test_limit]
        max_requests = min(args.test_limit, MAX_REQUESTS)
        print(f"Test mode: submitting {len(urls)} URL(s) with a {max_requests}-request limit.")

    print(f"Processing {len(urls)} target URLs...")
    run_scraping_pipeline(
        urls,
        progress_callback=lambda _index, _total, message: print(message),
        max_requests=max_requests,
    )


if __name__ == "__main__":
    main()
