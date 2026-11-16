"""Dashboard page: Raw Data — Migrated to React."""
import streamlit as st

st.set_page_config(
    page_title="Raw Data — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import render_page_shell

render_page_shell()

st.subheader("2. Raw Data (Migrated to React)")
st.caption("Raw job vacancy inspection, filtering, provenance metadata, and CSV export have been migrated to the React frontend.")

st.success("✨ **UI Migration Active:** The modern light-themed **Raw Data** console is now live on the React application at [http://localhost:3000](http://localhost:3000) (or [http://127.0.0.1:8000](http://127.0.0.1:8000)).")

st.markdown("""
> **Component Status: Disconnected from Streamlit**  
> In accordance with the partial UI migration requirements, this Streamlit interface has been cleanly disconnected to prevent duplicate table renders and dual-interface conflicts.
>
> **Active Capabilities in the New React Console:**
> - **Structured Data Overview:** Real-time cards for total raw records, successful extractions, distinct sources, and batch ID
> - **Multi-Criteria Filtering & Search:** Search by job title and company, plus company, source platform, and extractor dropdown filters
> - **Professional Raw Records Table:** Clean light-themed data table with status pills, confidence percentages, pagination, and source link buttons
> - **Deep Record Inspector:** Record provenance & metadata chips (title, host, country, extractor, timestamp, fetch method) and scrollable raw description viewer
> - **Durable CSV Export:** One-click download of the active raw crawl dataset
""")
