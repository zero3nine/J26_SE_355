"""Shared imports, paths, session state, and dashboard helpers."""
import os
import sys
import pathlib
import json
import re
import urllib.parse
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
import threading
import time

current_dir = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from src.cleaning.clean_jobs import clean_raw_dataframe
from src.cleaning.validate_jobs import run_validation_pipeline
from src.roles.role_skill_analysis import classify_roles, build_role_skill_frequency_table
from src.security.url_validator import validate_url, is_approved_domain
from src.scraping.service import run_collection_pipeline
from src.scraping.models import RAW_SCHEMA_COLUMNS
from src.evaluation.dashboard_view import render_accuracy_validation_tab
from src.evaluation.dashboard_data import get_benchmark_accuracy_summary_for_quality_tab
from src.analytics.regional_dashboard_view import render_regional_analysis_view
from theme import (
    THEME_CSS,
    render_header,
    render_ssrf_banner,
    render_kpis,
    render_custom_table,
    make_status_pill,
    make_link_icon,
    render_terminal,
    render_pipeline_funnel,
    render_validation_checklist,
)

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
    """Ensure all default session keys are initialized for the active session."""
    for key, default in {**DEFAULT_STATE, **EXTRA_STATE}.items():
        if key not in st.session_state:
            # Avoid sharing mutable default objects between reruns / sessions.
            if isinstance(default, (dict, list)):
                st.session_state[key] = default.copy()
            elif isinstance(default, pd.DataFrame):
                st.session_state[key] = default.copy()
            else:
                st.session_state[key] = default

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
