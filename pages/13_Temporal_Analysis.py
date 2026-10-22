"""Temporal Trend & Emerging Skill Analysis Streamlit page.

This file handles UI, filters, visualizations, and downloads.
Reusable calculations are implemented in src/analytics/temporal_analysis.py.
"""
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# Allow imports from the project root when this page is run by Streamlit.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from src.database.connection import get_connection, initialize_database, DB_PATH
    from src.analytics.temporal_analysis import (
        load_temporal_input,
        load_eligible_jobs,
        build_demand_series,
        expand_zero_demand_periods,
        trend_table,
        forecast_skill,
        representation_comparison,
    )
except Exception as exc:
    st.error(f"Could not import temporal-analysis/database modules: {exc}")
    st.stop()


st.set_page_config(page_title="Temporal Analysis", page_icon="📈", layout="wide")
st.title("Temporal Trend & Emerging Skill Analysis")
st.caption(
    "Normalized skill-demand trends, emerging-skill screening, forecasting "
    "baselines, and lexical-versus-semantic sensitivity."
)
st.info(
    "Temporal grouping uses `jobs.posting_date` (the original advertised date). "
    "`first_seen_at`, `scraped_at`, and other collection/import timestamps must "
    "not be used as substitutes for historical posting dates."
)

# ---------------------------------------------------------------------
# Database summary and available filter options
# ---------------------------------------------------------------------
try:
    initialize_database()
    with get_connection() as conn:
        jobs_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        dated_count = conn.execute(
            "SELECT COUNT(*) FROM jobs "
            "WHERE posting_date IS NOT NULL AND TRIM(posting_date) <> ''"
        ).fetchone()[0]
        skills_count = conn.execute(
            "SELECT COUNT(*) FROM extracted_skills"
        ).fetchone()[0]
        methods = [
            row[0] for row in conn.execute(
                "SELECT DISTINCT method FROM extracted_skills ORDER BY method"
            ).fetchall() if row[0]
        ]
        countries = [
            row[0] for row in conn.execute(
                "SELECT DISTINCT COALESCE(country, 'Unknown') FROM jobs ORDER BY 1"
            ).fetchall()
        ]
        sources = [
            row[0] for row in conn.execute(
                "SELECT DISTINCT COALESCE(source_platform, 'Unknown') "
                "FROM jobs ORDER BY 1"
            ).fetchall()
        ]
except Exception as exc:
    st.error(f"Unable to read the master database at `{DB_PATH}`: {exc}")
    st.info(
        "Check that the configured SQLite database contains jobs and extracted "
        "skill records, and that the connection points to the intended database."
    )
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Master jobs", f"{jobs_count:,}")
c2.metric("Jobs with posting dates", f"{dated_count:,}")
c3.metric("Stored skill records", f"{skills_count:,}")

if dated_count == 0:
    st.warning("No usable posting dates are stored. Missing dates are not inferred.")
if skills_count == 0:
    st.warning(
        "No extracted skills are stored. Run extraction and persist the results "
        "to extracted_skills before analysing skill demand."
    )
    st.stop()

# ---------------------------------------------------------------------
# Analysis filters
# ---------------------------------------------------------------------
with st.sidebar:
    st.header("Analysis settings")
    method = st.selectbox(
        "Skill representation",
        options=["all"] + methods,
        help="Select the extraction method recorded in the master database.",
    )
    frequency_label = st.radio(
        "Aggregation interval", ["Monthly", "Quarterly"], horizontal=True
    )
    frequency = "M" if frequency_label == "Monthly" else "Q"
    country = st.selectbox("Country", ["All"] + countries)
    source = st.selectbox("Source platform", ["All"] + sources)
    min_jobs = st.number_input(
        "Minimum eligible jobs per period",
        min_value=1, max_value=100000, value=5, step=1,
    )
    min_observations = st.number_input(
        "Minimum periods for trend labels",
        min_value=3, max_value=120, value=6, step=1,
    )
    recent_periods = st.number_input(
        "Recent window (periods)", min_value=1, max_value=24, value=3, step=1
    )

