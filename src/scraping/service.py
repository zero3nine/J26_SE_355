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
import re
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


import pkgutil
import importlib.util
if not hasattr(pkgutil, "find_loader"):
    pkgutil.find_loader = lambda name: importlib.util.find_spec(name)

import shutil
import pytesseract
pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract") or "/opt/homebrew/bin/tesseract"

from src.cleaning.it_classifier import ITClassifier
from src.scraping.http_client import USER_AGENT
from src.scraping.source_registry import get_source_registry

_ocr_cache = {}

BOILERPLATE_PATTERNS = [
    r"please refer (?:the|to the) full details",
    r"refer (?:the|to the) (?:full details|vacancy advert|advertisement|image flyer)",
    r"topjobs sri lanka job network",
    r"most popular online job site in sri lanka",
    r"recruitment automation for employers",
    r"please see the full job description",
    r"all terms and conditions apply",
]


def is_boilerplate_description(text: str) -> bool:
    """Detects whether text is generic portal boilerplate rather than a real job description."""
    if not text or not isinstance(text, str):
        return True
    cleaned = text.strip().lower()
    if not cleaned:
        return True
    import re
    for pat in BOILERPLATE_PATTERNS:
        if re.search(pat, cleaned):
            return True
    return False


def process_ocr_for_job(result, use_ocr=False):
    """Downloads and processes image advertisement OCR if enabled and appropriate."""
    if not use_ocr:
        result.ocr_status = "not_permitted"
        return result

    try:
        image_urls = json.loads(result.advert_image_urls or "[]")
    except Exception:
        result.ocr_status = "failed"
        result.error_message = "Failed to parse advert_image_urls JSON"
        return result

    desc = (result.job_description_raw or "").strip()
    needs_ocr = (
        result.ocr_status == "pending"
        or result.description_type in ("image", "hybrid")
        or (bool(image_urls) and (is_boilerplate_description(desc) or len(desc) < 40))
    )

    if not needs_ocr:
        if not result.ocr_status or result.ocr_status == "pending":
            result.ocr_status = "not_required"
        return result

    if not image_urls:
        result.ocr_status = "failed"
        result.error_message = "No advertisement flyer images discovered for OCR"
        return result

    # 1. Process candidate images
    import requests
    from PIL import Image as PILImage
    from PIL import ImageOps, ImageEnhance
    import io
    import hashlib

    extracted_texts = []
    confs = []

    for img_idx, image_url in enumerate(image_urls[:3]):
        # Validate image URL (prevent SSRF)
        is_valid, reason = validate_url(image_url)
        if not is_valid:
            print(f"  → OCR image URL validation failed: {reason}")
            continue

        try:
            headers = {
                "User-Agent": USER_AGENT,
                "Referer": result.final_url or "https://www.topjobs.lk"
            }
            response = requests.get(image_url, headers=headers, timeout=15, stream=True)
            if response.status_code != 200:
                print(f"  → OCR image download failed: HTTP {response.status_code}")
                continue

            content_type = response.headers.get("Content-Type", "")
            if content_type and not content_type.startswith("image/") and "octet-stream" not in content_type:
                print(f"  → Invalid image content type: {content_type}")
                continue

            # Size limit: 10MB
            content = []
            size = 0
            for chunk in response.iter_content(8192):
                size += len(chunk)
                if size > 10 * 1024 * 1024:
                    print("  → Image size exceeds 10MB limit")
                    break
                content.append(chunk)

            image_bytes = b"".join(content)
            if not image_bytes:
                continue

            # Cache check via MD5
            img_hash = hashlib.md5(image_bytes).hexdigest()
            if img_hash in _ocr_cache:
                print("  → Using cached OCR results.")
                cached_text, cached_conf = _ocr_cache[img_hash]
                if cached_text:
                    extracted_texts.append(cached_text)
                    confs.append(float(cached_conf))
                continue

            # Open with PIL
            img = PILImage.open(io.BytesIO(image_bytes))

            # Preprocessing: convert to grayscale, upscale if low resolution, enhance contrast
            img_gray = ImageOps.grayscale(img)
            if img_gray.width < 1200:
                ratio = 1200.0 / img_gray.width
                new_size = (1200, int(img_gray.height * ratio))
                img_gray = img_gray.resize(new_size, PILImage.Resampling.LANCZOS)

            enhancer = ImageEnhance.Contrast(img_gray)
            img_enhanced = enhancer.enhance(1.8)

            # Run pytesseract OCR
            ocr_text = pytesseract.image_to_string(img_enhanced)
            clean_text = ocr_text.strip()

            # Calculate confidence using word-level confidence scores
            data = pytesseract.image_to_data(img_enhanced, output_type=pytesseract.Output.DICT)
            word_confs = [
                float(c) for c, t in zip(data.get("conf", []), data.get("text", []))
                if float(c) > 0 and t.strip()
            ]
            avg_conf = (sum(word_confs) / len(word_confs) / 100.0) if word_confs else 0.75

            if clean_text:
                extracted_texts.append(clean_text)
                confs.append(avg_conf)
                _ocr_cache[img_hash] = (clean_text, str(round(avg_conf, 2)))

        except Exception as e:
            print(f"  → OCR processing error on image {img_idx + 1}: {e}")

    if extracted_texts:
        result.ocr_text_raw = "\n\n".join(extracted_texts).strip()
        result.ocr_status = "success"
        mean_conf = sum(confs) / len(confs) if confs else 0.75
        result.ocr_confidence = str(round(mean_conf, 2))

        # Update description_type if HTML description was boilerplate or empty
        if is_boilerplate_description(result.job_description_raw) or not (result.job_description_raw or "").strip():
            result.description_type = "image"
        else:
            result.description_type = "hybrid"

        # Update field provenance
        try:
            prov = json.loads(result.field_provenance or "{}")
        except Exception:
            prov = {}
        prov["description_source"] = result.description_type
        prov["ocr_status"] = "success"
        prov["ocr_confidence"] = result.ocr_confidence
        result.field_provenance = json.dumps(prov)
    else:
        result.ocr_status = "failed"
        result.error_message = "No text could be extracted from advertisement images via OCR"

    return result


