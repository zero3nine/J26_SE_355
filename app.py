"""
IT Job Advertisement Data Collector — Streamlit Frontend

Multi-site academic prototype for collecting and preparing IT job-advertisement data
from multiple publicly accessible job portals.
"""

import os
import sys
import pathlib
import json
import re
import urllib.parse
from datetime import datetime, timezone
import pandas as pd
import streamlit as st

# Add project root to system path
current_dir = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from src.security.url_validator import validate_url, is_approved_domain
from src.scraping.service import run_collection_pipeline
from src.scraping.models import RAW_SCHEMA_COLUMNS
from src.cleaning.clean_jobs import clean_raw_dataframe
from src.cleaning.validate_jobs import run_validation_pipeline

# ==========================================
# Streamlit App Configurations
# ==========================================

st.set_page_config(
    page_title="IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide"
)

# Initialize Session State Variables
if "valid_urls" not in st.session_state:
    st.session_state.valid_urls = []
if "rejected_urls" not in st.session_state:
    st.session_state.rejected_urls = {}
if "raw_df" not in st.session_state:
    st.session_state.raw_df = pd.DataFrame()
if "clean_df" not in st.session_state:
    st.session_state.clean_df = pd.DataFrame()
if "clean_internal_df" not in st.session_state:
    st.session_state.clean_internal_df = pd.DataFrame()
if "failures_df" not in st.session_state:
    st.session_state.failures_df = pd.DataFrame()
if "quality_report" not in st.session_state:
    st.session_state.quality_report = ""
if "collection_batch_id" not in st.session_state:
    st.session_state.collection_batch_id = ""
if "scraping_completed" not in st.session_state:
    st.session_state.scraping_completed = False
if "cleaning_completed" not in st.session_state:
    st.session_state.cleaning_completed = False
if "cleaning_stats" not in st.session_state:
    st.session_state.cleaning_stats = {}
if "scraping_confirmed" not in st.session_state:
    st.session_state.scraping_confirmed = False

# ==========================================
# UI Layout Header
# ==========================================

st.title("IT Job Advertisement Data Collector")
st.caption("Multi-site academic prototype for collecting and preparing IT job-advertisement data")

st.info(
    "⚠️ **Notice**: Only submit publicly accessible and permitted job page URLs. "
    "This application does not bypass login, CAPTCHA, rate limits, or access restrictions. "
    "Unknown websites are processed via JSON-LD or generic HTML extraction."
)

# Metric Cards Panel
cols = st.columns(4)

attempted_metric = len(st.session_state.valid_urls)
scraped_metric = 0
failed_metric = 0
clean_metric = len(st.session_state.clean_df)

if not st.session_state.raw_df.empty:
    if "extraction_status" in st.session_state.raw_df.columns:
        scraped_metric = sum(st.session_state.raw_df["extraction_status"].isin(["success", "partial"]))
        failed_metric = sum(~st.session_state.raw_df["extraction_status"].isin(["success", "partial", "manual_review"]))

# Add rejected URLs to failed/invalid count
failed_metric += len(st.session_state.rejected_urls)

cols[0].metric("Submitted URLs", attempted_metric)
cols[1].metric("Successfully Scraped", scraped_metric)
cols[2].metric("Failed", failed_metric)
cols[3].metric("Clean Records", clean_metric)

# ==========================================
# Tab Views
# ==========================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. Collect Data",
    "2. Raw Data",
    "3. Clean Data",
    "4. Quality Report",
    "5. Failure Logs"
])

