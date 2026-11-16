"""Dashboard page: Clean Data — Migrated to React."""
import streamlit as st

st.set_page_config(
    page_title="Clean Data — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import render_page_shell

render_page_shell()

st.subheader("3. Clean Data (Migrated to React)")
st.caption("Data cleaning, entity standardization, deduplication, and database publishing have been migrated to the React frontend.")

st.success("✨ **UI Migration Active:** The modern light-themed **Clean Data** console is now live on the React application at [http://localhost:3000](http://localhost:3000) (or [http://127.0.0.1:8000](http://127.0.0.1:8000)).")

st.markdown("""
> **Component Status: Disconnected from Streamlit**  
> In accordance with the partial UI migration requirements, this Streamlit interface has been cleanly disconnected to prevent duplicate cleaning pipeline executions, file collision, and inconsistent session states.
>
> **Active Capabilities in the New React Console:**
> - **Empty State Guidance:** Seamless workflow navigation back to Collect Data or Raw Data when no raw batch is staged.
> - **Cleaning Configuration Checklist:** Visible verification checklist for analytical rules (minimum length thresholds, non-IT filtering, temporal sanity checks, title/company/description deduplication).
> - **Execution Console:** Interactive "✨ Clean and Standardize Data" action trigger with progress and execution status.
> - **4-Stage Pipeline Funnel:** Real-time KPI summary cards displaying Total Raw, Validation Filtered, Deduplication Step Removed, and Final Clean Records.
> - **Diagnostics Accordion:** Expandable breakdown for analytically distinct work modes (Remote, Hybrid, Onsite) and geographic normalization.
> - **10-Column Clean Dataset Table:** Paginated, searchable presentation-ready table with monospace Job IDs, external links, and expandable full descriptions.
> - **Export & Publishing:** One-click CSV export and direct publishing into the SQLite master database (`data/master_jobs.sqlite3`) for downstream skill extraction.
""")
