import os
import sys
import pathlib
import json
import re
import html
import argparse
import pandas as pd
from datetime import datetime, timezone
from dateutil import parser as date_parser
from src.cleaning.it_classifier import ITClassifier

# ==========================================
# Reusable Helper Functions
# ==========================================

def clean_html_text(text):
    """Decodes HTML entities and strips HTML tags, preserving spacing and tech terms."""
    if not isinstance(text, str) or not text.strip():
        return ""
    
    # Decode HTML entities (e.g., &amp; -> &, &middot; -> ·)
    decoded = html.unescape(text)
    
    # Remove HTML tags using standard regex, replacing with space to prevent word joining
    no_tags = re.sub(r"<[^>]*>", " ", decoded)
    
    # Normalize repeated whitespace (tabs, multiple spaces, newlines) to a single space
    cleaned = re.sub(r"\s+", " ", no_tags)
    
    return cleaned.strip()

def clean_ocr_text(text):
    """Cleans OCR output by normalizing repeated whitespaces."""
    if not isinstance(text, str) or not text.strip():
        return ""
    # Normalize spacing in OCR output
    cleaned = re.sub(r"\s+", " ", text)
    return cleaned.strip()

def parse_date_to_iso(date_str):
    """Converts diverse date strings to standard YYYY-MM-DD format."""
    if not isinstance(date_str, str) or not date_str.strip():
        return ""
    try:
        parsed_dt = date_parser.parse(date_str)
        return parsed_dt.strftime("%Y-%m-%d")
    except Exception:
        return ""

