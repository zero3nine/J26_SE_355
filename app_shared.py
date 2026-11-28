"""Shared paths, session state, and Streamlit layout helpers."""
import pathlib
import sys
from importlib.util import find_spec

import pandas as pd
import streamlit as st

current_dir = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from theme import THEME_CSS, render_header, render_ssrf_banner


SEMANTIC_EXTRACTION_SETUP = (
    "To enable semantic extraction, calibration, and evaluation, rebuild with "
    "`ADMIN_INSTALL_EXTRACTION=true` for Docker or install "
    "`requirements-extraction.txt` in your local environment."
)


def semantic_extraction_available() -> bool:
    """Check for the optional packages without loading the model or its runtime."""
    return find_spec("sentence_transformers") is not None and find_spec("torch") is not None


DEFAULT_STATE = {
    "valid_urls": [],
    "rejected_urls": {},
    "raw_df": pd.DataFrame(),
    "clean_df": pd.DataFrame(),
    "clean_internal_df": pd.DataFrame(),
    "failures_df": pd.DataFrame(),
    "quality_report": "",
    "collection_batch_id": "",
    "scraping_completed": False,
    "cleaning_completed": False,
    "cleaning_stats": {},
    "scraping_confirmed": False,
    "extraction_completed": False,
    "extracted_df": pd.DataFrame(),
    "role_analysis_completed": False,
    "role_classified_df": pd.DataFrame(),
    "role_skill_freq_df": pd.DataFrame(),
    "current_run_id": "",
    "current_submitted_urls": [],
    "extracted_threshold": 0.45,
    "analytics_report": None,
    "analytics_mode": None,
    "analytics_run_id": "",
    "analytics_source_mtime": 0,
}

# Preserve additional state used by the scraping worker and analytics views.
EXTRA_STATE = {
    "scraping_active": False,
    "scraping_started": False,
    "scrape_logs": [],
    "crawl_progress": (0, 0, "Initializing..."),
    "crawl_thread_result": None,
    "run_config": {},
}

def init_session_state():
    """Ensure all required session state keys exist for the active Streamlit session."""
    for key, default in {**DEFAULT_STATE, **EXTRA_STATE}.items():
        if key not in st.session_state:
            st.session_state[key] = default.copy() if isinstance(default, (dict, list, pd.DataFrame)) else default


def open_collection_batch(batch_id, batch):
    """Replace the active workflow with a batch's persisted records."""
    for key in (
        "valid_urls", "rejected_urls", "failures_df", "quality_report", "cleaning_stats",
        "current_submitted_urls", "extracted_df", "extraction_completed", "extracted_threshold",
        "analytics_report", "analytics_mode", "analytics_run_id", "analytics_source_mtime",
        "role_analysis_completed", "role_classified_df", "role_skill_freq_df",
    ):
        default = DEFAULT_STATE[key]
        st.session_state[key] = default.copy() if isinstance(default, (dict, list, pd.DataFrame)) else default
    st.session_state.last_published_import_run_id = None
    st.session_state.extraction_saved_run_id = None
    st.session_state.current_run_id = batch_id
    st.session_state.collection_batch_id = batch_id
    st.session_state.scraping_completed = True
    st.session_state.raw_df = batch.raw
    st.session_state.clean_df = batch.cleaned if batch.cleaned is not None else pd.DataFrame()
    st.session_state.clean_internal_df = (
        batch.cleaned_internal if batch.cleaned_internal is not None else pd.DataFrame()
    )
    st.session_state.cleaning_completed = batch.cleaned is not None


init_session_state()

def render_page_shell():
    """Render shared branding on each multipage view."""
    init_session_state()
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    st.markdown(render_header(), unsafe_allow_html=True)
    st.markdown(render_ssrf_banner(), unsafe_allow_html=True)

def project_metrics():
    init_session_state()
    attempted = len(st.session_state.valid_urls)
    cleaned = len(st.session_state.clean_df)
    extracted = len(st.session_state.extracted_df)
    scraped = 0
    failed = len(st.session_state.rejected_urls)
    raw_df = st.session_state.raw_df
    if not raw_df.empty and "extraction_status" in raw_df.columns:
        status = raw_df["extraction_status"]
        scraped = int(status.isin(["success", "partial"]).sum())
        failed += int((~status.isin(["success", "partial", "manual_review"])).sum())
    return attempted, scraped, failed, cleaned, extracted
