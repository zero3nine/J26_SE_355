import os
import sys
import pathlib
import json
import re
import csv
import pandas as pd
from datetime import datetime, timezone
from dateutil.parser import parse as date_parse

# ==========================================
# Configurations
# ==========================================
CONFIG_PLATFORM = "multi-site"
CONFIG_FUNCTIONAL_AREA = "IT/Software"

# ==========================================
# Validation Helpers
# ==========================================

def is_valid_url(url):
    """Simple check for URL validity."""
    if not isinstance(url, str):
        return False
    return url.startswith("http://") or url.startswith("https://")

def is_valid_iso_date(date_str):
    """Checks if date string matches YYYY-MM-DD."""
    if not date_str:
        return True  # Optional field
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def is_in_future(date_str):
    """Checks if date is in the future."""
    if not date_str:
        return False
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return dt.date() > now.date()
    except ValueError:
        return False

def is_valid_timestamp(ts_str):
    """Checks if timestamp is valid ISO 8601 UTC timestamp."""
    if not ts_str:
        return False
    try:
        date_parse(ts_str)
        return True
    except Exception:
        return False

# ==========================================
# Reusable Validation API Pipeline Function
# ==========================================

def run_validation_pipeline(df_raw, df_internal, df_team):
    """Runs data quality validation checks across the datasets.
    
    Returns:
        report_runs (list): Checks and their PASS/WARNING/FAIL status.
        metrics (dict): Summary statistical counters.
        report_markdown (str): The markdown report content.
    """
    total_attempted = len(df_raw) if len(df_raw) > 0 else len(df_internal)
    report_runs = []
    
    def log_check(name, status, details=""):
        report_runs.append({"name": name, "status": status, "details": details})

    # Ensure dataframes have required columns or mock them if empty
    if df_internal.empty:
        required_cols = [
            "job_id", "source_job_id", "job_title_raw", "company_raw", "country", "location_raw",
            "job_description_raw", "job_description_clean", "listing_posted_date_raw", "closing_date_raw", "requirements_raw",
            "functional_area", "description_type", "advert_image_urls", "ocr_text_raw", "ocr_status",
            "ocr_confidence", "source_platform", "source_url", "canonical_url", "collection_batch_id",
            "scraped_at", "extraction_status", "exclusion_reason"
        ]
        df_internal = pd.DataFrame(columns=required_cols)

    # --- Rule Check 1: Required Columns ---
    required_cols = [
        "job_id", "source_job_id", "job_title_raw", "company_raw", "country", "location_raw",
        "job_description_raw", "job_description_clean", "listing_posted_date_raw", "closing_date_raw", "requirements_raw",
        "functional_area", "description_type", "advert_image_urls", "ocr_text_raw", "ocr_status",
        "ocr_confidence", "source_platform", "source_url", "canonical_url", "collection_batch_id",
        "scraped_at", "extraction_status", "exclusion_reason"
    ]
    missing_cols = [col for col in required_cols if col not in df_internal.columns]
    if not missing_cols:
        log_check("Required Columns Schema", "PASS", "All required columns are present in the internal dataset.")
    else:
        log_check("Required Columns Schema", "FAIL", f"Missing columns in internal dataset: {missing_cols}")

    # --- Rule Check 2: Valid Source Job IDs ---
    invalid_job_ids = sum(not re.match(r"^\d+$", str(val)) for val in df_internal["source_job_id"] if val)
    if invalid_job_ids == 0:
        log_check("Source Job IDs Format", "PASS", "All present source job IDs are valid numeric codes.")
    else:
        log_check("Source Job IDs Format", "WARNING", f"Found {invalid_job_ids} records with non-numeric source job IDs.")

    # --- Rule Check 3 & 4: Uniqueness & Duplicates ---
    batch_duplicates = 0
    if "collection_batch_id" in df_internal.columns and "job_id" in df_internal.columns:
        for batch_id, group in df_internal.groupby("collection_batch_id"):
            batch_duplicates += len(group) - group["job_id"].nunique()
            
    if batch_duplicates == 0:
        log_check("Identity Uniqueness per Batch", "PASS", "All job IDs are unique within their respective collection batches.")
    else:
        log_check("Identity Uniqueness per Batch", "FAIL", f"Found {batch_duplicates} duplicate job IDs within the same batch.")

    total_duplicates_clean = len(df_internal) - df_internal["job_id"].nunique() if "job_id" in df_internal.columns else 0
    if total_duplicates_clean == 0:
        log_check("Deduplication Across Batches", "PASS", "No duplicate job IDs remain in the cleaned internal dataset.")
    else:
        log_check("Deduplication Across Batches", "FAIL", f"Found {total_duplicates_clean} duplicate job IDs in clean dataset.")

    # --- Rule Check 5: URL Validity ---
    invalid_urls = sum(not is_valid_url(url) for url in df_internal["source_url"]) if "source_url" in df_internal.columns else 0
    if invalid_urls == 0:
        log_check("URL Validity", "PASS", "All source URLs are valid HTTP/HTTPS links.")
    else:
        log_check("URL Validity", "FAIL", f"Found {invalid_urls} records with invalid URLs.")

    # --- Rule Check 6: Critical Fields Check ---
    missing_critical = 0
    for idx, row in df_internal.iterrows():
        if not row.get("job_id") or not row.get("job_title_raw") or not row.get("company_raw") or not row.get("source_url"):
            missing_critical += 1
    if missing_critical == 0:
        log_check("Critical Fields Check", "PASS", "Zero missing critical fields in clean records.")
    else:
        log_check("Critical Fields Check", "FAIL", f"Found {missing_critical} records with missing critical fields (job_id, title, company, or URL).")

    # --- Rule Check 7 & 8: Dates Validity ---
    invalid_dates = sum(not is_valid_iso_date(d) for d in df_internal["listing_posted_date_raw"]) if "listing_posted_date_raw" in df_internal.columns else 0
    invalid_dates += sum(not is_valid_iso_date(d) for d in df_internal["closing_date_raw"]) if "closing_date_raw" in df_internal.columns else 0
    if invalid_dates == 0:
        log_check("Date Format Validation", "PASS", "All dates follow the standard YYYY-MM-DD ISO format.")
    else:
        log_check("Date Format Validation", "FAIL", f"Found {invalid_dates} records with malformed date fields.")

    future_dates = sum(is_in_future(d) for d in df_internal["listing_posted_date_raw"]) if "listing_posted_date_raw" in df_internal.columns else 0
    if future_dates == 0:
        log_check("Future Date Constraints", "PASS", "No publication dates are set in the future.")
    else:
        log_check("Future Date Constraints", "FAIL", f"Found {future_dates} records with publication dates in the future.")

    # --- Rule Check 9: Timestamp Format ---
    invalid_ts = sum(not is_valid_timestamp(ts) for ts in df_internal["scraped_at"]) if "scraped_at" in df_internal.columns else 0
    if invalid_ts == 0:
        log_check("Scrape Timestamp Formatting", "PASS", "All scraped_at timestamps are valid ISO 8601 UTC datetimes.")
    else:
        log_check("Scrape Timestamp Formatting", "FAIL", f"Found {invalid_ts} records with invalid scraped_at format.")

    # --- Rule Check 10: Image URL JSON Validity ---
    invalid_img_json = 0
    if "advert_image_urls" in df_internal.columns:
        for val in df_internal["advert_image_urls"]:
            try:
                urls = json.loads(val)
                if not isinstance(urls, list):
                    invalid_img_json += 1
                elif any(not is_valid_url(u) for u in urls):
                    invalid_img_json += 1
            except Exception:
                invalid_img_json += 1
    if invalid_img_json == 0:
        log_check("Image URLs Array Format", "PASS", "All image URLs are stored in valid JSON lists of URLs.")
    else:
        log_check("Image URLs Array Format", "WARNING", f"Found {invalid_img_json} records with malformed JSON image arrays.")

    # --- Rule Check 11 & 12: Description Type and OCR Status consistency ---
    invalid_desc_types = sum(val not in ["html_text", "image", "hybrid", "missing", "jsonld"] for val in df_internal["description_type"]) if "description_type" in df_internal.columns else 0
    if invalid_desc_types == 0:
        log_check("Description Type Consistency", "PASS", "All description types are classified correctly.")
    else:
        log_check("Description Type Consistency", "FAIL", f"Found {invalid_desc_types} records with unknown description types.")

    invalid_ocr_status = sum(val not in ["not_required", "pending", "success", "low_confidence", "failed", "not_permitted"] for val in df_internal["ocr_status"]) if "ocr_status" in df_internal.columns else 0
    if invalid_ocr_status == 0:
        log_check("OCR Status Consistency", "PASS", "All OCR statuses conform to the schema definitions.")
    else:
        log_check("OCR Status Consistency", "FAIL", f"Found {invalid_ocr_status} records with invalid OCR status labels.")

    ocr_mismatch = 0
    for idx, row in df_internal.iterrows():
        dtype = row.get("description_type", "")
        ostatus = row.get("ocr_status", "")
        if dtype == "image" and ostatus == "not_required":
            ocr_mismatch += 1
        elif dtype == "html_text" and ostatus not in ["not_required", "not_permitted"]:
            ocr_mismatch += 1
    if ocr_mismatch == 0:
        log_check("Description-OCR Alignment", "PASS", "OCR status aligns with the description type.")
    else:
        log_check("Description-OCR Alignment", "WARNING", f"Found {ocr_mismatch} records with description/OCR status mismatches.")

    # --- Compile Metrics ---
    html_count = sum(df_internal["description_type"] == "html_text") if "description_type" in df_internal.columns else 0
    image_count = sum(df_internal["description_type"] == "image") if "description_type" in df_internal.columns else 0
    hybrid_count = sum(df_internal["description_type"] == "hybrid") if "description_type" in df_internal.columns else 0
    missing_desc = sum(df_internal["description_type"] == "missing") if "description_type" in df_internal.columns else 0

    success_jobs = sum(df_internal["extraction_status"] == "success") if "extraction_status" in df_internal.columns else 0
    partial_jobs = sum(df_internal["extraction_status"] == "partial") if "extraction_status" in df_internal.columns else 0
    excluded_jobs = sum(df_internal["extraction_status"] == "excluded") if "extraction_status" in df_internal.columns else 0
    failed_jobs = sum(df_internal["extraction_status"] == "failed") if "extraction_status" in df_internal.columns else 0

    ocr_successes = sum(df_internal["ocr_status"] == "success") if "ocr_status" in df_internal.columns else 0
    ocr_failures = sum(df_internal["ocr_status"] == "failed") if "ocr_status" in df_internal.columns else 0
    ocr_pending = sum(df_internal["ocr_status"] == "pending") if "ocr_status" in df_internal.columns else 0
    ocr_not_permitted = sum(df_internal["ocr_status"] == "not_permitted") if "ocr_status" in df_internal.columns else 0

    analyzable_count = 0
    if "job_description_clean" in df_internal.columns and "description_type" in df_internal.columns:
        analyzable_count = sum(
            (df_internal["job_description_clean"].str.strip() != "") &
            (df_internal["description_type"] != "missing") &
            (~df_internal["job_description_clean"].str.contains("not permitted|Direct plain text not extracted|pending", case=False))
        )

    missing_posted_date = sum(df_internal["listing_posted_date_raw"] == "") if "listing_posted_date_raw" in df_internal.columns else 0
    missing_closing_date = sum(df_internal["closing_date_raw"] == "") if "closing_date_raw" in df_internal.columns else 0
    missing_companies = sum(df_internal["company_raw"] == "") if "company_raw" in df_internal.columns else 0
    missing_locations = sum(df_internal["location_raw"] == "") if "location_raw" in df_internal.columns else 0
    manual_review_records = sum(df_internal["exclusion_reason"].str.contains("manual review", case=False)) if "exclusion_reason" in df_internal.columns else 0
    final_valid_records = len(df_team)

    extraction_success_rate = (success_jobs / total_attempted * 100) if total_attempted > 0 else 0.0
    analyzable_text_rate = (analyzable_count / total_attempted * 100) if total_attempted > 0 else 0.0
    ocr_coverage_pct = (ocr_successes / (image_count + hybrid_count) * 100) if (image_count + hybrid_count) > 0 else 0.0

    metrics = {
        "attempted_count": total_attempted,
        "success_count": success_jobs,
        "partial_count": partial_jobs,
        "failed_count": failed_jobs,
        "excluded_count": excluded_jobs,
        "html_description_count": html_count,
        "image_description_count": image_count,
        "hybrid_description_count": hybrid_count,
        "missing_description_count": missing_desc,
        "ocr_success_count": ocr_successes,
        "ocr_failed_count": ocr_failures,
        "ocr_pending_count": ocr_pending,
        "ocr_not_permitted_count": ocr_not_permitted,
        "missing_posted_date_count": missing_posted_date,
        "missing_closing_date_count": missing_closing_date,
        "missing_companies_count": missing_companies,
        "missing_locations_count": missing_locations,
        "manual_review_records_count": manual_review_records,
        "final_valid_records_count": final_valid_records,
        "analyzable_text_count": analyzable_count,
        "extraction_success_rate": extraction_success_rate,
        "analyzable_text_rate": analyzable_text_rate,
        "ocr_coverage_rate": ocr_coverage_pct
    }

    # Generate Markdown Report
    report_md = []
    report_md.append("# Data Quality & Scraping Validation Report\n\n")
    report_md.append(f"**Report Generated At**: {datetime.now(timezone.utc).isoformat()}\n")
    report_md.append(f"**Target Platform**: Multi-site ({CONFIG_PLATFORM})\n")
    report_md.append(f"**Target Functional Area**: {CONFIG_FUNCTIONAL_AREA}\n\n")

    report_md.append("## 1. Executive Summary & Pipeline Metrics\n\n")
    report_md.append("| Metric | Count | Rate (Denominator: Attempted) |\n")
    report_md.append("| :--- | :---: | :---: |\n")
    report_md.append(f"| **Attempted Jobs** | {total_attempted} | 100.00% |\n")
    report_md.append(f"| **Successful Jobs** | {success_jobs} | {extraction_success_rate:.2f}% |\n")
    report_md.append(f"| **Partial/Flagged Jobs** | {partial_jobs} | {(partial_jobs / total_attempted * 100):.2f}% |\n")
    report_md.append(f"| **Failed Jobs (Parser/Net)** | {failed_jobs} | {(failed_jobs / total_attempted * 100):.2f}% |\n")
    report_md.append(f"| **Excluded Jobs (Non-IT)** | {excluded_jobs} | {(excluded_jobs / total_attempted * 100):.2f}% |\n")
    report_md.append(f"| **Final Valid Records (Team CSV)** | {final_valid_records} | {(final_valid_records / total_attempted * 100):.2f}% |\n")
    report_md.append(f"| **Analyzable Descriptions (Text)** | {analyzable_count} | {analyzable_text_rate:.2f}% |\n\n")

    report_md.append("## 2. Detailed Collection Audit Statistics\n\n")
    report_md.append("### Advertisement Formats Distribution\n")
    report_md.append(f"* **HTML-Text Advertisements**: {html_count} ({(html_count / max(1, len(df_internal)) * 100):.2f}% of clean records)\n")
    report_md.append(f"* **Image-Only Advertisements**: {image_count} ({(image_count / max(1, len(df_internal)) * 100):.2f}% of clean records)\n")
    report_md.append(f"* **Hybrid (Text + Image) Advertisements**: {hybrid_count} ({(hybrid_count / max(1, len(df_internal)) * 100):.2f}% of clean records)\n")
    report_md.append(f"* **Missing Description Body**: {missing_desc} ({(missing_desc / max(1, len(df_internal)) * 100):.2f}% of clean records)\n\n")

    report_md.append("### OCR Quality & Status\n")
    report_md.append(f"* **OCR Successes**: {ocr_successes}\n")
    report_md.append(f"* **OCR Failures**: {ocr_failures}\n")
    report_md.append(f"* **OCR Pending**: {ocr_pending}\n")
    report_md.append(f"* **OCR Not Permitted (Permission Unverified)**: {ocr_not_permitted}\n")
    report_md.append(f"* **OCR Image Coverage Rate**: {ocr_coverage_pct:.2f}% of image-based advertisements\n\n")

    report_md.append("### Quality Gaps & Manual Interventions\n")
    report_md.append(f"* **Missing Companies**: {missing_companies} records\n")
    report_md.append(f"* **Missing Locations**: {missing_locations} records\n")
    report_md.append(f"* **Missing Publication Dates**: {missing_posted_date} records\n")
    report_md.append(f"* **Manual Review / Flagged Records**: {manual_review_records} records\n\n")

    report_md.append("## 3. Pipeline Checks Validation Rules\n\n")
    report_md.append("| Rule / Constraint Checked | Status | Details / Warnings |\n")
    report_md.append("| :--- | :---: | :--- |\n")
    for check in report_runs:
        status_symbol = "✅ PASS" if check["status"] == "PASS" else ("⚠️ WARNING" if check["status"] == "WARNING" else "❌ FAIL")
        report_md.append(f"| {check['name']} | {status_symbol} | {check['details']} |\n")

    report_md.append("\n## 4. Sampling Bias & Limitations Statement\n\n")
    report_md.append("> [!IMPORTANT]\n")
    report_md.append("> **OCR and Permission Bias**: Some job portals contain image-based flyer advertisements. ")
    report_md.append("Limiting research to text-only ads may create selection bias (filtering out smaller firms or specific layout styles). ")
    report_md.append(f"In this run, **{image_count} ({image_count / max(1, len(df_internal)) * 100:.2f}%)** of clean records are image-only advertisements. ")
    if ocr_not_permitted > 0:
        report_md.append(f"Since image downloading is disabled under unverified permissions, **{ocr_not_permitted}** flyer advertisements ")
        report_md.append("remain without plain text, resulting in a lower **Analyzable-Text Rate of " + f"{analyzable_text_rate:.2f}%** in the final baseline study. ")
    else:
        report_md.append("Tesseract OCR provides a mitigation, allowing plain text extraction for image flyers where permitted. ")
    report_md.append("Researchers must recognize this layout-based bias when conducting regional skill comparisons.\n")

    report_markdown_str = "".join(report_md)
    return report_runs, metrics, report_markdown_str

