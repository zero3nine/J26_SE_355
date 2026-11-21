"""Local publication controls; public visitors use the independent web app."""
import os
import tempfile
from pathlib import Path

import streamlit as st
from theme import THEME_CSS

from public_dashboard.publication import publish, synthetic_records
from tools.publish_dashboard import from_master
from src.database.connection import DB_PATH, get_connection, initialize_database
from src.database.extraction_cohort import list_matched_extraction_runs

st.set_page_config(page_title="Public Dashboard", page_icon="◈", layout="wide")
st.markdown(THEME_CSS, unsafe_allow_html=True)
st.title("SkillScope · Public dashboard")
st.write("The public dashboard runs independently of these research tools. Publish a separate, sanitized snapshot here, then deploy only the dashboard and that snapshot.")
st.link_button("Open SkillScope dashboard ↗", os.environ.get("PUBLIC_DASHBOARD_URL", "http://localhost:8080"), type="primary")
st.code("python -m public_dashboard.app", language="bash")

output = Path(__file__).resolve().parents[1] / "data/public/dashboard.sqlite3"
st.subheader("Prepare the public dataset")
mode = st.radio("Publication source", ["Synthetic demonstration", "Reviewed extraction cohort"], horizontal=True)
if mode == "Synthetic demonstration":
    st.info("Creates 4,896 synthetic advertisements across four markets and 36 months. This replaces only the separate public snapshot; the master research database is untouched.")
    if st.button("Publish synthetic demonstration"):
        with st.spinner("Preparing public data and baseline outlooks..."):
            metadata = publish(synthetic_records(), output, {
                "title": "SkillScope demonstration · November 2023–October 2026", "is_synthetic": True,
                "provenance": "Deterministic synthetic advertisements; seed 355. No empirical findings.",
                "configuration": "Synthetic v1; matched extraction methods; 36 months; 4 markets; 5 career areas.",
            })
        st.success(f"Published {metadata['job_count']:,} synthetic jobs. Refresh the public dashboard.")
else:
    initialize_database()
    conn = get_connection()
    try:
        runs = list_matched_extraction_runs(conn)
    finally:
        conn.close()
    if runs.empty:
        st.info("Save a matched lexical and semantic extraction run before preparing a reviewed publication.")
        st.stop()
    run_id = st.selectbox("Matched lexical/semantic extraction run", runs["run_id"].tolist())
    title = st.text_input("Publication title")
    provenance = st.text_area("Source coverage, review protocol, and known limitations")
    st.write("Upload a reviewed cohort CSV with job_id, lexical_completed, and semantic_completed columns. Mark both completion fields true only for jobs successfully processed by both methods in this run, including genuine zero-skill results.")
    cohort = st.file_uploader("Reviewed cohort CSV", type=["csv"])
    st.caption("Publication verifies recorded completion and current inputs for each approved job. Only jobs marked empirical can be published here.")
    if st.button("Publish reviewed cohort", disabled=not (title.strip() and provenance.strip() and cohort)):
        try:
            with tempfile.TemporaryDirectory() as directory:
                file = Path(directory) / "cohort.csv"
                file.write_bytes(cohort.getvalue())
                records, metadata = from_master(DB_PATH, run_id, file)
                metadata.update(title=title.strip(), provenance=provenance.strip(), is_synthetic=False)
                result = publish(records, output, metadata)
            st.success(f"Published {result['job_count']:,} jobs as snapshot {result['snapshot_id']}. Refresh the public dashboard.")
        except Exception as exc:
            st.error(f"Publication failed; the previous snapshot is retained. {exc}")

st.caption(f"Publication output: {output}")
st.caption("The public process reads this snapshot only. It cannot import records, edit data, or access the master database through its API.")