def run_collection_pipeline(
    urls,
    target_valid_jobs=50,
    max_requests=120,
    max_time_seconds=300,
    polite_delay=2.0,
    use_browser_fallback=False,
    use_ocr=False,
    progress_callback=None,
    batch_id=None,
    cancel_requested_cb=None,
    crawl_all_pages=False,
):
    """Executes the multi-site collection pipeline with configurable crawl budgets.

    Args:
        urls: List of URL strings to process.
        target_valid_jobs: Target count of valid IT jobs.
        max_requests: Safety request cap.
        max_time_seconds: Safety elapsed time cap.
        polite_delay: Standby delay between requests in seconds.
        use_browser_fallback: Toggle Playwright rendering fallback.
        use_ocr: Toggle Pytesseract OCR execution.
        progress_callback: Optional callback(current_index, total, status_text).
        batch_id: Optional batch ID override.
        cancel_requested_cb: Optional callback checking if cancellation is requested.
        crawl_all_pages: Continue through listing pagination after reaching the job target.

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
    start_time = time.time()
    batch_time = datetime.now(timezone.utc)
    collection_batch_id = batch_id or f"batch_{batch_time.strftime('%Y%m%d_%H%M%S')}"
    raw_data_file = batches_dir / f"jobs_raw_{collection_batch_id}.csv"

    print(f"Initializing collection batch: {collection_batch_id}")

    # Initialize components
    link_extractor = LinkExtractor()
    registry = ExtractorRegistry()
    classifier = ITClassifier()
    source_registry = get_source_registry()

    # Set up failed URL log header if not present
    if not failed_log_file.exists():
        with open(failed_log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["url", "error_type", "error_message", "timestamp"])

    # Write batch CSV header
    with open(raw_data_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_SCHEMA_COLUMNS)
        writer.writeheader()

    # Track metrics
    metrics = {
        "requests_attempted": 0,
        "requests_completed": 0,
        "listing_pages_visited": 0,
        "detail_pages_processed": 0,
        "valid_jobs_accepted": 0,
        "non_it_jobs_rejected": 0,
        "ambiguous_jobs_awaiting_review": 0,
        "duplicate_urls_skipped": 0,
        "failed_urls_count": 0,
        "access_restricted_count": 0,
        "browser_fallback_count": 0,
        "ocr_success_count": 0,
        "extractor_counts": {},
    }

    url_queue = list(dict.fromkeys(urls))
    processed_urls = set()
    seen_job_ids = set()
    topjobs_listing_metadata = {}
    idx = 0

    while idx < len(url_queue):
        # 1. Stop conditions checks
        if not crawl_all_pages and metrics["valid_jobs_accepted"] >= target_valid_jobs:
            print(f"Stop crawl: Target of {target_valid_jobs} valid IT jobs reached.")
            break
        if metrics["requests_attempted"] >= max_requests:
            print(f"Stop crawl: Maximum request safety budget of {max_requests} reached.")
            break
        if (time.time() - start_time) >= max_time_seconds:
            print(f"Stop crawl: Maximum crawl duration limit of {max_time_seconds}s reached.")
            break
        if cancel_requested_cb and cancel_requested_cb():
            print("Stop crawl: Cancellation requested by user.")
            break

        url = url_queue[idx]
        idx += 1

        # Check for duplicate URL
        if url in processed_urls:
            metrics["duplicate_urls_skipped"] += 1
            continue
        processed_urls.add(url)

        if progress_callback:
            status_desc = f"Processing {metrics['requests_attempted'] + 1} (Queue: {len(url_queue)}): {url[:50]}..."
            progress_callback(metrics["requests_attempted"] + 1, len(url_queue), status_desc)

        print(f"\nProcessing request {metrics['requests_attempted'] + 1}: {url}")

        result = ExtractionResult.create_for_url(url, collection_batch_id)

        # Step 1: Validate URL
        is_valid, reason = validate_url(url)
        if not is_valid:
            result.extraction_status = "invalid_url"
            result.error_type = "invalid_url"
            result.error_message = reason
            print(f"  → Rejected URL validation: {reason}")
            _write_result(result, raw_data_file, failed_log_file)
            metrics["failed_urls_count"] += 1
            continue

        # Step 1b: Assess Source Governance and Access Restrictions
        permitted, access_status, access_reason = source_registry.check_access_permission(url)
        if not permitted and access_status == "access_restricted":
            result.extraction_status = "blocked"
            result.error_type = "blocked"
            result.error_message = access_reason
            result.failure_reason = access_reason
            print(f"  → Access restricted by portal policy: {access_reason}")
            _write_result(result, raw_data_file, failed_log_file)
            metrics["access_restricted_count"] += 1
            metrics["failed_urls_count"] += 1
            continue

        # Step 1c: Pre-populate Country context from registry if recognized
        registered_country = source_registry.get_country(url)
        if registered_country and registered_country != "Unspecified":
            result.country_raw = registered_country

        # Step 2: Fetch Page with Source-Specific Delay
        metrics["requests_attempted"] += 1
        delay = metrics["requests_attempted"] > 1
        hostname = get_hostname(url)
        is_spa_site = requires_js_rendering(hostname) or source_registry.requires_browser_rendering(hostname)

        effective_delay = max(polite_delay, source_registry.get_rate_limit(url, default=polite_delay))
        fetch_result = fetch_page(url, delay_before=delay, polite_delay=effective_delay)

        # If HTTP fetch failed with blocked (403) or rate-limit or network error, and browser fallback is enabled:
        if not fetch_result.success and use_browser_fallback:
            print(f"  → Plain HTTP fetch failed ({fetch_result.error_message}). Attempting browser fetch...")
            rendered_fetch = fetch_page_rendered(url)
            if rendered_fetch.success:
                fetch_result = rendered_fetch
                metrics["browser_fallback_count"] += 1

        if not fetch_result.success:
            result.extraction_status = fetch_result.error_type or "network_error"
            result.error_type = fetch_result.error_type
            result.error_message = fetch_result.error_message
            result.final_url = fetch_result.final_url or url
            print(f"  → Fetch failed: {fetch_result.error_message}")
            _write_result(result, raw_data_file, failed_log_file)
            metrics["failed_urls_count"] += 1
            continue

        metrics["requests_completed"] += 1
        result.final_url = fetch_result.final_url

        print(f"DEBUG FETCH LENGTH: {len(fetch_result.html)}")
        print(f"DEBUG HAS LDJSON: {'application/ld+json' in fetch_result.html}")
        print(f"DEBUG HAS JOBPOSTING: {'JobPosting' in fetch_result.html}")

        # Step 3: Check if listing page or direct job posting page
        has_jsonld_job = "application/ld+json" in fetch_result.html and "JobPosting" in fetch_result.html
        is_known_detail_url = (
            "jobadvertismentservlet" in url.lower() or
            bool(re.search(r'[a-f0-9]{32}', url.lower())) or
            ("/jobs/view/" in url.lower() and bool(re.search(r'/\d{4,}', url))) or
            ("/en/ad/" in url.lower()) or
            (("/jobs/" in url.lower() or "/job/" in url.lower()) and bool(re.search(r'/\d{4,}', url)))
        )

        discovered_links = []
        if not has_jsonld_job and not is_known_detail_url:
            # Fast path for MyCareersFuture search pages
            if "mycareersfuture.gov.sg" in hostname and ("/search" in url or not re.search(r'[a-f0-9]{32}', url)):
                from src.scraping.extractors.mycareersfuture import MyCareersFutureExtractor
                parsed_query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                search_term = parsed_query.get("search", ["software"])[0]
                discovered_links = MyCareersFutureExtractor.search_candidate_links(search_term, limit=25)
                if not discovered_links and use_browser_fallback:
                    rendered_search = fetch_page_rendered(url)
                    if rendered_search.success:
                        discovered_links = link_extractor.extract_job_links(rendered_search.final_url, rendered_search.html)

            if not discovered_links:
                discovered_links = link_extractor.extract_job_links(fetch_result.final_url, fetch_result.html)
                
                # If plain HTTP yielded 0 or 1 link, but site is known SPA or user enabled browser fallback:
                if len(discovered_links) <= 1 and (is_spa_site or use_browser_fallback):
                    print(f"  → Potential SPA listing page ({len(fetch_result.html)} bytes). Rendering in browser to discover job cards...")
                    rendered_listing = fetch_page_rendered(url)
                    if rendered_listing.success:
                        rendered_candidates = link_extractor.extract_job_links(rendered_listing.final_url, rendered_listing.html)
                        if len(rendered_candidates) > len(discovered_links):
                            discovered_links = rendered_candidates
                            fetch_result.html = rendered_listing.html

        if len(discovered_links) > 1:
            metrics["listing_pages_visited"] += 1
            print(f"  → Listing page. Discovered {len(discovered_links)} candidates.")
            
            # Enqueue unique candidate links
            added_count = 0
            for link in discovered_links:
                if link not in url_queue and link not in processed_urls:
                    url_queue.append(link)
                    added_count += 1
            print(f"  → Enqueued {added_count} new unique links.")
            if hostname.endswith("topjobs.lk"):
                from src.scraping.extractors.topjobs import parse_topjobs_listing_html
                topjobs_listing_metadata.update(
                    parse_topjobs_listing_html(fetch_result.html)
                )
            # Follow explicit next/older links to reach earlier listing pages.
            # The existing request/time budgets bound this traversal.
            older_pages = link_extractor.extract_pagination_links(
                fetch_result.final_url, fetch_result.html
            )
            added_pages = 0
            for page_url in older_pages:
                if page_url not in url_queue and page_url not in processed_urls:
                    url_queue.append(page_url)
                    added_pages += 1
            if added_pages:
                print(f"  → Enqueued {added_pages} older listing page(s).")
            continue

        # Step 4: Route to Extractor Registry
        metrics["detail_pages_processed"] += 1
        result = registry.extract(
            fetch_result.final_url,
            fetch_result.html,
            result,
            use_browser_fallback=use_browser_fallback
        )

        # TopJobs puts its opening date on the listing row, not reliably on the
        # detail page. Preserve that source date for temporal analysis.
        listing_record = topjobs_listing_metadata.get(result.source_job_id, {})
        if listing_record:
            if not result.posted_date_raw:
                result.posted_date_raw = listing_record.get("listing_posted_date_raw", "")
            if not result.closing_date_raw:
                result.closing_date_raw = listing_record.get("closing_date_raw", "")
            if not result.location_raw:
                result.location_raw = listing_record.get("location_raw", "")

        if result.rendering_used == "True":
            metrics["browser_fallback_count"] += 1

        # Step 5: OCR Workflow if appropriate
        result = process_ocr_for_job(result, use_ocr=use_ocr)
        if result.ocr_status == "success":
            metrics["ocr_success_count"] += 1

        # Generate job_id if not set
        if not result.job_id:
            result.job_id = generate_job_id(result.source_hostname, result.source_job_id, url)

        # Check for duplicate job across the batch
        if result.job_id in seen_job_ids:
            metrics["duplicate_urls_skipped"] += 1
            print(f"  → Skipping duplicate job ID: {result.job_id}")
            continue
        seen_job_ids.add(result.job_id)

        # Run IT Relevance Classifier using best available description (prefer OCR if description is boilerplate)
        desc_for_classify = result.job_description_raw or ""
        if (is_boilerplate_description(desc_for_classify) or len(desc_for_classify.strip()) < 30) and result.ocr_text_raw:
            desc_for_classify = result.ocr_text_raw
        elif result.ocr_text_raw and result.ocr_text_raw not in desc_for_classify:
            desc_for_classify = f"{desc_for_classify}\n\n{result.ocr_text_raw}".strip()
        classification = classifier.classify(
            title=result.job_title_raw,
            category=result.industry_raw or result.qualifications_raw, # hints
            skills=result.skills_raw,
            description=desc_for_classify
        )

        result.classification_status = classification["status"]
        result.classification_explanation = json.dumps(classification["explanation"])
        result.classification_override = json.dumps({}) # Initial override empty

        # If it's classified as IT, count as accepted
        if classification["status"] == "it":
            metrics["valid_jobs_accepted"] += 1
        elif classification["status"] == "non_it":
            metrics["non_it_jobs_rejected"] += 1
        elif classification["status"] == "ambiguous":
            metrics["ambiguous_jobs_awaiting_review"] += 1

        print(f"  → Title: {result.job_title_raw[:30]} | Extractor: {result.extractor_name} | Classify: {result.classification_status}")

        # Step 6: Write result
        _write_result(result, raw_data_file, failed_log_file)
        
        # Track extractor stats
        ext_name = result.extractor_name or "none"
        metrics["extractor_counts"][ext_name] = metrics["extractor_counts"].get(ext_name, 0) + 1

    # Compile collection manifest
    manifest_record = {
        "collection_batch_id": collection_batch_id,
        "started_at": batch_time.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": int(time.time() - start_time),
        "requests_attempted": metrics["requests_attempted"],
        "requests_completed": metrics["requests_completed"],
        "listing_pages_visited": metrics["listing_pages_visited"],
        "detail_pages_processed": metrics["detail_pages_processed"],
        "valid_jobs_accepted": metrics["valid_jobs_accepted"],
        "non_it_jobs_rejected": metrics["non_it_jobs_rejected"],
        "ambiguous_jobs_awaiting_review": metrics["ambiguous_jobs_awaiting_review"],
        "duplicate_urls_skipped": metrics["duplicate_urls_skipped"],
        "failed_urls": metrics["failed_urls_count"],
        "access_restricted_count": metrics.get("access_restricted_count", 0),
        "browser_fallback_used": metrics["browser_fallback_count"],
        "ocr_successes": metrics["ocr_success_count"],
        "extractor_counts": metrics["extractor_counts"],
        "configurations": {
            "target_valid_jobs": target_valid_jobs,
            "max_requests": max_requests,
            "max_time_seconds": max_time_seconds,
            "polite_delay": polite_delay,
            "use_browser_fallback": use_browser_fallback,
            "use_ocr": use_ocr,
            "crawl_all_pages": crawl_all_pages,
        },
        "source_registry_version": "1.2.0",
        "software_version": ITClassifier.CLASSIFIER_VERSION,
        "rules_version": ITClassifier.RULES_VERSION,
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
    print(f"Requests Attempted   : {metrics['requests_attempted']}")
    print(f"Requests Completed   : {metrics['requests_completed']}")
    print(f"Listing Pages Visited: {metrics['listing_pages_visited']}")
    print(f"Detail Pages Processed: {metrics['detail_pages_processed']}")
    print(f"Valid IT Jobs Accepted: {metrics['valid_jobs_accepted']}")
    print(f"Non-IT Jobs Rejected : {metrics['non_it_jobs_rejected']}")
    print(f"Ambiguous Awaiting   : {metrics['ambiguous_jobs_awaiting_review']}")
    print(f"Duplicates Skipped   : {metrics['duplicate_urls_skipped']}")
    print(f"Failed URLs          : {metrics['failed_urls_count']}")
    print(f"Batch file: {raw_data_file}")
    print(f"Manifest updated.")

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
    """Updates running statistics counters (legacy)."""
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

    ext_name = result.extractor_name or "none"
    stats["extractor_counts"][ext_name] = stats["extractor_counts"].get(ext_name, 0) + 1
