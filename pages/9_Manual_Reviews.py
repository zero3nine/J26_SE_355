"""Dashboard page: Manual Reviews."""
import streamlit as st

st.set_page_config(
    page_title="Manual Reviews — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *  # noqa: F401,F403

render_page_shell()

st.subheader("Manual record review & IT relevance override audit trail")
st.markdown("""
<div style="background-color: #161D30; border: 1px solid #1E293B; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; font-size: 13px; color: #94A3B8;">
    💡 <strong>Scraping Accuracy Cross-Reference:</strong> This tab manages operational IT-relevance classification overrides. 
    For field-level scraping discrepancy verification (titles, employers, salaries against independently verified ground truth), 
    navigate to <strong>Tab 11: Scraping Accuracy & Validation</strong>.
</div>
""", unsafe_allow_html=True)
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
