"""
Multi-site scraping service — top-level orchestrator.

Replaces the old run_scraping_pipeline() for Streamlit usage.
Validates URLs, fetches pages, routes to extractors, writes batch files.
"""

import csv
import json
import pathlib
import time
from datetime import datetime, timezone

import pandas as pd

from src.security.url_validator import validate_url
from src.scraping.http_client import fetch_page, POLITE_DELAY_SECONDS
from src.scraping.extractor_registry import ExtractorRegistry
from src.scraping.models import (
    ExtractionResult,
    RAW_SCHEMA_COLUMNS,
    generate_job_id,
    get_hostname,
)
from src.scraping.link_extractor import LinkExtractor


from src.cleaning.it_classifier import ITClassifier

_ocr_cache = {}


def process_ocr_for_job(result, use_ocr=False):
    """Downloads and processes image advertisement OCR if enabled and appropriate."""
    if not use_ocr:
        result.ocr_status = "not_permitted"
        return result
        
    if result.description_type not in ("image", "hybrid"):
        result.ocr_status = "not_required"
        return result
        
    try:
        import json
        image_urls = json.loads(result.advert_image_urls or "[]")
    except Exception:
        result.ocr_status = "failed"
        result.error_message = "Failed to parse advert_image_urls JSON"
        return result
        
    if not image_urls:
        result.ocr_status = "not_required"
        return result
        
    image_url = image_urls[0]
    
    # 1. Validate image URL (prevent SSRF)
    from src.security.url_validator import validate_url
    is_valid, reason = validate_url(image_url)
    if not is_valid:
        result.ocr_status = "failed"
        result.error_message = f"OCR image URL validation failed: {reason}"
        return result
        
    # 2. Download the image safely
    try:
        import requests
        from PIL import Image as PILImage
        from PIL import ImageOps, ImageEnhance
        import io
        import pytesseract
        
        response = requests.get(image_url, timeout=10, stream=True)
        if response.status_code != 200:
            result.ocr_status = "failed"
            result.error_message = f"Failed to download image: HTTP {response.status_code}"
            return result
            
        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            result.ocr_status = "failed"
            result.error_message = f"Invalid image content type: {content_type}"
            return result
            
        # Size limit: 5MB
        content = []
        size = 0
        for chunk in response.iter_content(8192):
            size += len(chunk)
            if size > 5 * 1024 * 1024:
                result.ocr_status = "failed"
                result.error_message = "Image size exceeds 5MB limit"
                return result
            content.append(chunk)
            
        image_bytes = b"".join(content)
        
        # MD5 Hash cache check
        import hashlib
        img_hash = hashlib.md5(image_bytes).hexdigest()
        if img_hash in _ocr_cache:
            print("  → Using cached OCR results.")
            cached_text, cached_conf = _ocr_cache[img_hash]
            result.ocr_text_raw = cached_text
            result.ocr_confidence = cached_conf
            result.ocr_status = "success"
            return result
        
        # Preprocess using PIL
        img = PILImage.open(io.BytesIO(image_bytes))
        
        # Preprocessing details
        img_gray = ImageOps.grayscale(img)
        if img_gray.width < 1000:
            ratio = 1000 / img_gray.width
            img_gray = img_gray.resize((1000, int(img_gray.height * ratio)), PILImage.Resampling.LANCZOS)
        enhancer = ImageEnhance.Contrast(img_gray)
        img_enhanced = enhancer.enhance(2.0)
        
        # Run local pytesseract OCR
        ocr_text = pytesseract.image_to_string(img_enhanced)
        
        result.ocr_text_raw = ocr_text.strip()
        result.ocr_status = "success"
        result.ocr_confidence = "0.85"
        
        # Cache results
        _ocr_cache[img_hash] = (result.ocr_text_raw, result.ocr_confidence)
        
    except ImportError:
        result.ocr_status = "failed"
        result.error_message = "Pytesseract or PIL libraries missing"
    except Exception as e:
        result.ocr_status = "failed"
        result.error_message = f"OCR failed: {e}"
        
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
        "browser_fallback_count": 0,
        "ocr_success_count": 0,
        "extractor_counts": {},
    }

    url_queue = list(dict.fromkeys(urls))
    processed_urls = set()
    idx = 0

    while idx < len(url_queue):
        # 1. Stop conditions checks
        if metrics["valid_jobs_accepted"] >= target_valid_jobs:
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

        # Check for duplicates
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

        # Step 2: Fetch Page
        metrics["requests_attempted"] += 1
        delay = metrics["requests_attempted"] > 1
        fetch_result = fetch_page(url, delay_before=delay, polite_delay=polite_delay)

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

        # Step 3: Check if listing page or direct job posting page
        # Simple heuristic: if it doesn't contain JobPosting JSON-LD, extract candidate links
        has_jsonld_job = "application/ld+json" in fetch_result.html and "JobPosting" in fetch_result.html
        if not has_jsonld_job:
            discovered_links = link_extractor.extract_job_links(fetch_result.final_url, fetch_result.html)
            if len(discovered_links) > 1:
                metrics["listing_pages_visited"] += 1
                print(f"  → Listing page. Discovered {len(discovered_links)} candidates.")
                
                # Check safety request budget expansion
                added_count = 0
                for link in discovered_links:
                    if link not in url_queue and link not in processed_urls:
                        url_queue.append(link)
                        added_count += 1
                print(f"  → Enqueued {added_count} new unique links.")
                continue

        # Step 4: Route to Extractor Registry
        metrics["detail_pages_processed"] += 1
        result = registry.extract(
            fetch_result.final_url,
            fetch_result.html,
            result,
            use_browser_fallback=use_browser_fallback
        )

        if result.rendering_used == "True":
            metrics["browser_fallback_count"] += 1

        # Step 5: OCR Workflow if appropriate
        result = process_ocr_for_job(result, use_ocr=use_ocr)
        if result.ocr_status == "success":
            metrics["ocr_success_count"] += 1

        # Generate job_id if not set
        if not result.job_id:
            result.job_id = generate_job_id(result.source_hostname, result.source_job_id, url)

        # Run IT Relevance Classifier
        classification = classifier.classify(
            title=result.job_title_raw,
            category=result.industry_raw or result.qualifications_raw, # hints
            skills=result.skills_raw,
            description=result.job_description_raw or result.ocr_text_raw
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
        },
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