def is_date_in_future(date_iso_str):
    """Checks if date is in the future relative to UTC today."""
    if not date_iso_str:
        return False
    try:
        dt = datetime.strptime(date_iso_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return dt.date() > now.date()
    except Exception:
        return False

def standardize_location(loc_str):
    """Cleans and standardizes Sri Lankan location names."""
    if not isinstance(loc_str, str) or not loc_str.strip():
        return ""
    # Standardize common names
    cleaned = " ".join(loc_str.split()).strip()
    cleaned = re.sub(r"(?i),\s*sri\s*lanka", "", cleaned).strip()
    return cleaned

# ==========================================
# Refactored Reusable API Function
# ==========================================

def clean_raw_dataframe(df_raw):
    """Applies multi-stage cleaning, IT job filters, and deduplication to a raw job DataFrame.
    
    Returns:
        df_internal (pd.DataFrame): Rich internal dataset with 22 columns.
        df_team (pd.DataFrame): Final team-required dataset with 10 columns.
        stats (dict): Performance counters and deduplication metrics.
    """
    total_raw_records = len(df_raw)
    cleaned_records = []
    
    # Initialize IT relevance classifier
    classifier = ITClassifier()
    
    # Counter statistics
    filtered_future_date = 0
    filtered_short_desc = 0
    filtered_short_title = 0
    filtered_non_it = 0

    for idx, row in df_raw.iterrows():
        # Trim whitespace — handle both old and new schema columns
        job_id = str(row.get("job_id", "")).strip()
        source_job_id = str(row.get("source_job_id", "")).strip()
        job_title_raw = str(row.get("job_title_raw", "")).strip()
        company_raw = str(row.get("company_raw", "")).strip()
        # Support both old 'country' and new 'country_raw' column names
        country = str(row.get("country", row.get("country_raw", ""))).strip()
        location_raw = str(row.get("location_raw", "")).strip()
        job_description_raw = str(row.get("job_description_raw", "")).strip()
        # Support both old 'listing_posted_date_raw' and new 'posted_date_raw'
        listing_posted_date_raw = str(row.get("listing_posted_date_raw", row.get("posted_date_raw", ""))).strip()
        closing_date_raw = str(row.get("closing_date_raw", "")).strip()
        functional_area = str(row.get("functional_area", "")).strip()
        description_type = str(row.get("description_type", "")).strip()
        advert_image_urls = str(row.get("advert_image_urls", "[]")).strip()
        ocr_text_raw = str(row.get("ocr_text_raw", "")).strip()
        ocr_status = str(row.get("ocr_status", "")).strip()
        ocr_confidence = str(row.get("ocr_confidence", "-1.0")).strip()
        source_platform = str(row.get("source_platform", row.get("source_hostname", ""))).strip()
        source_url = str(row.get("source_url", "")).strip()
        # Support both old 'canonical_url' and new 'final_url'
        canonical_url = str(row.get("canonical_url", row.get("final_url", ""))).strip()
        collection_batch_id = str(row.get("collection_batch_id", "")).strip()
        scraped_at = str(row.get("scraped_at", "")).strip()
        extraction_status = str(row.get("extraction_status", "")).strip()
        # Support both old 'exclusion_reason' and new 'error_message'
        exclusion_reason = str(row.get("exclusion_reason", row.get("error_message", ""))).strip()
        # New schema fields (optional)
        extractor_name = str(row.get("extractor_name", "")).strip()
        extraction_method = str(row.get("extraction_method", "")).strip()
        manual_review_reason = str(row.get("manual_review_reason", "")).strip()

                # Requirements may be supplied directly by the extractor.
        # Fall back to qualifications_raw for older datasets.
        requirements_raw = str(
            row.get(
                "requirements_raw",
                row.get("qualifications_raw", "")
            )
        ).strip()

        qualifications_raw = str(
            row.get(
                "qualifications_raw",
                ""
            )
        ).strip()

        # Clean HTML fields
        clean_title = clean_html_text(job_title_raw)
        clean_company = clean_html_text(company_raw)
        clean_location = standardize_location(location_raw)
        clean_country = "Sri Lanka" if country.lower() in ["sri lanka", "lk", "srilanka", ""] else country

        # Clean Description HTML and OCR separately
        clean_desc_html = clean_html_text(job_description_raw)

        print(
            f"\nDEBUG JOB: {job_id}"
            f"\n  title={clean_title}"
            f"\n  description_type={description_type}"
            f"\n  raw_desc_length={len(job_description_raw)}"
            f"\n  clean_desc_length={len(clean_desc_html)}"
            f"\n  extraction_status={extraction_status}"
        )
        
        clean_ocr_text_val = clean_ocr_text(ocr_text_raw)

        # Clean requirements separately so the final CSV has
        # a dedicated requirements field.
        clean_requirements = clean_html_text(
            requirements_raw
        )

        # Backward-compatible fallback for old raw datasets.
        if not clean_requirements:
            clean_requirements = clean_html_text(
                qualifications_raw
            )

        # Standardize dates
        clean_posted_date = parse_date_to_iso(listing_posted_date_raw)
        clean_closing_date = parse_date_to_iso(closing_date_raw)

        # Skip future publication dates
        if clean_posted_date and is_date_in_future(clean_posted_date):
            filtered_future_date += 1
            extraction_status = "excluded"
            exclusion_reason = f"Future publication date: {clean_posted_date}"
        
        # Apply filters for clean title length
        if len(clean_title) < 3 and extraction_status != "excluded":
            filtered_short_title += 1
            extraction_status = "excluded"
            exclusion_reason = "Short job title (< 3 characters)"

        # Apply IT relevance classifier filter
        if extraction_status != "excluded":
            is_it, is_ambig, reason = classifier.evaluate_title(clean_title)
            if not is_it:
                filtered_non_it += 1
                extraction_status = "excluded"
                exclusion_reason = reason
            elif is_ambig:
                extraction_status = "manual_review"
                manual_review_reason = reason

        # Construct final clean description based on description_type
        final_description = ""
        if description_type in ("html_text", "jsonld"):
            final_description = clean_desc_html
        elif description_type == "image":
            if ocr_status == "success":
                final_description = clean_ocr_text_val
            else:
                try:
                    img_list = json.loads(advert_image_urls)
                    img_ref = img_list[0] if img_list else source_url
                except Exception:
                    img_ref = source_url
                final_description = (
                    f"Job advertisement flyer image: {img_ref}. "
                    "(Note: The actual job description is embedded in this image flyer. "
                    f"OCR status: {ocr_status}. Direct plain text not extracted.)"
                )
        elif description_type == "hybrid":
            if ocr_status == "success":
                final_description = f"{clean_desc_html} \n\n--- OCR Text ---\n{clean_ocr_text_val}"
            else:
                final_description = clean_desc_html
        else:
            final_description = "Job description missing from source website."

        # Description length constraint (only apply to text-based ads)
        if description_type in ("html_text", "jsonld") and len(final_description) < 100 and extraction_status != "excluded":
            filtered_short_desc += 1
            extraction_status = "excluded"
            exclusion_reason = "Short text description (< 100 characters)"

        # Save record
        cleaned_records.append({
            "job_id": job_id,
            "source_job_id": source_job_id,
            "job_title_raw": clean_title,
            "company_raw": clean_company,
            "country": clean_country,
            "location_raw": clean_location,
            "job_description_raw": job_description_raw,
            "job_description_clean": final_description,
            "listing_posted_date_raw": clean_posted_date,
            "closing_date_raw": clean_closing_date,
            "requirements_raw": clean_requirements,
            "functional_area": functional_area,
            "description_type": description_type,
            "advert_image_urls": advert_image_urls,
            "ocr_text_raw": ocr_text_raw,
            "ocr_status": ocr_status,
            "ocr_confidence": ocr_confidence,
            "source_platform": source_platform,
            "source_url": source_url,
            "canonical_url": canonical_url,
            "collection_batch_id": collection_batch_id,
            "scraped_at": scraped_at,
            "extraction_status": extraction_status,
            "exclusion_reason": exclusion_reason
        })

    if not cleaned_records:
        headers_schema = [
            "job_id", "source_job_id", "job_title_raw", "company_raw", "country", "location_raw",
            "job_description_raw", "job_description_clean", "listing_posted_date_raw", "closing_date_raw",
            "functional_area", "description_type", "advert_image_urls", "ocr_text_raw", "ocr_status",
            "ocr_confidence", "source_platform", "source_url", "canonical_url", "collection_batch_id",
            "scraped_at", "extraction_status", "exclusion_reason", "requirements_raw"
        ]
        return pd.DataFrame(columns=headers_schema), pd.DataFrame(), {}

    df_processed = pd.DataFrame(cleaned_records)

    # Deduplication Phase
    df_processed["status_order"] = df_processed["extraction_status"].map(
        {"success": 0, "partial": 1, "excluded": 2, "failed": 3}
    )
    df_processed = df_processed.sort_values(by=["status_order", "scraped_at"], ascending=[True, False])

    initial_len = len(df_processed)

    # Deduplicate Step 1: source_job_id
    has_source_id = df_processed["source_job_id"] != ""
    df_with_id = df_processed[has_source_id].drop_duplicates(subset=["source_job_id"], keep="first")
    df_no_id = df_processed[~has_source_id]

    df_dedup = pd.concat([df_with_id, df_no_id], ignore_index=True)
    dedup_step1_removed = initial_len - len(df_dedup)

    # Deduplicate Step 2: canonical_url
    step2_len = len(df_dedup)
    has_canonical = df_dedup["canonical_url"] != ""
    df_with_canonical = df_dedup[has_canonical].drop_duplicates(subset=["canonical_url"], keep="first")
    df_no_canonical = df_dedup[~has_canonical]

    df_dedup = pd.concat([df_with_canonical, df_no_canonical], ignore_index=True)
    dedup_step2_removed = step2_len - len(df_dedup)

    # Deduplicate Step 3: Title, Company, and Clean Description (fallback)
    step3_len = len(df_dedup)
    df_dedup = df_dedup.drop_duplicates(subset=["job_title_raw", "company_raw", "job_description_clean"], keep="first")
    dedup_step3_removed = step3_len - len(df_dedup)

    # Remove status ordering helper column
    df_dedup = df_dedup.drop(columns=["status_order"])

    # Export Final Team-Required Dataset (10 columns only, filtered to non-excluded jobs)
    df_team = df_dedup[df_dedup["extraction_status"] != "excluded"].copy()
    
    # Rename columns to match the team's standard schema:
    df_team = df_team.rename(columns={
        "company_raw": "company",
        "job_description_clean": "job_description",
        "requirements_raw": "requirements",
        "listing_posted_date_raw": "posted_date",
        "closing_date_raw": "closing_date"
    })

    team_columns = [
        "job_id", "job_title_raw", "company", "country", "location_raw",
        "job_description", "posted_date", "closing_date", "source_platform", "source_url", "scraped_at", "requirements"
    ]
    
    # Ensure team_columns exist or create empty
    for c in team_columns:
        if c not in df_team.columns:
            df_team[c] = ""
            
    df_team = df_team[team_columns]

    stats = {
        "total_raw_records": total_raw_records,
        "filtered_short_title": filtered_short_title,
        "filtered_short_desc": filtered_short_desc,
        "filtered_future_date": filtered_future_date,
        "filtered_non_it": filtered_non_it,
        "dedup_step1_removed": dedup_step1_removed,
        "dedup_step2_removed": dedup_step2_removed,
        "dedup_step3_removed": dedup_step3_removed,
        "final_internal_records": len(df_dedup),
        "final_team_records": len(df_team)
    }

    return df_dedup, df_team, stats

# ==========================================
# CLI Main Execution
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="Academic Topjobs.lk Data Cleaning Pipeline")
    parser.add_argument("--batch-id", type=str, default=None, help="Process a specific batch ID instead of all batches")
    args = parser.parse_args()

    current_dir = pathlib.Path(__file__).resolve().parent
    project_root = current_dir.parent.parent
    batches_dir = project_root / "data" / "raw" / "batches"
    processed_dir = project_root / "data" / "processed"
    processed_internal_csv = processed_dir / "jobs_clean_internal.csv"
    processed_team_csv = processed_dir / "jobs_clean.csv"

    processed_dir.mkdir(parents=True, exist_ok=True)

    print("Executing Cleaning Module...")

    if not batches_dir.exists():
        print(f"Error: Batches directory {batches_dir} does not exist. Please run scraper first.")
        sys.exit(1)

    raw_files = []
    if args.batch_id:
        batch_file = batches_dir / f"jobs_raw_{args.batch_id}.csv"
        if batch_file.exists():
            raw_files.append(batch_file)
        else:
            print(f"Error: Batch file {batch_file} not found.")
            sys.exit(1)
    else:
        raw_files = list(batches_dir.glob("jobs_raw_*.csv"))

    if not raw_files:
        print("No raw batch files found to clean.")
        sys.exit(0)

    print(f"Loading {len(raw_files)} raw batch file(s) for cleaning...")
    dfs = []
    for f in raw_files:
        try:
            df_temp = pd.read_csv(f, dtype=str).fillna("")
            dfs.append(df_temp)
        except Exception as e:
            print(f"  Error reading {f.name}: {e}")

    if not dfs:
        print("No data loaded. Exiting.")
        sys.exit(1)

    df_raw = pd.concat(dfs, ignore_index=True)
    
    # Run the cleaning API pipeline function
    df_internal, df_team, stats = clean_raw_dataframe(df_raw)

    # Save outputs
    df_internal.to_csv(processed_internal_csv, index=False, encoding="utf-8")
    print(f"Richer internal dataset saved to: {processed_internal_csv}")
    
    df_team.to_csv(processed_team_csv, index=False, encoding="utf-8")
    print(f"Final team-required dataset saved to: {processed_team_csv}")

    print("\n--- Cleaning Pipeline Summary ---")
    print(f"Total raw records input : {stats.get('total_raw_records', 0)}")
    print(f"Removed - Short Title   : {stats.get('filtered_short_title', 0)}")
    print(f"Removed - Short Desc    : {stats.get('filtered_short_desc', 0)}")
    print(f"Removed - Future Date   : {stats.get('filtered_future_date', 0)}")
    print(f"Removed - Non-IT Job    : {stats.get('filtered_non_it', 0)}")
    print(f"Deduplicated by Job ID  : {stats.get('dedup_step1_removed', 0)}")
    print(f"Deduplicated by URL     : {stats.get('dedup_step2_removed', 0)}")
    print(f"Deduplicated by Fallback: {stats.get('dedup_step3_removed', 0)}")
    print(f"Final internal dataset records : {stats.get('final_internal_records', 0)}")
    print(f"Final team-required records    : {stats.get('final_team_records', 0)}")

if __name__ == "__main__":
    main()