# ------------------------------------------
# Tab 1: Collect Data
# ------------------------------------------
with tab1:
    st.subheader("Submit target vacancy URLs")

    url_input = st.text_area(
        "Enter job detail URLs OR job portal/listing search URLs (one per line):",
        placeholder=(
            "https://www.itpro.lk/jobs/quality-assurance/\n"
            "https://www.topjobs.lk/employer/JobAdvertismentServlet?rid=0&ac=0000000375&jc=0001540527...\n"
            "https://www.example-jobs.com/job/12345"
        ),
        height=200
    )

    save_to_file = st.checkbox("Save submitted URLs to urls.txt", value=False)

    if st.button("Scrape submitted URLs"):
        # Split URLs and validate
        lines = [line.strip() for line in url_input.split("\n") if line.strip() and not line.strip().startswith("#")]

        valid = []
        rejected = {}

        for url in lines:
            is_valid, reason = validate_url(url)
            if is_valid:
                valid.append(url)
            else:
                rejected[url] = reason

        # Deduplicate
        valid = list(dict.fromkeys(valid))

        # Prototype Limit Check
        if len(valid) > 20:
            truncated = valid[20:]
            valid = valid[:20]
            for u in truncated:
                rejected[u] = "Prototype limit exceeded (maximum 20 URLs allowed per batch)."

        # Store in session state
        st.session_state.valid_urls = valid
        st.session_state.rejected_urls = rejected

        if not valid:
            st.error("No valid URLs submitted. Please correct the links and try again.")
            if rejected:
                st.subheader("Rejected URLs & Reasons:")
                for url, reason in rejected.items():
                    st.warning(f"🔴 `{url[:80]}...` : {reason}")
        else:
            # Show warnings for rejected items before start
            if rejected:
                st.subheader("Rejected URLs (skipped from run):")
                for url, reason in rejected.items():
                    st.warning(f"🔴 `{url[:80]}...` : {reason}")

            # Show domain info
            hostnames = set()
            for u in valid:
                try:
                    h = urllib.parse.urlparse(u).hostname
                    if h:
                        hostnames.add(h)
                except Exception:
                    pass

            approved = [h for h in hostnames if is_approved_domain(h)]
            unapproved = [h for h in hostnames if not is_approved_domain(h)]

            if approved:
                st.success(f"Reviewed domains: {', '.join(approved)}")
            if unapproved:
                st.info(
                    f"Unreviewed domains (will use JSON-LD/generic extraction): {', '.join(unapproved)}. "
                    "Add to `config/approved_domains.txt` after review."
                )

            # Require confirmation for >10 URLs
            if len(valid) > 10 and not st.session_state.scraping_confirmed:
                st.session_state.scraping_confirmed = True
                st.warning(f"You have submitted {len(valid)} valid URLs. Rate limits apply.")
                st.info("Click the button again to confirm and start sequential scraping.")
            else:
                st.session_state.scraping_confirmed = False
                # Run Scraper
                st.info("Starting multi-site collection pipeline...")
                progress_bar = st.progress(0.0)
                status_text = st.empty()

                def progress_cb(current, total, text):
                    ratio = min(current / total, 1.0) if total > 0 else 0.0
                    progress_bar.progress(ratio)
                    status_text.text(f"Status: {text} (Processed {current} of {total})")

                # Execute new multi-site pipeline
                raw_df, batch_id = run_collection_pipeline(
                    valid,
                    progress_callback=progress_cb,
                )

                # Update Session State
                st.session_state.raw_df = raw_df
                st.session_state.collection_batch_id = batch_id
                st.session_state.scraping_completed = True

                # Save to urls.txt if checkbox enabled
                if save_to_file:
                    urls_path = current_dir / "urls.txt"
                    try:
                        with open(urls_path, "w", encoding="utf-8") as f:
                            for url in valid:
                                f.write(f"{url}\n")
                        st.success(f"Saved {len(valid)} unique URLs to {urls_path.name}")
                    except Exception as e:
                        st.error(f"Failed to update urls.txt: {e}")

                st.success(f"Collection completed! Raw batch file saved as jobs_raw_{batch_id}.csv")
                st.info("Navigate to the 'Raw Data' tab to inspect the scraped records.")
                st.rerun()

