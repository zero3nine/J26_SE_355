"""
Multi-site scraping service — top-level orchestrator.

Replaces the old run_scraping_pipeline() for Streamlit usage.
Validates URLs, fetches pages, routes to extractors, writes batch files.
"""

import csv
import json
import pathlib
import time
import urllib.parse
import pandas as pd

from datetime import datetime, timezone
from urllib.parse import urlparse
from src.security.url_validator import validate_url
from src.scraping.http_client import fetch_page, POLITE_DELAY_SECONDS
from src.scraping.browser_fetch import fetch_page_rendered, requires_js_rendering
from src.scraping.extractor_registry import ExtractorRegistry
from src.scraping.models import (
    ExtractionResult,
    RAW_SCHEMA_COLUMNS,
    generate_job_id,
    get_hostname,
)
from src.scraping.link_extractor import LinkExtractor

def is_xpress_job_detail_url(url):
    """Return True when a URL is an XpressJobs job-detail page."""
    if not url:
        return False

    try:
        parsed = urllib.parse.urlparse(url)
        hostname = (parsed.hostname or "").lower()
        path = parsed.path.lower()

        if hostname not in {"xpress.jobs", "www.xpress.jobs"}:
            return False

        return "/jobs/view/" in path

    except Exception:
        return False

def run_collection_pipeline(
    urls,
    progress_callback=None,
    batch_id=None,
):
    """Executes the multi-site collection pipeline for a list of URLs.

    Args:
        urls: List of URL strings to process.
        progress_callback: Optional callback(current_index, total, status_text).
        batch_id: Optional batch ID override.

    Returns:
        (df_raw, batch_id): DataFrame of raw results and the batch ID string.
    """
    # Paths setup
    project_root = pathlib.Path(__file__).resolve().parent.parent.parent
    batches_dir = project_root / "data" / "raw" / "batches"
    manifest_file = project_root / "data" / "raw" / "collection_manifest.json"
    failed_log_file = project_root / "logs" / "failed_urls.csv"

    batches_dir.mkdir(parents=True, exist_ok=True)
    failed_log_file.parent.mkdir(parents=True, exist_ok=True)

    # Batch configuration
    batch_time = datetime.now(timezone.utc)
    collection_batch_id = batch_id or f"batch_{batch_time.strftime('%Y%m%d_%H%M%S')}"
    raw_data_file = batches_dir / f"jobs_raw_{collection_batch_id}.csv"

    print(f"Initializing collection batch: {collection_batch_id}")

    # Initialize link extractor and extractor registry
    link_extractor = LinkExtractor()
    registry = ExtractorRegistry()

    # Set up failed URL log header if not present
    if not failed_log_file.exists():
        with open(failed_log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["url", "error_type", "error_message", "timestamp"])

    # Write batch CSV header
    with open(raw_data_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_SCHEMA_COLUMNS)
        writer.writeheader()

    # Statistics counters
    stats = {
        "success": 0,
        "partial": 0,
        "failed": 0,
        "blocked": 0,
        "rate_limited": 0,
        "unsupported": 0,
        "manual_review": 0,
        "extractor_counts": {},
    }

    url_queue = list(dict.fromkeys(urls))
    crawled_count = 0
    max_total_crawl = 30
    idx = 0

    while idx < len(url_queue) and crawled_count < max_total_crawl:
        url = url_queue[idx]
        idx += 1

        if progress_callback:
            progress_callback(crawled_count + 1, len(url_queue), f"Processing {crawled_count + 1} of {len(url_queue)}: {url[:80]}")

        print(f"\nProcessing {crawled_count + 1}/{len(url_queue)}: {url}")

        # Create result object
        result = ExtractionResult.create_for_url(url, collection_batch_id)

        # Step 1: Validate URL
        is_valid, reason = validate_url(url)
        if not is_valid:
            result.extraction_status = "invalid_url"
            result.error_type = "invalid_url"
            result.error_message = reason
            print(f"  → Rejected: {reason}")
            _write_result(result, raw_data_file, failed_log_file)
            _update_stats(stats, result)
            continue

        # Step 2: Fetch page
        crawled_count += 1
        delay = crawled_count > 1  # Delay after first request

        # Some sites (e.g. xpress.jobs) render job content client-side via
        # JavaScript — a plain HTTP GET only returns an empty shell. Those
        # hostnames are routed through headless-browser rendering instead;
        # every other site keeps using the faster plain-HTTP path.
        hostname = get_hostname(url)
        if requires_js_rendering(hostname):
            print(f"  → {hostname} requires JS rendering, using headless browser...")
            fetch_result = fetch_page_rendered(url, delay_before=delay)
        else:
            fetch_result = fetch_page(url, delay_before=delay)

        if not fetch_result.success:
            result.extraction_status = fetch_result.error_type or "network_error"
            result.error_type = fetch_result.error_type
            result.error_message = fetch_result.error_message
            result.final_url = fetch_result.final_url or url
            print(f"  → Fetch failed: {fetch_result.error_message}")
            _write_result(result, raw_data_file, failed_log_file)
            _update_stats(stats, result)
            continue

        result.final_url = fetch_result.final_url

        # Step 3: Check if this is a listing page or direct job page
        # XpressJobs job-detail URLs can be identified reliably from their URL
        # even when the rendered page does not contain JobPosting JSON-LD.
        is_direct_job_page = is_xpress_job_detail_url(fetch_result.final_url)

        has_jsonld_job = (
            "application/ld+json" in fetch_result.html
            and "JobPosting" in fetch_result.html
        )

        # Detect URLs that already look like direct job-detail pages
        parsed_url = urllib.parse.urlparse(fetch_result.final_url)
        path_lower = parsed_url.path.lower()

        if not is_direct_job_page and not has_jsonld_job:
            discovered_links = link_extractor.extract_job_links(
                fetch_result.final_url,
                fetch_result.html
            )

            # Keep only actual XpressJobs job-detail URLs.
            discovered_links = [
                link for link in discovered_links
                if not is_xpress_job_detail_url(link)
                or "/jobs/view/" in urlparse(link).path.lower()
            ]

            if len(discovered_links) > 1:
                print(
                    f"  → Detected listing page. "
                    f"Extracted {len(discovered_links)} candidate job links."
                )

                # Check maximum cap to stay polite
                if len(url_queue) + len(discovered_links) > max_total_crawl:
                    available_slots = max_total_crawl - len(url_queue)

                    if available_slots > 0:
                        discovered_links = discovered_links[:available_slots]
                        print(
                            f"  → Capped to {len(discovered_links)} links "
                            f"due to max batch limit of {max_total_crawl}."
                        )
                    else:
                        discovered_links = []
                        print(
                            f"  → Max crawl cap {max_total_crawl} reached. "
                            f"Skipping further queue expansion."
                        )

                added_count = 0

                for link in discovered_links:
                    if link not in url_queue:
                        url_queue.append(link)
                        added_count += 1

                print(f"  → Queued {added_count} new job URLs for collection.")

                # Since this is a listing page, we don't save it as a raw job.
                continue

            elif not is_direct_job_page:
                print("  → Page is not a recognized job-detail page.")

        # Step 4: Route to extractor registry
        print(f"  → Fetched OK ({len(fetch_result.html)} chars), routing to extractors...")
        result = registry.extract(fetch_result.final_url, fetch_result.html, result)

        # Generate job_id if not set by extractor
        if not result.job_id:
            result.job_id = generate_job_id(
                result.source_hostname, result.source_job_id, url
            )

        print(f"  → {result.extractor_name}: {result.extraction_status} "
              f"(confidence={result.extraction_confidence:.1%})")

        # Step 5: Write result
        _write_result(result, raw_data_file, failed_log_file)
        _update_stats(stats, result)

    # Compile collection manifest
    manifest_record = {
        "collection_batch_id": collection_batch_id,
        "started_at": batch_time.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "attempted_count": crawled_count,
        "success_count": stats["success"],
        "partial_count": stats["partial"],
        "failed_count": stats["failed"],
        "blocked_count": stats["blocked"],
        "rate_limited_count": stats["rate_limited"],
        "unsupported_count": stats["unsupported"],
        "manual_review_count": stats["manual_review"],
        "extractor_counts": stats["extractor_counts"],
        "permission_status": "unverified",
    }

    manifest_list = []
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_list = json.load(f)
        except Exception:
            manifest_list = []

    manifest_list.append(manifest_record)
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_list, f, indent=4)

    # Print batch summary
    print(f"\n{'='*50}")
    print(f"Collection Batch Summary: {collection_batch_id}")
    print(f"{'='*50}")
    print(f"Total URLs attempted : {crawled_count}")
    print(f"Success              : {stats['success']}")
    print(f"Partial              : {stats['partial']}")
    print(f"Failed/Error         : {stats['failed']}")
    print(f"Blocked (403)        : {stats['blocked']}")
    print(f"Rate Limited (429)   : {stats['rate_limited']}")
    print(f"Unsupported          : {stats['unsupported']}")
    print(f"Manual Review        : {stats['manual_review']}")
    print(f"Batch file: {raw_data_file}")
    print(f"Manifest updated.")

    # Read and return DataFrame
    try:
        df_raw = pd.read_csv(raw_data_file, dtype=str).fillna("")
    except Exception:
        df_raw = pd.DataFrame(columns=RAW_SCHEMA_COLUMNS)

    return df_raw, collection_batch_id


def _write_result(result, raw_data_file, failed_log_file):
    """Writes an ExtractionResult to the batch CSV and failure log if applicable."""
    row = result.to_dict()

    # Append to batch CSV
    with open(raw_data_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_SCHEMA_COLUMNS)
        writer.writerow(row)

    # Append to failure log if not success/partial
    if result.extraction_status not in ("success", "partial", "manual_review"):
        with open(failed_log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                result.source_url,
                result.error_type,
                result.error_message,
                result.scraped_at,
            ])


def _update_stats(stats, result):
    """Updates running statistics counters."""
    status = result.extraction_status
    if status == "success":
        stats["success"] += 1
    elif status == "partial":
        stats["partial"] += 1
    elif status == "blocked":
        stats["blocked"] += 1
    elif status == "rate_limited":
        stats["rate_limited"] += 1
    elif status == "unsupported":
        stats["unsupported"] += 1
    elif status == "manual_review":
        stats["manual_review"] += 1
    else:
        stats["failed"] += 1

    # Track extractor usage
    ext_name = result.extractor_name or "none"
    stats["extractor_counts"][ext_name] = stats["extractor_counts"].get(ext_name, 0) + 1
