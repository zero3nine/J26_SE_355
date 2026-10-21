"""Streamlit page: Temporal Trend & Emerging Skill Analysis.

The page reads from the shared master SQLite database. Uploading a cleaned CSV
into the Master Dataset tab adds job records; skill mentions must also be
extracted and persisted in `extracted_skills` before they appear here.
"""
from pathlib import Path
import sys

import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from src.database.connection import get_connection, initialize_database, DB_PATH
    from src.analytics.temporal_analysis import (
        load_temporal_input, load_eligible_jobs, build_demand_series,
        expand_zero_demand_periods, trend_table, forecast_skill,
        evaluate_forecast_baselines, representation_comparison,
    )
except Exception as exc:
    st.error(f"Could not import temporal-analysis/database modules: {exc}")
    st.stop()

st.set_page_config(page_title="Temporal Analysis", page_icon="📈", layout="wide")
st.title("Temporal Trend & Emerging Skill Analysis")
st.caption("Normalized demand trends, emerging-skill screening, short-term forecasting, and extraction-method sensitivity.")
st.info(
    "Temporal grouping uses the original job posting date. Scrape, import, and "
    "cleaning timestamps are not substitutes for a missing posting date. Results "
    "describe the collected sample, not the entire labour market."
)

# ---------------------------------------------------------------------------
# Database health and extraction-method discovery
# ---------------------------------------------------------------------------
try:
    initialize_database()
    with get_connection() as conn:
        jobs_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        dated_count = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE posting_date IS NOT NULL AND TRIM(posting_date) <> ''"
        ).fetchone()[0]
        skills_count = conn.execute("SELECT COUNT(*) FROM extracted_skills").fetchone()[0]
        methods = [r[0] for r in conn.execute(
            "SELECT DISTINCT method FROM extracted_skills ORDER BY method"
        ).fetchall() if r[0]]
        countries = [r[0] for r in conn.execute(
            "SELECT DISTINCT COALESCE(country, 'Unknown') FROM jobs ORDER BY 1"
        ).fetchall()]
        sources = [r[0] for r in conn.execute(
            "SELECT DISTINCT COALESCE(source_platform, 'Unknown') FROM jobs ORDER BY 1"
        ).fetchall()]
except Exception as exc:
    st.error(f"Unable to read the master database at `{DB_PATH}`: {exc}")
    st.stop()

if not dated_count:
    st.warning("No dated jobs are available. Add a reliable posting date to the cleaned data; dates will not be inferred.")
