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
        return "Remote Work"
    # Standardize common names
    cleaned = " ".join(loc_str.split()).strip()
    cleaned = re.sub(r"(?i),\s*sri\s*lanka", "", cleaned).strip()
    return cleaned if cleaned else "Remote Work"

# ==========================================
# Refactored Reusable API Function
# ==========================================

def clean_job_description_body(html_content):
    """Cleans job description HTML, preserving paragraph boundaries and linebreaks,
    while removing style/script tags and other boilerplate.
    """
    if not html_content or not isinstance(html_content, str):
        return ""
        
    if "<" not in html_content and ">" not in html_content:
        return html_content.strip()
        
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove unwanted tags
        for element in soup(["script", "style", "nav", "footer", "header", "iframe", "form"]):
            element.decompose()
            
        # Replace line-breaks, paragraphs, and list items with newline markers
        for br in soup.find_all("br"):
            br.replace_with("\n")
        for p in soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr"]):
            p.insert_before("\n")
            p.insert_after("\n")
        for li in soup.find_all("li"):
            li.insert_before("\n• ")
            li.insert_after("\n")
            
        text = soup.get_text()
        
        # Decode HTML entities
        import html as html_lib
        text = html_lib.unescape(text)
        
        # Clean whitespaces but preserve single newlines
        lines = []
        for line in text.split("\n"):
            cleaned_line = " ".join(line.split()).strip()
            if cleaned_line:
                lines.append(cleaned_line)
                
        return "\n".join(lines).strip()
    except Exception:
        import html as html_lib
        decoded = html_lib.unescape(html_content)
        decoded = re.sub(r"(?i)<br\s*/?>", "\n", decoded)
        decoded = re.sub(r"(?i)</?p>", "\n", decoded)
        decoded = re.sub(r"(?i)<li>", "\n• ", decoded)
        no_tags = re.sub(r"<[^>]*>", " ", decoded)
        return "\n".join(line.strip() for line in no_tags.split("\n") if line.strip())


def normalize_date_reproducible(raw_date_str, collected_at_str):
    """Converts absolute and relative date strings to YYYY-MM-DD using collected_at as baseline.

    Returns:
        (posting_date: str, method: str, status: str, warning: str)
    """
    if not raw_date_str or not isinstance(raw_date_str, str) or not raw_date_str.strip():
        return "", "", "failed", "Empty raw date"

    raw_date_str = raw_date_str.strip()
    
    try:
        if collected_at_str:
            base_dt = date_parser.parse(collected_at_str)
        else:
            base_dt = datetime.now(timezone.utc)
    except Exception:
        base_dt = datetime.now(timezone.utc)

    norm_str = raw_date_str.lower()
    
    # Relative checks
    days_ago = None
    if "today" in norm_str:
        days_ago = 0
    elif "yesterday" in norm_str:
        days_ago = 1
    elif "day" in norm_str:
        match = re.search(r"(\d+)\s+day", norm_str)
        if match:
            days_ago = int(match.group(1))
    elif "week" in norm_str:
        match = re.search(r"(\d+)\s+week", norm_str)
        if match:
            days_ago = int(match.group(1)) * 7
        else:
            if "a week" in norm_str or "one week" in norm_str:
                days_ago = 7
    elif "month" in norm_str:
        match = re.search(r"(\d+)\s+month", norm_str)
        if match:
            days_ago = int(match.group(1)) * 30

    if days_ago is not None:
        from datetime import timedelta
        target_dt = base_dt - timedelta(days=days_ago)
        return target_dt.strftime("%Y-%m-%d"), "relative", "success", ""

    # Absolute parser
    try:
        parsed_dt = date_parser.parse(raw_date_str)
        return parsed_dt.strftime("%Y-%m-%d"), "absolute", "success", ""
    except Exception as e:
        return "", "failed", "failed", f"Failed to parse absolute date: {e}"


# ==========================================
# Refactored Reusable API Function
# ==========================================