# ------------------------------------------
# Tab 2: Raw Data
# ------------------------------------------
with tab2:
    if st.session_state.raw_df.empty:
        st.info("No raw data collected in session. Please run the collection pipeline under 'Collect Data' tab.")
    else:
        st.subheader("Raw collected data view")
        st.write(f"Total attempted rows: {len(st.session_state.raw_df)}")

        # Filters and Search
        col1, col2, col3 = st.columns(3)
        search_query = col1.text_input("Search by job title / company:", "")

        companies_col = "company_raw" if "company_raw" in st.session_state.raw_df.columns else None
        if companies_col:
            companies = ["All"] + list(st.session_state.raw_df[companies_col].unique())
            comp_filter = col2.selectbox("Filter by company:", companies)
        else:
            comp_filter = "All"

        # Extractor filter (new multi-site feature)
        if "extractor_name" in st.session_state.raw_df.columns:
            extractors = ["All"] + list(st.session_state.raw_df["extractor_name"].unique())
            ext_filter = col3.selectbox("Filter by extractor:", extractors)
        elif "description_type" in st.session_state.raw_df.columns:
            desc_types = ["All"] + list(st.session_state.raw_df["description_type"].unique())
            ext_filter = col3.selectbox("Filter by description type:", desc_types)
        else:
            ext_filter = "All"

        # Apply filters
        df_filtered = st.session_state.raw_df.copy()
        if search_query:
            title_col = "job_title_raw" if "job_title_raw" in df_filtered.columns else None
            company_col = companies_col
            if title_col and company_col:
                df_filtered = df_filtered[
                    df_filtered[title_col].str.contains(search_query, case=False, na=False) |
                    df_filtered[company_col].str.contains(search_query, case=False, na=False)
                ]

        if comp_filter != "All" and companies_col:
            df_filtered = df_filtered[df_filtered[companies_col] == comp_filter]
        if ext_filter != "All":
            if "extractor_name" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["extractor_name"] == ext_filter]
            elif "description_type" in df_filtered.columns:
                df_filtered = df_filtered[df_filtered["description_type"] == ext_filter]

        # Display table with shortened description preview
        df_display = df_filtered.copy()
        if "job_description_raw" in df_display.columns:
            df_display["job_description_raw"] = df_display["job_description_raw"].apply(
                lambda x: x[:100] + "..." if len(str(x)) > 100 else str(x)
            )

        # Select display columns based on available schema
        display_cols = [c for c in [
            "job_id", "job_title_raw", "company_raw", "source_hostname",
            "extractor_name", "extraction_status", "extraction_confidence",
            "description_type", "source_url"
        ] if c in df_display.columns]

        if display_cols:
            st.dataframe(
                df_display[display_cols],
                column_config={
                    "source_url": st.column_config.LinkColumn("Source URL"),
                },
                hide_index=True
            )
        else:
            st.dataframe(df_display, hide_index=True)

        # Inspect full record
        if not df_filtered.empty and "job_title_raw" in df_filtered.columns:
            st.write("---")
            st.subheader("Inspect raw job description")
            job_options = {}
            for idx, row in df_filtered.iterrows():
                title = row.get("job_title_raw", "Unknown")
                company = row.get("company_raw", "")
                jid = row.get("job_id", "")[:8]
                label = f"{title} ({company}) - ID: {jid}"
                job_options[label] = idx

            selected_job_name = st.selectbox("Select record to inspect details:", list(job_options.keys()))
            selected_idx = job_options[selected_job_name]

            selected_row = df_filtered.loc[selected_idx]
            st.write(f"**Job title**: {selected_row.get('job_title_raw', '')}")
            st.write(f"**Company**: {selected_row.get('company_raw', '')}")
            st.write(f"**Source hostname**: {selected_row.get('source_hostname', '')}")
            st.write(f"**Extractor**: {selected_row.get('extractor_name', '')} ({selected_row.get('extraction_method', '')})")
            st.write(f"**Status**: {selected_row.get('extraction_status', '')} (confidence: {selected_row.get('extraction_confidence', '')})")
            st.write(f"**Description type**: {selected_row.get('description_type', '')}")

            if "job_description_raw" in selected_row:
                st.text_area("Raw description content:", value=str(selected_row["job_description_raw"]), height=200, disabled=True)

        # Download Raw CSV
        csv_raw_data = st.session_state.raw_df.to_csv(index=False, encoding="utf-8")
        batch_id = st.session_state.collection_batch_id
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        st.download_button(
            label="Download raw CSV",
            data=csv_raw_data,
            file_name=f"jobs_raw_{date_str}_{batch_id}.csv",
            mime="text/csv"
        )

