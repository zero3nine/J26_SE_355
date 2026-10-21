"""Dashboard page: Raw Data."""
import streamlit as st

st.set_page_config(
    page_title="Raw Data — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *  # noqa: F401,F403

render_page_shell()

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
        country_val = selected_row.get('country_raw', selected_row.get('country', 'N/A'))
        fetch_val = selected_row.get('fetch_method', 'http')
        rend_val = selected_row.get('rendering_used', 'False')
        diag_val = selected_row.get('failure_reason', selected_row.get('error_message', ''))
        diag_chip = f'<span class="chip amber">Diagnostic: {diag_val}</span>' if diag_val else ''

        chips_html = f"""
        <div class="console-card" style="margin-bottom: 12px; padding: 16px;">
            <div style="font-size: 11px; text-transform: uppercase; color: #94A3B8; font-weight: 600; margin-bottom: 8px;">Record Provenance & Metadata</div>
            <div class="chip-container">
                <span class="chip blue">Title: {selected_row.get('job_title_raw', '')}</span>
                <span class="chip purple">Company: {selected_row.get('company_raw', '')}</span>
                <span class="chip">Host: {selected_row.get('source_hostname', '')}</span>
                <span class="chip purple">Country: {country_val}</span>
                <span class="chip purple">Extractor: {selected_row.get('extractor_name', '')} ({selected_row.get('extraction_method', 'N/A')})</span>
                <span class="chip blue">Fetch: {fetch_val} (Rendered: {rend_val})</span>
                <span class="chip blue">Status: {selected_row.get('extraction_status', '')} (Confidence: {selected_row.get('extraction_confidence', '')})</span>
                <span class="chip amber">Type: {selected_row.get('description_type', '')}</span>
                {diag_chip}
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
