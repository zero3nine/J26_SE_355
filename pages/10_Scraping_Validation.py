"""Dashboard page: Scraping Accuracy & Validation."""
import streamlit as st

st.set_page_config(
    page_title="Scraping Accuracy & Validation — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import current_dir, render_page_shell
from src.evaluation.dashboard_view import render_accuracy_validation_tab

render_page_shell()

render_accuracy_validation_tab(current_dir)
