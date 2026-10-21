"""Temporal Trend & Emerging Skill Analysis page."""
from pathlib import Path
import sys
import sqlite3
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from src.database.connection import get_connection, initialize_database, DB_PATH
    from src.analytics.temporal_analysis import (
        load_temporal_input, build_demand_series, trend_table, forecast_skill,
        representation_comparison,
    )
except Exception as exc:
    st.error(f"Could not import the temporal-analysis/database modules: {exc}")
    st.stop()

st.set_page_config(page_title="Temporal Analysis", page_icon="📈", layout="wide")
st.title("Temporal Trend & Emerging Skill Analysis")
st.caption("Normalized skill-demand trends, emerging-skill screening, forecasting baselines, and lexical-versus-semantic sensitivity.")

try:
    initialize_database()
    with get_connection() as conn:
        jobs_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        dated_count = conn.execute("SELECT COUNT(*) FROM jobs WHERE posting_date IS NOT NULL AND TRIM(posting_date) <> ''").fetchone()[0]
        skills_count = conn.execute("SELECT COUNT(*) FROM extracted_skills").fetchone()[0]
        methods = [r[0] for r in conn.execute("SELECT DISTINCT method FROM extracted_skills ORDER BY method").fetchall() if r[0]]
        countries = [r[0] for r in conn.execute("SELECT DISTINCT COALESCE(country,'Unknown') FROM jobs ORDER BY 1").fetchall()]
        sources = [r[0] for r in conn.execute("SELECT DISTINCT COALESCE(source_platform,'Unknown') FROM jobs ORDER BY 1").fetchall()]
except Exception as exc:
    st.error(f"Unable to read the master database at `{DB_PATH}`: {exc}")
    st.info("Copy the database implementation into the project and import jobs plus extracted skill results before running temporal analysis.")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Master jobs", f"{jobs_count:,}")
c2.metric("Jobs with posting dates", f"{dated_count:,}")
c3.metric("Stored skill records", f"{skills_count:,}")
if dated_count == 0:
    st.warning("The master dataset has no usable posting dates. Temporal analysis requires reliable dates; missing dates are not inferred.")
if skills_count == 0:
    st.warning("No extracted skills are stored yet. Run lexical/semantic extraction and persist its results to `extracted_skills` before analysing skill demand.")

with st.sidebar:
    st.header("Analysis settings")
    method = st.selectbox("Skill representation", options=["all"] + methods, index=0,
                          help="Choose the extraction method recorded in the master database.")
    frequency_label = st.radio("Aggregation interval", ["Monthly", "Quarterly"], horizontal=True)
    frequency = "M" if frequency_label == "Monthly" else "Q"
    country = st.selectbox("Country", ["All"] + countries)
    source = st.selectbox("Source platform", ["All"] + sources)
    min_jobs = st.number_input("Minimum eligible jobs per period", min_value=1, max_value=100000, value=5, step=1)
    min_observations = st.number_input("Minimum periods for directional labels", min_value=3, max_value=120, value=6, step=1)
    recent_periods = st.number_input("Recent window (periods)", min_value=1, max_value=24, value=3, step=1)

with get_connection() as conn:
    raw = load_temporal_input(conn, method=method)

if raw.empty:
    st.info("No dated skill records match this representation. Check the extraction runs and date fields in the master dataset.")
    st.stop()

# Keep a complete eligible-job table for denominators, including dated jobs with no matched skill.
with get_connection() as conn:
    jobs = pd.read_sql_query("SELECT job_id, posting_date, country, source_platform, job_title, source_url FROM jobs WHERE posting_date IS NOT NULL AND TRIM(posting_date) <> ''", conn)
    if method != "all":
        raw = raw[raw["method"].fillna("").str.lower().eq(method.lower())]

data = raw.copy()
data["posting_date"] = pd.to_datetime(data["posting_date"], errors="coerce", utc=True).dt.tz_convert(None)
data = data.dropna(subset=["posting_date"])
if country != "All":
    data = data[data["country"].fillna("Unknown").eq(country)]
    jobs = jobs[jobs["country"].fillna("Unknown").eq(country)]
if source != "All":
    data = data[data["source_platform"].fillna("Unknown").eq(source)]
    jobs = jobs[jobs["source_platform"].fillna("Unknown").eq(source)]