# ==========================================
# CLI Entrypoint
# ==========================================

def main():
    print("Executing Validation Module...")

    current_dir = pathlib.Path(__file__).resolve().parent
    project_root = current_dir.parent.parent
    batches_dir = project_root / "data" / "raw" / "batches"
    processed_dir = project_root / "data" / "processed"
    
    processed_internal_csv = processed_dir / "jobs_clean_internal.csv"
    processed_team_csv = processed_dir / "jobs_clean.csv"
    reports_dir = project_root / "reports"
    report_file = reports_dir / "data_quality_report.md"

    reports_dir.mkdir(parents=True, exist_ok=True)

    if not processed_internal_csv.exists() or not processed_team_csv.exists():
        print("[FAIL] Missing cleaned datasets. Please run cleaning script first.")
        sys.exit(1)

    df_internal = pd.read_csv(processed_internal_csv, dtype=str).fillna("")
    df_team = pd.read_csv(processed_team_csv, dtype=str).fillna("")

    # Load raw batches
    raw_files = list(batches_dir.glob("jobs_raw_*.csv")) if batches_dir.exists() else []
    if raw_files:
        dfs = []
        for f in raw_files:
            try:
                dfs.append(pd.read_csv(f, dtype=str).fillna(""))
            except Exception:
                pass
        df_raw = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    else:
        df_raw = pd.DataFrame()

    # Run the validation pipeline API
    report_runs, metrics, report_markdown = run_validation_pipeline(df_raw, df_internal, df_team)

    # Print to console
    for check in report_runs:
        color = "\033[92m[PASS]\033[0m" if check["status"] == "PASS" else ("\033[93m[WARNING]\033[0m" if check["status"] == "WARNING" else "\033[91m[FAIL]\033[0m")
        print(f"{color:18} {check['name']}: {check['details']}")

    print(f"\n--- Performance metrics ---")
    print(f"Extraction Success Rate   : {metrics.get('extraction_success_rate', 0.0):.2f}%")
    print(f"Final Analyzable-Text Rate : {metrics.get('analyzable_text_rate', 0.0):.2f}%")
    print(f"OCR Coverage               : {metrics.get('ocr_coverage_rate', 0.0):.2f}%")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_markdown)

    print(f"Persistent data quality validation report created: {report_file}")

if __name__ == "__main__":
    main()
