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
from app_shared import render_page_shell

render_page_shell()
st.subheader("Research Dashboard (Migrated to React)")
st.caption("The primary Research Dashboard interface has been migrated to React, TypeScript, and Tailwind CSS.")

st.success("✨ **UI Migration Active:** The modern light-themed Research Dashboard is running on the React frontend at [http://localhost:3000](http://localhost:3000) (or via FastAPI at [http://127.0.0.1:8000](http://127.0.0.1:8000)).")

st.markdown("""
> **Component Status: Disconnected from Streamlit**  
> In accordance with the UI migration plan, the duplicate Streamlit KPI cards and workflow display have been disconnected to prevent dual-interface conflicts.
>
> **Team Member Pages Active:**  
> Use the sidebar navigation on the left to access all other operational pipeline stages:
> - **1 Collect Data**: Live scraping & historical data import
> - **2 Raw Data**: Raw vacancy inspection & HTML snippets
> - **3 Clean Data**: Normalization, deduplication & IT role heuristic
> - **4 Master Dataset**: Persistent SQLite master storage & exports
> - **5 Extract Skills**: Lexical & semantic skill identification
> - **6 Quality Report / 7 Failure Logs / 8 External Domains / 9 Manual Reviews**
> - **10 Scraping Validation / 11 Skill Relationships / 12 Regional Analysis / 13 Temporal / 14 Role Skills**
""")