# Build series using the full dated-job denominator, not just jobs with extracted skill mentions.
period_freq = "M" if frequency == "M" else "Q"
jobs["posting_date"] = pd.to_datetime(jobs["posting_date"], errors="coerce", utc=True).dt.tz_convert(None)
jobs = jobs.dropna(subset=["posting_date"])
jobs["period"] = jobs["posting_date"].dt.to_period(period_freq).dt.to_timestamp()
eligible = jobs[["job_id", "period"]].drop_duplicates().groupby("period").size().rename("eligible_jobs").reset_index()
data["period"] = data["posting_date"].dt.to_period(period_freq).dt.to_timestamp()
mentions = data.dropna(subset=["skill_name"])[["job_id", "period", "skill_name"]].copy()
mentions["skill_name"] = mentions["skill_name"].astype(str).str.strip()
mentions = mentions[mentions["skill_name"].ne("") & mentions["skill_name"].ne("nan")].drop_duplicates(["job_id", "period", "skill_name"])
counts = mentions.groupby(["period", "skill_name"]).size().rename("jobs_mentioning_skill").reset_index()
series = counts.merge(eligible, on="period", how="left")
series["demand_rate"] = 100 * series["jobs_mentioning_skill"] / series["eligible_jobs"].replace(0, pd.NA)
series = series[series["eligible_jobs"].fillna(0) >= min_jobs].sort_values(["period", "skill_name"])

if series.empty:
    st.warning("No periods meet the minimum eligible-job threshold. Reduce the threshold or check the date/source filters.")
    st.stop()

# Include explicit zero-demand periods for each skill between its first and last observed period.
full_rows = []
period_index = pd.DatetimeIndex(sorted(series["period"].unique()))
for skill, group in series.groupby("skill_name"):
    g = group.set_index("period").reindex(period_index)
    g["skill_name"] = skill
    g["jobs_mentioning_skill"] = g["jobs_mentioning_skill"].fillna(0)
    g["eligible_jobs"] = eligible.set_index("period")["eligible_jobs"].reindex(period_index).fillna(0)
    g["demand_rate"] = (100 * g["jobs_mentioning_skill"] / g["eligible_jobs"].replace(0, pd.NA)).fillna(0)
    g.index.name = "period"
    full_rows.append(g.reset_index())
series_full = pd.concat(full_rows, ignore_index=True) if full_rows else series
trends = trend_table(series_full, recent_periods=int(recent_periods), baseline_periods=int(recent_periods), min_observations=int(min_observations))

st.subheader("1. Temporal demand")
skills = sorted(series_full["skill_name"].unique())
default_skills = list(series_full.groupby("skill_name")["jobs_mentioning_skill"].sum().nlargest(8).index)
selected_skills = st.multiselect("Skills to compare", skills, default=default_skills)
if selected_skills:
    chart_data = series_full[series_full.skill_name.isin(selected_skills)].pivot_table(index="period", columns="skill_name", values="demand_rate", aggfunc="first").sort_index()
    st.line_chart(chart_data, y_label="Demand rate (%)")
else:
    st.caption("Select at least one skill to display its demand trend.")
st.caption("Demand rate = jobs mentioning the skill in the period ÷ all eligible dated IT jobs in the selected period × 100. The denominator is shown separately and should be considered when interpreting changes.")
st.dataframe(eligible.rename(columns={"period":"Period", "eligible_jobs":"Eligible jobs"}), use_container_width=True, hide_index=True)

st.subheader("2. Trend and emerging-skill screening")
if not trends.empty:
    display = trends.copy()
    display["baseline_rate"] = display["baseline_rate"].round(3)
    display["recent_rate"] = display["recent_rate"].round(3)
    display["absolute_change_pp"] = display["absolute_change_pp"].round(3)
    display["relative_growth_pct"] = display["relative_growth_pct"].round(2)
    display["trend_slope_pp_per_period"] = display["trend_slope_pp_per_period"].round(4)
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.download_button("Download trend classifications (CSV)", trends.to_csv(index=False).encode("utf-8"), "temporal_trend_classifications.csv", "text/csv")
    emerging = trends[trends.classification.eq("Emerging")].sort_values("recent_rate", ascending=False)
    if not emerging.empty:
        st.markdown("**Emerging candidates**")
        st.dataframe(emerging, use_container_width=True, hide_index=True)
    st.caption("These labels are screening heuristics, not validated ground truth. Inspect sample size, source coverage, baseline demand, persistence and sensitivity to thresholds before making research claims.")

st.subheader("3. Short-term forecasting")
forecastable = sorted([s for s in skills if series_full[series_full.skill_name.eq(s)].period.nunique() >= 8])
if forecastable:
    chosen_forecast = st.selectbox("Skill to forecast", forecastable)
    horizon = st.slider("Forecast horizon (periods)", 1, 3, 3)
    if st.button("Generate baseline forecasts"):
        fc, note = forecast_skill(series_full, chosen_forecast, horizon=horizon, min_periods=8)
        if fc.empty:
            st.warning(note)
        else:
            st.dataframe(fc, use_container_width=True, hide_index=True)
            st.line_chart(fc.set_index("period"))
            st.info(note)
            st.download_button("Download forecast (CSV)", fc.to_csv(index=False).encode("utf-8"), "temporal_forecast.csv", "text/csv")
