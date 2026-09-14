"""Temporal skill-demand analysis for the shared master SQLite database."""
from __future__ import annotations
import sqlite3
import numpy as np
import pandas as pd


def load_temporal_input(conn: sqlite3.Connection, method: str = "all") -> pd.DataFrame:
    """One row per job-skill mention. Method may be all, lexical, semantic, canonical."""
    query = """
        SELECT j.job_id, j.posting_date, j.country, j.source_platform, j.job_title,
               j.source_url, es.skill_name, es.method, er.run_type, er.run_id
        FROM jobs j
        LEFT JOIN extracted_skills es ON es.job_id = j.job_id
        LEFT JOIN extraction_runs er ON er.run_id = es.run_id
        WHERE j.posting_date IS NOT NULL AND TRIM(j.posting_date) <> ''
    """
    params = []
    if method != "all":
        query += " AND LOWER(es.method) = LOWER(?)"
        params.append(method)
    return pd.read_sql_query(query, conn, params=params)


def normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["posting_date"] = pd.to_datetime(out["posting_date"], errors="coerce", utc=True).dt.tz_convert(None)
    out["skill_name"] = out["skill_name"].astype(str).str.strip()
    out = out.dropna(subset=["posting_date"])
    out = out[out["skill_name"].ne("") & out["skill_name"].ne("nan")]
    out["period"] = out["posting_date"].dt.to_period("M").dt.to_timestamp()
    return out


