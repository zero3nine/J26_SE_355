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
import threading
import time

# Add project root to system path
current_dir = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from src.cleaning.clean_jobs import clean_raw_dataframe
from src.cleaning.validate_jobs import run_validation_pipeline
from src.roles.role_skill_analysis import classify_roles, build_role_skill_frequency_table
from src.security.url_validator import validate_url, is_approved_domain
from src.scraping.service import run_collection_pipeline
from src.scraping.models import RAW_SCHEMA_COLUMNS
from src.cleaning.clean_jobs import clean_raw_dataframe
from src.cleaning.validate_jobs import run_validation_pipeline
from theme import (
    THEME_CSS,
    render_header,
    render_ssrf_banner,
    render_kpis,
    render_custom_table,
    make_status_pill,
    make_link_icon,
    render_terminal,
    render_pipeline_funnel,
    render_validation_checklist
)

# ==========================================
# Streamlit App Configurations
# ==========================================

st.set_page_config(
    page_title="IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide"
)

# Inject custom dashboard CSS theme
st.markdown(THEME_CSS, unsafe_allow_html=True)

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
if "extraction_completed" not in st.session_state:
    st.session_state.extraction_completed = False
if "extracted_df" not in st.session_state:
    st.session_state.extracted_df = pd.DataFrame()
if "role_analysis_completed" not in st.session_state:
    st.session_state.role_analysis_completed = False
if "role_classified_df" not in st.session_state:
    st.session_state.role_classified_df = pd.DataFrame()
if "role_skill_freq_df" not in st.session_state:
    st.session_state.role_skill_freq_df = pd.DataFrame()

# ==========================================
# UI Layout Header
# ==========================================

st.markdown(render_header(), unsafe_allow_html=True)
st.markdown(render_ssrf_banner(), unsafe_allow_html=True)

# Calculate metrics for the session
attempted_metric = len(st.session_state.valid_urls)
scraped_metric = 0
failed_metric = 0
clean_metric = len(st.session_state.clean_df)
extracted_metric = len(st.session_state.extracted_df)

if not st.session_state.raw_df.empty:
    if "extraction_status" in st.session_state.raw_df.columns:
        scraped_metric = sum(st.session_state.raw_df["extraction_status"].isin(["success", "partial"]))
        failed_metric = sum(~st.session_state.raw_df["extraction_status"].isin(["success", "partial", "manual_review"]))

# Add rejected URLs to failed/invalid count
failed_metric += len(st.session_state.rejected_urls)

# Render customized telemetry cards
st.markdown(render_kpis(attempted_metric, scraped_metric, failed_metric, clean_metric), unsafe_allow_html=True)

