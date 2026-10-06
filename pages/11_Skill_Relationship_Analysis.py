"""Dashboard page: Skill Analysis."""
import importlib
import streamlit as st

st.set_page_config(
    page_title="Skill Relationship Analysis — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *  # noqa: F401,F403

render_page_shell()

st.subheader("Skill Relationship & Technology Stack Analysis")

# Load helper functions locally with dynamic reload to ensure latest updates
import src.analytics.cooccurrence
import src.analytics.similarity
import src.analytics.association_rules
import src.analytics.technology_stacks
import src.analytics.network
import src.analytics.dashboard
import src.analytics.run_analysis
from src.database.connection import DB_PATH
from src.database.repository import get_database_summary

importlib.reload(src.analytics.cooccurrence)
importlib.reload(src.analytics.similarity)
importlib.reload(src.analytics.association_rules)
importlib.reload(src.analytics.technology_stacks)
importlib.reload(src.analytics.network)
importlib.reload(src.analytics.dashboard)
importlib.reload(src.analytics.run_analysis)

from src.analytics.run_analysis import run_analysis, load_jobs, load_jobs_from_database
from src.analytics.dashboard import render_all_analytics

st.markdown("""
<div style="background: linear-gradient(90deg, rgba(56, 189, 248, 0.08) 0%, rgba(99, 102, 241, 0.08) 100%); border-left: 3px solid #38BDF8; padding: 10px 14px; border-radius: 6px; margin-bottom: 14px; font-size: 13px; color: #E2E8F0;">
    <b style="color: #38BDF8;">Skill Relationship & Technology Stack Analysis</b><br/>
    <span style="color: #94A3B8; font-size: 12px;">
        Co-occurrence Matrix • Jaccard Similarity • Pointwise Mutual Information (PMI) • Directional Association Rules • Multi-Skill Technology Stacks • Network Graphs
    </span>
</div>
""", unsafe_allow_html=True)

# Inspect authoritative database status
summary = get_database_summary()
db_jobs = summary.get("jobs", 0)
db_mentions = summary.get("skill_mentions", 0)
db_runs = summary.get("extraction_runs", 0)
csv_path = current_dir / "data" / "processed" / "jobs_extracted.csv"
has_csv = csv_path.exists()

col_src, col_db_stat = st.columns([3, 2])
with col_src:
    source_options = [f"Authoritative Master SQL Database ({DB_PATH.name})"]
    if has_csv:
        source_options.append("Session CSV (data/processed/jobs_extracted.csv)")

    selected_source = st.radio(
        "Analytics Data Source:",
        source_options,
        horizontal=True,
    )

with col_db_stat:
    st.markdown(
        f"""<div style="font-size: 12px; color: #94A3B8; background: rgba(30, 41, 59, 0.5); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(148, 163, 184, 0.2);">
            <b>Master DB Status:</b> {DB_PATH.name}<br/>
            💼 Jobs: <b>{db_jobs}</b> | 🏷️ Skill Mentions: <b>{db_mentions}</b> | 🚀 Runs: <b>{db_runs}</b>
        </div>""",
        unsafe_allow_html=True,
    )

is_db_source = "Master SQL Database" in selected_source

if is_db_source:
    if db_jobs == 0:
        st.warning("⚠️ The Master Job Database is empty. Please scrape and publish jobs on the 'Master Dataset' page first.")
        st.stop()
    if db_mentions == 0:
        st.warning("⚠️ No extracted skills found in Master SQL Database (`data/master_jobs.sqlite3`).")
        st.info(
            f"The database currently contains **{db_jobs} master job advertisements**, but no skills have been recorded in the `extracted_skills` table yet.\n\n"
            "Please run lexical and semantic skill extraction on the **'Extract Skills'** tab, or click the button below to extract skills directly for all master jobs."
        )
        if st.button("⚡ Run Skill Extraction on Master Jobs Now", type="primary", use_container_width=True):
            with st.spinner("Running lexical & semantic skill extraction on master jobs..."):
                from src.extraction.run_extraction import run_extraction
                from src.database.repository import get_master_jobs
                master_df = get_master_jobs()
                run_extraction(
                    input_path=master_df,
                    taxonomy_path=current_dir / "config" / "skill_taxonomy.json",
                    semantic_threshold=0.58,
                    persist_to_db=True,
                )
                st.success("Extraction completed and persisted to Master Database!")
                st.rerun()
        st.stop()

    input_target = "database"
    source_fingerprint = f"db_{db_mentions}_{db_runs}"
else:
    if not has_csv:
        st.info("Please run the skill extraction pipeline on the 'Extract Skills' tab before analyzing skills.")
        st.stop()
    input_target = csv_path
    source_fingerprint = str(csv_path.stat().st_mtime if csv_path.exists() else 0)

# Determine current stats without running full analysis
try:
    _, summary_report = load_jobs(input_target, skill_mode="combined")
    jobs_available = summary_report.get("jobs_with_selected_skills", 0)
    jobs_lexical = summary_report.get("jobs_with_lexical_skills", 0)
    jobs_semantic = summary_report.get("jobs_with_semantic_skills", 0)
    total_unique = summary_report.get("unique_skills", 0)
except Exception:
    jobs_available, jobs_lexical, jobs_semantic, total_unique = 0, 0, 0, 0

if "analytics_source_mtime" in st.session_state and st.session_state.analytics_source_mtime != source_fingerprint:
    st.session_state.analytics_report = None
    st.warning("⚠️ The dataset has changed since the last analysis. Click '⚡ Run Skill Analysis' below to recompute.")

st.markdown(f"""
<div style="font-size: 13px; color: #94A3B8; margin-top: -6px; margin-bottom: 16px;">
    Target: <b>{'Authoritative Database' if is_db_source else 'Session CSV'}</b> | 
    Contains <b>{jobs_available}</b> jobs with technical skills 
    (Lexical: {jobs_lexical} | Semantic: {jobs_semantic}). Total unique terms: <b>{total_unique}</b>.
</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    skill_mode = st.radio(
        "Select Skill Mode for Analysis:",
        ["Lexical Skills", "Semantic Skills", "Combined"],
        horizontal=True
    )
    mode_map = {
        "Lexical Skills": "lexical_skills",
        "Semantic Skills": "semantic_skills",
        "Combined": "combined"
    }
    selected_mode = mode_map[skill_mode]

    run_clicked = st.button("⚡ Run Skill Analysis", use_container_width=True, type="primary")

    mode_dir = current_dir / "data" / "analytics" / selected_mode
    if mode_dir.exists() and (mode_dir / "cooccurrence_matrix.csv").exists():
        if ("analytics_report" not in st.session_state or 
            st.session_state.analytics_report is None or 
            st.session_state.get("analytics_mode") != selected_mode):
            try:
                jobs_data, rep = load_jobs(input_target, skill_mode=selected_mode, normalize=True)
                rep["status"] = "complete"
                rep["skill_pairs"] = len(pd.read_csv(mode_dir / "skill_pairs.csv")) if (mode_dir / "skill_pairs.csv").exists() else 0
                rep["association_rules_generated"] = (mode_dir / "association_rules.csv").exists()
                rep["technology_stacks_generated"] = (mode_dir / "technology_stacks.csv").exists()
                st.session_state.analytics_report = rep
                st.session_state.analytics_mode = selected_mode
                st.session_state.analytics_source_mtime = source_fingerprint
            except Exception:
                pass
    else:
        if st.session_state.get("analytics_source_mtime") != source_fingerprint:
            st.info(f"ℹ️ Precomputed analytical results on disk reflect an earlier dataset. Click **⚡ Run Skill Analysis** above to compute fresh relationships for **{skill_mode}** on the current dataset.")

if run_clicked:
    with st.spinner(f"Running {skill_mode} analytics pipeline on {selected_source}..."):
        output_dir = current_dir / "data" / "analytics"
        try:
            report = run_analysis(input_path=input_target, output_dir=output_dir, skill_mode=selected_mode)
            st.session_state.analytics_report = report
            st.session_state.analytics_mode = selected_mode
            st.session_state.analytics_source_mtime = source_fingerprint

            if report.get("status") == "insufficient_data":
                st.warning("No technical skills are currently available for analysis. The job advertisements were collected successfully, but the extracted skill fields contain no usable technical skills.")
            else:
                st.success(f"Analysis completed successfully for {skill_mode}.")
        except Exception as e:
            st.error(f"Analysis failed: {e}")

# Render Analytics Dashboard if report exists in session state
if "analytics_report" in st.session_state and st.session_state.analytics_report and st.session_state.analytics_report.get("status") == "complete":
    render_all_analytics(
        report=st.session_state.analytics_report,
        mode=st.session_state.analytics_mode,
        output_dir=current_dir / "data" / "analytics"
    )
