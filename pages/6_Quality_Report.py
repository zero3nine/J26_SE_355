"""Dashboard page: Quality Report."""
import streamlit as st

st.set_page_config(
    page_title="Quality Report — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import current_dir, render_page_shell
from src.cleaning.validate_jobs import run_validation_pipeline
from src.evaluation.dashboard_data import get_benchmark_accuracy_summary_for_quality_tab
from theme import render_validation_checklist

render_page_shell()

if not st.session_state.cleaning_completed:
    st.info("Please execute the data cleaning step on the 'Clean Data' tab to compile the quality report.")
else:
    st.subheader("Data quality assessment")

    # Run validation pipeline dynamically
    report_runs, metrics, report_md = run_validation_pipeline(
        st.session_state.raw_df,
        st.session_state.clean_internal_df,
        st.session_state.clean_df
    )

    # Persist report to file system
    reports_dir = current_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"data_quality_report_{st.session_state.collection_batch_id}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_md)

    # Display checks list using custom checklist helper
    st.subheader("Pipeline validation status checks")
    st.markdown(render_validation_checklist(report_runs), unsafe_allow_html=True)

    # Cross-reference with Ground-Truth Scraping Accuracy Benchmark (Tab 11)
    st.write("---")
    st.subheader("Scraping Accuracy Benchmark Cross-Reference")
    acc_summary = get_benchmark_accuracy_summary_for_quality_tab()
    if acc_summary:
        st.markdown(f"""
        <div class="console-card" style="padding: 16px; margin-bottom: 16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:12px; font-weight:600; text-transform:uppercase; color:var(--admin-muted);">Independently Verified Benchmark Metrics</span>
                <span class="status-pill success">Benchmark N = {acc_summary['total_benchmark']}</span>
            </div>
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 12px;">
                <div><span style="color:var(--admin-muted); font-size:12px;">Title Agreement:</span> <strong style="color:var(--admin-positive); font-size:16px;">{acc_summary['title_agreement']:.1f}%</strong></div>
                <div><span style="color:var(--admin-muted); font-size:12px;">Employer Agreement:</span> <strong style="color:var(--admin-positive); font-size:16px;">{acc_summary['employer_agreement']:.1f}%</strong></div>
                <div><span style="color:var(--admin-muted); font-size:12px;">Salary Disclosed Agree:</span> <strong style="color:var(--admin-positive); font-size:16px;">{acc_summary['salary_disclosed_agreement']:.1f}%</strong></div>
                <div><span style="color:var(--admin-muted); font-size:12px;">Macro Precision:</span> <strong style="color:var(--admin-primary); font-size:16px;">{acc_summary['macro_correctness']:.1f}%</strong></div>
            </div>
            <div style="font-size:11px; color:var(--admin-muted); margin-top:10px;">
                * Empirical accuracy metrics are evaluated against ground-truth reference advertisements in <strong>Tab 11: Scraping Accuracy & Validation</strong>, strictly separated from schema format checks.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No benchmark accuracy evaluation results found. See Tab 11 to run the evaluation.")

    st.write("---")

    # Display Markdown report preview inside custom document viewport card
    st.subheader("Report content preview")
    st.markdown('<div class="document-frame">', unsafe_allow_html=True)
    st.markdown(report_md)
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("") # Spacer

    # Download Markdown Quality Report
    batch_id = st.session_state.collection_batch_id
    st.download_button(
        label="📄 Download quality report (Markdown)",
        data=report_md,
        file_name=f"jobs_quality_report_{batch_id}.md",
        mime="text/markdown"
    )
