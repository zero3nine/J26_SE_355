
"""Dashboard page: Extract Skills."""

import html
import json

import pandas as pd
import streamlit as st

from app_shared import *  # noqa: F401,F403

from src.database.repository import (
    get_master_jobs,
    record_extraction_run,
    store_extracted_skills,
)


st.set_page_config(
    page_title="Extract Skills — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

render_page_shell()

st.subheader("Extraction Comparison")

st.markdown(
    "Extract skills from jobs saved in the master dataset. "
    "Lexical and semantic results can be saved as separate "
    "records linked to the original jobs."
)


# --------------------------------------------------
# Load master jobs
# --------------------------------------------------

try:
    master_jobs = get_master_jobs()
except Exception as exc:
    st.error(f"Could not load the master dataset: {exc}")
    st.stop()

if master_jobs.empty:
    st.info(
        "The master dataset is empty. Import jobs in the "
        "Master Dataset page before running skill extraction."
    )
    st.stop()

if "job_description" not in master_jobs.columns:
    st.error(
        "The master dataset does not contain a job_description column."
    )
    st.stop()

# Extractor expects job_id and job_description.
# Keep source_url so saved results can be linked to master records.
master_jobs = master_jobs.copy()

if "job_title_raw" not in master_jobs.columns:
    master_jobs["job_title_raw"] = master_jobs.get(
        "job_title", ""
    )

if "company" not in master_jobs.columns:
    master_jobs["company"] = master_jobs.get(
        "company_name", ""
    )

# Only process jobs with usable descriptions or titles.
description = master_jobs["job_description"].fillna("").astype(str)

if "job_title_raw" in master_jobs.columns:
    title = master_jobs["job_title_raw"].fillna("").astype(str)
else:
    title = pd.Series("", index=master_jobs.index)

eligible_mask = (
    description.str.strip().ne("")
    | title.str.strip().ne("")
)

eligible_jobs = master_jobs.loc[eligible_mask].copy()


# --------------------------------------------------
# Extraction controls
# --------------------------------------------------

st.caption(
    f"{len(master_jobs):,} jobs in the master dataset · "
    f"{len(eligible_jobs):,} eligible for extraction"
)

with st.container(border=True):
    threshold = st.slider(
        "Semantic threshold",
        min_value=0.30,
        max_value=0.85,
        value=0.45,
        step=0.05,
        help=(
            "Minimum semantic similarity required for a skill "
            "to be extracted. The selected value is stored with "
            "the extraction run."
        ),
    )

    extract_clicked = st.button(
        "Run Lexical + Semantic Extraction",
        use_container_width=True,
        disabled=eligible_jobs.empty,
    )


# --------------------------------------------------
# Run extraction
# --------------------------------------------------

if extract_clicked:
    from src.extraction.run_extraction import run_extraction

    with st.spinner(
        "Running lexical and semantic skill extraction..."
    ):
        try:
            extracted_df = run_extraction(
                input_df=eligible_jobs,
                taxonomy_path=(
                    current_dir
                    / "config"
                    / "skill_taxonomy.json"
                ),
                semantic_threshold=threshold,
            )

            st.session_state["extracted_df"] = extracted_df
            st.session_state["extraction_completed"] = True
            st.session_state["extraction_threshold"] = threshold
            st.session_state["extraction_saved_run_id"] = None

            # Preserve the existing CSV output workflow.
            extracted_path = (
                current_dir
                / "data"
                / "processed"
                / "jobs_extracted.csv"
            )
            extracted_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            extracted_df.to_csv(
                extracted_path,
                index=False,
                encoding="utf-8",
            )

            st.success(
                "Lexical and semantic extraction completed. "
                "Results have not yet been saved to the master database."
            )

        except Exception as exc:
            st.error(f"Skill extraction failed: {exc}")


# --------------------------------------------------
# Display and save extraction results
# --------------------------------------------------

if st.session_state.get("extraction_completed", False):

    st.divider()
    st.subheader("Save results to the master database")

    st.write(
        "Saving stores lexical and semantic skill mentions "
        "separately and links them to their original master job IDs. "
        "A new extraction run is recorded for each save."
    )

    already_saved_run = st.session_state.get(
        "extraction_saved_run_id"
    )

    if already_saved_run:
        st.success(
            f"These results were saved under run ID: "
            f"{already_saved_run}"
        )
    else:
        if st.button(
            "Save lexical and semantic results",
            type="primary",
            use_container_width=True,
        ):
            try:
                # Require source URLs because the current repository
                # helper matches extracted records to master jobs by URL.
                if (
                    "source_url" not in extracted_df.columns
                    or extracted_df["source_url"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .eq("")
                    .any()
                ):
                    st.error(
                        "Some extracted rows have no source_url. "
                        "Cannot safely link every result to its "
                        "master job. Check the master dataset URLs."
                    )
                    st.stop()

                run_id = record_extraction_run(
                    run_type="lexical_and_semantic",
                    model_name="SBERT",
                    semantic_threshold=float(
                        st.session_state.get(
                            "extraction_threshold", 0.45
                        )
                    ),
                    source_batch_id=None,
                    notes=(
                        "Lexical and semantic extraction from "
                        "the master dataset"
                    ),
                )

                lexical_count = store_extracted_skills(
                    jobs_df=extracted_df,
                    run_id=run_id,
                    method="lexical",
                    skills_column="lexical_skills",
                )

                semantic_count = store_extracted_skills(
                    jobs_df=extracted_df,
                    run_id=run_id,
                    method="semantic",
                    skills_column="semantic_skills",
                )

                st.session_state["extraction_saved_run_id"] = run_id

                st.success(
                    f"Saved extraction run {run_id}. "
                    f"Lexical mentions: {lexical_count:,}. "
                    f"Semantic mentions: {semantic_count:,}."
                )

            except Exception as exc:
                st.error(
                    f"Could not save extraction results: {exc}"
                )

    extracted_df = st.session_state.get("extracted_df")

    if extracted_df is None or extracted_df.empty:
        st.info("No extraction results are available.")
        st.stop()

    extracted_df = extracted_df.copy()

    st.subheader("Extraction Results")

    st.caption(
        f"{len(extracted_df):,} jobs processed using lexical "
        "and semantic skill extraction."
    )

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

    # Build escaped HTML so titles/skill labels cannot inject markup.
    headers = [
        html.escape(col.replace("_", " ").title())
        for col in display_cols
    ]
    rows = []

    for _, row in extracted_df.iterrows():
        cells = []

        for col in display_cols:
            value = row.get(col, "")

            if pd.isna(value):
                value = ""

            value = str(value)

            if col == "job_id":
                cells.append(
                    f"<code>{html.escape(value)}</code>"
                )

            elif col in ("lexical_skills", "semantic_skills"):
                try:
                    skills = json.loads(value)
                    if not isinstance(skills, list):
                        skills = []
                except (json.JSONDecodeError, TypeError):
                    skills = []

                if skills:
                    chips = "".join(
                        '<span class="chip purple">'
                        f'{html.escape(str(skill))}'
                        "</span>"
                        for skill in skills
                    )
                    cells.append(
                        '<div class="chip-container">'
                        f"{chips}</div>"
                    )
                else:
                    cells.append(
                        '<span style="color:#64748B;">None</span>'
                    )

            else:
                if len(value) > 40:
                    value = value[:37] + "..."
                cells.append(html.escape(value))

        rows.append(cells)

    st.markdown(
        render_custom_table(headers, rows),
        unsafe_allow_html=True,
    )

    st.download_button(
        label="Download enriched dataset",
        data=extracted_df.to_csv(
            index=False,
            encoding="utf-8",
        ),
        file_name="jobs_extracted.csv",
        mime="text/csv",
    )