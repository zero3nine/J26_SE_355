"""
Scraping Accuracy & Validation Dashboard Data Engine.
Academic Research Component for Regional Comparative IT Labor-Market Analysis.

Provides:
- Discovering, caching, and loading multi-run evaluation outputs (metrics, errors, summary, reports).
- Filter-aware metric recalculation preserving strict denominators and small-sample caveats.
- Multi-dimensional stratification (country, platform, extraction method, field).
- Persistent reviewer annotations & correction history without mutating reference benchmark data.
- Safe programmatic re-evaluation triggers.
- Sanitized export generators.
"""

from __future__ import annotations

import csv
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# Directory resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVALUATION_DIR = PROJECT_ROOT / "data" / "evaluation"
RESULTS_DIR = EVALUATION_DIR / "results"
BENCHMARK_PATH = EVALUATION_DIR / "benchmark_dataset.csv"
PREDICTIONS_PATH = PROJECT_ROOT / "data" / "raw" / "all_pilot_crawled_predictions.csv"
ANNOTATIONS_STORE = EVALUATION_DIR / "review_annotations.json"
HISTORY_STORE = EVALUATION_DIR / "correction_history.jsonl"


def get_results_dir() -> Path:
    """Returns the evaluation results directory."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR


def discover_evaluation_runs(results_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Discovers all evaluation runs available from the master SQLite database and results directory.
    
    Returns runs sorted by timestamp descending, with 'latest' run at the top.
    """
    runs = []
    seen_tags = set()

    # 1. Discover from master SQLite database when using default results location
    if results_dir is None:
        try:
            from src.database.repository import get_evaluation_runs_from_db
            db_runs = get_evaluation_runs_from_db()
            for dr in db_runs:
                seen_tags.add(dr["run_id"])
                runs.append(dr)
        except Exception:
            pass

    target_dir = results_dir or get_results_dir()
    if target_dir.exists():
        metric_files = list(target_dir.glob("evaluation_metrics_*.json"))
        for mf in metric_files:
            filename = mf.name
            is_latest = "latest" in filename
            match = re.search(r"evaluation_metrics_(\d{8}_\d{6})\.json", filename)
            run_ts = match.group(1) if match else ("latest" if is_latest else "unknown")

            if run_ts in seen_tags and not is_latest:
                continue

            try:
                mtime = mf.stat().st_mtime
                with open(mf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                meta = data.get("metadata", {})
                iso_ts = meta.get("timestamp", datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat())
                total_bm = meta.get("total_benchmark_records", 0)
                matched = meta.get("matched_records_count", 0)
                exact_match_pct = meta.get("exact_match_rate", 0.0) * 100.0
                coverage_pct = meta.get("macro_coverage", 0.0) * 100.0
                correctness_pct = meta.get("macro_correctness", 0.0) * 100.0

                is_synthetic = (
                    meta.get("is_synthetic", False) or
                    "synthetic" in filename.lower() or
                    bool(re.search(r"(?:^|[_\-])test(?:[_\-]|$)", filename.lower()))
                )

                label = f"Latest Run ({iso_ts[:19]})" if is_latest else f"Run {run_ts} ({iso_ts[:19]})"
                if is_synthetic:
                    label += " [Synthetic Test]"
                else:
                    label += " [Empirical Benchmark]"

                runs.append({
                    "run_id": run_ts,
                    "is_latest": is_latest,
                    "label": label,
                    "timestamp_iso": iso_ts,
                    "mtime": mtime,
                    "metrics_file": mf,
                    "total_benchmark": total_bm,
                    "matched_records": matched,
                    "exact_match_rate": exact_match_pct,
                    "macro_coverage": coverage_pct,
                    "macro_correctness": correctness_pct,
                    "is_synthetic": is_synthetic,
                    "from_database": False,
                })
            except Exception:
                continue

    # Sort: latest first, then chronological descending
    def sort_key(r):
        return (1 if r["is_latest"] else 0, r.get("mtime", 0.0))

    runs.sort(key=sort_key, reverse=True)
    return runs


def load_evaluation_run_data(run_id_or_file: Any, results_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Loads all associated artifacts for an evaluation run from SQLite database or disk files.
    
    Artifacts loaded:
    - metrics: dict from evaluation_metrics_*.json or SQLite evaluation_runs table
    - errors_df: pd.DataFrame from evaluation_errors_*.csv or SQLite evaluation_errors table
    - summary_df: pd.DataFrame from evaluation_summary_*.csv
    - report_md: str from evaluation_report_*.md or SQLite evaluation_runs table
    - reproducibility: dict from evaluation_reproducibility_*.json
    """
    # 1. Try loading from SQLite database first when results_dir is None
    if results_dir is None:
        tag = str(run_id_or_file.stem.replace("evaluation_metrics_", "") if isinstance(run_id_or_file, Path) else run_id_or_file)
        try:
            from src.database.repository import load_evaluation_run_data_from_db
            db_data = load_evaluation_run_data_from_db(tag)
            if db_data is not None and not db_data["errors_df"].empty:
                return db_data
        except Exception:
            pass

    target_dir = results_dir or get_results_dir()

    if isinstance(run_id_or_file, Path):
        metrics_file = run_id_or_file
        run_tag = metrics_file.stem.replace("evaluation_metrics_", "")
    else:
        tag = str(run_id_or_file)
        if tag == "latest":
            metrics_file = target_dir / "evaluation_metrics_latest.json"
            run_tag = "latest"
        else:
            metrics_file = target_dir / f"evaluation_metrics_{tag}.json"
            run_tag = tag

    if not metrics_file.exists():
        # Fallback to latest
        latest_file = target_dir / "evaluation_metrics_latest.json"
        if latest_file.exists():
            metrics_file = latest_file
            run_tag = "latest"
        else:
            return None

    try:
        with open(metrics_file, "r", encoding="utf-8") as f:
            metrics = json.load(f)
    except Exception:
        return None


    # Load paired files
    errors_csv = target_dir / f"evaluation_errors_{run_tag}.csv"
    if not errors_csv.exists():
        errors_csv = target_dir / "evaluation_errors_latest.csv"

    errors_df = pd.DataFrame()
    if errors_csv.exists():
        try:
            errors_df = pd.read_csv(errors_csv, dtype=str).fillna("")
        except Exception:
            errors_df = pd.DataFrame()

    summary_csv = target_dir / f"evaluation_summary_{run_tag}.csv"
    if not summary_csv.exists():
        summary_csv = target_dir / "evaluation_summary_latest.csv"

    summary_df = pd.DataFrame()
    if summary_csv.exists():
        try:
            summary_df = pd.read_csv(summary_csv)
        except Exception:
            summary_df = pd.DataFrame()

    report_md_file = target_dir / f"evaluation_report_{run_tag}.md"
    if not report_md_file.exists():
        report_md_file = target_dir / "evaluation_report_latest.md"

    report_md = ""
    if report_md_file.exists():
        try:
            with open(report_md_file, "r", encoding="utf-8") as f:
                report_md = f.read()
        except Exception:
            report_md = ""

    repro_file = target_dir / f"evaluation_reproducibility_{run_tag}.json"
    if not repro_file.exists():
        repro_file = target_dir / "evaluation_reproducibility_latest.json"

    repro = {}
    if repro_file.exists():
        try:
            with open(repro_file, "r", encoding="utf-8") as f:
                repro = json.load(f)
        except Exception:
            repro = {}

    meta = metrics.get("metadata", {})
    is_synthetic = (
        meta.get("is_synthetic", False) or
        "synthetic" in metrics_file.name.lower() or
        bool(re.search(r"(?:^|[_\-])test(?:[_\-]|$)", metrics_file.name.lower()))
    )

    return {
        "run_tag": run_tag,
        "is_synthetic": is_synthetic,
        "metrics": metrics,
        "errors_df": errors_df,
        "summary_df": summary_df,
        "report_md": report_md,
        "reproducibility": repro,
        "metrics_file": str(metrics_file),
    }


def filter_evaluation_errors(
    errors_df: pd.DataFrame,
    country: Optional[str] = None,
    platform: Optional[str] = None,
    method: Optional[str] = None,
    field_name: Optional[str] = None,
    status: Optional[str] = None,
    error_cat: Optional[str] = None,
    search_query: Optional[str] = None,
) -> pd.DataFrame:
    """Filters field-level evaluation errors according to user-selected controls."""
    if errors_df.empty:
        return errors_df

    df = errors_df.copy()

    if country and country != "All":
        df = df[df["country"] == country]

    if platform and platform != "All":
        df = df[df["source_platform"] == platform]

    if method and method != "All":
        df = df[df["extraction_method"] == method]

    if field_name and field_name != "All":
        df = df[df["field_name"] == field_name]

    if status and status != "All":
        if "error_status" in df.columns:
            df = df[df["error_status"] == status]
        elif "error_type" in df.columns:
            df = df[df["error_type"] == status]

    if error_cat and error_cat != "All":
        if "error_category" in df.columns:
            df = df[df["error_category"] == error_cat]

    if search_query and search_query.strip():
        q = search_query.strip().lower()
        search_cols = [c for c in ["benchmark_id", "source_url", "expected_value", "predicted_value", "discrepancy_details"] if c in df.columns]
        mask = False
        for c in search_cols:
            mask = mask | df[c].str.lower().str.contains(q, na=False)
        df = df[mask]

    return df


def compute_stratified_view(
    summary_df: pd.DataFrame,
    dimension: str,
    filter_value: Optional[str] = None,
) -> pd.DataFrame:
    """Extracts stratified breakdown (country, platform, or method) with safe denominator reporting."""
    if summary_df.empty or "dimension" not in summary_df.columns:
        return pd.DataFrame()

    sub = summary_df[summary_df["dimension"] == dimension].copy()
    if filter_value and filter_value != "All" and "subgroup_name" in sub.columns:
        sub = sub[sub["subgroup_name"] == filter_value]

    return sub


def load_review_annotations(storage_path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Loads durable reviewer annotations from JSON store.
    
    Keyed by composite ID: '{benchmark_id}::{field_name}'
    """
    store_file = storage_path or ANNOTATIONS_STORE
    if not store_file.exists():
        return {}
    try:
        with open(store_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_review_annotation(
    benchmark_id: str,
    field_name: str,
    status: str,
    reviewer_id: str,
    reviewer_notes: str,
    corrected_value: str = "",
    original_predicted: str = "",
    original_expected: str = "",
    source_url: str = "",
    country: str = "",
    source_platform: str = "",
    storage_path: Optional[Path] = None,
    history_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Persists a reviewer decision and appends an immutable entry to the correction history.
    
    Guarantees:
    - Validates status in ['verified', 'incorrect', 'unavailable', 'ambiguous'].
    - Enforces reviewer_id and reviewer_notes presence.
    - Never modifies benchmark_dataset.csv or original scraped batch CSVs.
    - Preserves full audit trail in correction_history.jsonl.
    """
    allowed_statuses = {"verified", "incorrect", "unavailable", "ambiguous"}
    if status not in allowed_statuses:
        return False, f"Invalid review status '{status}'. Must be one of {sorted(allowed_statuses)}"

    if not reviewer_id.strip():
        return False, "Reviewer identifier is required for research provenance."

    if not reviewer_notes.strip():
        return False, "Reviewer justification notes are mandatory."

    now_iso = datetime.now(timezone.utc).isoformat()
    composite_key = f"{benchmark_id}::{field_name}"

    record = {
        "annotation_id": f"REV_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{benchmark_id}_{field_name}",
        "benchmark_id": benchmark_id,
        "field_name": field_name,
        "status": status,
        "corrected_value": corrected_value.strip(),
        "original_predicted": original_predicted,
        "original_expected": original_expected,
        "reviewer_id": reviewer_id.strip(),
        "reviewer_notes": reviewer_notes.strip(),
        "timestamp": now_iso,
        "source_url": source_url,
        "country": country,
        "source_platform": source_platform,
    }

    # 1. Update persistent JSON store
    store_file = storage_path or ANNOTATIONS_STORE
    store_file.parent.mkdir(parents=True, exist_ok=True)
    all_annotations = load_review_annotations(store_file)
    all_annotations[composite_key] = record

    try:
        with open(store_file, "w", encoding="utf-8") as f:
            json.dump(all_annotations, f, indent=2)
    except Exception as e:
        return False, f"Failed to persist review annotation: {e}"

    # 2. Append to audit log
    hist_file = history_path or HISTORY_STORE
    try:
        with open(hist_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        return False, f"Failed to write correction history audit log: {e}"

    return True, f"Review decision for {benchmark_id} [{field_name}] persisted successfully."


def get_correction_history(history_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Loads all historical review decisions from correction_history.jsonl."""
    hist_file = history_path or HISTORY_STORE
    if not hist_file.exists():
        return []
    history = []
    try:
        with open(hist_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    history.append(json.loads(line))
    except Exception:
        pass
    # Reverse to show newest first
    history.reverse()
    return history


def rerun_evaluation_pipeline(
    benchmark_path: Optional[Path] = None,
    predictions_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Triggers the evaluation engine programmatically and writes timestamped outputs.
    
    Returns (success, message, new_run_data).
    """
    out_dir = output_dir or RESULTS_DIR

    if predictions_path is None:
        cmd = [
            sys.executable,
            "-m",
            "src.evaluation.evaluate_scraping",
            "--use-database",
            "--output-dir",
            str(out_dir),
        ]
    else:
        bm_file = benchmark_path or BENCHMARK_PATH
        pred_file = predictions_path
        if not bm_file.exists():
            return False, f"Benchmark dataset not found at {bm_file}", None
        if not pred_file.exists():
            return False, f"Predictions dataset not found at {pred_file}", None
        cmd = [
            sys.executable,
            "-m",
            "src.evaluation.evaluate_scraping",
            "--benchmark",
            str(bm_file),
            "--predictions",
            str(pred_file),
            "--output-dir",
            str(out_dir),
        ]

    try:
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False)
        if res.returncode == 0:
            new_data = load_evaluation_run_data("latest", results_dir=out_dir)
            return True, "Evaluation completed successfully! All benchmark metrics recompiled.", new_data
        else:
            err = res.stderr or res.stdout
            return False, f"Evaluation execution failed with code {res.returncode}: {err}", None
    except Exception as ex:
        return False, f"Subprocess invocation error: {ex}", None


def build_review_queue(
    errors_df: pd.DataFrame,
    annotations: Optional[Dict[str, Dict[str, Any]]] = None,
) -> pd.DataFrame:
    """Builds the pending review queue by merging errors with existing annotations."""
    if errors_df.empty:
        return pd.DataFrame()

    ann_dict = annotations if annotations is not None else load_review_annotations()
    queue_rows = []

    for idx, row in errors_df.iterrows():
        b_id = str(row.get("benchmark_id", ""))
        f_name = str(row.get("field_name", ""))
        comp_key = f"{b_id}::{f_name}"
        ann = ann_dict.get(comp_key)

        queue_rows.append({
            "benchmark_id": b_id,
            "field_name": f_name,
            "country": str(row.get("country", "")),
            "source_platform": str(row.get("source_platform", "")),
            "extraction_method": str(row.get("extraction_method", "")),
            "expected_raw": str(row.get("expected_raw", row.get("expected_value", ""))),
            "expected_normalized": str(row.get("expected_normalized", "")),
            "predicted_raw": str(row.get("predicted_raw", row.get("predicted_value", ""))),
            "predicted_normalized": str(row.get("predicted_normalized", "")),
            "error_category": str(row.get("error_category", "")),
            "error_type": str(row.get("error_type", "")),
            "discrepancy_details": str(row.get("discrepancy_details", "")),
            "source_url": str(row.get("source_url", "")),
            "review_status": ann["status"] if ann else "pending_review",
            "reviewer_id": ann["reviewer_id"] if ann else "",
            "reviewer_notes": ann["reviewer_notes"] if ann else "",
            "corrected_value": ann["corrected_value"] if ann else "",
            "review_timestamp": ann["timestamp"] if ann else "",
        })

    return pd.DataFrame(queue_rows)


def get_benchmark_accuracy_summary_for_quality_tab() -> Optional[Dict[str, Any]]:
    """Retrieves high-level accuracy summary metrics for cross-referencing in Tab 6 (Quality Report)."""
    data = load_evaluation_run_data("latest")
    if not data:
        return None
    metrics = data.get("metrics", {})
    meta = metrics.get("metadata", {})
    f_metrics = metrics.get("field_metrics", {})

    return {
        "timestamp": meta.get("timestamp", ""),
        "total_benchmark": meta.get("total_benchmark_records", 0),
        "matched_records": meta.get("matched_records_count", 0),
        "macro_coverage": meta.get("macro_coverage", 0.0) * 100.0,
        "macro_correctness": meta.get("macro_correctness", 0.0) * 100.0,
        "exact_match_rate": meta.get("exact_match_rate", 0.0) * 100.0,
        "title_agreement": f_metrics.get("job_title", {}).get("normalized_agreement_rate", 0.0) * 100.0,
        "employer_agreement": f_metrics.get("employer", {}).get("normalized_agreement_rate", 0.0) * 100.0,
        "salary_disclosed_agreement": f_metrics.get("salary_disclosed", {}).get("normalized_agreement_rate", 0.0) * 100.0,
        "is_synthetic": data.get("is_synthetic", False),
    }

