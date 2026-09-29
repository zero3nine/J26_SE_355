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
