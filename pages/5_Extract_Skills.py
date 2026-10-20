"""Dashboard page: Extract Skills."""

from __future__ import annotations

import html
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from app_shared import render_custom_table, render_page_shell
from src.database.repository import (
    get_master_jobs,
    record_extraction_run,
    store_extracted_skills,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = PROJECT_ROOT / "config" / "skill_taxonomy.json"

st.set_page_config(
    page_title="Extract Skills — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)
render_page_shell()

st.subheader("Extraction Comparison")
st.markdown(
    "Run lexical and semantic skill extraction on either the master database "
    "or an uploaded jobs CSV. Both sources use the same extraction pipeline."
)


def _prepare_jobs(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and harmonize the input without dropping source text columns."""
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    result = df.copy()
    required = {"job_id", "job_description"}
    missing = required - set(result.columns)
    if missing:
        raise ValueError(
            f"Jobs CSV is missing required columns: {', '.join(sorted(missing))}"
        )

    if "job_title_raw" not in result.columns:
        result["job_title_raw"] = result.get("job_title", "")
    if "job_title" not in result.columns:
        result["job_title"] = result["job_title_raw"]
    if "company" not in result.columns:
        result["company"] = result.get("company_name", "")
    if "company_name" not in result.columns:
        result["company_name"] = result["company"]

    # Normalize missing values while preserving all columns, especially requirements.
    for column in ("job_id", "job_description", "requirements", "job_title_raw"):
        if column in result.columns:
            result[column] = result[column].fillna("").astype(str)

    result["job_id"] = result["job_id"].str.strip()
    if result["job_id"].eq("").any():
        raise ValueError("Jobs input contains blank job_id values.")
    if result["job_id"].duplicated().any():
        duplicate_ids = result.loc[result["job_id"].duplicated(), "job_id"].head(5).tolist()
        raise ValueError(f"Jobs input contains duplicate job IDs, e.g. {duplicate_ids}.")

    return result


def _eligible_jobs(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    columns = [
        column for column in ("job_description", "job_title_raw", "requirements")
        if column in df.columns
    ]
    mask = pd.Series(False, index=df.index)
    for column in columns:
        mask |= df[column].fillna("").astype(str).str.strip().ne("")
    return df.loc[mask].copy()


def _run_evaluation_command(
    module_name: str,
    jobs_df: pd.DataFrame,
    ground_truth_bytes: bytes,
    semantic_threshold: float | None = None,
) -> subprocess.CompletedProcess:
    """Run an existing evaluation module on the same raw fields as extraction."""
    with tempfile.TemporaryDirectory(prefix="skill_eval_") as temp_dir:
        temp_path = Path(temp_dir)
        jobs_path = temp_path / "evaluation_jobs.csv"
        ground_truth_path = temp_path / "ground_truth.csv"

        # Keep title, description, and requirements separate. Evaluation modules
        # build the same combined text using src.extraction.input_text.
        columns = [
            column for column in (
                "job_id", "job_description", "requirements",
                "job_title_raw", "job_title", "description_source",
            )
            if column in jobs_df.columns
        ]
        jobs_df[columns].to_csv(jobs_path, index=False, encoding="utf-8")
        ground_truth_path.write_bytes(ground_truth_bytes)

        command = [
            sys.executable, "-m", module_name,
            str(jobs_path), str(ground_truth_path),
        ]
        if semantic_threshold is not None:
            command.extend(["--semantic-threshold", str(semantic_threshold)])

        return subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
            check=False,
        )


# Load master jobs, but do not prevent uploaded-file extraction if the master is empty.
try:
    master_jobs = _prepare_jobs(get_master_jobs())
    master_load_error = None
except Exception as exc:
    master_jobs = pd.DataFrame()
    master_load_error = str(exc)

source_mode = st.radio(
    "Extraction source",
    options=["Master database", "Upload jobs CSV"],
    horizontal=True,
    key="extract_source_mode",
)

uploaded_jobs_df = None
if source_mode == "Upload jobs CSV":
    uploaded_jobs_file = st.file_uploader(
        "Upload jobs CSV",
        type=["csv"],
        key="extract_jobs_csv",
        help=(
            "Use the same cleaned jobs CSV that you publish to the master database. "
            "The requirements column is retained if present."
        ),
    )
    if uploaded_jobs_file is not None:
        try:
            uploaded_jobs_df = _prepare_jobs(
                pd.read_csv(io.BytesIO(uploaded_jobs_file.getvalue()), dtype=str)
            )
        except Exception as exc:
            st.error(f"Could not prepare uploaded jobs CSV: {exc}")
else:
    if master_load_error:
        st.error(f"Could not load the master dataset: {master_load_error}")
    elif master_jobs.empty:
        st.info("The master database is empty. Publish jobs on the Master Dataset page first.")

if source_mode == "Master database":
    source_jobs = master_jobs
    source_label = "master database"
else:
    source_jobs = uploaded_jobs_df if uploaded_jobs_df is not None else pd.DataFrame()
    source_label = "uploaded CSV"

eligible_jobs = _eligible_jobs(source_jobs) if not source_jobs.empty else pd.DataFrame()

if not source_jobs.empty:
    st.caption(
        f"Source: {source_label} · {len(source_jobs):,} jobs · "
        f"{len(eligible_jobs):,} eligible for extraction"
    )
    if "requirements" not in source_jobs.columns:
        st.warning(
            "This input has no requirements column. Extraction will use the title "
            "and job description only. If the uploaded source has requirements, "
            "update the database import/schema and re-import it."
        )

# Calibration and evaluation operate on the selected source, not an unrelated dataset.
with st.expander("Calibration and evaluation", expanded=False):
    st.warning(
        "Upload ground truth whose job_id values match the selected source. "
        "Do not use requirements as input when those same requirements were "
        "created directly from the ground-truth labels; that would leak labels."
    )
    ground_truth_file = st.file_uploader(
        "Ground-truth CSV",
        type=["csv"],
        key="extract_ground_truth_csv",
        help="Expected columns: job_id and skill_id, one row per expected skill.",
    )

    calibration_col, evaluation_col = st.columns(2)
    with calibration_col:
        calibrate_clicked = st.button(
            "Calibrate semantic threshold",
            use_container_width=True,
            disabled=ground_truth_file is None or eligible_jobs.empty,
        )
    with evaluation_col:
        evaluate_clicked = st.button(
            "Evaluate extraction",
            use_container_width=True,
            disabled=ground_truth_file is None or eligible_jobs.empty,
        )

    if calibrate_clicked and ground_truth_file is not None:
        with st.spinner("Calibrating semantic threshold..."):
            try:
                result = _run_evaluation_command(
                    "src.extraction.evaluation.calibrate",
                    eligible_jobs,
                    ground_truth_file.getvalue(),
                )
                st.session_state["calibration_stdout"] = result.stdout
                st.session_state["calibration_stderr"] = result.stderr
                st.session_state["calibration_returncode"] = result.returncode
                if result.returncode == 0:
                    match = re.search(
                        r"Threshold\s*:\s*([0-9]*\.?[0-9]+)",
                        result.stdout,
                        flags=re.IGNORECASE,
                    )
                    if match:
                        best_threshold = float(match.group(1))
                        st.session_state["calibrated_threshold"] = best_threshold
                        st.session_state["semantic_threshold"] = best_threshold
                else:
                    st.error("Calibration failed. See output below.")
            except subprocess.TimeoutExpired:
                st.error("Calibration exceeded the 15-minute time limit.")
            except Exception as exc:
                st.error(f"Could not run calibration: {exc}")

    if evaluate_clicked and ground_truth_file is not None:
        threshold_for_eval = float(st.session_state.get("semantic_threshold", 0.45))
        with st.spinner("Evaluating lexical and semantic extraction..."):
            try:
                result = _run_evaluation_command(
                    "src.extraction.evaluation.evaluate",
                    eligible_jobs,
                    ground_truth_file.getvalue(),
                    semantic_threshold=threshold_for_eval,
                )
                st.session_state["evaluation_stdout"] = result.stdout
                st.session_state["evaluation_stderr"] = result.stderr
                st.session_state["evaluation_returncode"] = result.returncode
                st.session_state["evaluation_threshold"] = threshold_for_eval
                if result.returncode != 0:
                    st.error("Evaluation failed. See output below.")
            except subprocess.TimeoutExpired:
                st.error("Evaluation exceeded the 15-minute time limit.")
            except Exception as exc:
                st.error(f"Could not run evaluation: {exc}")

    if "calibrated_threshold" in st.session_state:
        st.info(
            f"Most recent calibrated threshold: "
            f"{st.session_state['calibrated_threshold']:.2f}. "
            "The semantic threshold slider has been updated."
        )
    if "calibration_stdout" in st.session_state:
        st.markdown("**Calibration output**")
        st.code(st.session_state["calibration_stdout"], language="text")
        if st.session_state.get("calibration_stderr"):
            st.code(st.session_state["calibration_stderr"], language="text")
    if "evaluation_stdout" in st.session_state:
        st.markdown(
            f"**Evaluation output** (threshold "
            f"{st.session_state.get('evaluation_threshold', 0.45):.2f})"
        )
        st.code(st.session_state["evaluation_stdout"], language="text")
        if st.session_state.get("evaluation_stderr"):
            st.code(st.session_state["evaluation_stderr"], language="text")

st.session_state.setdefault("semantic_threshold", 0.45)
with st.container(border=True):
    threshold = st.slider(
        "Semantic threshold",
        min_value=0.30,
        max_value=0.85,
        step=0.05,
        key="semantic_threshold",
        help="Calibration updates this value; extraction uses the currently selected threshold.",
    )
    extract_clicked = st.button(
        "Run Lexical + Semantic Extraction",
        use_container_width=True,
        disabled=eligible_jobs.empty,
    )

if extract_clicked:
    from src.extraction.run_extraction import run_extraction

    with st.spinner(f"Running extraction on the {source_label}..."):
        try:
            extracted_df = run_extraction(
                input_df=eligible_jobs,
                taxonomy_path=TAXONOMY_PATH,
                semantic_threshold=float(threshold),
            )
            st.session_state["extracted_df"] = extracted_df
            st.session_state["extraction_completed"] = True
            st.session_state["extraction_threshold"] = float(threshold)
            st.session_state["extraction_source_label"] = source_label
            st.session_state["extraction_source_mode"] = source_mode
            st.session_state["extraction_saved_run_id"] = None

            output_filename = (
                "jobs_extracted_upload.csv"
                if source_mode == "Upload jobs CSV"
                else "jobs_extracted.csv"
            )
            output_path = PROJECT_ROOT / "data" / "processed" / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            extracted_df.to_csv(output_path, index=False, encoding="utf-8")
            st.success(f"Extraction completed for {source_label}.")
        except Exception as exc:
            st.error(f"Skill extraction failed: {exc}")

if st.session_state.get("extraction_completed", False):
    extracted_df = st.session_state.get("extracted_df")
    if extracted_df is None or extracted_df.empty:
        st.info("No extraction results are available.")
        st.stop()

    extracted_df = extracted_df.copy()
    result_source = st.session_state.get("extraction_source_label", "selected source")
    result_mode = st.session_state.get("extraction_source_mode", "Master database")
    result_threshold = float(st.session_state.get("extraction_threshold", 0.45))

    st.subheader("Extraction Results")
    st.caption(
        f"{len(extracted_df):,} jobs · Source: {result_source} · "
        f"Semantic threshold: {result_threshold:.2f}"
    )

    st.divider()
    if result_mode == "Master database":
        st.subheader("Save results to the master database")
        st.write(
            "Saving links extracted skill mentions to existing master job records. "
            "Only results produced from the master database can be saved here."
        )
        already_saved_run = st.session_state.get("extraction_saved_run_id")
        if already_saved_run:
            st.success(f"These results were saved under run ID: {already_saved_run}")
        elif st.button(
            "Save lexical and semantic results",
            type="primary",
            use_container_width=True,
        ):
            try:
                if (
                    "source_url" not in extracted_df.columns
                    or extracted_df["source_url"].fillna("").astype(str).str.strip().eq("").any()
                ):
                    st.error(
                        "Some rows have no source_url. Cannot safely link every result "
                        "to master jobs."
                    )
                    st.stop()

                run_id = record_extraction_run(
                    run_type="lexical_and_semantic",
                    model_name="SBERT",
                    semantic_threshold=result_threshold,
                    source_batch_id=None,
                    notes="Lexical and semantic extraction from the master dataset",
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
                    f"Saved run {run_id}. Lexical mentions: {lexical_count:,}; "
                    f"semantic mentions: {semantic_count:,}."
                )
            except Exception as exc:
                st.error(f"Could not save extraction results: {exc}")
    else:
        st.info("Results from an uploaded CSV are not saved to the master database.")

    st.divider()
    display_cols = [
        column for column in (
            "job_id", "job_title_raw", "company",
            "lexical_skills", "semantic_skills",
        )
        if column in extracted_df.columns
    ]
    headers = [html.escape(column.replace("_", " ").title()) for column in display_cols]
    rows = []
    for _, row in extracted_df.iterrows():
        cells = []
        for column in display_cols:
            value = row.get(column, "")
            if pd.isna(value):
                value = ""
            value = str(value)

            if column in ("lexical_skills", "semantic_skills"):
                try:
                    skills = json.loads(value)
                    if not isinstance(skills, list):
                        skills = []
                except (json.JSONDecodeError, TypeError):
                    skills = []
                # Separators ensure adjacent skills remain readable.
                display_value = ", ".join(str(skill) for skill in skills) if skills else "None"
                cells.append(html.escape(display_value))
            elif column == "job_id":
                cells.append(f"<code>{html.escape(value)}</code>")
            else:
                if len(value) > 40:
                    value = value[:37] + "..."
                cells.append(html.escape(value))
        rows.append(cells)

    st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)
    st.download_button(
        label="Download enriched dataset",
        data=extracted_df.to_csv(index=False, encoding="utf-8"),
        file_name="jobs_extracted.csv",
        mime="text/csv",
    )
