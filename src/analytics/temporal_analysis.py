"""Temporal skill-demand analytics for the shared master SQLite database.

Research safeguards:
* Uses original posting_date values, never scrape/import timestamps as substitutes.
* Calculates demand as jobs mentioning a skill / all eligible dated jobs.
* Keeps forecasting exploratory and evaluates it chronologically against baselines.
* Treats emerging/growing/declining labels as screening candidates, not ground truth.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Optional

import numpy as np
import pandas as pd


def load_temporal_input(conn: sqlite3.Connection, method: str = "all") -> pd.DataFrame:
    """Load dated job-skill records from the shared database."""
    query = """
        SELECT j.job_id, j.posting_date, j.country, j.source_platform,
               j.job_title, j.source_url, es.skill_name, es.method,
               er.run_type, er.run_id
        FROM jobs AS j
        INNER JOIN extracted_skills AS es ON es.job_id = j.job_id
        LEFT JOIN extraction_runs AS er ON er.run_id = es.run_id
        WHERE j.posting_date IS NOT NULL AND TRIM(j.posting_date) <> ''
    """
    params: list[str] = []
    if method.lower() != "all":
        query += " AND LOWER(es.method) = LOWER(?)"
        params.append(method)
    return pd.read_sql_query(query, conn, params=params)


def load_eligible_jobs(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load the job population, including missing dates and zero skill mentions."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    declaration = "data_provenance" if "data_provenance" in columns else "NULL"
    return pd.read_sql_query(
        f"""SELECT job_id, posting_date, country, source_platform, job_title, source_url,
                  {declaration} AS data_provenance
           FROM jobs""",
        conn,
    )


def matched_temporal_mentions(cohort: pd.DataFrame) -> pd.DataFrame:
    """Convert a verified cohort's per-method results to job and skill rows."""
    job_fields = ["job_id", "posting_date", "country", "source_platform", "job_title", "source_url"]
    methods = []
    for method in ("lexical", "semantic"):
        mentions = cohort[job_fields].assign(
            skill_name=cohort[f"{method}_skills"].map(json.loads),
            method=method,
        )
        methods.append(mentions.explode("skill_name").dropna(subset=["skill_name"]))
    return pd.concat(methods, ignore_index=True)


def parse_posting_dates(values: pd.Series) -> pd.Series:
    """Parse mixed posting-date formats per value before grouping in UTC."""
    return pd.to_datetime(values, format="mixed", errors="coerce", utc=True).dt.tz_convert(None)


def normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse real posting dates and remove invalid dates; do not infer missing dates."""
    out = df.copy()
    if "posting_date" not in out:
        out["posting_date"] = pd.NaT
    out["posting_date"] = parse_posting_dates(out["posting_date"])
    out = out.dropna(subset=["posting_date"])
    if "skill_name" in out:
        out["skill_name"] = out["skill_name"].fillna("").astype(str).str.strip()
        out = out[out["skill_name"].ne("")]
    return out


def _frequency(value: str) -> str:
    return "Q" if str(value).strip().upper() in {"Q", "QUARTERLY"} else "M"


def _filter_scope(df: pd.DataFrame, country: str = "All", source: str = "All") -> pd.DataFrame:
    out = df.copy()
    if country != "All" and "country" in out:
        out = out[out["country"].fillna("Unknown").astype(str).eq(country)]
    if source != "All" and "source_platform" in out:
        out = out[out["source_platform"].fillna("Unknown").astype(str).eq(source)]
    return out


def build_demand_series(
    df: pd.DataFrame, frequency: str = "M", min_jobs: int = 1,
    country: str = "All", source: str = "All",
    jobs_df: Optional[pd.DataFrame] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return skill-period demand and denominator table.

    A job is counted once per skill per period. The denominator is every eligible,
    dated job in the selected scope, including jobs with zero extracted skills.
    """
    if min_jobs < 1:
        raise ValueError("min_jobs must be at least 1.")
    freq = _frequency(frequency)
    jobs = _filter_scope(jobs_df if jobs_df is not None else df, country, source)
    jobs = normalize_dates(jobs.reindex(columns=["job_id", "posting_date"])).dropna(subset=["job_id"])
    jobs["period"] = jobs["posting_date"].dt.to_period(freq).dt.to_timestamp()
    job_periods = jobs[["job_id", "period"]].drop_duplicates()
    eligible = job_periods.groupby("period").size().rename("eligible_jobs").reset_index()
    # Retain low-sample counts for diagnostics without using them for demand.
    eligible["meets_min_jobs"] = eligible["eligible_jobs"] >= int(min_jobs)

    # Require the same eligible job and period in the numerator and denominator.
    mentions = normalize_dates(df.reindex(columns=["job_id", "posting_date", "skill_name"]))
    mentions["period"] = mentions["posting_date"].dt.to_period(freq).dt.to_timestamp()
    mentions = mentions[["job_id", "period", "skill_name"]].drop_duplicates()
    mentions = job_periods.merge(mentions, on=["job_id", "period"], how="inner")
    counts = (mentions.groupby(["period", "skill_name"])["job_id"].nunique()
              .rename("jobs_mentioning_skill").reset_index())
    qualified = eligible.loc[eligible["meets_min_jobs"], ["period", "eligible_jobs"]]
    series = counts.merge(qualified, on="period", how="inner")
    series["demand_rate"] = 100 * series["jobs_mentioning_skill"] / series["eligible_jobs"].replace(0, np.nan)
    series = series[["period", "skill_name", "jobs_mentioning_skill", "eligible_jobs", "demand_rate"]]
    return (series.sort_values(["period", "skill_name"]).reset_index(drop=True),
            eligible.sort_values("period").reset_index(drop=True))


def expand_zero_demand_periods(series: pd.DataFrame, eligible: pd.DataFrame, frequency: str = "M") -> pd.DataFrame:
    """Fill observed zero demand from a skill's first mention to the latest eligible period."""
    if series.empty or eligible.empty:
        return series.iloc[:0].copy()
    freq = _frequency(frequency)
    pandas_freq = "MS" if freq == "M" else "QS"
    if "meets_min_jobs" in eligible:
        eligible = eligible.loc[eligible["meets_min_jobs"]]
    eligible_by_period = eligible.drop_duplicates("period").set_index("period")["eligible_jobs"]
    observed_periods = pd.DatetimeIndex(sorted(pd.to_datetime(eligible_by_period.index).unique()))
    rows = []
    for skill, group in series.groupby("skill_name"):
        group = group.drop_duplicates("period").set_index("period")
        index = pd.date_range(group.index.min(), observed_periods.max(), freq=pandas_freq).intersection(observed_periods)
        if index.empty:
            continue
        counts = group["jobs_mentioning_skill"].reindex(index, fill_value=0)
        denominators = eligible_by_period.reindex(index)
        frame = pd.DataFrame({"period": index, "skill_name": skill,
                              "jobs_mentioning_skill": counts.to_numpy(),
                              "eligible_jobs": denominators.to_numpy()})
        frame["demand_rate"] = 100 * frame["jobs_mentioning_skill"] / frame["eligible_jobs"].replace(0, np.nan)
        rows.append(frame)
    if not rows:
        return series.iloc[:0].copy()
    return pd.concat(rows, ignore_index=True).sort_values(["period", "skill_name"]).reset_index(drop=True)