# Read skill records and all eligible dated jobs from the shared master DB.
with get_connection() as conn:
    raw = load_temporal_input(conn, method=method)
    all_jobs = load_eligible_jobs(conn)

if raw.empty:
    st.info(
        "No dated skill records match this method. Check posting dates, method "
        "labels, and whether extraction results were saved to the master database."
    )
    st.stop()

# One shared denominator definition is used for the selected representation.
series, eligible = build_demand_series(
    raw,
    frequency=frequency,
    min_jobs=int(min_jobs),
    country=country,
    source=source,
    jobs_df=all_jobs,
)

if series.empty:
    st.warning(
        "No periods meet the minimum eligible-job threshold. Lower the threshold "
        "or check the date, source, country, and extraction-method filters."
    )
    st.stop()

# Include zero-demand periods only where eligible jobs exist in that period.
series_full = expand_zero_demand_periods(series, eligible, frequency=frequency)
trends = trend_table(
    series_full,
    recent_periods=int(recent_periods),
    baseline_periods=int(recent_periods),
    min_observations=int(min_observations),
    frequency=frequency,
)

# ---------------------------------------------------------------------
# 1. Skill-demand trends
# ---------------------------------------------------------------------
st.subheader("1. Temporal demand")
skills = sorted(series_full["skill_name"].dropna().unique())
default_skills = list(
    series_full.groupby("skill_name")["jobs_mentioning_skill"]
    .sum().nlargest(8).index
)
selected_skills = st.multiselect("Skills to compare", skills, default=default_skills)

if selected_skills:
    chart_data = (
        series_full[series_full["skill_name"].isin(selected_skills)]
        .pivot_table(
            index="period", columns="skill_name",
            values="demand_rate", aggfunc="first",
        )
        .sort_index()
    )
    st.line_chart(chart_data, y_label="Demand rate (%)")
else:
    st.caption("Select at least one skill to display its demand trend.")

