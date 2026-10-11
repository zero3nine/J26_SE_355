"""Temporal skill-demand analysis for the shared master SQLite database.

Database inputs:
    jobs             Job metadata and posting dates; defines eligible-job counts.
    extracted_skills Extracted skill mentions and extraction-method labels.
    extraction_runs  Optional metadata about the extraction run.

All functions are independent of Streamlit so they can be reused and tested.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

import numpy as np
import pandas as pd


def load_temporal_input(
    conn: sqlite3.Connection,
    method: str = "all",
) -> pd.DataFrame:
    """Load dated job-skill records, optionally restricted to one method."""
    query = """
        SELECT
            j.job_id, j.posting_date, j.country, j.source_platform,
            j.job_title, j.source_url,
            es.skill_name, es.method, er.run_type, er.run_id
        FROM jobs AS j
        INNER JOIN extracted_skills AS es ON es.job_id = j.job_id
        LEFT JOIN extraction_runs AS er ON er.run_id = es.run_id
        WHERE j.posting_date IS NOT NULL
          AND TRIM(j.posting_date) <> ''
    """
    params: list[str] = []

    if method.lower() != "all":
        query += " AND LOWER(es.method) = LOWER(?)"
        params.append(method)

    return pd.read_sql_query(query, conn, params=params)


def load_eligible_jobs(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load all dated jobs, including jobs without extracted skill records.

    This dataset must be used as the denominator for demand percentages.
    """
    return pd.read_sql_query(
        """
        SELECT job_id, posting_date, country, source_platform,
               job_title, source_url
        FROM jobs
        WHERE posting_date IS NOT NULL
          AND TRIM(posting_date) <> ''
        """,
        conn,
    )


def normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse the original posting date and discard invalid/missing dates.

    `posting_date` is the event date used for temporal analysis. Do not substitute
    first_seen_at, scraped_at, collected_at, or imported_at: those record when a
    job was encountered or stored, not when it was advertised.
    """
    out = df.copy()
    out["posting_date"] = pd.to_datetime(
        out["posting_date"], errors="coerce", utc=True
    ).dt.tz_convert(None)
    out = out.dropna(subset=["posting_date"])

    if "skill_name" in out.columns:
        out["skill_name"] = out["skill_name"].fillna("").astype(str).str.strip()
        out = out[out["skill_name"].ne("")]

    return out


def _frequency(value: str) -> str:
    """Return the supported pandas period frequency: monthly or quarterly."""
    return "Q" if str(value).strip().upper() in {"Q", "QUARTERLY"} else "M"


def _filter_scope(
    df: pd.DataFrame,
    country: str = "All",
    source: str = "All",
) -> pd.DataFrame:
    """Apply identical country and source filters to jobs and skill records."""
    out = df.copy()
    if country != "All" and "country" in out.columns:
        out = out[out["country"].fillna("Unknown").eq(country)]
    if source != "All" and "source_platform" in out.columns:
        out = out[out["source_platform"].fillna("Unknown").eq(source)]
    return out


def build_demand_series(
    df: pd.DataFrame,
    frequency: str = "M",
    min_jobs: int = 1,
    country: str = "All",
    source: str = "All",
    jobs_df: Optional[pd.DataFrame] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate skill-period demand and the eligible-job denominator.

    Args:
        df: Extracted job-skill rows.
        frequency: 'M' for monthly or 'Q' for quarterly.
        min_jobs: Minimum eligible jobs required for a period.
        country: Country filter, or 'All'.
        source: Source-platform filter, or 'All'.
        jobs_df: All dated jobs from load_eligible_jobs(). Pass this to ensure
            jobs without extracted skills remain in the denominator.

    Returns:
        (skill_period_series, eligible_jobs_by_period).

    Each job counts at most once for a given skill in a period.
    Demand rate = jobs mentioning skill / all eligible jobs * 100.
    """
    if min_jobs < 1:
        raise ValueError("min_jobs must be at least 1.")

    data = _filter_scope(df, country, source)
    if data.empty:
        return pd.DataFrame(), pd.DataFrame()

    data = normalize_dates(data).dropna(subset=["job_id"])
    if data.empty:
        return pd.DataFrame(), pd.DataFrame()

    freq = _frequency(frequency)
    data["period"] = data["posting_date"].dt.to_period(freq).dt.to_timestamp()

    # Use the complete jobs table for the denominator whenever supplied.
    denominator = jobs_df if jobs_df is not None else df
    denominator = _filter_scope(denominator, country, source)
    denominator = normalize_dates(denominator).dropna(subset=["job_id"])
    denominator["period"] = (
        denominator["posting_date"].dt.to_period(freq).dt.to_timestamp()
    )

    eligible = (
        denominator[["job_id", "period"]]
        .drop_duplicates()
        .groupby("period")
        .size()
        .rename("eligible_jobs")
        .reset_index()
    )

    mentions = data[["job_id", "period", "skill_name"]].copy()
    mentions["skill_name"] = (
        mentions["skill_name"].fillna("").astype(str).str.strip()
    )
    mentions = mentions[mentions["skill_name"].ne("")]
    mentions = mentions.drop_duplicates(["job_id", "period", "skill_name"])

    counts = (
        mentions.groupby(["period", "skill_name"])["job_id"]
        .nunique()
        .rename("jobs_mentioning_skill")
        .reset_index()
    )

    series = counts.merge(eligible, on="period", how="left")
    series["demand_rate"] = (
        100 * series["jobs_mentioning_skill"]
        / series["eligible_jobs"].replace(0, np.nan)
    )
    series = series[series["eligible_jobs"] >= int(min_jobs)]

    return (
        series.sort_values(["period", "skill_name"]).reset_index(drop=True),
        eligible.sort_values("period").reset_index(drop=True),
    )


