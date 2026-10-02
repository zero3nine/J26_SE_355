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

csv_path = current_dir / "data" / "processed" / "jobs_extracted.csv"
if not csv_path.exists():
    st.info("Please run the skill extraction pipeline on the 'Extract Skills' tab before analyzing skills.")
else:
    # Load helper functions locally with dynamic reload to ensure latest updates
    import src.analytics.cooccurrence
    import src.analytics.similarity
    import src.analytics.association_rules
    import src.analytics.technology_stacks
    import src.analytics.network
    import src.analytics.dashboard
    import src.analytics.run_analysis

    importlib.reload(src.analytics.cooccurrence)
    importlib.reload(src.analytics.similarity)
    importlib.reload(src.analytics.association_rules)
    importlib.reload(src.analytics.technology_stacks)
    importlib.reload(src.analytics.network)
    importlib.reload(src.analytics.dashboard)
    importlib.reload(src.analytics.run_analysis)

    from src.analytics.run_analysis import run_analysis, load_jobs
    from src.analytics.dashboard import render_all_analytics

    st.markdown("""
    <div style="background: linear-gradient(90deg, rgba(56, 189, 248, 0.08) 0%, rgba(99, 102, 241, 0.08) 100%); border-left: 3px solid #38BDF8; padding: 10px 14px; border-radius: 6px; margin-bottom: 14px; font-size: 13px; color: #E2E8F0;">
        <b style="color: #38BDF8;">Skill Relationship & Technology Stack Analysis</b><br/>
        <span style="color: #94A3B8; font-size: 12px;">
            Co-occurrence Matrix • Jaccard Similarity • Pointwise Mutual Information (PMI) • Directional Association Rules • Multi-Skill Technology Stacks • Network Graphs
        </span>
    </div>
    """, unsafe_allow_html=True)

    # Determine current stats without running full analysis
    try:
        _, summary_report = load_jobs(csv_path, skill_mode="combined")
        jobs_available = summary_report.get("jobs_with_selected_skills", 0)
        jobs_lexical = summary_report.get("jobs_with_lexical_skills", 0)
        jobs_semantic = summary_report.get("jobs_with_semantic_skills", 0)
        total_unique = summary_report.get("unique_skills", 0)
    except Exception as e:
        jobs_available, jobs_lexical, jobs_semantic, total_unique = 0, 0, 0, 0

    current_csv_mtime = csv_path.stat().st_mtime if csv_path.exists() else 0
    if "analytics_source_mtime" in st.session_state and st.session_state.analytics_source_mtime != current_csv_mtime:
        st.session_state.analytics_report = None
        st.warning("⚠️ The extracted job dataset has changed since the last analysis. Click '⚡ Run Skill Analysis' below to recompute.")

    st.markdown(f"""
    <div style="font-size: 13px; color: #94A3B8; margin-top: -6px; margin-bottom: 16px;">
        Dataset contains <b>{jobs_available}</b> jobs with technical skills 
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

        run_clicked = st.button("⚡ Run Skill Analysis", use_container_width=True)

        mode_dir = current_dir / "data" / "analytics" / selected_mode
        if mode_dir.exists() and (mode_dir / "cooccurrence_matrix.csv").exists():
            if ("analytics_report" not in st.session_state or 
                st.session_state.analytics_report is None or 
                st.session_state.get("analytics_mode") != selected_mode):
                try:
                    jobs_data, rep = load_jobs(csv_path, skill_mode=selected_mode, normalize=True)
                    rep["status"] = "complete"
                    rep["skill_pairs"] = len(pd.read_csv(mode_dir / "skill_pairs.csv")) if (mode_dir / "skill_pairs.csv").exists() else 0
                    rep["association_rules_generated"] = (mode_dir / "association_rules.csv").exists()
                    rep["technology_stacks_generated"] = (mode_dir / "technology_stacks.csv").exists()
                    st.session_state.analytics_report = rep
                    st.session_state.analytics_mode = selected_mode
                    st.session_state.analytics_source_mtime = current_csv_mtime
                except Exception:
                    pass
        else:
            if st.session_state.get("analytics_source_mtime") != current_csv_mtime:
                st.info(f"ℹ️ Precomputed analytical results on disk reflect an earlier dataset. Click **⚡ Run Skill Analysis** above to compute fresh relationships for **{skill_mode}** on the current dataset.")

    if run_clicked:
        with st.spinner(f"Running {skill_mode} analytics pipeline..."):
            output_dir = current_dir / "data" / "analytics"
            try:
                report = run_analysis(input_path=csv_path, output_dir=output_dir, skill_mode=selected_mode)
                st.session_state.analytics_report = report
                st.session_state.analytics_mode = selected_mode
                st.session_state.analytics_source_mtime = current_csv_mtime

                if report.get("status") == "insufficient_data":
                    st.warning("No technical skills are currently available for analysis. The job advertisements were collected successfully, but the extracted skill fields contain no usable technical skills. Please run the extraction pipeline again after valid job descriptions are available.")
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