st.caption(
    "Demand rate = jobs mentioning a skill ÷ all eligible dated jobs in the "
    "selected period × 100. Interpret demand rates alongside eligible-job counts."
)
st.dataframe(
    eligible.rename(columns={
        "period": "Period", "eligible_jobs": "Eligible jobs"
    }),
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------------------
# 2. Trend and emerging-skill screening
# ---------------------------------------------------------------------
st.subheader("2. Trend and emerging-skill screening")
if not trends.empty:
    display = trends.copy()
    for column in [
        "baseline_rate", "recent_rate", "absolute_change_pp",
        "relative_growth_pct", "trend_slope_pp_per_period",
    ]:
        if column in display.columns:
            display[column] = display[column].round(3)

    st.dataframe(display, use_container_width=True, hide_index=True)
    st.download_button(
        "Download trend classifications (CSV)",
        trends.to_csv(index=False).encode("utf-8"),
        "temporal_trend_classifications.csv",
        "text/csv",
    )

    emerging = trends[trends["classification"].eq("Emerging")].sort_values(
        "recent_rate", ascending=False
    )
    if not emerging.empty:
        st.markdown("**Emerging-skill candidates**")
        st.dataframe(emerging, use_container_width=True, hide_index=True)

    st.caption(
        "These labels are screening heuristics, not validated ground truth. "
        "Review sample size, source coverage, baseline demand, persistence, and "
        "threshold sensitivity before making research claims."
    )
else:
    st.info("There are not enough usable observations to classify trends.")

# ---------------------------------------------------------------------
# 3. Short-term forecasts
# ---------------------------------------------------------------------
st.subheader("3. Short-term forecasting")
forecastable = sorted([
    skill for skill in skills
    if series_full.loc[
        series_full["skill_name"].eq(skill), "period"
    ].nunique() >= 8
])

if forecastable:
    chosen_forecast = st.selectbox("Skill to forecast", forecastable)
    horizon = st.slider("Forecast horizon (periods)", 1, 3, 3)

    if st.button("Generate baseline forecasts"):
        forecast, note = forecast_skill(
            series_full,
            chosen_forecast,
            horizon=horizon,
            min_periods=8,
            frequency=frequency,
        )
        if forecast.empty:
            st.warning(note)
        else:
            st.dataframe(forecast, use_container_width=True, hide_index=True)
            st.line_chart(forecast.set_index("period"))
            st.info(note)
            st.download_button(
                "Download forecast (CSV)",
                forecast.to_csv(index=False).encode("utf-8"),
                "temporal_forecast.csv",
                "text/csv",
            )
else:
    st.info(
        "Forecasting is disabled because no skill has at least eight periods. "
        "Use a sufficiently dense time series before forecasting."
    )

# ---------------------------------------------------------------------
# 4. Lexical-versus-semantic sensitivity comparison
# ---------------------------------------------------------------------
st.subheader("4. Lexical versus semantic temporal sensitivity")
lexical_method = next((m for m in methods if m.lower() == "lexical"), None)
semantic_method = next(
    (m for m in methods if m.lower() in {
        "semantic", "canonical", "semantic/canonical"
    }),
    None,
)

if lexical_method and semantic_method:
    with get_connection() as conn:
        lexical_raw = load_temporal_input(conn, method=lexical_method)
        semantic_raw = load_temporal_input(conn, method=semantic_method)

    # Both representations use identical filters and the complete jobs table.
    lexical_series, _ = build_demand_series(
        lexical_raw,
        frequency=frequency,
        min_jobs=int(min_jobs),
        country=country,
        source=source,
        jobs_df=all_jobs,
    )
    semantic_series, _ = build_demand_series(
        semantic_raw,
        frequency=frequency,
        min_jobs=int(min_jobs),
        country=country,
        source=source,
        jobs_df=all_jobs,
    )

    comparison, stats = representation_comparison(
        lexical_series,
        semantic_series,
        "Lexical mean demand (%)",
        "Semantic mean demand (%)",
    )

    if not comparison.empty:
        k1, k2 = st.columns(2)
        k1.metric(
            "Spearman rank correlation",
            "—" if pd.isna(stats["spearman"]) else f"{stats['spearman']:.3f}",
        )
        k2.metric("Top-10 Jaccard overlap", f"{stats['top_k_overlap']:.1%}")

        st.dataframe(
            comparison.sort_values(
                "Lexical mean demand (%)", ascending=False
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Download representation comparison (CSV)",
            comparison.to_csv(index=False).encode("utf-8"),
            "lexical_semantic_temporal_comparison.csv",
            "text/csv",
        )
        st.caption(
            "This compares average demand and rankings. It does not yet measure "
            "agreement between emerging-skill labels or trend directions."
        )
    else:
        st.info("Insufficient data to compare the two representations.")
else:
    st.info(
        "The database needs both lexical and semantic/canonical values in "
        "extracted_skills.method to run this comparison."
    )

# ---------------------------------------------------------------------
# 5. Data-quality checks
# ---------------------------------------------------------------------
st.subheader("5. Data-quality checks")
all_dates = pd.to_datetime(all_jobs["posting_date"], errors="coerce")

q1, q2, q3 = st.columns(3)
q1.metric("Missing/invalid dates", f"{int(all_dates.isna().sum()):,}")
q2.metric(
    "Distinct sources",
    f"{all_jobs['source_platform'].nunique(dropna=True):,}",
)
q3.metric(
    "Observed date range",
    (
        f"{all_dates.min().date()} – {all_dates.max().date()}"
        if all_dates.notna().any() else "N/A"
    ),
)
st.caption(
    "Only advertisements with parseable posting dates enter temporal calculations. "
    "This page does not infer missing dates or claim the sample represents the "
    "entire labour market."
)
