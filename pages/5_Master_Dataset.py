"""Master dataset: import, inspect, and export persistent job records."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app_shared import render_page_shell
from src.database.connection import initialize_database, DB_PATH
from src.database.repository import (
    import_jobs_dataframe,
    get_master_jobs,
    get_database_summary,
)

st.set_page_config(
    page_title="Master Dataset — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

render_page_shell()
st.subheader("Master Dataset")
st.caption("Persistent SQL storage for cleaned job advertisements and their extraction history.")

try:
    initialize_database()
    summary = get_database_summary()
except Exception as exc:
    st.error(f"Could not initialize the master database: {exc}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Master jobs", summary["jobs"])
c2.metric("Job versions", summary["versions"])
c3.metric("Skill mentions", summary["skill_mentions"])
c4.metric("Extraction runs", summary["extraction_runs"])

st.caption(f"SQLite database file: `{DB_PATH}`")

st.markdown("### Publish cleaned jobs")
st.write(
    "Choose the cleaned dataset from this session or upload a prepared CSV. "
    "Rows need a source URL; duplicate URLs are matched to existing jobs."
)

source_choice = st.radio(
    "Import source",
    ["Current session cleaned data", "Upload cleaned CSV"],
    horizontal=True,
)

import_df = pd.DataFrame()
if source_choice == "Current session cleaned data":
    session_df = st.session_state.get("clean_df", pd.DataFrame())
    if not isinstance(session_df, pd.DataFrame):
        session_df = pd.DataFrame()
    import_df = session_df.copy()
    if import_df.empty:
        st.info("No cleaned data is available in the current session. Run the Clean Data page first or upload a CSV.")
else:
    uploaded = st.file_uploader("Upload cleaned jobs CSV", type=["csv"])
    if uploaded is not None:
        try:
            import_df = pd.read_csv(uploaded, dtype=str).fillna("")
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}")

if not import_df.empty:
    st.write(f"Import preview: {len(import_df)} rows")
    st.dataframe(import_df.head(100), use_container_width=True, hide_index=True)

    url_candidates = [c for c in ["source_url", "job_url", "url"] if c in import_df.columns]
    if not url_candidates:
        st.error("No source URL column found. Expected one of: source_url, job_url, url.")
    else:
        with st.expander("Import behaviour"):
            st.markdown(
                "- New URLs are inserted as new jobs.\n"
                "- Existing URLs with unchanged content are skipped as duplicates.\n"
                "- Existing URLs with changed content update the current record and create a historical version.\n"
                "- Rows without a usable source URL are counted as failed.\n"
                "- Re-importing the same file should not create duplicate jobs."
            )

        if st.button("Publish jobs to master database", type="primary"):
            try:
                result = import_jobs_dataframe(import_df, source_name=source_choice)
                st.success("Import finished.")
                st.json(result)
                st.rerun()
            except Exception as exc:
                st.error(f"Import failed: {exc}")

st.markdown("### Browse master jobs")
master_df = get_master_jobs()
if master_df.empty:
    st.info("The master database is empty. Publish cleaned jobs above to begin.")
else:
    query = st.text_input("Search title, company, country, or URL")
    filtered = master_df.copy()
    if query.strip():
        q = query.strip()
        searchable = ["job_title", "company_name", "country", "source_url", "source_platform"]
        mask = pd.Series(False, index=filtered.index)
        for col in searchable:
            if col in filtered.columns:
                mask |= filtered[col].fillna("").astype(str).str.contains(q, case=False, regex=False)
        filtered = filtered[mask]

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        column_config={
            "source_url": st.column_config.LinkColumn("Source URL"),
            "job_description": st.column_config.TextColumn("Job description", width="large"),
        },
    )

    st.download_button(
        "Export master jobs CSV",
        data=filtered.to_csv(index=False, encoding="utf-8"),
        file_name="master_jobs_export.csv",
        mime="text/csv",
    )