if not skills_count:
    st.warning(
        "The master dataset has no saved skill mentions yet. Uploading a clean CSV stores job records, "
        "but this page also requires running skill extraction and saving its results."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Shared filters. These filters are applied to numerator and denominator.
# ---------------------------------------------------------------------------
with st.container(border=True):
    st.subheader("Filters and analysis settings")
    st.caption("These settings apply to the temporal trends, trend classifications, and forecasts below. The method-comparison section intentionally loads both methods independently.")
    f1, f2, f3 = st.columns(3)
    method = f1.selectbox("Skill representation", ["all"] + methods, help="Uses the method labels stored with extraction results.")
    frequency_label = f2.radio("Time aggregation", ["Monthly", "Quarterly"], horizontal=True)
    frequency = "M" if frequency_label == "Monthly" else "Q"
    country = f3.selectbox("Country", ["All"] + countries)
    f4, f5, f6, f7 = st.columns(4)
    source = f4.selectbox("Source platform", ["All"] + sources)
    min_jobs = f5.number_input("Minimum eligible jobs per period", 1, 100000, 5, 1)
    min_observations = f6.number_input("Minimum periods for trend classification", 3, 120, 6, 1)
    recent_periods = f7.number_input("Recent window (periods)", 1, 24, 3, 1)
    baseline_periods = st.number_input("Baseline window (periods)", 1, 24, 3, 1, help="Number of periods before the recent window used as a baseline.")

a, b, c, d = st.columns(4)
a.metric("Master jobs", f"{jobs_count:,}")
b.metric("Jobs with posting dates", f"{dated_count:,}")
c.metric("Stored skill mentions", f"{skills_count:,}")
d.metric("Extraction methods", f"{len(methods):,}")

with get_connection() as conn:
    raw = load_temporal_input(conn, method=method)
    all_jobs = load_eligible_jobs(conn)

if raw.empty:
    st.info("No dated skill records match this representation. Check the extraction method and saved results.")
    st.stop()

series, eligible = build_demand_series(
    raw, frequency=frequency, min_jobs=int(min_jobs), country=country,
    source=source, jobs_df=all_jobs,
)
if series.empty:
    st.warning("No periods meet the minimum eligible-job threshold. Lower the threshold or adjust filters.")
    st.stop()
series_full = expand_zero_demand_periods(series, eligible, frequency=frequency)
trends = trend_table(
    series_full, recent_periods=int(recent_periods), baseline_periods=int(baseline_periods),
    min_observations=int(min_observations), frequency=frequency,
)
skills = sorted(series_full["skill_name"].dropna().unique())

# ---------------------------------------------------------------------------
# 1. Historical trend chart and optional role family slice
# ---------------------------------------------------------------------------
st.subheader("1. Historical skill-demand trends")
st.caption("Demand rate = jobs mentioning a skill ÷ all eligible dated jobs in the same period × 100.")
selected_skills = st.multiselect(
    "Skills to plot", skills,
    default=list(series_full.groupby("skill_name")["jobs_mentioning_skill"].sum().nlargest(8).index),
)
if selected_skills:
    chart_data = series_full[series_full["skill_name"].isin(selected_skills)].copy()
    fig = px.line(chart_data, x="period", y="demand_rate", color="skill_name", markers=True,
                  labels={"period": "Period", "demand_rate": "Demand rate (%)", "skill_name": "Skill"})
    fig.update_layout(legend_title_text="Skill", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("Select one or more skills to plot.")

with st.expander("View period denominators and skill counts"):
    st.dataframe(eligible.rename(columns={"period": "Period", "eligible_jobs": "Eligible jobs"}),
                 use_container_width=True, hide_index=True)
    st.dataframe(series_full.rename(columns={
        "period": "Period", "skill_name": "Skill", "jobs_mentioning_skill": "Jobs mentioning skill",
        "eligible_jobs": "Eligible jobs", "demand_rate": "Demand rate (%)"
    }), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# 2. Role-based temporal trends. Role family is derived from the stored job title
# with simple transparent rules; it is a convenience grouping, not a validated
# role classifier. Unmatched titles remain "Other / unclassified".
# ---------------------------------------------------------------------------
st.subheader("2. Role-based temporal trends")
role_rules = [
    ("QA / Testing", r"\b(qa|quality assurance|test engineer|software tester|automation tester)\b"),
    ("Data / AI", r"\b(data|machine learning|ai engineer|analytics|data scientist)\b"),
    ("DevOps / Cloud", r"\b(devops|site reliability|cloud engineer|platform engineer|sre)\b"),
    ("Security", r"\b(security|penetration tester|cybersecurity)\b"),
    ("Frontend", r"\b(front.?end|ui engineer|web designer)\b"),
    ("Backend", r"\b(back.?end|api engineer)\b"),
    ("Software Development", r"\b(software engineer|software developer|full.?stack|programmer|application developer)\b"),
]
def infer_role(title):
    import re
    value = str(title or "").lower()
    for label, pattern in role_rules:
        if re.search(pattern, value):
            return label
    return "Other / unclassified"

# Classify all master jobs, not only jobs that yielded a skill mention. This
# preserves the correct role-specific denominator, including eligible jobs
# where extraction found no skills.
role_source = all_jobs[["job_id", "job_title"]].drop_duplicates()
role_source["role_family"] = role_source["job_title"].map(infer_role)
role_options = sorted(role_source["role_family"].unique())
role_choice = st.selectbox("Role family (title-derived)", ["All roles"] + role_options)
if role_choice != "All roles":
    role_ids = set(role_source.loc[role_source["role_family"].eq(role_choice), "job_id"])
    role_raw = raw[raw["job_id"].isin(role_ids)]
    role_jobs = all_jobs[all_jobs["job_id"].isin(role_ids)]
    role_series, role_eligible = build_demand_series(
        role_raw, frequency=frequency, min_jobs=int(min_jobs), country=country,
        source=source, jobs_df=role_jobs,
    )
    role_full = expand_zero_demand_periods(role_series, role_eligible, frequency=frequency)
    if role_full.empty:
        st.info("This role does not have enough eligible dated jobs in the selected scope.")
    else:
        role_skills = st.multiselect(
            "Skills in this role", sorted(role_full["skill_name"].unique()),
            default=list(role_full.groupby("skill_name")["jobs_mentioning_skill"].sum().nlargest(6).index),
            key="role_skill_select",
        )
        if role_skills:
            role_fig = px.line(role_full[role_full["skill_name"].isin(role_skills)],
                               x="period", y="demand_rate", color="skill_name", markers=True,
                               labels={"period":"Period","demand_rate":"Demand rate (%)","skill_name":"Skill"})
            st.plotly_chart(role_fig, use_container_width=True)
        st.caption("Role families are inferred from job titles using transparent keyword rules. Validate classifications before making research claims.")
else:
    st.caption("Select a role family to inspect skill demand within that group.")

# ---------------------------------------------------------------------------
# 3. Trend classification, growth, persistence, and volatility
# ---------------------------------------------------------------------------
st.subheader("3. Trend and emerging-skill screening")
if not trends.empty:
    numeric_cols = ["baseline_rate", "recent_rate", "absolute_change_pp", "relative_growth_pct",
                    "trend_slope_pp_per_period", "positive_change_persistence", "volatility_std_pp"]
    display = trends.copy()
    for col in numeric_cols:
        if col in display:
            display[col] = display[col].round(3)
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.download_button("Download trend classifications (CSV)", trends.to_csv(index=False).encode("utf-8"),
                       "temporal_trend_classifications.csv", "text/csv")
    emerging = trends[trends["classification"].eq("Emerging candidate")].sort_values("recent_rate", ascending=False)
    if not emerging.empty:
        st.markdown("**Emerging-skill candidates**")
        st.dataframe(emerging, use_container_width=True, hide_index=True)
    st.caption("Labels are heuristic screening signals, not confirmed facts. Check sample sizes, source mix, baseline demand, persistence, and sensitivity to period grouping.")
else:
    st.info("There are not enough observations for trend classification.")

# ---------------------------------------------------------------------------
# 4. Forecasting and chronological baseline evaluation
# ---------------------------------------------------------------------------
st.subheader("4. Short-term forecasting")
forecastable = sorted([skill for skill in skills if series_full.loc[series_full["skill_name"].eq(skill), "period"].nunique() >= 8])
if forecastable:
    selected_forecast = st.selectbox("Skill to forecast", forecastable)
    horizon = st.slider("Forecast horizon (periods)", 1, 3, 3)
    if st.button("Generate forecasts and evaluate baselines", type="primary"):
        forecast, note = forecast_skill(series_full, selected_forecast, horizon=int(horizon),
                                        min_periods=8, frequency=frequency)
        evaluation, eval_note = evaluate_forecast_baselines(series_full, selected_forecast, frequency=frequency, min_train=8)
        if forecast.empty:
            st.warning(note)
        else:
            st.markdown("**Future demand-rate estimates**")
            st.dataframe(forecast, use_container_width=True, hide_index=True)
            historical = series_full[series_full["skill_name"].eq(selected_forecast)][["period","demand_rate"]].copy()
            historical["Series"] = "Historical"
            future_long = forecast.melt(id_vars="period", var_name="Series", value_name="demand_rate")
            fig = px.line(pd.concat([historical.rename(columns={"demand_rate":"demand_rate"}), future_long],
                                    ignore_index=True, sort=False),
                          x="period", y="demand_rate", color="Series", markers=True,
                          labels={"period":"Period","demand_rate":"Demand rate (%)"})
            st.plotly_chart(fig, use_container_width=True)
            historical_rates = historical["demand_rate"].dropna()
            if len(historical_rates) >= 2:
                recent_mean = float(historical_rates.tail(min(3, len(historical_rates))).mean())
                earlier = historical_rates.iloc[:-min(3, len(historical_rates))]
                if not earlier.empty:
                    earlier_mean = float(earlier.tail(min(3, len(earlier))).mean())
                    direction = "higher" if recent_mean > earlier_mean + 0.5 else "lower" if recent_mean < earlier_mean - 0.5 else "broadly similar to"
                    st.markdown(f"**What the history suggests:** The average demand rate in the latest available periods is {direction} the preceding comparison window. This describes the collected sample, not the whole labour market.")
                else:
                    st.markdown("**What the history suggests:** There is not enough earlier history to compare recent demand reliably.")
            st.info(note + " Forecasts are exploratory estimates, not guarantees. Sparse history, changing source coverage, and uneven posting dates can materially affect results.")
            st.download_button("Download forecast (CSV)", forecast.to_csv(index=False).encode("utf-8"),
                               "temporal_forecast.csv", "text/csv")
        st.markdown("**How reliable have simple baselines been on earlier periods?**")
        if evaluation.empty:
            st.info(eval_note)
        else:
            st.dataframe(evaluation.round(4), use_container_width=True, hide_index=True)
            st.caption(eval_note + " Lower MAE/RMSE is better; directional accuracy measures whether the predicted movement matches the observed movement.")
            st.download_button("Download forecast evaluation (CSV)", evaluation.to_csv(index=False).encode("utf-8"),
                               "temporal_forecast_evaluation.csv", "text/csv")
else:
    st.info("Forecasting requires at least eight periods for a skill. A longer series is needed for more credible evaluation and machine-learning candidates.")

# ---------------------------------------------------------------------------
# 5. Lexical-versus-semantic sensitivity: same scope, periods, denominator.
# ---------------------------------------------------------------------------
st.subheader("5. Lexical versus semantic temporal sensitivity")
lexical_method = next((m for m in methods if m.lower() == "lexical"), None)
semantic_method = next((m for m in methods if m.lower() in {"semantic", "canonical", "semantic/canonical"}), None)
if lexical_method and semantic_method:
    with get_connection() as conn:
        lexical_raw = load_temporal_input(conn, method=lexical_method)
        semantic_raw = load_temporal_input(conn, method=semantic_method)
    lex_series, _ = build_demand_series(lexical_raw, frequency, int(min_jobs), country, source, all_jobs)
    sem_series, _ = build_demand_series(semantic_raw, frequency, int(min_jobs), country, source, all_jobs)
    comparison, stats = representation_comparison(lex_series, sem_series, "Lexical mean demand (%)", "Semantic mean demand (%)")
    if not comparison.empty:
        # Compare period-aligned trends using the same filters and eligible-job denominator.
        lex_full = expand_zero_demand_periods(lex_series, build_demand_series(lexical_raw, frequency, int(min_jobs), country, source, all_jobs)[1], frequency=frequency)
        sem_full = expand_zero_demand_periods(sem_series, build_demand_series(semantic_raw, frequency, int(min_jobs), country, source, all_jobs)[1], frequency=frequency)
        lex_trends = trend_table(lex_full, recent_periods=int(recent_periods), baseline_periods=int(baseline_periods), min_observations=int(min_observations), frequency=frequency) if not lex_full.empty else pd.DataFrame()
        sem_trends = trend_table(sem_full, recent_periods=int(recent_periods), baseline_periods=int(baseline_periods), min_observations=int(min_observations), frequency=frequency) if not sem_full.empty else pd.DataFrame()
        trend_agreement = float("nan")
        if not lex_trends.empty and not sem_trends.empty:
            lt = lex_trends[["skill_name", "classification"]].rename(columns={"classification":"Lexical trend"})
            stt = sem_trends[["skill_name", "classification"]].rename(columns={"classification":"Semantic trend"})
            joined_trends = lt.merge(stt, on="skill_name", how="inner")
            if not joined_trends.empty:
                trend_agreement = float(joined_trends["Lexical trend"].eq(joined_trends["Semantic trend"]).mean()) * 100
                comparison = comparison.merge(joined_trends, on="skill_name", how="left")
                comparison["Trend classification agrees"] = comparison["Lexical trend"].eq(comparison["Semantic trend"])
        x, y, z = st.columns(3)
        x.metric("Spearman rank correlation", "—" if pd.isna(stats["spearman"]) else f"{stats['spearman']:.3f}")
        y.metric("Top-10 Jaccard overlap", "—" if pd.isna(stats["top_k_overlap"]) else f"{stats['top_k_overlap']:.1%}")
        z.metric("Trend classification agreement", "—" if pd.isna(trend_agreement) else f"{trend_agreement:.1f}%")
        # Overlay selected skills on a shared period axis for direct visual comparison.
        trend_parts = []
        for frame, label in [(lex_full, "Lexical"), (sem_full, "Semantic")]:
            if not frame.empty:
                temp = frame[["period", "skill_name", "demand_rate"]].copy()
                temp["Extraction method"] = label
                trend_parts.append(temp)
        if trend_parts:
            overlay = pd.concat(trend_parts, ignore_index=True)
            overlay_skills = sorted(overlay.groupby("skill_name")["demand_rate"].mean().nlargest(8).index)
            chosen_compare_skills = st.multiselect("Skills to compare over time", overlay_skills, default=overlay_skills[:5], key="method_compare_skills")
            if chosen_compare_skills:
                plot_data = overlay[overlay["skill_name"].isin(chosen_compare_skills)]
                fig = px.line(plot_data, x="period", y="demand_rate", color="Extraction method", line_dash="Extraction method", facet_row="skill_name", markers=True, labels={"period":"Posting period", "demand_rate":"Demand rate (%)"})
                fig.update_layout(height=max(360, 190 * len(chosen_compare_skills)), hovermode="x unified", legend_title_text="Method")
                st.plotly_chart(fig, use_container_width=True)
        comparison["Demand difference (semantic - lexical, pp)"] = comparison["Semantic mean demand (%)"] - comparison["Lexical mean demand (%)"]
        st.dataframe(comparison.sort_values("Lexical mean demand (%)", ascending=False), use_container_width=True, hide_index=True)
        st.download_button("Download representation comparison (CSV)", comparison.to_csv(index=False).encode("utf-8"),
                           "lexical_semantic_temporal_comparison.csv", "text/csv")
        st.caption("These metrics measure sensitivity of downstream analysis, not extraction accuracy. RQ1 is evaluated separately with ground-truth precision, recall, and F1. Trend comparisons use the same date scope and eligible-job denominator; absent skill mentions are only treated as zero in periods where eligible advertisements exist.")
    else:
        st.info("Insufficient overlapping data for comparison.")
else:
    st.info("This comparison becomes available when extraction results for both lexical and semantic/canonical methods are stored in the database.")

# ---------------------------------------------------------------------------
# 6. Data-quality diagnostics and CSV exports
# ---------------------------------------------------------------------------
st.subheader("6. Data-quality checks")
dates = pd.to_datetime(all_jobs["posting_date"], errors="coerce")
q1, q2, q3, q4 = st.columns(4)
q1.metric("Missing/invalid dates in master jobs", f"{int(dates.isna().sum()):,}")
q2.metric("Distinct sources", f"{all_jobs['source_platform'].nunique(dropna=True):,}")
q3.metric("Dated observation range", f"{dates.min().date()} – {dates.max().date()}" if dates.notna().any() else "N/A")
q4.metric("Periods in current series", f"{series_full['period'].nunique():,}")
st.caption("Demand percentages use the number of eligible dated jobs as denominator. Changes in source coverage and collection volume can still affect interpretation.")
st.download_button("Download aggregated skill-period series (CSV)", series_full.to_csv(index=False).encode("utf-8"),
                   "temporal_skill_period_series.csv", "text/csv")

# ---------------------------------------------------------------------------
# 7. Automated master-data checks and a reproducible manual source audit sample
# ---------------------------------------------------------------------------
st.subheader("7. Scraped-data quality and source verification")
with get_connection() as conn:
    master_jobs = pd.read_sql_query("SELECT * FROM jobs", conn)
if master_jobs.empty:
    st.info("The master database contains no job records to validate.")
else:
    required_fields = [c for c in ["job_title", "company_name", "source_platform", "source_url", "posting_date", "country"] if c in master_jobs.columns]
    quality_rows = []
    for field in required_fields:
        values = master_jobs[field]
        missing = values.isna() | values.astype(str).str.strip().isin(["", "None", "nan", "NaT"])
        quality_rows.append({"Check": f"Missing {field}", "Affected records": int(missing.sum()), "Records checked": int(len(master_jobs)), "Rate (%)": round(float(missing.mean() * 100), 2)})
    if "source_url" in master_jobs.columns:
        valid_urls = master_jobs["source_url"].fillna("").astype(str).str.strip()
        duplicate_url = valid_urls.ne("") & valid_urls.duplicated(keep=False)
        quality_rows.append({"Check":"Duplicate non-empty source URLs", "Affected records":int(duplicate_url.sum()), "Records checked":int(len(master_jobs)), "Rate (%)":round(float(duplicate_url.mean()*100),2)})
    if "posting_date" in master_jobs.columns:
        parsed_dates = pd.to_datetime(master_jobs["posting_date"], errors="coerce", utc=True)
        invalid_date = master_jobs["posting_date"].notna() & master_jobs["posting_date"].astype(str).str.strip().ne("") & parsed_dates.isna()
        future_date = parsed_dates > pd.Timestamp.now(tz="UTC")
        quality_rows.append({"Check":"Unparseable non-empty posting dates", "Affected records":int(invalid_date.sum()), "Records checked":int(len(master_jobs)), "Rate (%)":round(float(invalid_date.mean()*100),2)})
        quality_rows.append({"Check":"Posting dates in the future", "Affected records":int(future_date.sum()), "Records checked":int(len(master_jobs)), "Rate (%)":round(float(future_date.mean()*100),2)})
    quality_df = pd.DataFrame(quality_rows)
    st.markdown("**Automated checks**")
    st.dataframe(quality_df, use_container_width=True, hide_index=True)
    st.download_button("Download automated data-quality report (CSV)", quality_df.to_csv(index=False).encode("utf-8"), "master_data_quality_checks.csv", "text/csv")
    st.markdown("**Manual verification sample**")
    st.caption("Export a reproducible sample and compare each record with its original advertisement. Stratification spreads the sample across source platforms and, where available, posting years. This is an audit aid, not proof of statistical representativeness.")
    audit_size = st.selectbox("Target sample size", [25, 50, 75, 100], index=1, key="source_audit_size")
    audit = master_jobs.copy()
    if "source_url" not in audit.columns:
        audit["source_url"] = ""
    if "source_platform" not in audit.columns:
        audit["source_platform"] = "Unknown"
    audit["source_platform"] = audit["source_platform"].fillna("Unknown").astype(str)
    audit["_audit_date"] = pd.to_datetime(audit.get("posting_date", pd.Series(index=audit.index, dtype=object)), errors="coerce")
    audit["_audit_year"] = audit["_audit_date"].dt.year.fillna(-1).astype(int).astype(str).replace({"-1":"Unknown date"})
    audit = audit.drop_duplicates(subset=[c for c in ["job_id", "source_url"] if c in audit.columns])
    # Allocate approximately evenly across source/year strata, then fill any remaining slots deterministically.
    strata_cols = [c for c in ["source_platform", "_audit_year"] if c in audit.columns]
    sample_parts = []
    if not audit.empty:
        groups = list(audit.groupby(strata_cols, dropna=False, sort=True)) if strata_cols else [("all", audit)]
        per_group = max(1, int(audit_size) // max(1, len(groups)))
        for _, group in groups:
            sample_parts.append(group.sample(n=min(per_group, len(group)), random_state=42))
        sampled = pd.concat(sample_parts).drop_duplicates() if sample_parts else audit.iloc[0:0]
        if len(sampled) < min(int(audit_size), len(audit)):
            remaining = audit.loc[~audit.index.isin(sampled.index)]
            if not remaining.empty:
                sampled = pd.concat([sampled, remaining.sample(n=min(int(audit_size)-len(sampled), len(remaining)), random_state=42)])
        sampled = sampled.head(int(audit_size)).copy()
        sampled.insert(0, "manual_verification_status", "Not yet checked")
        sampled.insert(1, "manual_notes", "")
        sampled = sampled.drop(columns=[c for c in ["_audit_date", "_audit_year"] if c in sampled.columns])
        preferred = [c for c in ["manual_verification_status", "manual_notes", "job_id", "source_platform", "source_url", "job_title", "company_name", "country", "location", "posting_date", "work_mode"] if c in sampled.columns]
        st.write(f"Sample prepared: **{len(sampled):,} advertisements**. Use the exported file to record verification status and notes after checking the source page.")
        st.dataframe(sampled[preferred].head(15), use_container_width=True, hide_index=True)
        st.download_button("Download manual source-verification sample (CSV)", sampled[preferred].to_csv(index=False).encode("utf-8-sig"), "manual_source_verification_sample.csv", "text/csv")
    else:
        st.info("No records are available to sample.")