# ==========================================
# Tab Views
# ==========================================

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "Collect Data",
    "Raw Data",
    "Clean Data",
    "Extract Skills",
    "Quality Report",
    "Failure Logs",
    "External Domains",
    "Manual Reviews",
    "Role-Skill Analysis"
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

    # Live URL line counter
    num_urls_detected = len([line.strip() for line in url_input.split("\n") if line.strip() and not line.strip().startswith("#")])
    st.markdown(f"<div style='text-align: right; font-size: 12px; color: #94A3B8; margin-top: -10px; margin-bottom: 12px;'>🔍 Detected <b>{num_urls_detected}</b> URL{'s' if num_urls_detected != 1 else ''} in input buffer</div>", unsafe_allow_html=True)

    save_to_file = st.checkbox("Save submitted URLs to urls.txt", value=False)

    # Render safety parameters grouped in a sleek card
    st.subheader("Run Configuration")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        target_valid = c1.slider("Target Valid IT Jobs", 5, 200, 50, help="Stop when this many valid IT jobs are collected.")
        max_requests = c2.slider("Maximum Requests Budget", 10, 500, 120, help="Absolute request cap.")
        max_time = c1.slider("Maximum Duration (seconds)", 30, 1800, 300, help="Elapsed time cap.")
        polite_delay = c2.slider("Polite Delay (seconds)", 0.5, 10.0, 2.0, step=0.5)
        fallback = c1.checkbox("Playwright Browser Fallback", value=False, help="Render JavaScript pages using Playwright on approved domains.")
        ocr = c2.checkbox("Run Advertisement Image OCR", value=False, help="Process flyer ads using local OCR.")

    # Scrape Trigger Action Area
    col_trigger, _ = st.columns([1, 3])
    with col_trigger:
        scrape_clicked = st.button("⚡ Scrape submitted URLs", use_container_width=True)
        
    if scrape_clicked and not st.session_state.get("scraping_active", False):
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
            # Check confirmation requirements for >10 URLs
            if len(valid) > 10 and not st.session_state.get("scraping_confirmed", False):
                st.session_state.scraping_confirmed = True
                st.warning(f"You have submitted {len(valid)} valid URLs. Rate limits apply.")
                st.info("Click the button again to confirm and start sequential scraping.")
            else:
                st.session_state.scraping_confirmed = False
                st.session_state.run_config = {
                    "target_valid": target_valid,
                    "max_requests": max_requests,
                    "max_time": max_time,
                    "polite_delay": polite_delay,
                    "fallback": fallback,
                    "ocr": ocr,
                    "save_to_file": save_to_file
                }
                st.session_state.scraping_active = True
                st.session_state.scraping_started = False
                st.session_state.scrape_logs = []  # Clear log history
                st.rerun()

    # Show warning for rejected items if any (and not actively scraping)
    if not st.session_state.get("scraping_active", False) and st.session_state.get("rejected_urls"):
        st.subheader("Rejected URLs (skipped from run):")
        for url, reason in st.session_state.rejected_urls.items():
            st.warning(f"🔴 `{url[:80]}...` : {reason}")

    # Active scraping execution
    if st.session_state.get("scraping_active", False):
        valid = st.session_state.valid_urls
        cfg = st.session_state.run_config

        if not st.session_state.get("scraping_started", False):
            # Show domain info once
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

            if "cancel_event" not in st.session_state:
                st.session_state.cancel_event = threading.Event()
            st.session_state.cancel_event.clear()

            st.session_state.crawl_progress = (0, len(valid), "Initializing...")
            st.session_state.crawl_thread_result = None
            st.session_state.scrape_logs = ["System status: Initializing scraping run..."]

            def run_thread(urls, target_val, max_req, max_t, delay, use_fallback, use_ocr, cancel_ev):
                try:
                    def progress_cb(current, total, text):
                        st.session_state.crawl_progress = (current, total, text)
                    def cancel_cb():
                        return cancel_ev.is_set()

                    df, b_id = run_collection_pipeline(
                        urls=urls,
                        target_valid_jobs=target_val,
                        max_requests=max_req,
                        max_time_seconds=max_t,
                        polite_delay=delay,
                        use_browser_fallback=use_fallback,
                        use_ocr=use_ocr,
                        progress_callback=progress_cb,
                        cancel_requested_cb=cancel_cb
                    )
                    st.session_state.crawl_thread_result = (df, b_id)
                except Exception as e:
                    st.session_state.crawl_thread_result = e

            t = threading.Thread(
                target=run_thread,
                args=(
                    valid, cfg["target_valid"], cfg["max_requests"], cfg["max_time"],
                    cfg["polite_delay"], cfg["fallback"], cfg["ocr"], st.session_state.cancel_event
                )
            )
            from streamlit.runtime.scriptrunner import add_script_run_ctx
            add_script_run_ctx(t)
            t.start()
            st.session_state.crawl_thread = t
            st.session_state.scraping_started = True
            st.rerun()

        # Render progress UI
        st.subheader("Data-Ops Collection Pipeline In Progress")
        
        # Track logging from callbacks safely
        if "scrape_logs" not in st.session_state:
            st.session_state.scrape_logs = []
            
        current, total, txt = st.session_state.crawl_progress
        ratio = min(current / total, 1.0) if total > 0 else 0.0
        
        # Capture logs if the progress string has changed
        if txt and (not st.session_state.scrape_logs or txt not in st.session_state.scrape_logs[-1]):
            t_stamp = datetime.now().strftime("%H:%M:%S")
            st.session_state.scrape_logs.append(f"[{t_stamp}] {txt}")

        col_pb, col_cancel = st.columns([4, 1])
        with col_pb:
            st.progress(ratio)
        with col_cancel:
            cancel_clicked = st.button("🔴 Cancel Crawl Run", use_container_width=True)
            
        if cancel_clicked:
            st.session_state.cancel_event.set()
            st.session_state.scrape_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Cancellation requested. Shutting down worker thread cleanly...")
            st.warning("Cancellation requested, waiting for pipeline thread to stop cleanly...")

        # Display monospace scrollable logs console
        st.markdown(render_terminal(st.session_state.scrape_logs), unsafe_allow_html=True)

        t = st.session_state.crawl_thread
        if t.is_alive():
            time.sleep(0.5)
            st.rerun()
        else:
            # Done!
            st.session_state.scraping_active = False
            st.session_state.scraping_started = False
            
            res = st.session_state.crawl_thread_result
            if isinstance(res, Exception):
                st.error(f"Scraping encountered an error: {res}")
            elif res is not None:
                raw_df, batch_id = res
                st.session_state.raw_df = raw_df
                st.session_state.collection_batch_id = batch_id
                st.session_state.scraping_completed = True
                st.success(f"Scraping run completed successfully. Batch ID: {batch_id}")
                
                if cfg["save_to_file"]:
                    urls_path = current_dir / "urls.txt"
                    try:
                        with open(urls_path, "w", encoding="utf-8") as f:
                            for url in valid:
                                f.write(f"{url}\n")
                    except Exception as e:
                        st.error(f"Failed to update urls.txt: {e}")

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
        st.markdown(f"<div style='font-size:12px; color:#94A3B8; margin-top:-10px; margin-bottom:16px;'>Session log contains <b>{len(st.session_state.raw_df)}</b> raw crawls. Use filters below to search.</div>", unsafe_allow_html=True)

        # Filters and Search Toolbar grouped in a card
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            search_query = col1.text_input("🔍 Search by title / company:", "")

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

        # Display custom HTML table
        df_display = df_filtered.copy()

        # Select display columns based on available schema
        display_cols = [c for c in [
            "job_id", "job_title_raw", "company_raw", "source_hostname",
            "extractor_name", "extraction_status", "extraction_confidence",
            "description_type", "source_url"
        ] if c in df_display.columns]

        if display_cols:
            headers = [c.replace("_", " ").title() for c in display_cols]
            rows = []
            for _, row in df_display.iterrows():
                row_cells = []
                for col in display_cols:
                    val = str(row[col])
                    if col == "extraction_status":
                        style = "success" if val in ("success", "partial") else ("warning" if val == "manual_review" else "error")
                        row_cells.append(make_status_pill(val, style))
                    elif col == "source_url":
                        row_cells.append(make_link_icon(val))
                    elif col == "job_id":
                        row_cells.append(f"<code>{val}</code>")
                    elif col in ("extraction_confidence", "confidence"):
                        try:
                            conf_val = float(val)
                            conf_pct = f"{conf_val * 100:.0f}%"
                            row_cells.append(conf_pct)
                        except ValueError:
                            row_cells.append(val)
                    else:
                        if len(val) > 40:
                            val = val[:37] + "..."
                        row_cells.append(val)
                rows.append(row_cells)
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)
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
                jid = row.get("job_id", "")
                label = f"{title} ({company}) - ID: {jid}"
                job_options[label] = idx

            selected_job_name = st.selectbox("Select record to inspect details:", list(job_options.keys()))
            selected_idx = job_options[selected_job_name]

            selected_row = df_filtered.loc[selected_idx]
            
            # Render a custom metadata chip dashboard inside console-card style
            chips_html = f"""
            <div class="console-card" style="margin-bottom: 12px; padding: 16px;">
                <div style="font-size: 11px; text-transform: uppercase; color: #94A3B8; font-weight: 600; margin-bottom: 8px;">Record Metadata</div>
                <div class="chip-container">
                    <span class="chip blue">Title: {selected_row.get('job_title_raw', '')}</span>
                    <span class="chip purple">Company: {selected_row.get('company_raw', '')}</span>
                    <span class="chip">Host: {selected_row.get('source_hostname', '')}</span>
                    <span class="chip purple">Extractor: {selected_row.get('extractor_name', '')} ({selected_row.get('extraction_method', 'N/A')})</span>
                    <span class="chip blue">Status: {selected_row.get('extraction_status', '')} (Confidence: {selected_row.get('extraction_confidence', '')})</span>
                    <span class="chip amber">Type: {selected_row.get('description_type', '')}</span>
                </div>
            </div>
            """
            st.markdown(chips_html, unsafe_allow_html=True)

            if "job_description_raw" in selected_row:
                st.text_area("Raw description content (Read-only):", value=str(selected_row["job_description_raw"]), height=250, disabled=True)

        # Download Raw CSV
        csv_raw_data = st.session_state.raw_df.to_csv(index=False, encoding="utf-8")
        batch_id = st.session_state.collection_batch_id
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        st.download_button(
            label="💾 Download raw CSV",
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

        # Action Area trigger
        col_clean_trig, _ = st.columns([1, 3])
        with col_clean_trig:
            clean_clicked = st.button("✨ Clean and Standardize Data", use_container_width=True)

        if clean_clicked:
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

            # Display stats panels as visual step funnel
            st.subheader("Cleaning pipeline statistics summary")
            st.markdown(render_pipeline_funnel(stats), unsafe_allow_html=True)

            st.subheader("Cleaned dataset (team schema format — 10 columns)")
            
            # Render Clean DF as Custom HTML table
            clean_df = st.session_state.clean_df.copy()
            clean_cols = list(clean_df.columns)
            headers = [c.replace("_", " ").title() for c in clean_cols]
            rows = []
            for _, row in clean_df.iterrows():
                row_cells = []
                for col in clean_cols:
                    val = str(row[col])
                    if col == "source_url" or "url" in col:
                        row_cells.append(make_link_icon(val))
                    elif col == "job_id":
                        row_cells.append(f"<code>{val}</code>")
                    elif col == "job_description":
                        short_val = val[:37] + "..." if len(val) > 40 else val
                        row_cells.append(f"""
                        <details style="cursor: pointer; min-width: 150px;">
                            <summary style="outline: none; color: #3B82F6; font-weight: 500;">{short_val}</summary>
                            <div style="margin-top: 8px; font-family: sans-serif; white-space: pre-wrap; font-size: 12px; color: #E2E8F0; background-color: #0F172A; padding: 10px; border-radius: 6px; border: 1px solid #1E293B; max-height: 250px; overflow-y: auto; text-align: left; line-height: 1.5;">{val}</div>
                        </details>
                        """)
                    else:
                        if len(val) > 40:
                            val = val[:37] + "..."
                        row_cells.append(val)
                rows.append(row_cells)
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

            # Download Clean CSV
            csv_clean_data = st.session_state.clean_df.to_csv(index=False, encoding="utf-8")
            batch_id = st.session_state.collection_batch_id
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            st.download_button(
                label="💾 Download clean CSV",
                data=csv_clean_data,
                file_name=f"jobs_clean_{date_str}_{batch_id}.csv",
                mime="text/csv"
            )

# ------------------------------------------
# Tab 4: Extraction Comparison
# ------------------------------------------
with tab4:
    st.subheader("Extraction Comparison")

    if not st.session_state.cleaning_completed:
        st.info(
            "Please execute the data cleaning step on the "
            "'Clean Data' tab before running skill extraction."
        )
    else:
        st.markdown(
            "Run both extraction approaches against the "
            "same cleaned job descriptions."
        )

        with st.container(border=True):
            threshold = st.slider(
                "Semantic threshold",
                min_value=0.30,
                max_value=0.85,
                value=0.45,
                step=0.05,
                help=(
                    "Minimum semantic similarity required "
                    "for a skill to be extracted."
                ),
            )

            extract_clicked = st.button(
                "Run Lexical + Semantic Extraction",
                use_container_width=True,
            )

        if extract_clicked:
            from src.extraction.run_extraction import run_extraction
            with st.spinner(
                "Running lexical and semantic skill extraction..."
            ):
                try:
                    extracted_df = run_extraction(
                        input_path=(
                            current_dir
                            / "data"
                            / "processed"
                            / "jobs_clean.csv"
                        ),
                        taxonomy_path=(
                            current_dir
                            / "config"
                            / "skill_taxonomy.json"
                        ),
                        semantic_threshold=threshold,
                    )

                    st.session_state.extracted_df = extracted_df
                    st.session_state.extraction_completed = True

                    # Persist enriched dataset
                    extracted_path = (
                        current_dir
                        / "data"
                        / "processed"
                        / "jobs_extracted.csv"
                    )

                    extracted_df.to_csv(
                        extracted_path,
                        index=False,
                        encoding="utf-8",
                    )

                    st.success(
                        "Lexical and semantic extraction completed."
                    )

                except Exception as e:
                    st.error(
                        f"Skill extraction failed: {e}"
                    )

        if st.session_state.extraction_completed:
            extracted_df = st.session_state.extracted_df.copy()

            st.subheader("Extraction Results")

            st.markdown(
                f"""
                <div style="
                    font-size: 12px;
                    color: #94A3B8;
                    margin-top: -10px;
                    margin-bottom: 16px;
                ">
                    <b>{len(extracted_df)}</b> jobs processed using
                    lexical and semantic skill extraction.
                </div>
                """,
                unsafe_allow_html=True,
            )

            # ------------------------------------------
            # Extraction Results Custom Table
            # ------------------------------------------

            display_cols = [
                "job_id",
                "job_title_raw",
                "company",
                "lexical_skills",
                "semantic_skills",
            ]

            display_cols = [
                col for col in display_cols
                if col in extracted_df.columns
            ]

            headers = [
                col.replace("_", " ").title()
                for col in display_cols
            ]

            rows = []

            for _, row in extracted_df.iterrows():
                row_cells = []

                for col in display_cols:
                    val = row.get(col, "")

                    if pd.isna(val):
                        val = ""

                    val = str(val)

                    if col == "job_id":
                        row_cells.append(
                            f"<code>{val}</code>"
                        )

                    elif col in (
                        "lexical_skills",
                        "semantic_skills",
                    ):
                        try:
                            skills = json.loads(val)

                            if not isinstance(skills, list):
                                skills = []

                        except (json.JSONDecodeError, TypeError):
                            skills = []

                        if skills:
                            chips = []

                            for skill in skills:
                                chips.append(
                                    f'<span class="chip purple">'
                                    f'{skill}'
                                    f'</span>'
                                )

                            row_cells.append(
                                '<div class="chip-container">'
                                + "".join(chips)
                                + "</div>"
                            )
                        else:
                            row_cells.append(
                                '<span style="color:#64748B;">'
                                "None"
                                "</span>"
                            )

                    else:
                        if len(val) > 40:
                            val = val[:37] + "..."

                        row_cells.append(val)

                rows.append(row_cells)

            st.markdown(
                render_custom_table(
                    headers,
                    rows,
                ),
                unsafe_allow_html=True,
            )

            # ------------------------------------------
            # Download Enriched Dataset
            # ------------------------------------------

            st.download_button(
                label="💾 Download enriched dataset",
                data=extracted_df.to_csv(
                    index=False,
                    encoding="utf-8",
                ),
                file_name=(
                    f"jobs_extracted_"
                    f"{st.session_state.collection_batch_id}.csv"
                ),
                mime="text/csv",
            )

# ------------------------------------------
# Tab 5: Quality Report
# ------------------------------------------
with tab5:
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

        # Display checks list using custom checklist helper
        st.subheader("Pipeline validation status checks")
        st.markdown(render_validation_checklist(report_runs), unsafe_allow_html=True)

        st.write("---")

        # Display Markdown report preview inside custom document viewport card
        st.subheader("Report content preview")
        st.markdown('<div class="document-frame">', unsafe_allow_html=True)
        st.markdown(report_md)
        st.markdown('</div>', unsafe_allow_html=True)

        st.write("") # Spacer

        # Download Markdown Quality Report
        batch_id = st.session_state.collection_batch_id
        st.download_button(
            label="📄 Download quality report (Markdown)",
            data=report_md,
            file_name=f"jobs_quality_report_{batch_id}.md",
            mime="text/markdown"
        )

# ------------------------------------------
# Tab 6: Failure Logs
# ------------------------------------------
with tab6:
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
        
        # Render custom HTML table with badges
        cols_failures = list(df_failures.columns)
        headers = [c.replace("_", " ").title() for c in cols_failures]
        rows = []
        for _, row in df_failures.iterrows():
            row_cells = []
            for col in cols_failures:
                val = str(row[col])
                if col == "url" or "url" in col:
                    row_cells.append(make_link_icon(val))
                elif col == "error_type":
                    style = "error" if any(x in val.lower() for x in ("fail", "error", "invalid")) else "warning"
                    row_cells.append(make_status_pill(val, style))
                elif col == "retryable":
                    style = "success" if val.lower() == "yes" else "info"
                    row_cells.append(make_status_pill(val, style))
                else:
                    if len(val) > 40:
                        val = val[:37] + "..."
                    row_cells.append(val)
            rows.append(row_cells)
        st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

        # Download Failures CSV
        csv_failures = df_failures.to_csv(index=False, encoding="utf-8")
        batch_id = st.session_state.collection_batch_id if st.session_state.collection_batch_id else "temp"
        st.download_button(
            label="💾 Download failures log CSV",
            data=csv_failures,
            file_name=f"jobs_failures_{batch_id}.csv",
            mime="text/csv"
        )

# ------------------------------------------
# Tab 7: External Domains Queue
# ------------------------------------------
with tab7:
    st.subheader("External vacancy detail links review queue")
    queue_path = current_dir / "data" / "external_links_queue.json"
    if not queue_path.exists():
        st.info("No external links recorded in the queue.")
    else:
        try:
            with open(queue_path, "r", encoding="utf-8") as f:
                queue_data = json.load(f)
        except Exception as e:
            st.error(f"Failed to read queue: {e}")
            queue_data = []

        if not queue_data:
            st.info("External queue is empty.")
        else:
            df_queue = pd.DataFrame(queue_data)
            
            # Display domain queue as sleek card list
            st.markdown('<div class="queue-list">', unsafe_allow_html=True)
            for idx, item in df_queue.iterrows():
                host = item.get("destination_hostname", "")
                status = item.get("review_status", "pending")
                status_style = "warning" if status == "pending" else "success"
                status_pill = make_status_pill(status, status_style)
                source = item.get("source_url", "")
                st.markdown(f"""
                <div class="queue-item">
                    <div>
                        <div class="queue-host">{host}</div>
                        <div class="queue-meta">Discovered on: <a href="{source}" target="_blank" style="color:#3B82F6; text-decoration:none;">{source[:80]}...</a></div>
                    </div>
                    <div>{status_pill}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Domain Approval Action
            pending_hosts = sorted(list(set(
                item["destination_hostname"] for item in queue_data if item.get("review_status") == "pending"
            )))

            if not pending_hosts:
                st.success("All identified external domains have been processed/approved!")
            else:
                st.write("---")
                st.subheader("Approve External Domain")
                with st.container(border=True):
                    c_sel, c_act = st.columns([3, 1])
                    with c_sel:
                        selected_host = st.selectbox("Select external domain to approve:", pending_hosts, label_visibility="collapsed")
                    with c_act:
                        if st.button("Approve Domain", use_container_width=True):
                            from src.security.url_validator import approve_external_domain
                            approve_external_domain(selected_host)
                            st.success(f"Domain '{selected_host}' is approved!")
                            st.rerun()

# ------------------------------------------
# Tab 8: Manual Reviews & Overrides
# ------------------------------------------
with tab8:
    st.subheader("Manual record review & IT relevance override audit trail")
    clean_internal_path = current_dir / "data" / "processed" / "jobs_clean_internal.csv"
    if not clean_internal_path.exists():
        st.info("Please clean data to generate the internal review dataset.")
    else:
        df_clean_int = pd.read_csv(clean_internal_path, dtype=str).fillna("")
        
        # Ensure required columns for filtering exist to prevent KeyErrors on older CSV files
        for col in ["extraction_status", "classification_status"]:
            if col not in df_clean_int.columns:
                df_clean_int[col] = ""
        
        # Identify rows matching manual_review or ambiguous classification
        review_mask = (df_clean_int["extraction_status"] == "manual_review") | (df_clean_int["classification_status"] == "ambiguous")
        df_review = df_clean_int[review_mask]

        if df_review.empty:
            st.success("No records currently require manual review or override.")
        else:
            st.write(f"Found {len(df_review)} records awaiting review or available for override.")
            
            # Select record dropdown in a clean card
            with st.container(border=True):
                options_labels = []
                for idx, r in df_review.iterrows():
                    lbl = f"{r.get('job_title_raw', 'Untitled')} @ {r.get('company_raw', 'Unknown')} (ID: {r.get('job_id', '')})"
                    options_labels.append((lbl, r.get("job_id", "")))
                    
                selected_lbl = st.selectbox("Select job record to inspect:", [lbl for lbl, _ in options_labels])
                selected_id = [jid for lbl, jid in options_labels if lbl == selected_lbl][0]
            
            job_row = df_review[df_review["job_id"] == selected_id].iloc[0]

            # Display job details in a console-card
            st.markdown(f"""
            <div class="console-card" style="margin-top: 16px;">
                <div style="font-size: 11px; color: #94A3B8; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 8px;">Awaiting Review Details</div>
                <h3 style="margin: 0 0 12px 0; color: #F8FAFC; font-size: 20px;">{job_row.get('job_title_raw')}</h3>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; font-size: 13px;">
                    <div><span style="color:#94A3B8;">Company:</span> <strong style="color:#F8FAFC;">{job_row.get('company_raw')}</strong></div>
                    <div><span style="color:#94A3B8;">Location:</span> <strong style="color:#F8FAFC;">{job_row.get('location_raw')}</strong></div>
                    <div><span style="color:#94A3B8;">Platform:</span> <strong style="color:#F8FAFC;">{job_row.get('source_platform')}</strong></div>
                    <div><span style="color:#94A3B8;">Status:</span> <span class="status-pill warning">{job_row.get('classification_status')}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Classifier Audit Signals as Chips
            st.subheader("Classifier Audit Signals")
            try:
                # Safely parsing JSON string
                expl_str = job_row.get("classification_explanation", "{}")
                if isinstance(expl_str, str) and expl_str.strip().startswith("{"):
                    expl = json.loads(expl_str)
                else:
                    expl = {}
                    
                dbasis = expl.get('decision_basis', 'N/A')
                tscore = expl.get('title_score', 0)
                tsignals = expl.get('title_it_signals', [])
                skillsignals = expl.get('skills_signals', [])
                exclsignals = expl.get('exclusion_signals', [])
                
                # Render as modern chip layout
                c_signals = f"""
                <div class="chip-container">
                    <span class="chip blue" style="font-weight:600;">Decision: {dbasis}</span>
                    <span class="chip purple" style="font-weight:600;">Title Score: {tscore}</span>
                """
                for s in tsignals:
                    c_signals += f'<span class="chip blue">Title Match: {s}</span>'
                for s in skillsignals:
                    c_signals += f'<span class="chip purple">Skill: {s}</span>'
                if isinstance(exclsignals, list):
                    for s in exclsignals:
                        c_signals += f'<span class="chip amber">Exclusion: {s}</span>'
                elif exclsignals:
                    c_signals += f'<span class="chip amber">Exclusion: {exclsignals}</span>'
                c_signals += "</div>"
                st.markdown(c_signals, unsafe_allow_html=True)
            except Exception:
                st.info("No classification audit explanation available.")

            # OCR vs Cleaned Description
            st.subheader("Description Inspection Panels")
            col_d1, col_d2 = st.columns(2)
            
            with col_d1:
                ocr_text = job_row.get("ocr_text_raw", "")
                if job_row.get("ocr_status") == "success" and ocr_text:
                    st.text_area("OCR Raw Text Result (Read-only)", ocr_text, height=250, disabled=True)
                else:
                    st.text_area("OCR Raw Text Result (Not Available)", "No OCR text was captured for this vacancy flyer.", height=250, disabled=True)
            
            with col_d2:
                st.text_area("Cleaned Description Content (Read-only)", job_row.get("job_description_clean", ""), height=250, disabled=True)

            # Override Settings Panel
            st.write("---")
            st.markdown("""
            <div class="action-panel">
                <div class="action-panel-title">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                        <line x1="12" y1="9" x2="12" y2="13"></line>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                    Apply Classification Override
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.container():
                c_over_sel, c_over_just = st.columns([1, 2])
                with c_over_sel:
                    new_status = st.selectbox("New classification status:", ["it", "non_it", "ambiguous"])
                with c_over_just:
                    override_reason = st.text_input("Reason / Justification for override:")
                
                # Align action button inline
                col_over_btn, _ = st.columns([1, 3])
                with col_over_btn:
                    apply_clicked = st.button("Apply Classification Override", use_container_width=True)
                
                if apply_clicked:
                    if not override_reason.strip():
                        st.error("Please provide a reason for manual override.")
                    else:
                        # Execute Override logic on Raw Data Batch CSV
                        batch_id = job_row.get("collection_batch_id")
                        raw_batch_file = current_dir / "data" / "raw" / "batches" / f"jobs_raw_{batch_id}.csv"
                        
                        if not raw_batch_file.exists():
                            st.error(f"Cannot find raw batch file: {raw_batch_file}")
                        else:
                            try:
                                df_raw_batch = pd.read_csv(raw_batch_file, dtype=str).fillna("")
                                if "job_id" in df_raw_batch.columns:
                                    matched_row = df_raw_batch[df_raw_batch["job_id"] == selected_id]
                                    if not matched_row.empty:
                                        row_idx = matched_row.index[0]
                                        override_val = json.dumps({"new_status": new_status, "reason": override_reason})
                                        df_raw_batch.at[row_idx, "classification_override"] = override_val
                                        df_raw_batch.to_csv(raw_batch_file, index=False, encoding="utf-8")
                                        st.info("Raw batch file updated with override.")
                                        
                                        # Reload full raw dataframe and re-run cleaning
                                        # Load raw CSV batches
                                        batches_dir = current_dir / "data" / "raw" / "batches"
                                        raw_files = list(batches_dir.glob("jobs_raw_*.csv"))
                                        dfs = []
                                        for rf in raw_files:
                                            try:
                                                dfs.append(pd.read_csv(rf, dtype=str).fillna(""))
                                            except Exception:
                                                pass
                                        if dfs:
                                            full_raw_df = pd.concat(dfs, ignore_index=True)
                                            # Re-run cleaning pipeline
                                            df_internal, df_team, stats = clean_raw_dataframe(full_raw_df)
                                            
                                            # Save clean files
                                            processed_batches_dir = current_dir / "data" / "processed" / "batches"
                                            internal_batch_file = processed_batches_dir / f"jobs_clean_internal_{batch_id}.csv"
                                            team_batch_file = processed_batches_dir / f"jobs_clean_{batch_id}.csv"
                                            
                                            # Filter internal/team to batch ID if needed, or save full
                                            df_internal.to_csv(current_dir / "data" / "processed" / "jobs_clean_internal.csv", index=False, encoding="utf-8")
                                            df_team.to_csv(current_dir / "data" / "processed" / "jobs_clean.csv", index=False, encoding="utf-8")
                                            
                                            # Save batch-specific clean
                                            df_internal[df_internal["collection_batch_id"] == batch_id].to_csv(internal_batch_file, index=False, encoding="utf-8")
                                            df_team[df_team["collection_batch_id"] == batch_id].to_csv(team_batch_file, index=False, encoding="utf-8")
                                            
                                            st.session_state.raw_df = full_raw_df
                                            st.session_state.clean_internal_df = df_internal
                                            st.session_state.clean_df = df_team
                                            st.session_state.cleaning_stats = stats
                                            st.session_state.cleaning_completed = True
                                            
                                            st.success("Override applied successfully! Clean datasets re-compiled.")
                                            st.rerun()
                                    else:
                                        st.error("Could not find matching job ID in the raw batch file.")
                                else:
                                    st.error("No job_id column in raw batch file.")
                            except Exception as ex:
                                st.error(f"Override execution failed: {ex}")


# ------------------------------------------
# Tab 9: Role & Skill Demand
# ------------------------------------------
with tab9:
    st.subheader("Role based skill demand segementation")
    st.caption(
        "Groups job postings by IT role, then shows how often each skill "
        "appears within that role, separating skills that are core to "
        "the role from ones that only show up in a few postings."
    )

    if not st.session_state.extraction_completed or st.session_state.extracted_df.empty:
        st.info(
            "Please run skill extraction on the 'Extract Skills' tab first -- "
            "role analysis builds on top of its lexical_skills/semantic_skills output."
        )
    else:
        if st.button("Classify roles & analyze skill demand"):
            with st.spinner("Classifying job postings into role categories..."):
                try:
                    role_df = classify_roles(st.session_state.extracted_df)
                    freq_df = build_role_skill_frequency_table(role_df)

                    st.session_state.role_classified_df = role_df
                    st.session_state.role_skill_freq_df = freq_df
                    st.session_state.role_analysis_completed = True

                    analysis_dir = current_dir / "data" / "analysis"
                    analysis_dir.mkdir(parents=True, exist_ok=True)
                    freq_df.to_csv(
                        analysis_dir / "role_skill_frequencies.csv",
                        index=False,
                        encoding="utf-8",
                    )

                    st.success("Role classification and skill demand analysis complete.")
                except Exception as e:
                    st.error(f"Role analysis failed: {e}")

        if st.session_state.role_analysis_completed:
            role_df = st.session_state.role_classified_df
            freq_df = st.session_state.role_skill_freq_df

            st.subheader("Job postings by role category")
            st.bar_chart(role_df["role_name"].value_counts(), horizontal=True, height=400)

            st.subheader("Skill demand by role — lexical vs semantic")
            role_options = sorted(freq_df["role_name"].unique())

            if not role_options:
                st.info("No roles were classified yet -- this can happen with a very small sample.")
            else:
                selected_role = st.selectbox("Choose a role category", role_options)

                role_data = freq_df[freq_df["role_name"] == selected_role]
                pivot = role_data.pivot_table(
                    index="skill", columns="method", values="job_count", fill_value=0
                ).astype(int)

                if pivot.empty:
                    st.info(f"No skills were extracted for '{selected_role}' yet.")
                else:
                    pivot["_total"] = pivot.sum(axis=1)
                    top_skills = pivot.sort_values("_total", ascending=False).head(10).drop(columns="_total")
                    st.bar_chart(top_skills, horizontal=True, height=400)

            st.subheader("Skill demand by role table")
            freq_cols = list(freq_df.columns)
            headers = [c.replace("_", " ").title() for c in freq_cols]
            rows = []
            for _, row in freq_df.iterrows():
                row_cells = []
                for col in freq_cols:
                    val = row[col]
                    if col == "pct_of_role":
                        row_cells.append(f"{val}%")
                    else:
                        row_cells.append(str(val))
                rows.append(row_cells)
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

            csv_role_freq = freq_df.to_csv(index=False, encoding="utf-8")
            st.download_button(
                label="Download role x skill frequency CSV",
                data=csv_role_freq,
                file_name="role_skill_frequencies.csv",
                mime="text/csv",
            )