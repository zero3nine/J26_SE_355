"""Dashboard page: Failure Logs — Migrated to React."""
import streamlit as st

st.set_page_config(
    page_title="Failure Logs — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import render_page_shell  # noqa: F401,F403

render_page_shell()

st.subheader("7. Collection Failures & Exclusions Log (Migrated to React)")
st.caption("Diagnostic inspection of collection exceptions, perimeter bot-wall blocks, format exclusions, and validation failures encountered during academic scraping operations.")

st.success("✨ **UI Migration Active:** The modern light-themed **Collection Failures & Exclusions Log** is now live on the React application at [http://localhost:3000](http://localhost:3000) (or [http://127.0.0.1:8000](http://127.0.0.1:8000)).")

st.markdown("""
> **Component Status: Disconnected from Streamlit**  
> In accordance with the partial UI migration requirements, this Streamlit interface has been cleanly disconnected to prevent duplicate state logging and dual-session conflicts.
> All underlying Python error logging, scraping exception handling (`src.scraping.service`), SSRF validation, and failure tracking mechanisms remain 100% active.
>
> **Active Capabilities in the New React Console:**
> - **Collection Failures Overview:** Real-time metrics tracking Critical Failures, Policy Exclusions, Retryable Records, and Affected Hostnames.
> - **Multi-Run Scope Inspection:** Toggle seamlessly between Active Session Run, Historical Failures Log (`failed_urls.csv`), All Aggregated Events, and past batch snapshots.
> - **Separate Categorization:** Dedicated views for All Events, Collection Failures (network timeouts, HTTP 403 bot walls), and Excluded Records (SSRF blocks, layout mismatches, manual reviews, unpermitted OCR).
> - **Diagnostic Detail Modal:** Full-detail diagnostic modal with one-click URL copy, technical error breakdown, and stage provenance.
> - **One-Click Retry Pipeline:** Directly triggers automated retry scraping jobs for transient network and rate-limited URLs without leaving the page.
> - **Standardized CSV Export:** Download failure log CSV with exact schema compatibility (`jobs_failures_{batch_id}.csv`).
""")

