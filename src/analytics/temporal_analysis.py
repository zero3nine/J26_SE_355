"""Temporal skill-demand analytics for the shared master SQLite database.

Research safeguards:
* Uses original posting_date values, never scrape/import timestamps as substitutes.
* Calculates demand as jobs mentioning a skill / all eligible dated jobs.
* Keeps forecasting exploratory and evaluates it chronologically against baselines.
* Treats emerging/growing/declining labels as screening candidates, not ground truth.
"""
from __future__ import annotations

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
    """Load all dated jobs, including those with no extracted skill rows."""
    return pd.read_sql_query(
        """SELECT job_id, posting_date, country, source_platform, job_title, source_url
           FROM jobs WHERE posting_date IS NOT NULL AND TRIM(posting_date) <> ''""",
        conn,
    )


def normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse real posting dates and remove invalid dates; do not infer missing dates."""
    out = df.copy()
    if "posting_date" not in out:
        out["posting_date"] = pd.NaT
    out["posting_date"] = pd.to_datetime(out["posting_date"], errors="coerce", utc=True).dt.tz_convert(None)
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
    data = normalize_dates(_filter_scope(df, country, source))
    if data.empty or "job_id" not in data:
        return pd.DataFrame(), pd.DataFrame()
    data = data.dropna(subset=["job_id"])
    freq = _frequency(frequency)
    data["period"] = data["posting_date"].dt.to_period(freq).dt.to_timestamp()

    # Keep every eligible dated job in the denominator, including jobs with no
    # extracted skill rows. Otherwise skill demand would be inflated.
    denominator = jobs_df if jobs_df is not None else df
    denominator = normalize_dates(_filter_scope(denominator, country, source))
    if denominator.empty:
        return pd.DataFrame(), pd.DataFrame()
    denominator = denominator.dropna(subset=["job_id"])
    denominator["period"] = denominator["posting_date"].dt.to_period(freq).dt.to_timestamp()
    eligible = (denominator[["job_id", "period"]].drop_duplicates()
                .groupby("period").size().rename("eligible_jobs").reset_index())

    # Count a job at most once for a given skill and period, even if the source
    # contains duplicate extraction rows for that same job-skill pair.
    mentions = data[["job_id", "period", "skill_name"]].copy()
    mentions["skill_name"] = mentions["skill_name"].fillna("").astype(str).str.strip()
    mentions = mentions[mentions["skill_name"].ne("")].drop_duplicates(["job_id", "period", "skill_name"])
    counts = (mentions.groupby(["period", "skill_name"])["job_id"].nunique()
              .rename("jobs_mentioning_skill").reset_index())
    series = counts.merge(eligible, on="period", how="left")
    series["demand_rate"] = 100 * series["jobs_mentioning_skill"] / series["eligible_jobs"].replace(0, np.nan)
    series = series[series["eligible_jobs"] >= int(min_jobs)]
    return (series.sort_values(["period", "skill_name"]).reset_index(drop=True),
            eligible.sort_values("period").reset_index(drop=True))


def expand_zero_demand_periods(series: pd.DataFrame, eligible: pd.DataFrame, frequency: str = "M") -> pd.DataFrame:
    """Represent absent skill mentions as zero only when eligible jobs existed."""
    if series.empty or eligible.empty:
        return pd.DataFrame()
    freq = _frequency(frequency)
    pandas_freq = "MS" if freq == "M" else "QS"
    eligible_by_period = eligible.drop_duplicates("period").set_index("period")["eligible_jobs"]
    observed_periods = pd.DatetimeIndex(sorted(pd.to_datetime(eligible["period"]).unique()))
    rows = []
    for skill, group in series.groupby("skill_name"):
        group = group.drop_duplicates("period").set_index("period")
        index = pd.date_range(group.index.min(), group.index.max(), freq=pandas_freq).intersection(observed_periods)
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
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True).sort_values(["period", "skill_name"]).reset_index(drop=True)


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


def evaluate_forecast_baselines(series: pd.DataFrame, skill: str, frequency: str = "M", min_train: int = 8) -> tuple[pd.DataFrame, str]:
    """Evaluate one-step forecasts chronologically against simple baselines and Random Forest.

    Each forecast uses only observations before its target period. When enough history
    and scikit-learn are available, every model is evaluated over the same later periods
    so their errors are directly comparable. Random Forest uses lagged demand rates.
    """
    group = series[series["skill_name"].eq(skill)].copy()
    if group.empty:
        return pd.DataFrame(), "No observations exist for this skill."
    group["period"] = pd.to_datetime(group["period"], errors="coerce")
    group["demand_rate"] = pd.to_numeric(group["demand_rate"], errors="coerce")
    group = group.dropna(subset=["period", "demand_rate"]).drop_duplicates("period").sort_values("period")
    values = group["demand_rate"].to_numpy(dtype=float)
    if len(values) < min_train + 2:
        return pd.DataFrame(), f"Need at least {min_train + 2} usable periods for rolling-origin evaluation; found {len(values)}."

    rf_available = False
    rf_error = None
    if len(values) >= 15:
        try:
            from sklearn.ensemble import RandomForestRegressor  # noqa: F401
            rf_available = True
        except ImportError:
            rf_error = "Random Forest evaluation was skipped because scikit-learn is not installed."

    # RF needs enough lagged training examples to be meaningful. Evaluate all methods
    # over the same target periods when RF is included, avoiding an unfair comparison.
    # This is rolling-origin validation: no target-period data enters its own training set.
    first_target = max(int(min_train), 12) if rf_available else int(min_train)
    if len(values) <= first_target:
        return pd.DataFrame(), f"Need more than {first_target} usable periods for the selected evaluation setup; found {len(values)}."

    records = []
    for target_idx in range(first_target, len(values)):
        train = values[:target_idx]
        actual = float(values[target_idx])
        predictions = {
            "Last-value baseline": float(train[-1]),
            "Moving-average baseline": float(np.mean(train[-min(3, len(train)):])),
            "Linear-trend baseline": max(0.0, float(np.polyval(np.polyfit(np.arange(len(train)), train, 1), len(train)))),
        }
        if rf_available:
            # Training examples end strictly before the target period.
            X_train = np.asarray([[train[i - 1], train[i - 2], train[i - 3], float(np.mean(train[i - 3:i]))]
                                  for i in range(3, len(train))], dtype=float)
            y_train = train[3:]
            if len(y_train) >= 8:
                from sklearn.ensemble import RandomForestRegressor
                model = RandomForestRegressor(n_estimators=100, random_state=42, min_samples_leaf=2, n_jobs=1)
                model.fit(X_train, y_train)
                features = [[train[-1], train[-2], train[-3], float(np.mean(train[-3:]))]]
                predictions["Random Forest"] = max(0.0, float(model.predict(features)[0]))
        # Demand rate is a percentage, so keep all candidate predictions within
        # the valid 0–100 range before calculating comparable error metrics.
        for model_name, predicted in predictions.items():
            predicted = float(np.clip(predicted, 0, 100))
            records.append({
                "period": group.iloc[target_idx]["period"], "model": model_name,
                "actual_rate": actual, "predicted_rate": predicted,
                "absolute_error": abs(actual - predicted),
                "squared_error": (actual - predicted) ** 2,
                "direction_correct": bool(np.sign(predicted - train[-1]) == np.sign(actual - train[-1])),
            })

    detail = pd.DataFrame(records)
    summary = (detail.groupby("model").agg(
        evaluated_periods=("actual_rate", "count"),
        MAE=("absolute_error", "mean"),
        RMSE=("squared_error", lambda x: float(np.sqrt(x.mean()))),
        directional_accuracy=("direction_correct", "mean"),
    ).reset_index())
    note = ("Rolling-origin one-step evaluation: each prediction uses only observations earlier than its target period. "
            "When Random Forest is included, all methods are scored on the same target periods. "
            "Errors are in demand-rate percentage points; lower MAE/RMSE is better.")
    if rf_error:
        note += " " + rf_error
    elif not rf_available:
        note += " Random Forest evaluation requires at least 15 usable periods and an installed scikit-learn package."
    return summary, note


def forecast_skill(series: pd.DataFrame, skill: str, horizon: int = 3, min_periods: int = 8, frequency: str = "M") -> tuple[pd.DataFrame, str]:
    """Forecast 1–3 periods using baselines and, with enough history, ML candidates.

    Random Forest is trained on lag features and evaluated on a chronological holdout.
    It is displayed only when enough observations exist; its forecast is not presumed
    superior to the baselines.
    """
    if horizon < 1 or horizon > 3:
        return pd.DataFrame(), "Forecast horizon must be between one and three periods."
    group = series[series["skill_name"].eq(skill)].copy()
    if group.empty:
        return pd.DataFrame(), "No observations exist for this skill."
    group["period"] = pd.to_datetime(group["period"], errors="coerce")
    group["demand_rate"] = pd.to_numeric(group["demand_rate"], errors="coerce")
    group = group.dropna(subset=["period", "demand_rate"]).drop_duplicates("period").sort_values("period")
    freq = _frequency(frequency)
    if group["period"].nunique() < min_periods:
        return pd.DataFrame(), f"At least {min_periods} periods are required; this skill has {group['period'].nunique()}."
    values = group.set_index("period")["demand_rate"].astype(float)
    offset = pd.offsets.MonthBegin(1) if freq == "M" else pd.offsets.QuarterBegin(1)
    future = pd.date_range(values.index.max() + offset, periods=horizon, freq="MS" if freq == "M" else "QS")
    last = float(values.iloc[-1])
    moving = float(values.iloc[-min(3, len(values)):].mean())
    output = pd.DataFrame({"period": future, "last_value_baseline": [last]*horizon, "moving_average_3": [moving]*horizon})
    notes = ["Forecasts are exploratory; use the rolling-origin evaluation table to judge baseline performance."]
    vals = values.to_numpy()
    # Fit a transparent linear-trend candidate alongside the last-value and
    # recent-average baselines. Its historical quality is judged separately below.
    output["linear_trend_candidate"] = [max(0.0, float(np.polyval(np.polyfit(np.arange(len(vals)), vals, 1), len(vals)+step))) for step in range(horizon)]
    if len(vals) >= 24:
        try:
            from sklearn.ensemble import RandomForestRegressor
            # Fit the final forecast model on all available lagged observations. Its
            # historical performance is reported separately by rolling-origin evaluation.
            X, y = [], []
            for i in range(3, len(vals)):
                X.append([vals[i-1], vals[i-2], vals[i-3], float(np.mean(vals[i-3:i]))])
                y.append(vals[i])
            X, y = np.asarray(X), np.asarray(y)
            model = RandomForestRegressor(n_estimators=150, random_state=42, min_samples_leaf=2, n_jobs=1)
            model.fit(X, y)
            state = list(vals[-3:])
            forecasts = []
            for _ in range(horizon):
                feat = [state[-1], state[-2], state[-3], float(np.mean(state[-3:]))]
                val = max(0.0, float(model.predict([feat])[0]))
                forecasts.append(val)
                state.append(val)
            output["random_forest_candidate"] = forecasts
            notes.append("Random Forest forecast fitted on all available lagged observations; consult rolling-origin evaluation below for historical performance against baselines.")
        except ImportError:
            notes.append("Install scikit-learn to enable the Random Forest candidate.")
    output["period"] = pd.to_datetime(output["period"])
    # Demand rate cannot exceed 100%; clamp forecasts to valid percentage bounds.
    for col in output.columns:
        if col != "period":
            output[col] = output[col].clip(0, 100)
    return output, " ".join(notes)


def representation_comparison(series_a: pd.DataFrame, series_b: pd.DataFrame, label_a: str, label_b: str) -> tuple[pd.DataFrame, dict]:
    """Compare mean demand ranks, top-k overlap, and available trend agreement."""
    empty_stats = {"spearman": np.nan, "top_k_overlap": np.nan, "classification_agreement": np.nan}
    if series_a.empty or series_b.empty:
        return pd.DataFrame(), empty_stats
    # Compare per-skill mean demand rates so rankings are on a common scale.
    # This is downstream sensitivity analysis, not ground-truth extraction scoring.
    a = series_a.groupby("skill_name")["demand_rate"].mean().rename(label_a)
    b = series_b.groupby("skill_name")["demand_rate"].mean().rename(label_b)
    joined = pd.concat([a, b], axis=1).fillna(0)
    corr = joined[label_a].corr(joined[label_b], method="spearman") if len(joined) > 1 else np.nan
    k = min(10, len(joined))
    top_a, top_b = set(joined[label_a].nlargest(k).index), set(joined[label_b].nlargest(k).index)
    stats = {"spearman": float(corr) if pd.notna(corr) else np.nan,
             "top_k_overlap": len(top_a & top_b) / max(1, len(top_a | top_b)),
             "classification_agreement": np.nan}
    return joined.reset_index(), stats
