"""Build temporal analysis CSVs from existing scraper batch CSVs.
Run: python -m src.analysis.build_temporal_dataset --input data/raw/batches --output data/analysis/temporal --frequency M
This normalizes dates already collected; it cannot recover expired advertisements.
"""
import argparse, json
import re
from pathlib import Path
import pandas as pd

DATE_COLUMNS = ["posted_date_raw", "posted_date", "posting_date", "date_posted", "published_at"]
SKILL_COLUMNS = ["canonical_skills", "semantic_skills", "skills_semantic", "skills_raw", "lexical_skills", "skills_lexical"]

def first_existing(df, names):
    return next((name for name in names if name in df.columns), None)

def read_inputs(path):
    files = [path] if path.is_file() else sorted(path.rglob("*.csv"))
    frames = []
    for file in files:
        try:
            frame = pd.read_csv(file, dtype=str, keep_default_na=False, on_bad_lines="skip")
            if not frame.empty:
                frame["_input_file"] = str(file)
                frames.append(frame)
        except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
            print(f"Skipping {file}: {exc}")
    if not frames:
        raise SystemExit(f"No readable CSV files found under {path}")
    return pd.concat(frames, ignore_index=True, sort=False).fillna("")

def split_skills(value):
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return list(dict.fromkeys(str(x).strip() for x in parsed if str(x).strip()))
    except (ValueError, TypeError):
        pass
    for sep in [";", "|", ",", "\n"]:
        if sep in text:
            return list(dict.fromkeys(x.strip().strip("[]\"'") for x in text.split(sep) if x.strip().strip("[]\"'")))
    return [text.strip("[]\"'")]

def parse_posting_date(raw_value, collected_value):
    """Parse absolute dates and common portal labels such as '2 months ago'."""
    raw = str(raw_value).strip()
    parsed = pd.to_datetime(raw, errors="coerce", dayfirst=True, utc=True)
    if not pd.isna(parsed):
        return parsed.tz_convert(None), "absolute"
    collected = pd.to_datetime(collected_value, errors="coerce", utc=True)
    match = re.fullmatch(r"\s*(\d+)\s*(m|mo|mos|minute|minutes|h|hr|hrs|hour|hours|d|day|days|w|wk|wks|week|weeks|mon|month|months|y|yr|yrs|year|years)\s+ago\s*", raw, re.I)
    if pd.isna(collected) or not match:
        return pd.NaT, "unparsed"
    count = int(match.group(1))
    unit = match.group(2).lower()
    if unit in {"m", "mo", "mos", "mon", "month", "months"}:
        value = collected - pd.DateOffset(months=count)
    elif unit in {"y", "yr", "yrs", "year", "years"}:
        value = collected - pd.DateOffset(years=count)
    elif unit in {"w", "wk", "wks", "week", "weeks"}:
        value = collected - pd.Timedelta(weeks=count)
    elif unit in {"d", "day", "days"}:
        value = collected - pd.Timedelta(days=count)
    elif unit in {"h", "hr", "hrs", "hour", "hours"}:
        value = collected - pd.Timedelta(hours=count)
    else:
        value = collected - pd.Timedelta(minutes=count)
    return value.tz_convert(None), "relative_to_collected_at"

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", default="data/raw/batches", help="CSV file or directory")
    p.add_argument("--output", default="data/analysis/temporal")
    p.add_argument("--frequency", choices=["M", "Q"], default="M", help="M=monthly, Q=quarterly")
    args = p.parse_args()
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    df = read_inputs(Path(args.input))
    date_col = first_existing(df, DATE_COLUMNS)
    skill_col = first_existing(df, SKILL_COLUMNS)
    if not date_col:
        raise SystemExit(f"Missing posting date column. Expected one of: {DATE_COLUMNS}")
    if not skill_col:
        raise SystemExit(f"Missing skills column. Expected one of: {SKILL_COLUMNS}")

    collected_col = first_existing(df, ["scraped_at", "collected_at"])
    df["collected_at"] = df[collected_col] if collected_col else ""
    df["posting_date_raw"] = df[date_col].astype(str).str.strip()
    parsed_dates = [parse_posting_date(raw, collected) for raw, collected in zip(df["posting_date_raw"], df["collected_at"])]
    df["posting_date"] = [item[0] for item in parsed_dates]
    df["date_parse_method"] = [item[1] for item in parsed_dates]
    df["date_missing_or_unparsed"] = df["posting_date"].isna()
    df["period"] = df["posting_date"].dt.to_period(args.frequency).astype("string")
    df["skills_for_temporal_analysis"] = df[skill_col].astype(str)
    if "source_platform" not in df: df["source_platform"] = "unknown"
    if "job_id" not in df: df["job_id"] = df.index.astype(str)
    if "classification_status" in df:
        df["eligible_flag"] = df["classification_status"].str.lower().eq("it")
    else:
        df["eligible_flag"] = True
    if "duplicate_flag" not in df: df["duplicate_flag"] = False
    df.to_csv(out / "temporal_jobs_with_quality_flags.csv", index=False)

    eligible = df[df["posting_date"].notna()].copy()
    eligible = eligible[eligible["eligible_flag"].astype(str).str.lower().isin(["true", "1", "yes", "it"])]
    eligible = eligible[~eligible["duplicate_flag"].astype(str).str.lower().isin(["true", "1", "yes"])]
    jobs_by_period = eligible.groupby("period")["job_id"].nunique().rename("eligible_jobs")
    rows = []
    for _, row in eligible.iterrows():
        for skill in split_skills(row["skills_for_temporal_analysis"]):
            rows.append({"period": str(row["period"]), "skill": skill, "job_id": row["job_id"], "source_platform": row.get("source_platform", "unknown")})
    if rows:
        mentions = pd.DataFrame(rows).drop_duplicates(["period", "skill", "job_id"])
        demand = mentions.groupby(["period", "skill"]).agg(job_count=("job_id", "nunique"), sources=("source_platform", "nunique")).reset_index()
        demand = demand.join(jobs_by_period, on="period")
        demand["demand_rate_pct"] = (100 * demand["job_count"] / demand["eligible_jobs"].replace(0, pd.NA)).round(3)
    else:
        demand = pd.DataFrame(columns=["period", "skill", "job_count", "sources", "eligible_jobs", "demand_rate_pct"])
    demand.to_csv(out / "temporal_skill_demand.csv", index=False)
    quality = pd.DataFrame([{"input_rows": len(df), "dated_rows": int(df["posting_date"].notna().sum()), "missing_or_unparsed_dates": int(df["posting_date"].isna().sum()), "date_completeness_pct": round(100 * float(df["posting_date"].notna().mean()), 2), "eligible_dated_rows": len(eligible), "date_column_used": date_col, "skill_column_used": skill_col, "aggregation_frequency": "monthly" if args.frequency == "M" else "quarterly", "input_files": int(df["_input_file"].nunique())}])
    quality.to_csv(out / "temporal_data_quality_report.csv", index=False)
    print(quality.to_string(index=False))
    print(f"Outputs written to {out.resolve()}")

if __name__ == "__main__": main()
