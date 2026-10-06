"""Dashboard page: Extract Skills."""
import streamlit as st

st.set_page_config(
    page_title="Extract Skills — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *  # noqa: F401,F403

render_page_shell()

st.subheader("Extraction Comparison")

from src.database.repository import get_database_summary, get_master_jobs

db_summary = get_database_summary()
has_db_jobs = db_summary.get("jobs", 0) > 0
clean_csv_path = current_dir / "data" / "processed" / "jobs_clean.csv"
has_clean_csv = clean_csv_path.exists()
cleaning_completed = getattr(st.session_state, "cleaning_completed", False)

# Auto-load existing extraction results so the table is never blank on page load
if not getattr(st.session_state, "extraction_completed", False):
    if db_summary.get("skill_mentions", 0) > 0:
        from src.database.repository import get_extracted_skills_dataset
        existing_db_df = get_extracted_skills_dataset()
        if not existing_db_df.empty:
            st.session_state.extracted_df = existing_db_df
            st.session_state.extraction_completed = True
    elif (current_dir / "data" / "processed" / "jobs_extracted.csv").exists():
        try:
            st.session_state.extracted_df = pd.read_csv(current_dir / "data" / "processed" / "jobs_extracted.csv")
            st.session_state.extraction_completed = True
        except Exception:
            pass

if not cleaning_completed and not has_clean_csv and not has_db_jobs:
    st.info(
        "Please execute the data cleaning step on the "
        "'Clean Data' tab or publish jobs to the Master Dataset before running skill extraction."
    )
else:
    st.markdown(
        "Run lexical and semantic extraction against "
        "cleaned job descriptions and record results in the Master SQLite database."
    )

    with st.container(border=True):
        source_options = []
        if has_db_jobs:
            source_options.append(f"Master Database ({db_summary['jobs']} jobs)")
        if has_clean_csv or cleaning_completed:
            source_options.append("Cleaned Dataset (jobs_clean.csv)")

        if len(source_options) > 1:
            source_selection = st.radio(
                "Select extraction source:",
                source_options,
                horizontal=True,
            )
        elif source_options:
            source_selection = source_options[0]
            st.caption(f"Extraction source: **{source_selection}**")
        else:
            source_selection = None

        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            threshold = st.slider(
                "Semantic threshold",
                min_value=0.35,
                max_value=0.85,
                value=0.58,
                step=0.01,
                help=(
                    "Minimum semantic similarity required for a skill to be extracted. "
                    "Values between 0.55 and 0.65 offer optimal precision without spurious matches."
                ),
            )
        with col_t2:
            st.write("")
            st.write("")
            persist_db = st.checkbox("Persist to SQLite Database", value=True, help="Record extraction_runs and extracted_skills into data/master_jobs.sqlite3")

        extract_clicked = st.button(
            "Run Lexical + Semantic Extraction",
            use_container_width=True,
            type="primary",
        )

    if extract_clicked:
        from src.extraction.run_extraction import run_extraction
        with st.spinner(
            "Running lexical and semantic skill extraction..."
        ):
            try:
                if source_selection and "Master Database" in source_selection:
                    input_source = get_master_jobs()
                else:
                    input_source = clean_csv_path

                extracted_df = run_extraction(
                    input_path=input_source,
                    taxonomy_path=(
                        current_dir
                        / "config"
                        / "skill_taxonomy.json"
                    ),
                    semantic_threshold=threshold,
                    persist_to_db=persist_db,
                )

                st.session_state.extracted_df = extracted_df
                st.session_state.extraction_completed = True

                # Persist enriched dataset for backwards compatibility with CSV workflows
                extracted_path = (
                    current_dir
                    / "data"
                    / "processed"
                    / "jobs_extracted.csv"
                )
                extracted_path.parent.mkdir(parents=True, exist_ok=True)

                extracted_df.to_csv(
                    extracted_path,
                    index=False,
                    encoding="utf-8",
                )

                success_msg = f"Lexical and semantic extraction completed for {len(extracted_df)} jobs."
                if persist_db:
                    updated_sum = get_database_summary()
                    success_msg += f" Persisted to Master SQLite Database: {updated_sum['skill_mentions']} total skill mentions recorded."
                st.success(success_msg)

            except Exception as e:
                st.error(
                    f"Skill extraction failed: {e}"
                )

    if st.session_state.extraction_completed:
        extracted_df = st.session_state.extracted_df.copy()

        # Harmonize column names between Master Database and CSV schemas
        if "job_title_raw" not in extracted_df.columns and "job_title" in extracted_df.columns:
            extracted_df["job_title_raw"] = extracted_df["job_title"]
        elif "job_title" not in extracted_df.columns and "job_title_raw" in extracted_df.columns:
            extracted_df["job_title"] = extracted_df["job_title_raw"]

        if "company" not in extracted_df.columns and "company_name" in extracted_df.columns:
            extracted_df["company"] = extracted_df["company_name"]
        elif "company_name" not in extracted_df.columns and "company" in extracted_df.columns:
            extracted_df["company_name"] = extracted_df["company"]

        from src.extraction.normalization import normalize_skill

        # Compute combined skills column for complete visibility
        def _parse_skills_list(val) -> list[str]:
            if isinstance(val, (list, set, tuple)):
                return list(val)
            if not val or pd.isna(val):
                return []
            try:
                parsed = json.loads(val)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return [s.strip() for s in str(val).split(",") if s.strip()]

        combined_skills_col = []
        for _, r in extracted_df.iterrows():
            l_skills = _parse_skills_list(r.get("lexical_skills"))
            s_skills = _parse_skills_list(r.get("semantic_skills"))
            # Normalize to canonical names
            comb = sorted(list({normalize_skill(s) for s in (l_skills + s_skills) if s}))
            combined_skills_col.append(json.dumps(comb, ensure_ascii=False))
        extracted_df["combined_skills"] = combined_skills_col

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
                lexical and semantic skill extraction. Displaying canonical skill mappings.
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
            "combined_skills",
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

                if col == "job_id":
                    row_cells.append(
                        f"<code>{str(val)}</code>"
                    )

                elif col in (
                    "lexical_skills",
                    "semantic_skills",
                    "combined_skills",
                ):
                    skills = _parse_skills_list(val)

                    if skills:
                        chips = []
                        chip_class = "cyan" if col == "semantic_skills" else ("blue" if col == "lexical_skills" else "purple")

                        for skill in skills:
                            canon_name = normalize_skill(skill) if skill else skill
                            chips.append(
                                f'<span class="chip {chip_class}" title="Raw ID: {skill}">'
                                f'{canon_name}'
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
                    val_str = str(val)
                    if len(val_str) > 40:
                        val_str = val_str[:37] + "..."

                    row_cells.append(val_str)

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
