"""Dashboard page: Failure Logs."""
import streamlit as st

st.set_page_config(
    page_title="Failure Logs — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *  # noqa: F401,F403

render_page_shell()

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
            err_status = str(row.get("extraction_status", ""))
            err_msg = str(row.get("error_message", row.get("exclusion_reason", "Extraction failed")))
            if "anti-bot" in err_msg.lower() or "perimeter" in err_msg.lower() or "cloudflare" in err_msg.lower():
                err_type = "Access Restricted (Perimeter Bot Wall)"
            elif "ssl" in err_msg.lower() or "certificate" in err_msg.lower():
                err_type = "SSL/TLS Chain Fallback Error"
            elif "ssrf" in err_msg.lower():
                err_type = "Security Block (SSRF Protection)"
            elif "unsupported" in err_status or "not_a_job_page" in err_status:
                err_type = "Unsupported Layout / Non-Job Page"
            else:
                err_type = str(row.get("error_type", err_status))

            failures.append({
                "url": row.get("source_url", ""),
                "source_hostname": row.get("source_hostname", ""),
                "extractor_name": row.get("extractor_name", ""),
                "error_type": err_type,
                "error_message": err_msg,
                "timestamp": row.get("scraped_at", ""),
                "retryable": "Yes" if err_status in ("network_error", "rate_limited") else "No"
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
