"""Dashboard page: Scraping Accuracy & Validation — Migrated to React."""
import streamlit as st

st.set_page_config(
    page_title="Scraping Accuracy & Validation — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import render_page_shell

render_page_shell()

st.subheader("10. Scraping Accuracy & Benchmark Validation (Migrated to React)")
st.caption("Quantitative empirical evaluation of extraction accuracy, coverage, and error patterns independently verified against ground-truth reference jobs have been migrated to the React frontend.")

st.success("✨ **UI Migration Active:** The modern light-themed **Scraping Accuracy & Benchmark Validation** console is now live on the React application at [http://localhost:3000](http://localhost:3000) (or [http://127.0.0.1:8000](http://127.0.0.1:8000)).")

st.markdown("""
> **Component Status: Disconnected from Streamlit**  
> In accordance with the partial UI migration requirements, this Streamlit interface has been cleanly disconnected to prevent redundant evaluation runs, dual database transactions, and session conflicts.
>
> **Active Capabilities in the New React Console:**
> - **Benchmark Snapshot Selection:** Historical snapshot selector across 17 empirical benchmark runs with provenance badges.
> - **Evaluation Engine Execution:** Programmatic execution of the Python benchmark evaluation engine with live loading states and feedback alerts.
> - **5 Core Scorecard KPIs:** Benchmark Corpus ($N=120$), Evaluated/Matched ($N=120$), Macro Coverage ($80.7\%$), Macro Correctness ($78.5\%$), and Exact Match Rate ($2$, $1.7\%$, $95\%$ Wilson CI).
> - **Multi-Filter & Slicing Toolbar:** Country/Market, Source Platform/Hostname, Extraction Architecture, Field Name, Validation Status, Error Category, and Text Search.
> - **Comparative Quality Analysis:**
>   1. *🌍 Country-Level Quality:* Geographic extraction quality comparison table, small-sample caveats ($N<10$), and grouped vertical bar charts.
>   2. *🏢 Source Platform Accuracy:* Portal-by-portal agreement rates and ethical access perimeter notes.
>   3. *⚙️ Extraction Architecture:* Performance benchmarks across JSON-LD, site adapters, generic HTML, and headless browser tiers.
>   4. *📋 Field-by-Field Matrix:* True Positives, False Positives, False Negatives, Completeness Coverage, Normalized Agreement, and Hallucination rates across canonical fields.
>   5. *💰 Numeric Salary Errors:* Comparable pairs, Minimum MAE ($0.00$), Maximum MAE ($0.00$), and currency-matched evaluation rules.
> - **Field-Level Discrepancy & Validation Review Queue:** Filterable review queue table, interactive peer verification submission form (verified, incorrect, unavailable, ambiguous), and immutable reviewer audit trail.
> - **Downloadable Accuracy Package:** One-click CSV and Markdown export buttons for Summary, Filtered Errors, Stratification, Review Queue, and Full Report.
""")