def expand_zero_demand_periods(
    series: pd.DataFrame,
    eligible: pd.DataFrame,
    frequency: str = "M",
) -> pd.DataFrame:
    """Add zero-demand periods between observations where jobs were eligible.

    Periods with no eligible jobs retain a missing demand rate rather than
    being treated as a real zero-demand observation.
    """
    if series.empty or eligible.empty:
        return pd.DataFrame()

    freq = _frequency(frequency)
    pandas_freq = "MS" if freq == "M" else "QS"
    eligible_by_period = (
        eligible.drop_duplicates("period").set_index("period")["eligible_jobs"]
    )
    observed_periods = pd.DatetimeIndex(
        sorted(pd.to_datetime(eligible["period"]).unique())
    )

    rows = []
    for skill, group in series.groupby("skill_name"):
        group = group.drop_duplicates("period").set_index("period")
        index = pd.date_range(
            group.index.min(), group.index.max(), freq=pandas_freq
        ).intersection(observed_periods)

        if index.empty:
            continue

        counts = group["jobs_mentioning_skill"].reindex(index, fill_value=0)
        denominators = eligible_by_period.reindex(index)
        frame = pd.DataFrame({
            "period": index,
            "skill_name": skill,
            "jobs_mentioning_skill": counts.to_numpy(),
            "eligible_jobs": denominators.to_numpy(),
        })
        frame["demand_rate"] = (
            100 * frame["jobs_mentioning_skill"]
            / frame["eligible_jobs"].replace(0, np.nan)
        )
        rows.append(frame)

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True).sort_values(
        ["period", "skill_name"]
    ).reset_index(drop=True)


