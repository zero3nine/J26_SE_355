"""Dashboard page: Collect Data."""
import streamlit as st

st.set_page_config(
    page_title="Collect Data — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *  # noqa: F401,F403

render_page_shell()

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

            # Strict run isolation: Invalidate all downstream datasets from earlier runs
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
            st.session_state.raw_df = raw_df
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
