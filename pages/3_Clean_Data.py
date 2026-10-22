"""Dashboard page: Clean Data."""
import streamlit as st

st.set_page_config(
    page_title="Clean Data — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *  # noqa: F401,F403

render_page_shell()

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

            # Invalidate downstream extraction states from prior runs so stale jobs are not shown
            st.session_state.extracted_df = pd.DataFrame()
            st.session_state.extraction_completed = False
            st.session_state.extraction_saved_run_id = None

        st.success("Cleaning completed successfully! Clean datasets saved to processed directory.")
        st.rerun()

    if st.session_state.cleaning_completed:
        stats = st.session_state.cleaning_stats

        # Display stats panels as visual step funnel
        st.subheader("Cleaning pipeline statistics summary")
        st.markdown(render_pipeline_funnel(stats), unsafe_allow_html=True)

        if not st.session_state.clean_internal_df.empty and "work_mode" in st.session_state.clean_internal_df.columns:
            with st.expander("📍 Geographic Normalization & Work-Mode Diagnostics", expanded=False):
                c_wm1, c_wm2 = st.columns(2)
                with c_wm1:
                    st.markdown("**Work-Mode Distribution (Analytically Distinct):**")
                    wm_s = st.session_state.clean_internal_df["work_mode"].value_counts()
                    st.dataframe(wm_s, use_container_width=True)
                with c_wm2:
                    st.markdown("**Country Normalization Breakdown:**")
                    c_col = "country_normalized" if "country_normalized" in st.session_state.clean_internal_df.columns else "country"
                    c_s = st.session_state.clean_internal_df[c_col].value_counts()
                    st.dataframe(c_s, use_container_width=True)

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

        st.divider()
        st.subheader("Publish to Master Database")
        st.markdown(
            "To extract skills and run relationship analysis across research batches, "
            "jobs must be published to the persistent SQLite master database. "
            "Publishing retains historical versions and performs duplicate detection."
        )

        col_pub1, col_pub2 = st.columns([1, 2])
        with col_pub1:
            if st.button("🚀 Publish this batch to Master Database now", type="primary", use_container_width=True):
                from src.database.repository import import_jobs_dataframe
                with st.spinner("Publishing cleaned jobs to master database..."):
                    res = import_jobs_dataframe(
                        st.session_state.clean_df,
                        source_name=f"Batch {st.session_state.collection_batch_id}",
                        batch_id=st.session_state.collection_batch_id,
                    )
                    st.session_state["last_published_import_run_id"] = res["import_run_id"]
                    st.success(
                        f"Published {res['inserted_jobs']} new jobs "
                        f"({res['skipped_duplicates']} duplicates skipped) under import run: {res['import_run_id']}"
                    )
        with col_pub2:
            if st.session_state.get("last_published_import_run_id"):
                st.info(f"✅ Published in Master Database (Run ID: `{st.session_state['last_published_import_run_id']}`). You can now navigate to **Extract Skills** to extract and inspect skills for this batch.")

