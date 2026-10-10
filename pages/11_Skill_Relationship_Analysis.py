"""Dashboard page: Skill Relationship & Technology Stack Analysis."""
import importlib
from pathlib import Path
import streamlit as st

st.set_page_config(
    page_title="Skill Relationship Analysis — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *  # noqa: F401,F403

render_page_shell()

# Dynamic reload to ensure newest updates are immediately picked up
import src.analytics.cooccurrence
import src.analytics.similarity
import src.analytics.association_rules
import src.analytics.technology_stacks
import src.analytics.network
import src.analytics.dashboard
import src.analytics.run_analysis
import src.database.connection
import src.database.repository

importlib.reload(src.database.connection)
importlib.reload(src.database.repository)
importlib.reload(src.analytics.cooccurrence)
importlib.reload(src.analytics.similarity)
importlib.reload(src.analytics.association_rules)
importlib.reload(src.analytics.technology_stacks)
importlib.reload(src.analytics.network)
importlib.reload(src.analytics.dashboard)
importlib.reload(src.analytics.run_analysis)

from src.database.connection import DB_PATH
from src.database.repository import get_database_summary, get_extracted_skills_dataset

from src.analytics.run_analysis import run_analysis, load_jobs
from src.analytics.dashboard import render_all_analytics

# Header
st.subheader("Skill Relationship & Technology Stack Analysis")
st.caption("Quantitative analysis of skill co-occurrence, multi-skill technology stack mining, and ecosystem network topology.")

# -----------------------------------------------------------------------------
# DATABASE AND SOURCE CONFIGURATION (Main Page Container)
# -----------------------------------------------------------------------------

summary = get_database_summary()
db_jobs = summary.get("jobs", 0)
db_mentions = summary.get("skill_mentions", 0)
db_runs = summary.get("extraction_runs", 0)
csv_path = current_dir / "data" / "processed" / "jobs_extracted.csv"
has_csv = csv_path.exists()

with st.container(border=True):
    col_src, col_mode = st.columns(2)
    with col_src:
        source_options = [f"Master SQL Database ({DB_PATH.name})"]
        if has_csv:
            source_options.append("Session CSV (data/processed/jobs_extracted.csv)")

        selected_source = st.radio(
            "Analytics Data Source:",
            source_options,
            horizontal=True,
            key="sec_analytics_source",
        )
    with col_mode:
        skill_mode = st.radio(
            "Skill Extraction Mode:",
            ["Combined", "Lexical Skills", "Semantic Skills"],
            horizontal=True,
            key="sec_skill_mode",
            help="Combined mode unifies lexical taxonomy matches with semantic embedding similarity (τ ≥ 0.58).",
        )
        mode_map = {
            "Combined": "combined",
            "Lexical Skills": "lexical_skills",
            "Semantic Skills": "semantic_skills",
        }
        selected_mode = mode_map[skill_mode]

    run_clicked = st.button("Run Skill Analysis", use_container_width=True, type="primary")

is_db_source = "Master SQL Database" in selected_source

# -----------------------------------------------------------------------------
# DATABASE AND EMPTY STATE HANDLING
# -----------------------------------------------------------------------------

if is_db_source:
    if db_jobs == 0:
        st.warning("The Master Job Database is empty. Please collect and publish job advertisements on the 'Master Dataset' page first.")
        st.stop()

    if db_mentions == 0:
        st.warning("Extraction Required: No extracted skills found in Master SQL Database (`data/master_jobs.sqlite3`).")
        st.info(
            f"The database currently contains **{db_jobs} collected job advertisements**, but no skills have been recorded in the `extracted_skills` table yet.\n\n"
            "Please run lexical and semantic skill extraction on the **'Extract Skills'** page, or click the button below to extract skills directly for all master jobs."
        )
        if st.button("Run Skill Extraction on Master Jobs Now", type="primary", use_container_width=True):
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
    jobs_df = get_extracted_skills_dataset()
else:
    if not has_csv:
        st.info("Session CSV not found. Please run the skill extraction pipeline on the 'Extract Skills' page first.")
        st.stop()
    input_target = csv_path
    source_fingerprint = str(csv_path.stat().st_mtime if csv_path.exists() else 0)
    try:
        jobs_df = pd.read_csv(csv_path)
    except Exception:
        jobs_df = pd.DataFrame()

# Check dataset stats
try:
    _, summary_report = load_jobs(input_target, skill_mode=selected_mode)
    jobs_available = summary_report.get("jobs_with_selected_skills", 0)
    total_unique = summary_report.get("unique_skills", 0)
except Exception:
    jobs_available, total_unique = 0, 0
    summary_report = {}

# Handle changed dataset mtime / fingerprint
if "analytics_source_mtime" in st.session_state and st.session_state.analytics_source_mtime not in (0, source_fingerprint):
    st.session_state.analytics_report = None
    st.info("The dataset has changed since the last analysis run. Click 'Run Skill Analysis' to recompute.")

mode_dir = current_dir / "data" / "analytics" / selected_mode
if mode_dir.exists() and (mode_dir / "cooccurrence_matrix.csv").exists():
    if ("analytics_report" not in st.session_state or 
        st.session_state.analytics_report is None or 
        st.session_state.get("analytics_mode") != selected_mode):
        try:
            _, rep = load_jobs(input_target, skill_mode=selected_mode, normalize=True)
            rep["status"] = "complete"
            rep["skill_pairs"] = len(pd.read_csv(mode_dir / "skill_pairs.csv")) if (mode_dir / "skill_pairs.csv").exists() else 0
            rep["association_rules_generated"] = (mode_dir / "association_rules.csv").exists()
            rep["technology_stacks_generated"] = (mode_dir / "technology_stacks.csv").exists()
            st.session_state.analytics_report = rep
            st.session_state.analytics_mode = selected_mode
            st.session_state.analytics_source_mtime = source_fingerprint
        except Exception:
            pass

if run_clicked:
    with st.spinner(f"Running {selected_mode} analytics pipeline on {selected_source}..."):
        output_dir = current_dir / "data" / "analytics"
        try:
            report = run_analysis(input_path=input_target, output_dir=output_dir, skill_mode=selected_mode)
            st.session_state.analytics_report = report
            st.session_state.analytics_mode = selected_mode
            st.session_state.analytics_source_mtime = source_fingerprint

            if report.get("status") == "insufficient_data":
                st.warning("No technical skills are currently available for analysis. The job advertisements contain no usable technical skills.")
            else:
                st.success(f"Analysis completed successfully for {selected_mode}.")
                st.rerun()
        except Exception as e:
            st.error(f"Analysis failed: {e}")

# Executive KPI Summary Cards
active_rep = st.session_state.get("analytics_report", {})
pair_count = active_rep.get("skill_pairs", 0) if active_rep else 0
if pair_count == 0 and mode_dir.exists() and (mode_dir / "skill_pairs.csv").exists():
    try:
        pair_count = len(pd.read_csv(mode_dir / "skill_pairs.csv"))
    except Exception:
        pair_count = 0

stacks_count = 0
if mode_dir.exists() and (mode_dir / "technology_stacks.csv").exists():
    try:
        stacks_count = len(pd.read_csv(mode_dir / "technology_stacks.csv"))
    except Exception:
        stacks_count = 0

st.markdown(f"""
<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
    <div class="kpi-card clean">
        <div class="kpi-label">Eligible IT Postings</div>
        <div class="kpi-value">{jobs_available}</div>
        <div class="kpi-trend"><span class="trend-up">N={jobs_available} analyzed</span></div>
    </div>
    <div class="kpi-card scraped">
        <div class="kpi-label">Canonical Skills</div>
        <div class="kpi-value">{total_unique}</div>
        <div class="kpi-trend"><span class="trend-up">Taxonomy entities</span></div>
    </div>
    <div class="kpi-card partial">
        <div class="kpi-label">Skill Pairs Analyzed</div>
        <div class="kpi-value">{pair_count:,}</div>
        <div class="kpi-trend"><span class="trend-neutral">Co-occurrence pairs</span></div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Technology Stacks</div>
        <div class="kpi-value">{stacks_count:,}</div>
        <div class="kpi-trend"><span class="trend-up" style="color: #A78BFA;">Size 2, 3, 4 bundles</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# RENDER THE 6 SECTIONS AS TABS IN THE MAIN VIEW
# -----------------------------------------------------------------------------

if "analytics_report" in st.session_state and st.session_state.analytics_report and st.session_state.analytics_report.get("status") == "complete":
    render_all_analytics(
        report=st.session_state.analytics_report,
        mode=st.session_state.analytics_mode,
        output_dir=current_dir / "data" / "analytics",
        jobs_df=jobs_df,
    )
else:
    # If report is not yet populated in session state, run analysis automatically
    with st.spinner(f"Initializing {selected_mode} analytics pipeline..."):
        output_dir = current_dir / "data" / "analytics"
        try:
            report = run_analysis(input_path=input_target, output_dir=output_dir, skill_mode=selected_mode)
            st.session_state.analytics_report = report
            st.session_state.analytics_mode = selected_mode
            st.session_state.analytics_source_mtime = source_fingerprint
            render_all_analytics(
                report=report,
                mode=selected_mode,
                output_dir=output_dir,
                jobs_df=jobs_df,
            )
        except Exception as e:
            st.error(f"Failed to initialize analytics: {e}")