def build_demand_series(df: pd.DataFrame, frequency: str = "M", min_jobs: int = 1,
                        country: str = "All", source: str = "All") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return skill-period metrics and eligible-job denominator by period."""
    data = df.copy()
    data["posting_date"] = pd.to_datetime(data["posting_date"], errors="coerce", utc=True).dt.tz_convert(None)
    data = data.dropna(subset=["posting_date", "job_id"])
    if country != "All" and "country" in data:
        data = data[data["country"].fillna("Unknown").eq(country)]
    if source != "All" and "source_platform" in data:
        data = data[data["source_platform"].fillna("Unknown").eq(source)]
    if data.empty:
        return pd.DataFrame(), pd.DataFrame()
    period_freq = "Q" if frequency == "Q" else "M"
    data["period"] = data["posting_date"].dt.to_period(period_freq).dt.to_timestamp()
    eligible = data[["job_id", "period"]].drop_duplicates().groupby("period").size().rename("eligible_jobs").reset_index()
    mentions = data[["job_id", "period", "skill_name"]].dropna(subset=["skill_name"]).copy()
    mentions["skill_name"] = mentions["skill_name"].astype(str).str.strip()
    mentions = mentions[mentions["skill_name"].ne("")]
    mentions = mentions.drop_duplicates(["job_id", "period", "skill_name"])
    counts = mentions.groupby(["period", "skill_name"]).size().rename("jobs_mentioning_skill").reset_index()
    series = counts.merge(eligible, on="period", how="left")
    series["demand_rate"] = 100 * series["jobs_mentioning_skill"] / series["eligible_jobs"].replace(0, np.nan)
    series = series[series["eligible_jobs"] >= int(min_jobs)]
    return series.sort_values(["period", "skill_name"]), eligible.sort_values("period")


def trend_table(series: pd.DataFrame, recent_periods: int = 3, baseline_periods: int = 3,
                min_observations: int = 6) -> pd.DataFrame:
    if series.empty:
        return pd.DataFrame()
    rows = []
    for skill, group in series.groupby("skill_name"):
        g = group.sort_values("period").copy()
        # Include zero-demand periods between first and last observed dates.
        idx = pd.date_range(g.period.min(), g.period.max(), freq="MS" if (g.period.dt.month.nunique() > 1 or len(g) > 1) else "QS")
        if len(idx) < len(g): idx = pd.DatetimeIndex(sorted(g.period.unique()))
        s = g.set_index("period")["demand_rate"].reindex(idx, fill_value=0).astype(float)
        n = len(s)
        recent_n = min(max(1, recent_periods), n)
        base_n = min(max(1, baseline_periods), max(1, n - recent_n))
        recent = float(s.iloc[-recent_n:].mean())
        baseline = float(s.iloc[-recent_n-base_n:-recent_n].mean()) if n > recent_n else float(s.iloc[:max(1, n//2)].mean())
        delta = recent - baseline
        relative = (delta / baseline * 100) if baseline > 0 else np.nan
        x = np.arange(n, dtype=float)
        slope = float(np.polyfit(x, s.to_numpy(), 1)[0]) if n >= 2 else 0.0
        direction = np.sign(np.diff(s.to_numpy()))
        persistence = float(np.mean(direction[-recent_n:] > 0)) if len(direction) else 0.0
        volatility = float(s.std(ddof=0)) if n else 0.0
        enough = n >= min_observations
        # Conservative, configurable starter rules; interpret as screening labels, not ground truth.
        if not enough:
            label = "Volatile / uncertain"
        elif baseline <= max(1.0, float(s.quantile(.35))) and delta > 0 and slope > 0 and persistence >= .5:
            label = "Emerging"
        elif slope > 0.05 and delta > 0:
            label = "Growing"
        elif slope < -0.05 and delta < 0:
            label = "Declining"
        elif volatility > max(1.0, float(s.mean()) * .75):
            label = "Volatile / uncertain"
        else:
            label = "Stable"
        rows.append({"skill_name": skill, "observations": n, "baseline_rate": baseline,
                     "recent_rate": recent, "absolute_change_pp": delta, "relative_growth_pct": relative,
                     "trend_slope_pp_per_period": slope, "positive_change_persistence": persistence,
                     "volatility_std_pp": volatility, "classification": label,
                     "latest_period": s.index.max()})
    return pd.DataFrame(rows).sort_values(["classification", "recent_rate"], ascending=[True, False])


def forecast_skill(series: pd.DataFrame, skill: str, horizon: int = 3, min_periods: int = 8) -> tuple[pd.DataFrame, str]:
    """Naive and moving-average forecasts; optional RF candidate if enough observations."""
    g = series[series.skill_name.eq(skill)].sort_values("period")
    if g.empty or g.period.nunique() < min_periods:
        return pd.DataFrame(), f"Need at least {min_periods} periods for a forecast; this series has {g.period.nunique()} (if any)."
    s = g.set_index("period")["demand_rate"].astype(float)
    freq = "Q" if (s.index.to_period("Q").nunique() == len(s) and len(s) > 1 and s.index.month.isin([1,4,7,10]).all()) else "M"
    future = pd.date_range(s.index.max() + pd.offsets.MonthBegin(3 if freq == "Q" else 1), periods=horizon, freq="QS" if freq == "Q" else "MS")
    naive = [float(s.iloc[-1])] * horizon
    moving = [float(s.iloc[-min(3, len(s)):].mean())] * horizon
    out = pd.DataFrame({"period": future, "naive_last_value": naive, "moving_average_3": moving})
    note = "Baseline forecasts only; no claim of predictive validity without walk-forward evaluation."
    # Train/test chronological holdout to decide whether RF is sufficiently supported.
    try:
        from sklearn.ensemble import RandomForestRegressor
        if len(s) >= 18:
            vals = s.to_numpy()
            X, y = [], []
            for i in range(3, len(vals)):
                X.append([vals[i-1], vals[i-2], vals[i-3], np.mean(vals[max(0, i-3):i])])
                y.append(vals[i])
            split = max(8, int(len(X) * .8))
            if len(X) - split >= 2:
                model = RandomForestRegressor(n_estimators=150, random_state=42, min_samples_leaf=2)
                model.fit(X[:split], y[:split])
                pred = model.predict(X[split:])
                actual = np.asarray(y[split:])
                mae = float(np.mean(np.abs(actual-pred)))
                rmse = float(np.sqrt(np.mean((actual-pred)**2)))
                state = list(vals[-3:])
                rf_preds = []
                for _ in range(horizon):
                    features = [state[-1], state[-2], state[-3], float(np.mean(state[-3:]))]
                    value = max(0.0, float(model.predict([features])[0]))
                    rf_preds.append(value); state.append(value)
                out["random_forest_candidate"] = rf_preds
                note = f"Random Forest is exploratory. Chronological holdout MAE={mae:.3f} pp; RMSE={rmse:.3f} pp. Compare against naive baseline before interpreting."
    except ImportError:
        note += " Install scikit-learn to enable the optional Random Forest candidate."
    return out, note


def representation_comparison(series_a: pd.DataFrame, series_b: pd.DataFrame, label_a: str, label_b: str) -> tuple[pd.DataFrame, dict]:
    if series_a.empty or series_b.empty:
        return pd.DataFrame(), {"spearman": np.nan, "top_k_overlap": np.nan, "classification_agreement": np.nan}
    a = series_a.groupby("skill_name").demand_rate.mean().rename(label_a)
    b = series_b.groupby("skill_name").demand_rate.mean().rename(label_b)
    joined = pd.concat([a, b], axis=1).fillna(0)
    joined["rank_a"] = joined[label_a].rank(ascending=False, method="average")
    joined["rank_b"] = joined[label_b].rank(ascending=False, method="average")
    corr = joined[[label_a, label_b]].corr(method="spearman").iloc[0,1] if len(joined) > 1 else np.nan
    k = min(10, len(joined))
    top_a = set(joined[label_a].nlargest(k).index); top_b = set(joined[label_b].nlargest(k).index)
    stats = {"spearman": float(corr) if pd.notna(corr) else np.nan,
             "top_k_overlap": len(top_a & top_b) / max(1, len(top_a | top_b)),
             "classification_agreement": np.nan}
    return joined.reset_index().rename(columns={"index":"skill_name"}), stats