else:
    st.info("Forecasting is disabled for now: no skill has at least eight distinct periods. Build a longer and sufficiently dense time series before forecasting.")

st.subheader("4. Lexical versus semantic temporal sensitivity")
method_lowers = {m.lower(): m for m in methods}
lexical_method = next((m for m in methods if m.lower() == "lexical"), None)
semantic_method = next((m for m in methods if m.lower() in {"semantic", "canonical", "semantic/canonical"}), None)
if lexical_method and semantic_method:
    with get_connection() as conn:
        lex_raw = load_temporal_input(conn, lexical_method)
        sem_raw = load_temporal_input(conn, semantic_method)
    lex = lex_raw.dropna(subset=["posting_date", "skill_name"]).copy()
    sem = sem_raw.dropna(subset=["posting_date", "skill_name"]).copy()
    lex["posting_date"] = pd.to_datetime(lex["posting_date"], errors="coerce", utc=True).dt.tz_convert(None)
    sem["posting_date"] = pd.to_datetime(sem["posting_date"], errors="coerce", utc=True).dt.tz_convert(None)
    lex = lex.dropna(subset=["posting_date"]); sem = sem.dropna(subset=["posting_date"])
    if country != "All":
        lex = lex[lex.country.fillna("Unknown").eq(country)]; sem = sem[sem.country.fillna("Unknown").eq(country)]
    if source != "All":
        lex = lex[lex.source_platform.fillna("Unknown").eq(source)]; sem = sem[sem.source_platform.fillna("Unknown").eq(source)]
    lex["period"] = lex.posting_date.dt.to_period(period_freq).dt.to_timestamp()
    sem["period"] = sem.posting_date.dt.to_period(period_freq).dt.to_timestamp()
    # Same dated-job denominator and period filtering for both representations.
    lex_jobs = lex[["job_id", "period", "skill_name"]].drop_duplicates()
    sem_jobs = sem[["job_id", "period", "skill_name"]].drop_duplicates()
    def make_rep(d):
        m = d.dropna(subset=["skill_name"]).drop_duplicates(["job_id", "period", "skill_name"])
        c = m.groupby(["period", "skill_name"]).job_id.nunique().rename("jobs_mentioning_skill").reset_index()
        denom = jobs[["job_id", "period"]].drop_duplicates().groupby("period").job_id.nunique().rename("eligible_jobs").reset_index()
        z = c.merge(denom, on="period", how="left")
        z["demand_rate"] = 100*z.jobs_mentioning_skill/z.eligible_jobs.replace(0, pd.NA)
        return z.dropna(subset=["demand_rate"])
    lex_series = make_rep(lex); sem_series = make_rep(sem)
    comp, stats = representation_comparison(lex_series, sem_series, "Lexical mean demand (%)", "Semantic mean demand (%)")
    if not comp.empty:
        k1, k2 = st.columns(2)
        k1.metric("Spearman rank correlation", "—" if pd.isna(stats["spearman"]) else f"{stats['spearman']:.3f}")
        k2.metric("Top-10 Jaccard overlap", f"{stats['top_k_overlap']:.1%}")
        st.dataframe(comp.sort_values("Lexical mean demand (%)", ascending=False), use_container_width=True, hide_index=True)
        st.download_button("Download representation comparison (CSV)", comp.to_csv(index=False).encode("utf-8"), "lexical_semantic_temporal_comparison.csv", "text/csv")
        st.caption("Rank correlation and top-skill overlap quantify whether the representation changes overall skill-demand rankings. For a defensible RQ5 result, also compare trend labels and emerging-skill overlap using the same periods, denominator, and filters.")
else:
    st.info("The database needs both `lexical` and `semantic` (or `canonical`) values in `extracted_skills.method` to run this comparison.")

st.subheader("5. Data-quality checks")
all_jobs = pd.read_sql_query("SELECT posting_date, country, source_platform FROM jobs", get_connection())
all_dates = pd.to_datetime(all_jobs["posting_date"], errors="coerce")
q1, q2, q3 = st.columns(3)
q1.metric("Missing/invalid dates", f"{int(all_dates.isna().sum()):,}")
q2.metric("Distinct sources", f"{all_jobs['source_platform'].nunique(dropna=True):,}")
q3.metric("Observed date range", f"{all_dates.min().date() if all_dates.notna().any() else 'N/A'} – {all_dates.max().date() if all_dates.notna().any() else 'N/A'}")
st.caption("This page analyzes only advertisements with parseable posting dates. It does not infer missing historical dates or claim national labor-market representativeness. Monthly/quarterly interval and thresholds should be documented in the final methodology.")