# ------------------------------------------
# Tab 3: Clean Data
# ------------------------------------------
with tab3:
    if st.session_state.raw_df.empty:
        st.info("No raw data to clean. Please collect raw records first.")
    else:
        st.subheader("Data cleaning pipeline")

        if st.button("Clean data"):
            with st.spinner("Executing cleaning, entity decoding, and deduplication logic..."):
                # Call backend clean API
                df_internal, df_team, stats = clean_raw_dataframe(st.session_state.raw_df)

                # Persist batch outputs to file system
                batch_id = st.session_state.collection_batch_id
                processed_batches_dir = current_dir / "data" / "processed" / "batches"
                processed_batches_dir.mkdir(parents=True, exist_ok=True)

                internal_batch_file = processed_batches_dir / f"jobs_clean_internal_{batch_id}.csv"
                team_batch_file = processed_batches_dir / f"jobs_clean_{batch_id}.csv"

                df_internal.to_csv(internal_batch_file, index=False, encoding="utf-8")
                df_team.to_csv(team_batch_file, index=False, encoding="utf-8")

                # Also overwrite global processed file for general checks
                df_team.to_csv(current_dir / "data" / "processed" / "jobs_clean.csv", index=False, encoding="utf-8")
                df_internal.to_csv(current_dir / "data" / "processed" / "jobs_clean_internal.csv", index=False, encoding="utf-8")

                # Store in session state
                st.session_state.clean_internal_df = df_internal
                st.session_state.clean_df = df_team
                st.session_state.cleaning_stats = stats
                st.session_state.cleaning_completed = True

            st.success("Cleaning completed successfully! Clean datasets saved to processed directory.")
            st.rerun()

        if st.session_state.cleaning_completed:
            stats = st.session_state.cleaning_stats

            # Display stats panels
            st.subheader("Cleaning pipeline statistics summary")
            stat_cols = st.columns(4)
            stat_cols[0].write(f"**Total raw input**: {stats.get('total_raw_records', 0)}")
            stat_cols[0].write(f"**Short title filter**: {stats.get('filtered_short_title', 0)} removed")

            stat_cols[1].write(f"**Short desc filter**: {stats.get('filtered_short_desc', 0)} removed")
            stat_cols[1].write(f"**Future date filter**: {stats.get('filtered_future_date', 0)} removed")

            stat_cols[2].write(f"**Deduplicated by job ID**: {stats.get('dedup_step1_removed', 0)} removed")
            stat_cols[2].write(f"**Deduplicated by URL**: {stats.get('dedup_step2_removed', 0)} removed")

            stat_cols[3].write(f"**Internal clean records**: {stats.get('final_internal_records', 0)}")
            stat_cols[3].write(f"**Final team records**: {stats.get('final_team_records', 0)}")

            st.subheader("Cleaned dataset (team schema format — 10 columns)")
            st.dataframe(st.session_state.clean_df, hide_index=True)

            # Download Clean CSV
            csv_clean_data = st.session_state.clean_df.to_csv(index=False, encoding="utf-8")
            batch_id = st.session_state.collection_batch_id
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            st.download_button(
                label="Download clean CSV",
                data=csv_clean_data,
                file_name=f"jobs_clean_{date_str}_{batch_id}.csv",
                mime="text/csv"
            )

# ------------------------------------------
# Tab 4: Quality Report
# ------------------------------------------
with tab4:
    if not st.session_state.cleaning_completed:
        st.info("Please execute the data cleaning step on the 'Clean Data' tab to compile the quality report.")
    else:
        st.subheader("Data quality assessment")

        # Run validation pipeline dynamically
        report_runs, metrics, report_md = run_validation_pipeline(
            st.session_state.raw_df,
            st.session_state.clean_internal_df,
            st.session_state.clean_df
        )

        # Persist report to file system
        reports_dir = current_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_file = reports_dir / f"data_quality_report_{st.session_state.collection_batch_id}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_md)

        # Display checks list
        st.subheader("Pipeline validation status checks")
        for check in report_runs:
            status = check["status"]
            icon = "✅ [PASS]" if status == "PASS" else ("⚠️ [WARNING]" if status == "WARNING" else "❌ [FAIL]")
            details = check["details"]
            st.write(f"**{icon}** - **{check['name']}**: {details}")

        st.write("---")

        # Display Markdown report preview
        st.subheader("Report content preview")
        st.markdown(report_md)

        # Download Markdown Quality Report
        batch_id = st.session_state.collection_batch_id
        st.download_button(
            label="Download quality report (Markdown)",
            data=report_md,
            file_name=f"jobs_quality_report_{batch_id}.md",
            mime="text/markdown"
        )

