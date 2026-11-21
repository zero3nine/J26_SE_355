"""Dashboard page: Skill Relationship & Technology Stack Analysis."""
from contextlib import closing
from hashlib import sha256
import streamlit as st

st.set_page_config(
    page_title="Skill Relationship Analysis — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *  # noqa: F401,F403

render_page_shell()

from src.database.extraction_cohort import get_matched_extraction_dataset, list_matched_extraction_runs, research_run_options
from src.database.connection import DB_PATH, get_connection
from src.database.provenance import exclude_synthetic_jobs
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
            help="Combined mode unifies the lexical and semantic skills from the selected source.",
        )
        mode_map = {
            "Combined": "combined",
            "Lexical Skills": "lexical_skills",
            "Semantic Skills": "semantic_skills",
        }
        selected_mode = mode_map[skill_mode]

    is_db_source = "Master SQL Database" in selected_source
    run_id = None
    if is_db_source:
        with closing(get_connection()) as conn:
            runs = list_matched_extraction_runs(conn)
        labels = research_run_options(runs)
        selection = st.selectbox(
            "Extraction run", list(labels), format_func=labels.get, key="relationship_extraction_run",
        )
        run_id = selection if selection != "legacy" else None
    run_clicked = st.button("Run Skill Analysis", use_container_width=True, type="primary")

# -----------------------------------------------------------------------------
# DATABASE AND EMPTY STATE HANDLING
# -----------------------------------------------------------------------------

if is_db_source:
    if db_jobs == 0:
        st.warning("The Master Job Database is empty. Please collect and publish job advertisements on the 'Master Dataset' page first.")
        st.stop()

    if db_mentions == 0 and run_id is None:
        st.warning("Extraction Required: No extracted skills found in Master SQL Database (`data/master_jobs.sqlite3`).")
        extraction_available = semantic_extraction_available()
        st.info(f"The database contains **{db_jobs} collected job advertisements**. "
                "Run lexical and semantic skill extraction here or on the **Extract Skills** page to add skills.")
        if not extraction_available:
            st.info(SEMANTIC_EXTRACTION_SETUP)
        if st.button(
            "Run Skill Extraction on Master Jobs Now",
            type="primary",
            use_container_width=True,
            disabled=not extraction_available,
        ):
            with st.spinner("Running lexical & semantic skill extraction on master jobs..."):
                from src.extraction.run_extraction import run_extraction
                from src.database.repository import get_master_jobs
                master_df = exclude_synthetic_jobs(get_master_jobs())
                if master_df.empty:
                    st.info("There are no master jobs eligible for extraction in this scope.")
                    st.stop()
                result = run_extraction(
                    input_path=master_df,
                    taxonomy_path=current_dir / "config" / "skill_taxonomy.json",
                    semantic_threshold=0.58,
                    persist_to_db=True,
                )
                if "extraction_run_id" in result:
                    st.success("Extraction completed and persisted to Master Database!")
                    st.rerun()
                else:
                    st.error("Extraction did not save a complete run. Check the application log and retry.")
        st.stop()

    if run_id is not None:
        try:
            with closing(get_connection()) as conn:
                jobs_df = get_matched_extraction_dataset(conn, run_id)
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
        scope_label = f"matched_{run_id}"
        st.caption(f"Matched cohort of {len(jobs_df):,} jobs. Support includes jobs with no skills from the selected method.")
    else:
        scope_label = "legacy_database"
        jobs_df = exclude_synthetic_jobs(get_extracted_skills_dataset())
        st.caption("Legacy support is conditional on a job having at least one selected skill.")
else:
    if not has_csv:
        st.info("Session CSV not found. Please run the skill extraction pipeline on the 'Extract Skills' page first.")
        st.stop()
    scope_label = "session_csv"
    try:
        jobs_df = exclude_synthetic_jobs(pd.read_csv(csv_path))
    except Exception:
        jobs_df = pd.DataFrame()

# Use one snapshot for the cache, statistics, and supporting advertisements.
source_digest = sha256(jobs_df.to_json(orient="split", index=False, date_format="iso").encode("utf-8")).hexdigest()
source_fingerprint = f"{scope_label}_{source_digest}"

# Check dataset stats
try:
    _, summary_report = load_jobs(
        jobs_df, skill_mode=selected_mode, include_jobs_without_skills=run_id is not None,
    )
    jobs_available = summary_report.get("jobs_with_selected_skills", 0)
    total_unique = summary_report.get("unique_skills", 0)
except Exception:
    jobs_available, total_unique = 0, 0
    summary_report = {}

# Handle changed dataset mtime / fingerprint
if "analytics_source_mtime" in st.session_state and st.session_state.analytics_source_mtime not in (0, source_fingerprint):
    st.session_state.analytics_report = None
    st.info("The dataset has changed since the last analysis run. Click 'Run Skill Analysis' to recompute.")

scope_dir = sha256(source_fingerprint.encode("utf-8")).hexdigest()[:24]
output_dir = current_dir / "data" / "analytics" / "runs" / scope_dir
mode_dir = output_dir / selected_mode
if jobs_available and (mode_dir / "cooccurrence_matrix.csv").is_file():
    if ("analytics_report" not in st.session_state or 
        st.session_state.analytics_report is None or 
        st.session_state.get("analytics_mode") != selected_mode):
        try:
            rep = summary_report.copy()
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
        try:
            report = run_analysis(
                input_path=jobs_df, output_dir=output_dir, skill_mode=selected_mode,
                run_id=run_id, include_jobs_without_skills=run_id is not None,
            )
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
        <div class="kpi-label">Postings with selected skills</div>
        <div class="kpi-value">{jobs_available}</div>
        <div class="kpi-trend"><span class="trend-up">N={len(jobs_df) if run_id is not None else jobs_available} analyzed</span></div>
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
        <div class="kpi-trend"><span class="trend-up" style="color: var(--admin-purple);">Size 2, 3, 4 bundles</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# RENDER THE 6 SECTIONS AS TABS IN THE MAIN VIEW
# -----------------------------------------------------------------------------

if (st.session_state.get("analytics_report") and st.session_state.analytics_mode == selected_mode
        and st.session_state.analytics_report.get("status") == "complete"):
    render_all_analytics(
        report=st.session_state.analytics_report,
        mode=st.session_state.analytics_mode,
        output_dir=output_dir,
        jobs_df=jobs_df,
    )
elif not run_clicked:
    # If report is not yet populated in session state, run analysis automatically
    with st.spinner(f"Initializing {selected_mode} analytics pipeline..."):
        try:
            report = run_analysis(
                input_path=jobs_df, output_dir=output_dir, skill_mode=selected_mode,
                run_id=run_id, include_jobs_without_skills=run_id is not None,
            )
            st.session_state.analytics_report = report
            st.session_state.analytics_mode = selected_mode
            st.session_state.analytics_source_mtime = source_fingerprint
            if report.get("status") == "complete":
                render_all_analytics(report=report, mode=selected_mode, output_dir=output_dir, jobs_df=jobs_df)
            else:
                st.info("No technical skill mentions are available for this selection.")
        except Exception as e:
            st.error(f"Failed to initialize analytics: {e}")
