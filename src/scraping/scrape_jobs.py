import os
import sys
import hashlib
import pathlib
import time
from datetime import datetime, timezone
import csv
import urllib.parse
import json
import re
import argparse
import requests
from bs4 import BeautifulSoup

# Try to import pytesseract, handle gracefully if not available or misconfigured
try:
    import pytesseract
    from PIL import Image as PILImage
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# ==========================================
# Configuration & Globals
# ==========================================
CONFIG_COUNTRY = "Sri Lanka"
CONFIG_PLATFORM = "topjobs.lk"
CONFIG_FUNCTIONAL_AREA = "SDQ"
ENABLE_IMAGE_DOWNLOAD = False  # Defaults to False due to unverified permissions

# ==========================================
# Helper Functions
# ==========================================

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

# ==========================================
# Listing-Page Parser
# ==========================================

def parse_listing_page(url, headers):
    """Fetches and parses the main functional area browse page."""
    print(f"Fetching listing page: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching listing page: {e}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 3:
        print("Warning: Listing page does not contain expected tables structure.")
        return {}

    # Table 2 contains the vacancy list
    listing_table = tables[2]
    rows = listing_table.find_all("tr")
    metadata = {}

    for row in rows:
        row_id = row.get("id", "")
        if not row_id.startswith("tr"):
            continue
        
        cells = row.find_all(["td", "th"])
        if len(cells) < 7:
            continue
        
        # Cell 1: Job Ref No.
        source_job_id = cells[1].get_text(strip=True)
        if not source_job_id:
            continue
        
        # Cell 2: Title & Company + Spans
        title_company_cell = cells[2]
        title_el = title_company_cell.find("h2")
        company_el = title_company_cell.find("h1")
        
        title = title_el.get_text(strip=True) if title_el else ""
        company = company_el.get_text(strip=True) if company_el else ""
        
        # Extract ac, ec, jc spans
        ac_span = title_company_cell.find("span", id=lambda x: x and x.startswith("hdnAC"))
        ec_span = title_company_cell.find("span", id=lambda x: x and x.startswith("hdnEC"))
        jc_span = title_company_cell.find("span", id=lambda x: x and x.startswith("hdnJC"))
        
        ac = ac_span.get_text(strip=True) if ac_span else ""
        ec = ec_span.get_text(strip=True) if ec_span else ""
        jc = jc_span.get_text(strip=True) if jc_span else ""
        
        # Parse onclick if spans are missing
        onclick = row.get("onclick", "")
        rid_val = row_id.replace("tr", "")
        if (not ac or not jc) and onclick:
            match = re.search(r"createAlert\('([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'", onclick)
            if match:
                rid, ac_val, jc_val, ec_val = match.groups()
                ac = ac_val
                jc = jc_val
                ec = ec_val
                rid_val = rid
        
        # Fallback to Cell 1 text for jc if still missing
        if not jc:
            jc = source_job_id
            
        detail_url = f"https://www.topjobs.lk/employer/JobAdvertismentServlet?rid={rid_val}&ac={ac}&jc={jc}&ec={ec}&pg=applicant/vacancybyfunctionalarea.jsp"
        
        # Cell 4: Opening Date
        opening_date = cells[4].get_text(strip=True)
        # Cell 5: Closing Date
        closing_date = cells[5].get_text(strip=True)
        # Cell 6: Location
        location = cells[6].get_text(strip=True)
        
        metadata[jc] = {
            "source_job_id": jc,
            "job_title_raw": title,
            "company_raw": company,
            "listing_posted_date_raw": opening_date,
            "closing_date_raw": closing_date,
            "location_raw": location,
            "detail_url": detail_url
        }
        
    print(f"Extracted listing metadata for {len(metadata)} vacancies.")
    return metadata

# ==========================================
# OCR Workflow Implementation
# ==========================================

def run_ocr_pipeline(image_urls, source_job_id, project_root, headers):
    """Downloads images to raw/images, preprocesses, runs OCR and saves raw OCR texts."""
    images_dir = project_root / "data" / "raw" / "images"
    ocr_raw_dir = project_root / "data" / "raw" / "ocr"
    ocr_failures_file = project_root / "logs" / "ocr_failures.csv"
    
    images_dir.mkdir(parents=True, exist_ok=True)
    ocr_raw_dir.mkdir(parents=True, exist_ok=True)
    ocr_failures_file.parent.mkdir(parents=True, exist_ok=True)
    
    ocr_texts = []
    downloaded_paths = []
    
    for idx, img_url in enumerate(image_urls, 1):
        # Extract file extension
        parsed_img = urllib.parse.urlparse(img_url)
        ext = pathlib.Path(parsed_img.path).suffix or ".png"
        if ext.lower() not in [".png", ".jpg", ".jpeg", ".gif"]:
            ext = ".png"
            
        img_filename = f"{source_job_id}_{idx}{ext}"
        img_path = images_dir / img_filename
        
        print(f"  Downloading flyer image {idx}: {img_url}")
        try:
            r = requests.get(img_url, headers=headers, timeout=20)
            r.raise_for_status()
            with open(img_path, "wb") as f:
                f.write(r.content)
            downloaded_paths.append(str(img_path))
        except Exception as e:
            print(f"  Failed to download image {img_url}: {e}")
            with open(ocr_failures_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([source_job_id, img_url, f"Download failed: {e}", datetime.now(timezone.utc).isoformat()])
            return "failed", -1.0, f"Image download failed: {e}"

        # Execute OCR
        if not TESSERACT_AVAILABLE:
            print("  pytesseract or Pillow is not installed. Skipping local OCR.")
            return "failed", -1.0, "Tesseract OCR engine / pytesseract not available locally."
            
        try:
            print(f"  Executing Tesseract OCR on {img_filename}...")
            img = PILImage.open(img_path)
            ocr_text = pytesseract.image_to_string(img)
            
            # Save raw OCR text to file
            txt_filename = f"{source_job_id}_{idx}.txt"
            txt_path = ocr_raw_dir / txt_filename
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(ocr_text)
                
            ocr_texts.append(ocr_text)
        except Exception as e:
            print(f"  Tesseract OCR failed on {img_filename}: {e}")
            with open(ocr_failures_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([source_job_id, img_url, f"OCR failed: {e}", datetime.now(timezone.utc).isoformat()])
            return "failed", -1.0, f"OCR execution failed: {e}"

    if ocr_texts:
        combined_text = "\n--- Next Page/Image ---\n".join(ocr_texts)
        # We set a placeholder confidence of 75.0 if success, since basic pytesseract image_to_string doesn't export confidence
        return "success", 75.0, combined_text
    else:
        return "failed", -1.0, "No text extracted."

# ==========================================
# Main Scraper Execution
# ==========================================

def scrape_job(url, headers, listing_meta, collection_batch_id, project_root):
    """Fetches and parses details for a single job."""
    # Parse source_job_id from URL query params
    parsed_url = urllib.parse.urlparse(url)
    queries = urllib.parse.parse_qs(parsed_url.query)
    source_job_id = queries.get("jc", [None])[0] or ""
    
    canonical_url = get_canonical_url(url)
    job_id = create_job_id(CONFIG_PLATFORM, source_job_id, url)
    scraped_at = datetime.now(timezone.utc).isoformat()
    
    # Default outputs
    job_data = {
        "job_id": job_id,
        "source_job_id": source_job_id,
        "job_title_raw": "",
        "company_raw": "",
        "country": CONFIG_COUNTRY,
        "location_raw": "",
        "job_description_raw": "",
        "listing_posted_date_raw": "",
        "closing_date_raw": "",
        "functional_area": CONFIG_FUNCTIONAL_AREA,
        "description_type": "missing",
        "advert_image_urls": "[]",
        "ocr_text_raw": "",
        "ocr_status": "not_required",
        "ocr_confidence": -1.0,
        "source_platform": CONFIG_PLATFORM,
        "source_url": url,
        "canonical_url": canonical_url,
        "collection_batch_id": collection_batch_id,
        "scraped_at": scraped_at,
        "extraction_status": "failed",
        "exclusion_reason": ""
    }

    print(f"Downloading detail page: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        return job_data, f"Network error: {e}"

    soup = BeautifulSoup(response.text, "lxml")
    
    # 1. Title, Company, Location (from detail page)
    title_el = soup.find(id="position") or soup.find(class_="job-title")
    job_title_raw = title_el.get_text() if title_el else ""
    
    company_el = soup.find(id="employer") or soup.find(class_="ad-company-name")
    company_raw = company_el.get_text() if company_el else ""
    
    location_el = soup.find(id="adview-job-location") or soup.find(class_="adview-job-location")
    location_raw = location_el.get_text() if location_el else ""
    
    # Merge listing page metadata if available
    meta = listing_meta.get(source_job_id, {})
    if meta:
        job_data["listing_posted_date_raw"] = meta.get("listing_posted_date_raw", "")
        job_data["closing_date_raw"] = meta.get("closing_date_raw", "")
        if not job_title_raw.strip():
            job_title_raw = meta.get("job_title_raw", "")
        if not company_raw.strip():
            company_raw = meta.get("company_raw", "")
        if not location_raw.strip():
            location_raw = meta.get("location_raw", "")
            
    # Clean strings but preserve spacing inside raw dataset
    job_data["job_title_raw"] = job_title_raw.strip()
    job_data["company_raw"] = company_raw.strip()
    job_data["location_raw"] = location_raw.strip()

    # 2. Extract Description & Flyer Images
    remark_div = soup.find(id="remark") or soup.find(class_="job-holder")
    
    if remark_div:
        # Preserve raw HTML content
        job_data["job_description_raw"] = str(remark_div)
        
        # Scan for images inside remark
        image_urls = []
        for img in remark_div.find_all("img"):
            src = img.get("src", "")
            if not src:
                continue
            # Filter utility/styling/loading images
            if any(term in src.lower() for term in ["local.jpg", "application.png", "loading.gif", "info.png"]):
                continue
            # Make absolute URL
            abs_src = urllib.parse.urljoin("https://www.topjobs.lk", src)
            image_urls.append(abs_src)
            
        job_data["advert_image_urls"] = json.dumps(image_urls)
        
        # Classify Description Type using plain text get_text() output
        plain_text_extracted = " ".join(remark_div.get_text().split()).strip()
        has_text = len(plain_text_extracted) > 100
        has_images = len(image_urls) > 0
        
        if has_text and has_images:
            job_data["description_type"] = "hybrid"
        elif has_images:
            job_data["description_type"] = "image"
        elif has_text:
            job_data["description_type"] = "html_text"
        else:
            job_data["description_type"] = "missing"
            
        # 3. Apply OCR Pipeline
        if has_images:
            if ENABLE_IMAGE_DOWNLOAD:
                status, confidence, ocr_text = run_ocr_pipeline(image_urls, source_job_id, project_root, headers)
                job_data["ocr_status"] = status
                job_data["ocr_confidence"] = confidence
                job_data["ocr_text_raw"] = ocr_text
            else:
                job_data["ocr_status"] = "not_permitted"  # Permission unverified
                job_data["ocr_text_raw"] = ""
                job_data["ocr_confidence"] = -1.0
        else:
            job_data["ocr_status"] = "not_required"
            
    else:
        job_data["job_description_raw"] = ""
        job_data["description_type"] = "missing"
        job_data["ocr_status"] = "not_required"

    # 4. Check for IT scope and set status
    if not job_data["job_title_raw"]:
        job_data["extraction_status"] = "failed"
        job_data["exclusion_reason"] = "Failed to extract job title"
    else:
        is_it, is_ambig, reason = evaluate_it_job_status(job_data["job_title_raw"])
        if not is_it:
            job_data["extraction_status"] = "excluded"
            job_data["exclusion_reason"] = reason
        else:
            if is_ambig:
                job_data["extraction_status"] = "partial"  # Ambiguous flag
                job_data["exclusion_reason"] = reason
            else:
                # Valid IT Job! Check description coverage
                if job_data["description_type"] == "missing":
                    job_data["extraction_status"] = "partial"
                    job_data["exclusion_reason"] = "Missing job description body"
                elif job_data["description_type"] in ["image", "hybrid"] and job_data["ocr_status"] == "failed":
                    job_data["extraction_status"] = "partial"
                    job_data["exclusion_reason"] = "OCR failed to parse advertisement image"
                else:
                    job_data["extraction_status"] = "success"
                    
    return job_data, None

# ==========================================
# Main Execution Entrypoint
# ==========================================

def run_scraping_pipeline(urls, progress_callback=None, enable_ocr=False, batch_id=None):
    """Executes the scraping pipeline for a list of URLs, generating an immutable batch file and updating the manifest."""
    import pandas as pd
    
    # Paths setup
    project_root = pathlib.Path(__file__).resolve().parent.parent.parent
    batches_dir = project_root / "data" / "raw" / "batches"
    manifest_file = project_root / "data" / "raw" / "collection_manifest.json"
    failed_log_file = project_root / "logs" / "failed_urls.csv"

    # Create directories
    batches_dir.mkdir(parents=True, exist_ok=True)
    failed_log_file.parent.mkdir(parents=True, exist_ok=True)

    # Dynamic collection batch configuration
    batch_time = datetime.now(timezone.utc)
    collection_batch_id = batch_id if batch_id else f"batch_{batch_time.strftime('%Y%m%d_%H%M%S')}"
    raw_data_file = batches_dir / f"jobs_raw_{collection_batch_id}.csv"

    print(f"Initializing collection batch: {collection_batch_id}")

    headers = {
        "User-Agent": "Academic Research Bot/1.0 (Contact: student-researcher@example.edu; Sri Lanka Skills Demand Study)"
    }

    # Set ENABLE_IMAGE_DOWNLOAD configuration value temporarily based on argument
    global ENABLE_IMAGE_DOWNLOAD
    original_ocr_flag = ENABLE_IMAGE_DOWNLOAD
    ENABLE_IMAGE_DOWNLOAD = enable_ocr

    # Fetch and parse listing metadata
    listing_meta_url = "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=SDQ"
    listing_meta = parse_listing_page(listing_meta_url, headers)

    # Set up failed URLs log header if not present
    if not failed_log_file.exists():
        with open(failed_log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["url", "error_message", "timestamp"])

    headers_schema = [
        "job_id", "source_job_id", "job_title_raw", "company_raw", "country", "location_raw",
        "job_description_raw", "listing_posted_date_raw", "closing_date_raw", "functional_area",
        "description_type", "advert_image_urls", "ocr_text_raw", "ocr_status", "ocr_confidence",
        "source_platform", "source_url", "canonical_url", "collection_batch_id", "scraped_at",
        "extraction_status", "exclusion_reason"
    ]

    success_count = 0
    partial_count = 0
    failed_count = 0
    excluded_count = 0
    html_desc_count = 0
    image_desc_count = 0
    hybrid_desc_count = 0
    ocr_success_count = 0

    # Write batch CSV header
    with open(raw_data_file, "w", newline="", encoding="utf-8") as raw_f:
        writer = csv.DictWriter(raw_f, fieldnames=headers_schema)
        writer.writeheader()

    for idx, url in enumerate(urls, 1):
        if progress_callback:
            progress_callback(idx, len(urls), f"Scraping {idx} of {len(urls)}: {url}")
            
        print(f"Scraping {idx}/{len(urls)}: {url}")
        
        job_data, err = scrape_job(url, headers, listing_meta, collection_batch_id, project_root)
        
        if err:
            print(f"  --> Failed: {err}")
            # Append failure log
            with open(failed_log_file, "a", newline="", encoding="utf-8") as failed_f:
                failed_writer = csv.writer(failed_f)
                failed_writer.writerow([url, err, datetime.now(timezone.utc).isoformat()])
            failed_count += 1
            
            # Save raw failure state row in batch CSV to preserve attempted record
            job_data["exclusion_reason"] = f"Network or request failure: {err}"
            with open(raw_data_file, "a", newline="", encoding="utf-8") as raw_f:
                writer = csv.DictWriter(raw_f, fieldnames=headers_schema)
                writer.writerow(job_data)
        else:
            # Save scraped data row in batch CSV
            with open(raw_data_file, "a", newline="", encoding="utf-8") as raw_f:
                writer = csv.DictWriter(raw_f, fieldnames=headers_schema)
                writer.writerow(job_data)
                
            # Compile batch run statistics
            status = job_data["extraction_status"]
            if status == "success":
                success_count += 1
            elif status == "partial":
                partial_count += 1
            elif status == "excluded":
                excluded_count += 1
            else:
                failed_count += 1
                
            desc_type = job_data["description_type"]
            if desc_type == "html_text":
                html_desc_count += 1
            elif desc_type == "image":
                image_desc_count += 1
            elif desc_type == "hybrid":
                hybrid_desc_count += 1
                
            if job_data["ocr_status"] == "success":
                ocr_success_count += 1

        # Strict 2-second rate-limiting delay between requests
        if idx < len(urls):
            time.sleep(2)

    # Compile Collection Manifest
    manifest_record = {
        "collection_batch_id": collection_batch_id,
        "started_at": batch_time.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "functional_area": CONFIG_FUNCTIONAL_AREA,
        "attempted_count": len(urls),
        "success_count": success_count,
        "partial_count": partial_count,
        "failed_count": failed_count,
        "excluded_count": excluded_count,
        "html_description_count": html_desc_count,
        "image_description_count": image_desc_count,
        "hybrid_description_count": hybrid_desc_count,
        "ocr_success_count": ocr_success_count,
        "permission_status": "unverified"
    }

    # Load existing manifest records or initialize new
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

    print("\n--- Scraping Batch Summary ---")
    print(f"Batch ID: {collection_batch_id}")
    print(f"Total attempted URLs: {len(urls)}")
    print(f"Success  : {success_count}")
    print(f"Failed   : {failed_count}")
    print(f"Excluded : {excluded_count}")
    print(f"Raw batch file saved in: {raw_data_file}")
    print(f"Collection manifest updated.")

    # Reset global OCR flag
    ENABLE_IMAGE_DOWNLOAD = original_ocr_flag

    # Read and return df and batch_id
    try:
        df_raw = pd.read_csv(raw_data_file, dtype=str).fillna("")
    except Exception:
        df_raw = pd.DataFrame(columns=headers_schema)
        
    return df_raw, collection_batch_id

# ==========================================
# Main Execution Entrypoint
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="Academic Topjobs.lk Job Scraper")
    parser.add_argument("--test-limit", type=int, default=None, help="Limit number of scraped URLs for testing (1-3)")
    args = parser.parse_args()

    # Paths setup
    current_dir = pathlib.Path(__file__).resolve().parent
    project_root = current_dir.parent.parent
    urls_file = project_root / "urls.txt"

    # Read target URLs
    if not urls_file.exists():
        print(f"Error: {urls_file} does not exist.")
        sys.exit(1)
        
    with open(urls_file, "r", encoding="utf-8") as f:
        raw_urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        
    urls = list(dict.fromkeys(raw_urls))
    
    # Handle test mode URL limiting
    if args.test_limit is not None:
        urls = urls[:args.test_limit]
        print(f"Test mode: limiting crawl to the first {args.test_limit} URLs.")
        
    print(f"Processing {len(urls)} target URLs...")

    run_scraping_pipeline(
        urls, 
        progress_callback=lambda idx, tot, txt: print(txt), 
        enable_ocr=ENABLE_IMAGE_DOWNLOAD
    )

if __name__ == "__main__":
    main()