def matched_method_demand_series(
    mentions: pd.DataFrame,
    jobs: pd.DataFrame,
    frequency: str = "M",
    min_jobs: int = 1,
    country: str = "All",
    source: str = "All",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Align both methods on every qualifying period and skill of a matched cohort."""
    series_by_method = []
    denominators = pd.DataFrame()
    for method in ("lexical", "semantic"):
        series, method_denominators = build_demand_series(
            mentions.loc[mentions["method"].eq(method)], frequency, min_jobs, country, source, jobs,
        )
        series_by_method.append(series)
        if not method_denominators.empty:
            denominators = method_denominators

    observed = pd.concat(series_by_method, ignore_index=True)
    if observed.empty:
        return pd.DataFrame(), pd.DataFrame()
    skills = pd.DataFrame({"skill_name": sorted(observed["skill_name"].unique())})
    periods = denominators.loc[denominators["meets_min_jobs"], ["period", "eligible_jobs"]]
    grid = periods.merge(skills, how="cross")

    aligned = []
    for series in series_by_method:
        if series.empty:
            frame = grid.assign(jobs_mentioning_skill=0)
        else:
            frame = grid.merge(
                series[["period", "skill_name", "jobs_mentioning_skill"]],
                on=["period", "skill_name"], how="left",
            )
            frame["jobs_mentioning_skill"] = frame["jobs_mentioning_skill"].fillna(0).astype(int)
        frame["demand_rate"] = 100 * frame["jobs_mentioning_skill"] / frame["eligible_jobs"]
        aligned.append(frame)
    return aligned[0], aligned[1]


def trend_table(
    series: pd.DataFrame, recent_periods: int = 3, baseline_periods: int = 3,
    min_observations: int = 6, frequency: str = "M",
) -> pd.DataFrame:
    """Calculate trend, persistence and volatility indicators with transparent labels."""
    if series.empty:
        return pd.DataFrame()
    freq = _frequency(frequency)
    pandas_freq = "MS" if freq == "M" else "QS"
    rows = []
    for skill, group in series.groupby("skill_name"):
        group = group.copy()
        group["period"] = pd.to_datetime(group["period"], errors="coerce")
        group["demand_rate"] = pd.to_numeric(group["demand_rate"], errors="coerce")
        group = group.dropna(subset=["period", "demand_rate"]).drop_duplicates("period").sort_values("period")
        if group.empty:
            continue
        # Keep internal periods explicit. Missing eligible periods remain missing;
        # only periods supplied by the expanded series become zero demand. A gap
        # with no eligible advertisements must not be mistaken for zero demand.
        index = pd.date_range(group["period"].min(), group["period"].max(), freq=pandas_freq)
        rates = group.set_index("period")["demand_rate"].reindex(index)
        rates = rates.dropna()
        n = len(rates)
        recent_n = min(max(1, int(recent_periods)), n)
        base_n = min(max(1, int(baseline_periods)), max(1, n - recent_n))
        recent = float(rates.iloc[-recent_n:].mean())
        baseline = float(rates.iloc[-recent_n-base_n:-recent_n].mean()) if n > recent_n else float(rates.iloc[:max(1, n // 2)].mean())
        delta = recent - baseline
        relative = delta / baseline * 100 if baseline > 0 else np.nan
        values = rates.to_numpy(dtype=float)
        slope = float(np.polyfit(np.arange(n), values, 1)[0]) if n >= 2 else 0.0
        changes = np.diff(values)
        persistence = float(np.mean(changes[-recent_n:] > 0)) if len(changes) else 0.0
        volatility = float(rates.std(ddof=0))
        low_baseline = baseline <= max(1.0, float(rates.quantile(0.35)))
        if n < int(min_observations):
            label = "Volatile / uncertain"
        elif low_baseline and delta > 0 and slope > 0 and persistence >= 0.5:
            label = "Emerging candidate"
        elif slope > 0.05 and delta > 0:
            label = "Growing"
        elif slope < -0.05 and delta < 0:
            label = "Declining"
        elif volatility > max(1.0, float(rates.mean()) * 0.75):
            label = "Volatile / uncertain"
        else:
            label = "Stable"
        rows.append({
            "skill_name": skill, "observations": n,
            "baseline_rate": baseline, "recent_rate": recent,
            "absolute_change_pp": delta, "relative_growth_pct": relative,
            "trend_slope_pp_per_period": slope,
            "positive_change_persistence": persistence,
            "volatility_std_pp": volatility, "classification": label,
            "latest_period": rates.index.max(),
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["classification", "recent_rate"], ascending=[True, False]).reset_index(drop=True)


_FORECAST_MODEL_NAMES = {
    "last_value_baseline": "Last-value baseline",
    "moving_average_3": "Moving-average baseline",
    "linear_trend_candidate": "Linear-trend baseline",
    "random_forest_candidate": "Random Forest",
}
_MIN_BACKTEST_ORIGINS = 2
_FOREST_MIN_TRAIN_PERIODS = 24


def _forecast_history(series: pd.DataFrame, skill: str, frequency: str) -> pd.Series:
    """Take the latest uninterrupted run of usable calendar periods."""
    group = series.loc[series["skill_name"].eq(skill), ["period", "demand_rate"]].copy()
    group["period"] = parse_posting_dates(group["period"]).dt.to_period(_frequency(frequency)).dt.to_timestamp()
    group["demand_rate"] = pd.to_numeric(group["demand_rate"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    rates = group.dropna().drop_duplicates("period").set_index("period")["demand_rate"].sort_index()
    if rates.empty:
        return rates
    calendar = pd.date_range(rates.index[0], rates.index[-1], freq="MS" if _frequency(frequency) == "M" else "QS")
    missing = calendar.difference(rates.index)
    return rates.loc[rates.index > missing[-1]] if not missing.empty else rates


def _forecast_validation_plan(period_count: int, min_train: int, horizon: int) -> tuple[int, type | None]:
    """Choose a common first origin and an optional forest for both forecast and backtest."""
    forest_min_train = max(min_train, _FOREST_MIN_TRAIN_PERIODS)
    if period_count >= forest_min_train + horizon + _MIN_BACKTEST_ORIGINS - 1:
        try:
            from sklearn.ensemble import RandomForestRegressor

            return forest_min_train, RandomForestRegressor
        except ImportError:
            pass
    return min_train, None


def _predict_forecast_models(values: np.ndarray, horizon: int, forest_type: type | None) -> dict[str, np.ndarray]:
    predictions = {
        "last_value_baseline": np.repeat(values[-1], horizon),
        "moving_average_3": np.repeat(values[-3:].mean(), horizon),
        "linear_trend_candidate": np.polyval(
            np.polyfit(np.arange(len(values)), values, 1), np.arange(len(values), len(values) + horizon),
        ),
    }
    if forest_type is not None:
        features = [[values[i - 1], values[i - 2], values[i - 3], values[i - 3:i].mean()]
                    for i in range(3, len(values))]
        model = forest_type(n_estimators=150, random_state=42, min_samples_leaf=2, n_jobs=1)
        model.fit(features, values[3:])
        state = values[-3:].tolist()
        forecast = []
        for _ in range(horizon):
            row = [state[-1], state[-2], state[-3], np.mean(state[-3:])]
            value = float(np.clip(model.predict([row])[0], 0, 100))
            forecast.append(value)
            state.append(value)
        predictions["random_forest_candidate"] = np.asarray(forecast)
    return {name: np.clip(estimates, 0, 100) for name, estimates in predictions.items()}


def evaluate_forecast_baselines(
    series: pd.DataFrame, skill: str, frequency: str = "M", min_train: int = 8, *, horizon: int = 1,
) -> tuple[pd.DataFrame, str]:
    """Evaluate every displayed horizon on the same rolling origins and model configuration."""
    if not 1 <= horizon <= 3:
        return pd.DataFrame(), "Forecast horizon must be between one and three periods."
    rates = _forecast_history(series, skill, frequency)
    min_train = max(2, int(min_train))
    required = min_train + horizon + _MIN_BACKTEST_ORIGINS - 1
    if len(rates) < required:
        return pd.DataFrame(), f"Need at least {required} consecutive usable periods for this backtest; found {len(rates)}."

    first_origin, forest_type = _forecast_validation_plan(len(rates), min_train, horizon)
    values = rates.to_numpy(dtype=float)
    records = []
    for origin in range(first_origin, len(values) - horizon + 1):
        train = values[:origin]
        predictions = _predict_forecast_models(train, horizon, forest_type)
        for model, estimates in predictions.items():
            for step, estimated in enumerate(estimates, start=1):
                actual = values[origin + step - 1]
                error = float(estimated - actual)
                records.append({
                    "horizon": step,
                    "model": _FORECAST_MODEL_NAMES[model],
                    "absolute_error": abs(error),
                    "squared_error": error ** 2,
                    "direction_correct": bool(np.sign(estimated - train[-1]) == np.sign(actual - train[-1])),
                })

    summary = pd.DataFrame(records).groupby(["horizon", "model"]).agg(
        evaluated_periods=("absolute_error", "count"),
        MAE=("absolute_error", "mean"),
        RMSE=("squared_error", lambda errors: float(np.sqrt(errors.mean()))),
        directional_accuracy=("direction_correct", "mean"),
    ).reset_index()
    note = (
        "Rolling-origin evaluation uses the latest uninterrupted history. "
        "Models use the same target periods within each horizon. "
        "Errors are in demand-rate percentage points."
    )
    if forest_type is None:
        note += " Random Forest requires scikit-learn and enough history to evaluate all selected horizons after its 24-period training minimum."
    return summary, note


def forecast_skill(
    series: pd.DataFrame, skill: str, horizon: int = 3, min_periods: int = 8, frequency: str = "M",
    *, latest_observed_period: pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, str]:
    """Forecast one to three periods once all displayed candidates can be backtested."""
    if not 1 <= horizon <= 3:
        return pd.DataFrame(), "Forecast horizon must be between one and three periods."
    rates = _forecast_history(series, skill, frequency)
    if rates.empty:
        return pd.DataFrame(), "No observations exist for this skill."
    if latest_observed_period is not None and rates.index[-1] < latest_observed_period:
        return pd.DataFrame(), "Forecasting is paused because the latest observed period is below the sample threshold."

    min_train = max(2, int(min_periods))
    required = min_train + horizon + _MIN_BACKTEST_ORIGINS - 1
    if len(rates) < required:
        return pd.DataFrame(), f"Need at least {required} consecutive usable periods to forecast and backtest this horizon; found {len(rates)}."

    _, forest_type = _forecast_validation_plan(len(rates), min_train, horizon)
    predictions = _predict_forecast_models(rates.to_numpy(dtype=float), horizon, forest_type)
    calendar_frequency = "MS" if _frequency(frequency) == "M" else "QS"
    periods = pd.date_range(rates.index[-1], periods=horizon + 1, freq=calendar_frequency)[1:]
    return pd.DataFrame({"period": periods, **predictions}), (
        f"Forecasts use {len(rates)} consecutive usable periods and are exploratory."
    )


def representation_comparison(series_a: pd.DataFrame, series_b: pd.DataFrame, label_a: str, label_b: str) -> tuple[pd.DataFrame, dict]:
    """Compare mean demand ranks, top-k overlap, and available trend agreement."""
    empty_stats = {"spearman": np.nan, "top_k_overlap": np.nan, "top_k_union_count": 0,
                   "classification_agreement": np.nan}
    if series_a.empty or series_b.empty:
        return pd.DataFrame(), empty_stats
    # Compare per-skill mean demand rates so rankings are on a common scale.
    # This is downstream sensitivity analysis, not ground-truth extraction scoring.
    a = series_a.groupby("skill_name")["demand_rate"].mean().rename(label_a)
    b = series_b.groupby("skill_name")["demand_rate"].mean().rename(label_b)
    joined = pd.concat([a, b], axis=1).fillna(0)
    varied = joined[label_a].nunique() > 1 and joined[label_b].nunique() > 1
    corr = joined[label_a].corr(joined[label_b], method="spearman") if varied else np.nan
    top_a, top_b = (set(joined.loc[joined[label].gt(0), label].nlargest(10).index) for label in (label_a, label_b))
    top_union_count = len(top_a | top_b)
    stats = {"spearman": float(corr) if pd.notna(corr) else np.nan,
             "top_k_overlap": len(top_a & top_b) / top_union_count if top_union_count else np.nan,
             "top_k_union_count": top_union_count,
             "classification_agreement": np.nan}
    return joined.reset_index(), stats
