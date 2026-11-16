"""Dashboard page: Collect Data — Migrated to React."""
import streamlit as st

st.set_page_config(
    page_title="Collect Data — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import render_page_shell

render_page_shell()

st.subheader("1. Collect Data (Migrated to React)")
st.caption("Live web crawling and historical data ingestion have been migrated to the React frontend.")

st.success("✨ **UI Migration Active:** The modern light-themed **Collect Data** console is now live on the React application at [http://localhost:3000](http://localhost:3000) (or [http://127.0.0.1:8000](http://127.0.0.1:8000)).")

st.markdown("""
> **Component Status: Disconnected from Streamlit**  
> In accordance with the partial UI migration requirements, this Streamlit interface has been cleanly disconnected to prevent duplicate crawler instances and inconsistent session states.
>
> **Active Capabilities in the New React Console:**
> - **Live URL Ingestion & Buffer:** Monospace input with automatic line counting and sample URL loading
> - **Real-time SSRF Validation:** Instant defense checks against local/private IPs and unapproved external hosts
> - **Crawl Configuration:** Sliders for job targets (5–200), safety budgets, polite delay (0.5s–10s), browser fallback, and flyer OCR
> - **Live Execution Console:** Real-time progress bar, cancellation controls, and interactive monospace log terminal
> - **Presentation-Ready Light Theme:** High-contrast, clean typography adhering to academic presentation standards
""")
