"""Dashboard page: Skill Analysis."""
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
    # Load helper functions locally
    from src.analytics.run_analysis import run_analysis, load_jobs
    from src.analytics.dashboard import render_all_analytics

    # Determine current stats without running full analysis
    try:
        _, summary_report = load_jobs(csv_path, skill_mode="combined")
        jobs_available = summary_report.get("jobs_with_selected_skills", 0)
        jobs_lexical = summary_report.get("jobs_with_lexical_skills", 0)
        jobs_semantic = summary_report.get("jobs_with_semantic_skills", 0)
        total_unique = summary_report.get("unique_skills", 0)
    except Exception as e:
        jobs_available, jobs_lexical, jobs_semantic, total_unique = 0, 0, 0, 0

    st.markdown(f"""
    <div style="font-size: 13px; color: #94A3B8; margin-top: -10px; margin-bottom: 16px;">
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

    if run_clicked:
        with st.spinner(f"Running {skill_mode} analytics pipeline..."):
            output_dir = current_dir / "data" / "analytics"
            try:
                report = run_analysis(input_path=csv_path, output_dir=output_dir, skill_mode=selected_mode)
                st.session_state.analytics_report = report
                st.session_state.analytics_mode = selected_mode

                if report.get("status") == "insufficient_data":
                    st.warning("No technical skills are currently available for analysis. The job advertisements were collected successfully, but the extracted skill fields contain no usable technical skills. Please run the extraction pipeline again after valid job descriptions are available.")
                else:
                    st.success(f"Analysis completed successfully for {skill_mode}.")
            except Exception as e:
                st.error(f"Analysis failed: {e}")

    # Render Analytics Dashboard if report exists in session state
    if "analytics_report" in st.session_state and st.session_state.analytics_report.get("status") == "complete":
        render_all_analytics(
            report=st.session_state.analytics_report,
            mode=st.session_state.analytics_mode,
            output_dir=current_dir / "data" / "analytics"
        )