# ------------------------------------------
# Tab 5: Failure Logs
# ------------------------------------------
with tab5:
    st.subheader("Collection failures & exclusions log")

    # Compile failures and exclusions
    failures = []

    # 1. Invalid URL Inputs
    for url, reason in st.session_state.rejected_urls.items():
        failures.append({
            "url": url,
            "source_hostname": "",
            "extractor_name": "",
            "error_type": "Invalid URL Input",
            "error_message": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retryable": "No"
        })

    # 2. Raw collection failures
    if not st.session_state.raw_df.empty:
        status_col = "extraction_status" if "extraction_status" in st.session_state.raw_df.columns else None
        if status_col:
            failed_statuses = ["network_error", "blocked", "rate_limited",
                               "invalid_url", "parse_error", "unsupported", "not_a_job_page"]
            failed_raw = st.session_state.raw_df[
                st.session_state.raw_df[status_col].isin(failed_statuses)
            ]
            for idx, row in failed_raw.iterrows():
                failures.append({
                    "url": row.get("source_url", ""),
                    "source_hostname": row.get("source_hostname", ""),
                    "extractor_name": row.get("extractor_name", ""),
                    "error_type": row.get("error_type", row.get("extraction_status", "")),
                    "error_message": row.get("error_message", row.get("exclusion_reason", "Extraction failed")),
                    "timestamp": row.get("scraped_at", ""),
                    "retryable": "Yes" if row.get("extraction_status", "") in ("network_error", "rate_limited") else "No"
                })

    # 3. Manual review records
    if not st.session_state.raw_df.empty:
        if "extraction_status" in st.session_state.raw_df.columns:
            manual = st.session_state.raw_df[
                st.session_state.raw_df["extraction_status"] == "manual_review"
            ]
            for idx, row in manual.iterrows():
                failures.append({
                    "url": row.get("source_url", ""),
                    "source_hostname": row.get("source_hostname", ""),
                    "extractor_name": row.get("extractor_name", ""),
                    "error_type": "Manual Review Required",
                    "error_message": row.get("manual_review_reason", "Flagged for manual review"),
                    "timestamp": row.get("scraped_at", ""),
                    "retryable": "No"
                })

    # 4. Image advertisements awaiting OCR
    if st.session_state.cleaning_completed and not st.session_state.clean_internal_df.empty:
        ocr_col = "ocr_status" if "ocr_status" in st.session_state.clean_internal_df.columns else None
        desc_col = "description_type" if "description_type" in st.session_state.clean_internal_df.columns else None
        if ocr_col and desc_col:
            pending_ocr = st.session_state.clean_internal_df[
                (st.session_state.clean_internal_df[ocr_col] == "not_permitted") &
                (st.session_state.clean_internal_df[desc_col].isin(["image", "hybrid"]))
            ]
            for idx, row in pending_ocr.iterrows():
                failures.append({
                    "url": row.get("source_url", ""),
                    "source_hostname": row.get("source_hostname", row.get("source_platform", "")),
                    "extractor_name": row.get("extractor_name", ""),
                    "error_type": "Image advertisement awaiting OCR",
                    "error_message": f"OCR is disabled under unverified permissions. Image URLs: {row.get('advert_image_urls', '')}",
                    "timestamp": row.get("scraped_at", ""),
                    "retryable": "Yes"
                })

    if not failures:
        st.info("No logs, failures, or exclusions recorded in this run.")
    else:
        df_failures = pd.DataFrame(failures)
        st.dataframe(df_failures, hide_index=True)

        # Download Failures CSV
        csv_failures = df_failures.to_csv(index=False, encoding="utf-8")
        batch_id = st.session_state.collection_batch_id if st.session_state.collection_batch_id else "temp"
        st.download_button(
            label="Download failures log CSV",
            data=csv_failures,
            file_name=f"jobs_failures_{batch_id}.csv",
            mime="text/csv"
        )