def clean_raw_dataframe(df_raw):
    """Applies multi-stage cleaning, IT job filters, and deduplication to a raw job DataFrame.
    
    Returns:
        df_internal (pd.DataFrame): Rich internal dataset with extended audit columns.
        df_team (pd.DataFrame): Final team-required dataset with 10 columns.
        stats (dict): Performance counters and deduplication metrics.
    """
    total_raw_records = len(df_raw)
    cleaned_records = []
    
    classifier = ITClassifier()
    
    # Counter statistics
    filtered_future_date = 0
    filtered_short_desc = 0
    filtered_short_title = 0
    filtered_non_it = 0

    for idx, row in df_raw.iterrows():
        # Extracted values from row
        job_id = str(row.get("job_id", "")).strip()
        source_job_id = str(row.get("source_job_id", "")).strip()
        job_title_raw = str(row.get("job_title_raw", "")).strip()
        company_raw = str(row.get("company_raw", "")).strip()
        country = str(row.get("country", row.get("country_raw", "Sri Lanka"))).strip()
        location_raw = str(row.get("location_raw", "")).strip()
        job_description_raw = str(row.get("job_description_raw", "")).strip()
        posted_date_raw = str(row.get("posted_date_raw", row.get("listing_posted_date_raw", ""))).strip()
        closing_date_raw = str(row.get("closing_date_raw", "")).strip()
        functional_area = str(row.get("functional_area", "")).strip()
        description_type = str(row.get("description_type", "")).strip()
        advert_image_urls = str(row.get("advert_image_urls", "[]")).strip()
        ocr_text_raw = str(row.get("ocr_text_raw", "")).strip()
        ocr_status = str(row.get("ocr_status", "not_required")).strip()
        ocr_confidence = str(row.get("ocr_confidence", "-1.0")).strip()
        source_platform = str(row.get("source_platform", row.get("source_hostname", ""))).strip()
        source_url = str(row.get("source_url", "")).strip()
        final_url = str(row.get("final_url", row.get("canonical_url", ""))).strip()
        collection_batch_id = str(row.get("collection_batch_id", "")).strip()
        scraped_at = str(row.get("scraped_at", "")).strip()
        extraction_status = str(row.get("extraction_status", "")).strip()
        error_message = str(row.get("error_message", row.get("exclusion_reason", ""))).strip()
        
        # New model audit fields
        fetch_method = str(row.get("fetch_method", "http")).strip()
        rendering_used = str(row.get("rendering_used", "False")).strip()
        failure_reason = str(row.get("failure_reason", "")).strip()
        field_provenance = str(row.get("field_provenance", "{}")).strip()
        classification_status = str(row.get("classification_status", "insufficient_data")).strip()
        classification_explanation = str(row.get("classification_explanation", "{}")).strip()
        classification_override = str(row.get("classification_override", "{}")).strip()
        manual_review_reason = str(row.get("manual_review_reason", "")).strip()

        # Clean HTML fields
        clean_title = clean_html_text(job_title_raw)
        clean_company = clean_html_text(company_raw)
        clean_location = standardize_location(location_raw)
        clean_country = "Sri Lanka" if country.lower() in ["sri lanka", "lk", "srilanka", ""] else country

        # Clean Description using paragraph-preserving logic
        clean_desc_html = clean_job_description_body(job_description_raw)
        clean_ocr_text_val = clean_ocr_text(ocr_text_raw)

        # Standarize dates using collected_at as baseline
        clean_posted_date, date_conv_method, date_parse_status, date_parse_warning = normalize_date_reproducible(
            posted_date_raw, scraped_at
        )
        clean_closing_date, _, _, _ = normalize_date_reproducible(closing_date_raw, scraped_at)

        # Skip future publication dates
        if clean_posted_date and is_date_in_future(clean_posted_date):
            filtered_future_date += 1
            extraction_status = "excluded"
            error_message = f"Future publication date: {clean_posted_date}"
        
        # Apply filters for clean title length
        if len(clean_title) < 3 and extraction_status != "excluded":
            filtered_short_title += 1
            extraction_status = "excluded"
            error_message = "Short job title (< 3 characters)"

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
                final_description = f"{clean_desc_html}\n\n--- OCR Text ---\n{clean_ocr_text_val}"
            else:
                final_description = clean_desc_html
        else:
            final_description = "Job description missing from source website."

        # Description length constraint (only apply to text-based ads)
        if description_type in ("html_text", "jsonld") and len(final_description) < 100 and extraction_status != "excluded":
            filtered_short_desc += 1
            extraction_status = "excluded"
            error_message = "Short text description (< 100 characters)"

        # Multi-signal IT Classification & Override Audit checks
        # Support override dictionary parsing
        has_override = False
        override_status = ""
        override_reason = ""
        try:
            override_data = json.loads(classification_override)
            if isinstance(override_data, dict) and override_data.get("new_status"):
                has_override = True
                override_status = override_data["new_status"]
                override_reason = override_data.get("reason", "Manual Override")
        except Exception:
            pass

        if extraction_status != "excluded":
            # Re-run classifier to update signals/explanation
            res_class = classifier.classify(
                title=clean_title,
                category=functional_area,
                skills=row.get("skills_raw", ""),
                description=final_description
            )
            
            classification_status = res_class["status"]
            classification_explanation = json.dumps(res_class["explanation"])

            if has_override:
                # Apply manual override
                classification_status = override_status
                manual_review_reason = f"Overridden to {override_status}: {override_reason}"
            
            # Apply exclusion filter based on classification status
            if classification_status == "non_it":
                filtered_non_it += 1
                extraction_status = "excluded"
                error_message = "Non-IT role: classified as non_it"
            elif classification_status == "ambiguous":
                extraction_status = "manual_review"
                manual_review_reason = res_class["explanation"].get("manual_review_reason", "Ambiguous IT role classification")

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
            "functional_area": functional_area,
            "description_type": description_type,
            "advert_image_urls": advert_image_urls,
            "ocr_text_raw": ocr_text_raw,
            "ocr_status": ocr_status,
            "ocr_confidence": ocr_confidence,
            "source_platform": source_platform,
            "source_url": source_url,
            "canonical_url": final_url,
            "collection_batch_id": collection_batch_id,
            "scraped_at": scraped_at,
            "extraction_status": extraction_status,
            "exclusion_reason": error_message,
            
            # Extended audit fields
            "fetch_method": fetch_method,
            "rendering_used": rendering_used,
            "failure_reason": failure_reason,
            "date_conversion_method": date_conv_method,
            "date_parse_status": date_parse_status,
            "date_parse_warning": date_parse_warning,
            "field_provenance": field_provenance,
            "classification_status": classification_status,
            "classification_explanation": classification_explanation,
            "classification_override": classification_override,
            "manual_review_reason": manual_review_reason
        })

    if not cleaned_records:
        headers_schema = [
            "job_id", "source_job_id", "job_title_raw", "company_raw", "country", "location_raw",
            "job_description_raw", "job_description_clean", "listing_posted_date_raw", "closing_date_raw",
            "functional_area", "description_type", "advert_image_urls", "ocr_text_raw", "ocr_status",
            "ocr_confidence", "source_platform", "source_url", "canonical_url", "collection_batch_id",
            "scraped_at", "extraction_status", "exclusion_reason",
            "fetch_method", "rendering_used", "failure_reason", "date_conversion_method",
            "date_parse_status", "date_parse_warning", "field_provenance", "classification_status",
            "classification_explanation", "classification_override", "manual_review_reason"
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
        "listing_posted_date_raw": "posted_date"
    })

    team_columns = [
        "job_id", "job_title_raw", "company", "country", "location_raw",
        "job_description", "posted_date", "source_platform", "source_url", "scraped_at"
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