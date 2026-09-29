"""Dashboard page: Scraping Accuracy & Validation."""
import streamlit as st

st.set_page_config(
    page_title="Scraping Accuracy & Validation — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *  # noqa: F401,F403

render_page_shell()

render_accuracy_validation_tab(current_dir)