def trend_table(
    series: pd.DataFrame,
    recent_periods: int = 3,
    baseline_periods: int = 3,
    min_observations: int = 6,
    frequency: str = "M",
) -> pd.DataFrame:
    """Create trend summaries using transparent, exploratory screening rules."""
    if series.empty:
        return pd.DataFrame()

    freq = _frequency(frequency)
    pandas_freq = "MS" if freq == "M" else "QS"
    rows = []

    for skill, group in series.groupby("skill_name"):
        group = group.copy()
        group["period"] = pd.to_datetime(group["period"], errors="coerce")
        group["demand_rate"] = pd.to_numeric(
            group["demand_rate"], errors="coerce"
        )
        group = group.dropna(subset=["period", "demand_rate"])
        group = group.drop_duplicates("period")
        if group.empty:
            continue

        index = pd.date_range(
            group["period"].min(), group["period"].max(), freq=pandas_freq
        )
        rates = (
            group.set_index("period")["demand_rate"]
            .reindex(index, fill_value=0)
            .astype(float)
        )

        n = len(rates)
        recent_n = min(max(1, int(recent_periods)), n)
        base_n = min(max(1, int(baseline_periods)), max(1, n - recent_n))
        recent = float(rates.iloc[-recent_n:].mean())
        baseline = (
            float(rates.iloc[-recent_n - base_n:-recent_n].mean())
            if n > recent_n
            else float(rates.iloc[:max(1, n // 2)].mean())
        )
        delta = recent - baseline
        relative = delta / baseline * 100 if baseline > 0 else np.nan

        values = rates.to_numpy()
        slope = (
            float(np.polyfit(np.arange(n), values, 1)[0])
            if n >= 2 else 0.0
        )
        changes = np.diff(values)
        persistence = (
            float(np.mean(changes[-recent_n:] > 0)) if len(changes) else 0.0
        )
        volatility = float(rates.std(ddof=0))

        # These labels are candidates for investigation, not verified facts.
        if n < min_observations:
            label = "Volatile / uncertain"
        elif (
            baseline <= max(1.0, float(rates.quantile(0.35)))
            and delta > 0 and slope > 0 and persistence >= 0.5
        ):
            label = "Emerging"
        elif slope > 0.05 and delta > 0:
            label = "Growing"
        elif slope < -0.05 and delta < 0:
            label = "Declining"
        elif volatility > max(1.0, float(rates.mean()) * 0.75):
            label = "Volatile / uncertain"
        else:
            label = "Stable"

        rows.append({
            "skill_name": skill,
            "observations": n,
            "baseline_rate": baseline,
            "recent_rate": recent,
            "absolute_change_pp": delta,
            "relative_growth_pct": relative,
            "trend_slope_pp_per_period": slope,
            "positive_change_persistence": persistence,
            "volatility_std_pp": volatility,
            "classification": label,
            "latest_period": rates.index.max(),
        })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values(
        ["classification", "recent_rate"], ascending=[True, False]
    ).reset_index(drop=True)


def forecast_skill(
    series: pd.DataFrame,
    skill: str,
    horizon: int = 3,
    min_periods: int = 8,
    frequency: str = "M",
) -> tuple[pd.DataFrame, str]:
    """Produce naive and moving-average forecasts plus an optional RF candidate.

    Random Forest is exploratory only. Compare it against simple baselines
    using chronological evaluation before interpreting predictive performance.
    """
    if horizon < 1:
        return pd.DataFrame(), "Forecast horizon must be at least one period."

    group = series[series["skill_name"].eq(skill)].copy()
    if group.empty:
        return pd.DataFrame(), "No observations exist for this skill."

    group["period"] = pd.to_datetime(group["period"], errors="coerce")
    group["demand_rate"] = pd.to_numeric(group["demand_rate"], errors="coerce")
    group = group.dropna(subset=["period", "demand_rate"])
    group = group.drop_duplicates("period").sort_values("period")

    freq = _frequency(frequency)
    if group["period"].nunique() < min_periods:
        return pd.DataFrame(), (
            f"At least {min_periods} periods are required; "
            f"this skill has {group['period'].nunique()}."
        )

    values = group.set_index("period")["demand_rate"].astype(float)
    future = pd.date_range(
        values.index.max() + (
            pd.offsets.MonthBegin(1) if freq == "M"
            else pd.offsets.QuarterBegin(1)
        ),
        periods=horizon,
        freq="MS" if freq == "M" else "QS",
    )

    output = pd.DataFrame({
        "period": future,
        "naive_last_value": [float(values.iloc[-1])] * horizon,
        "moving_average_3": [
            float(values.iloc[-min(3, len(values)):].mean())
        ] * horizon,
    })
    note = (
        "Baseline forecasts only; predictive validity requires chronological "
        "backtesting."
    )

    try:
        from sklearn.ensemble import RandomForestRegressor

        vals = values.to_numpy()
        if len(vals) >= 18:
            features, targets = [], []
            for i in range(3, len(vals)):
                features.append([
                    vals[i - 1], vals[i - 2], vals[i - 3],
                    float(np.mean(vals[i - 3:i])),
                ])
                targets.append(vals[i])

            split = max(8, int(len(features) * 0.8))
            if len(features) - split >= 2:
                model = RandomForestRegressor(
                    n_estimators=150,
                    random_state=42,
                    min_samples_leaf=2,
                )
                model.fit(features[:split], targets[:split])
                predicted = model.predict(features[split:])
                actual = np.asarray(targets[split:])
                mae = float(np.mean(np.abs(actual - predicted)))
                rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))

                state = list(vals[-3:])
                rf_forecasts = []
                for _ in range(horizon):
                    row = [
                        state[-1], state[-2], state[-3],
                        float(np.mean(state[-3:])),
                    ]
                    value = max(0.0, float(model.predict([row])[0]))
                    rf_forecasts.append(value)
                    state.append(value)

                output["random_forest_candidate"] = rf_forecasts
                note = (
                    "Random Forest is exploratory. Chronological holdout "
                    f"MAE={mae:.3f} pp; RMSE={rmse:.3f} pp. "
                    "Compare it against the naive baselines."
                )
    except ImportError:
        note += " Install scikit-learn to enable the Random Forest candidate."

    return output, note


def representation_comparison(
    series_a: pd.DataFrame,
    series_b: pd.DataFrame,
    label_a: str,
    label_b: str,
) -> tuple[pd.DataFrame, dict]:
    """Compare average demand rankings and top-skill overlap."""
    empty_stats = {
        "spearman": np.nan,
        "top_k_overlap": np.nan,
        "classification_agreement": np.nan,
    }
    if series_a.empty or series_b.empty:
        return pd.DataFrame(), empty_stats

    a = series_a.groupby("skill_name")["demand_rate"].mean().rename(label_a)
    b = series_b.groupby("skill_name")["demand_rate"].mean().rename(label_b)
    joined = pd.concat([a, b], axis=1).fillna(0)

    correlation = (
        joined[label_a].corr(joined[label_b], method="spearman")
        if len(joined) > 1 else np.nan
    )
    k = min(10, len(joined))
    top_a = set(joined[label_a].nlargest(k).index)
    top_b = set(joined[label_b].nlargest(k).index)
    jaccard = len(top_a & top_b) / max(1, len(top_a | top_b))

    stats = {
        "spearman": float(correlation) if pd.notna(correlation) else np.nan,
        "top_k_overlap": jaccard,
        "classification_agreement": np.nan,
    }
    return joined.reset_index(), stats
