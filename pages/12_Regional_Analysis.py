"""Dashboard page: Regional Analysis — Migrated to React."""
import streamlit as st

st.set_page_config(
    page_title="Regional Analysis — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import render_page_shell

render_page_shell()

st.subheader("12. Regional Analysis (Migrated to React)")
st.caption("Empirical comparative regional IT labour-market analysis and role-segmented skill demand have been migrated to the React frontend.")

st.success("✨ **UI Migration Active:** The modern light-themed **Regional Analysis** console is now live on the React application at [http://localhost:3000](http://localhost:3000) (or [http://127.0.0.1:8000](http://127.0.0.1:8000)).")

st.markdown("""
> **Component Status: Disconnected from Streamlit**  
> In accordance with the partial UI migration requirements, this Streamlit interface has been cleanly disconnected to prevent duplicate analytical evaluations, session conflicts, and redundant database re-queries.
>
> **Active Capabilities in the New React Console:**
> - **Dual Analytical Scopes:** Instant switching between *Comparative Regional Market Analysis (Sri Lanka vs. India, Singapore, Malaysia)* and *Single-Batch Role Segmentation*.
> - **Regional Analysis Pipeline & Architecture:** Interactive 6-stage workflow expander detailing ingestion, normalization, eligibility filtering, and statistical inference.
> - **Live Executive KPI Cards:** Dynamically populated counts for Focal Market Ads, Regional Comparators, Skill-Eligible Vacancies, and Salary Disclosure Rate.
> - **6 Deep Analytical Subsystems:**
>   1. *Skill Demand & Gaps:* Grouped bar charts, 2D heatmaps, dual view, category filters, and Wilson 95% CI divergence tables with automated artifact detection.
>   2. *Role Distribution:* Occupational role frequency pivots, classification quality audit, and role-segmented technical demand comparisons.
>   3. *Salary & Compensation:* Local currency range whiskers, interquartile ranges (IQR), median markers, coverage summaries, and indicative reference exchange rates.
>   4. *Profile Similarities:* Multidimensional alignment via Cosine Similarity, Jaccard Overlap (Top-10), and Spearman Rank Correlation with 4×4 symmetric matrix heatmaps.
>   5. *Sensitivity Analysis:* Evaluation across 5 systematic validation regimes with Mean MAD shift and stability assessment pills.
>   6. *Eligibility Funnel & Audit:* Complete record attrition funnel and 6 one-click reproducible CSV research artifact exports.
> - **Single-Batch Role Segmentation:** Taxonomic classification into IT roles, comparative lexical vs semantic skill frequencies, and frequency CSV export.
""")
