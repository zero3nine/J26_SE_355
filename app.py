"""IT Job Advertisement Data Collector — Streamlit entry point."""
import streamlit as st

st.set_page_config(
    page_title="IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

import importlib
import app_shared
importlib.reload(app_shared)
from app_shared import render_page_shell, project_metrics, render_kpis

render_page_shell()
st.subheader("Research Dashboard")
st.caption("Use the page navigation to collect, clean, extract, review, and analyze job-advertisement data.")

attempted, scraped, failed, cleaned, extracted = project_metrics()
st.markdown(
    render_kpis(attempted, scraped, failed, cleaned),
    unsafe_allow_html=True,
)

st.markdown("### Workflow")
st.markdown(
    "1. Collect job advertisements\n"
    "2. Inspect raw records\n"
    "3. Clean and validate data\n"
    "4. Extract skills using lexical and semantic methods\n"
    "5. Publish approved records to the master dataset\n"
    "6. Run analytical and validation views"
)
st.info("Session data is temporary. Use the Master Dataset page to publish records to persistent storage once its database integration is configured.")
