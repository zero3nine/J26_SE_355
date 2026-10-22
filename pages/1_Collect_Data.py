"""Dashboard page: Collect Data."""
import streamlit as st

st.set_page_config(
    page_title="Collect Data — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *  # noqa: F401,F403

render_page_shell()

from src.scraping.historical_importer import read_dataset, suggest_mapping, normalize_historical_dataset, duplicate_mask
import uuid

collection_mode = st.segmented_control(
    "Collection method",
    options=["Live Scraping", "Historical Data Import"],
    default="Live Scraping",
    key="collection_method_ui",
    help="Use live scraping for current pages or import an existing historical dataset.",
)

if collection_mode == "Live Scraping":

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
        ocr = c2.checkbox("Run Advertisement Image OCR", value=True, help="Process image flyers using local Tesseract OCR to extract technical requirements from poster ads.")
        crawl_all_pages = st.checkbox(
            "Temporal collection: keep paging after the job target",
            value=False,
            help="Useful for historical analysis. Traversal still stops at the request and duration limits."
        )
        dataset_behavior = st.radio(
            "Dataset behavior",
            options=["Replace current raw data", "Append to current raw data"],
            horizontal=True,
            help="Append retains previously imported or scraped records; replace starts a fresh dataset.",
        )

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
                import uuid
                new_run_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
                st.session_state.current_run_id = new_run_id
                st.session_state.collection_batch_id = new_run_id
                st.session_state.current_submitted_urls = list(valid)

                # In append mode, retain the existing raw records while invalidating downstream outputs.
                if dataset_behavior == "Append to current raw data":
                    st.session_state.raw_df_before_append = st.session_state.raw_df.copy()
                else:
                    st.session_state.raw_df_before_append = pd.DataFrame()
                    st.session_state.raw_df = pd.DataFrame()
                st.session_state.clean_df = pd.DataFrame()
                st.session_state.clean_internal_df = pd.DataFrame()
                st.session_state.extracted_df = pd.DataFrame()
                st.session_state.cleaning_completed = False
                st.session_state.cleaning_stats = {}
                st.session_state.extraction_completed = False
                st.session_state.extracted_threshold = None
                st.session_state.analytics_report = None
                st.session_state.analytics_mode = None
                st.session_state.analytics_run_id = ""
                st.session_state.role_analysis_completed = False
                st.session_state.role_classified_df = pd.DataFrame()
                st.session_state.role_skill_freq_df = pd.DataFrame()

                st.session_state.scraping_confirmed = False
                st.session_state.run_config = {
                    "target_valid": target_valid,
                    "max_requests": max_requests,
                    "max_time": max_time,
                    "polite_delay": polite_delay,
                    "fallback": fallback,
                    "ocr": ocr,
                    "crawl_all_pages": crawl_all_pages,
                    "dataset_behavior": dataset_behavior,
                    "save_to_file": save_to_file,
                    "batch_id": new_run_id,
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

            def run_thread(urls, target_val, max_req, max_t, delay, use_fallback, use_ocr, crawl_all, cancel_ev, b_id_override=None):
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
                        cancel_requested_cb=cancel_cb,
                        crawl_all_pages=crawl_all,
                        batch_id=b_id_override,
                    )
                    st.session_state.crawl_thread_result = (df, b_id)
                except Exception as e:
                    st.session_state.crawl_thread_result = e

            t = threading.Thread(
                target=run_thread,
                args=(
                    valid, cfg["target_valid"], cfg["max_requests"], cfg["max_time"],
                    cfg["polite_delay"], cfg["fallback"], cfg["ocr"], cfg.get("crawl_all_pages", False), st.session_state.cancel_event,
                    cfg.get("batch_id")
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
                previous_raw_df = st.session_state.get("raw_df_before_append", pd.DataFrame())
                if cfg.get("dataset_behavior") == "Append to current raw data" and not previous_raw_df.empty:
                    raw_df = pd.concat([previous_raw_df, raw_df], ignore_index=True, sort=False)
                st.session_state.raw_df = raw_df
                st.session_state.raw_df_before_append = pd.DataFrame()
                st.session_state.collection_batch_id = batch_id
                st.session_state.current_run_id = batch_id
                st.session_state.scraping_completed = True
                if raw_df.empty:
                    st.warning(f"Scraping run completed, but no job advertisements were successfully collected from the submitted URLs. Batch ID: {batch_id}")
                else:
                    st.success(f"Scraping run completed successfully. Collected {len(raw_df)} records. Batch ID: {batch_id}")

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
else:
    st.subheader("Import historical job advertisements")
    st.markdown(
        "Import a dataset obtained from a research repository or historical job-data provider. "
        "Imported records enter the same raw-data and cleaning workflow as live-scraped records."
    )

    with st.container(border=True):
        c1, c2 = st.columns(2)
        dataset_source = c1.selectbox(
            "Dataset source",
            options=["Moratuwa research dataset", "Techmap export", "Other dataset"],
            key="historical_dataset_source",
        )
        import_mode = c2.radio(
            "Import behavior",
            options=["Append to current raw data", "Replace current raw data"],
            horizontal=True,
            key="historical_import_mode",
            help="Append preserves existing records. Replace starts a new raw dataset.",
        )
        uploaded_file = st.file_uploader(
            "Upload historical dataset",
            type=["csv", "xlsx", "xls"],
            help="CSV and Excel files are supported. Original source fields are preserved where mapped.",
            key="historical_dataset_upload",
        )
        default_country = st.text_input("Default country for records with no country value", "Sri Lanka")

    if uploaded_file is not None:
        try:
            preview_df = read_dataset(uploaded_file)
            st.caption(f"Loaded {len(preview_df):,} rows and {len(preview_df.columns)} columns from {uploaded_file.name}.")
            with st.expander("Preview source file", expanded=True):
                st.dataframe(preview_df.head(10), use_container_width=True, hide_index=True)

            suggestions = suggest_mapping(preview_df.columns)
            st.subheader("Map source columns")
            st.caption("Review automatic suggestions. Job Title is required; descriptions and posting dates are strongly recommended.")
            mapping = {}
            options = ["(Do not map)"] + list(preview_df.columns)
            target_labels = {
                "job_title_raw": "Job Title (required)", "company_raw": "Company",
                "job_description_raw": "Job Description", "requirements_raw": "Requirements",
                "posted_date_raw": "Original Posting Date", "closing_date_raw": "Closing Date",
                "country_raw": "Country", "location_raw": "Location", "source_url": "Original Job URL",
                "source_platform": "Original Source / Portal", "source_job_id": "Source Job ID",
                "employment_type_raw": "Employment Type", "skills_raw": "Pre-extracted Skills (if any)",
                "salary_text_raw": "Salary Text", "work_mode_raw": "Work Mode",
            }
            targets = list(target_labels)
            for start in range(0, len(targets), 2):
                cols = st.columns(2)
                for offset, target in enumerate(targets[start:start+2]):
                    suggested = suggestions.get(target, "")
                    index = options.index(suggested) if suggested in options else 0
                    selected = cols[offset].selectbox(
                        target_labels[target], options=options, index=index, key=f"hist_map_{target}"
                    )
                    mapping[target] = "" if selected == "(Do not map)" else selected

            if mapping.get("job_description_raw"):
                description_count = int(preview_df[mapping["job_description_raw"]].fillna("").astype(str).str.strip().ne("").sum())
            else:
                description_count = 0
            if mapping.get("posted_date_raw"):
                date_count = int(preview_df[mapping["posted_date_raw"]].fillna("").astype(str).str.strip().ne("").sum())
            else:
                date_count = 0
            k1, k2, k3 = st.columns(3)
            k1.metric("Records", f"{len(preview_df):,}")
            k2.metric("Rows with descriptions", f"{description_count:,}")
            k3.metric("Rows with posting dates", f"{date_count:,}")

            if not mapping.get("job_title_raw"):
                st.warning("Map a source column to Job Title before importing.")
            if not mapping.get("job_description_raw"):
                st.warning("No description column is mapped. These records may be unsuitable for skill extraction.")
            if not mapping.get("posted_date_raw"):
                st.warning("No posting-date column is mapped. Records cannot support reliable temporal trends.")

            import_clicked = st.button("Import historical records", type="primary", use_container_width=True)
            if import_clicked:
                try:
                    batch_id = f"hist_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
                    source_label = {
                        "Moratuwa research dataset": "moratuwa_research",
                        "Techmap export": "techmap",
                        "Other dataset": "other_historical_dataset",
                    }[dataset_source]
                    incoming_df = normalize_historical_dataset(
                        preview_df, mapping, source_label, batch_id, default_country.strip() or "Sri Lanka"
                    )
                    duplicate_flags = duplicate_mask(incoming_df)
                    incoming_df["import_duplicate_flag"] = duplicate_flags.astype(bool)
                    if import_mode == "Append to current raw data" and not st.session_state.raw_df.empty:
                        existing_df = st.session_state.raw_df.copy()
                        combined_df = pd.concat([existing_df, incoming_df], ignore_index=True, sort=False)
                    else:
                        combined_df = incoming_df.copy()

                    st.session_state.raw_df = combined_df
                    st.session_state.collection_batch_id = batch_id
                    st.session_state.current_run_id = batch_id
                    st.session_state.scraping_completed = True
                    st.session_state.clean_df = pd.DataFrame()
                    st.session_state.clean_internal_df = pd.DataFrame()
                    st.session_state.extracted_df = pd.DataFrame()
                    st.session_state.cleaning_completed = False
                    st.session_state.cleaning_stats = {}
                    st.session_state.extraction_completed = False
                    st.session_state.extracted_threshold = None
                    st.session_state.analytics_report = None
                    st.session_state.analytics_mode = None
                    st.session_state.analytics_run_id = ""
                    st.session_state.role_analysis_completed = False
                    st.session_state.role_classified_df = pd.DataFrame()
                    st.session_state.role_skill_freq_df = pd.DataFrame()

                    # Persist the imported batch separately for reproducibility.
                    batch_dir = current_dir / "data" / "raw" / "historical_imports"
                    batch_dir.mkdir(parents=True, exist_ok=True)
                    incoming_df.to_csv(batch_dir / f"jobs_raw_{batch_id}.csv", index=False, encoding="utf-8")
                    st.success(f"Imported {len(incoming_df):,} records. Batch ID: {batch_id}")
                    st.info("Open Raw Data to inspect provenance, then continue to Clean Data.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Import failed: {exc}")
        except Exception as exc:
            st.error(f"Could not read this dataset: {exc}")
    else:
        st.info("Upload the Moratuwa dataset, a Techmap export, or another historical CSV/Excel file to begin.")
