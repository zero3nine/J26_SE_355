"""
Command-Line Interface for Information Extraction Benchmark Evaluation Engine.
Academic Research Component for Regional Comparative IT Labor-Market Analysis.

Produces:
1. Machine-readable metrics file (.json)
2. Field-level error CSV (.csv)
3. Stratified Country / Source / Method summary CSV (.csv)
4. Human-readable Markdown evaluation report (.md)
5. Reproducibility record with input hashes and parameters (.json)

Usage:
    python -m src.evaluation.evaluate_scraping \
        --benchmark data/evaluation/benchmark_dataset.csv \
        --predictions data/raw/batches/jobs_raw_batch_20261019_211946.csv \
        --output-dir data/evaluation/results/
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.evaluation.schema import load_benchmark_dataset, BenchmarkRecord
from src.evaluation.comparator import compare_records
from src.evaluation.metrics import compute_evaluation_metrics
from src.evaluation.reporter import (
    generate_markdown_report,
    export_metrics_json,
    export_field_errors_csv,
    export_stratified_summary_csv,
    export_reproducibility_record,
)


def load_predictions_file(file_path: Path) -> List[Dict[str, Any]]:
    """Loads prediction records from CSV or JSON format.
    
    Supports:
    - Raw extraction batch CSVs (RAW_SCHEMA_COLUMNS)
    - Cleaned operational dataset CSVs (TEAM_SCHEMA_COLUMNS)
    - Raw JSON batch outputs
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Predictions file not found: {file_path}")

    ext = file_path.suffix.lower()
    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                raise ValueError("JSON predictions file must be an object or list of objects.")
    elif ext == ".csv":
        df = pd.read_csv(file_path, dtype=str)
        df = df.fillna("")
        return df.to_dict(orient="records")
    else:
        raise ValueError(f"Unsupported prediction file format '{ext}'. Expected .csv or .json.")


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate information extraction predictions against an independently verified benchmark dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--benchmark",
        "-b",
        default="data/evaluation/benchmark_dataset.csv",
        help="Path to the benchmark dataset (.csv or .json)."
    )
    parser.add_argument(
        "--predictions",
        "-p",
        required=True,
        help="Path to predictions file (raw batch CSV or clean operational dataset)."
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="data/evaluation/results",
        help="Output directory for generated reports and data artifacts."
    )
    parser.add_argument(
        "--match-key",
        "-m",
        choices=["auto", "source_url", "job_id"],
        default="auto",
        help="Matching strategy for aligning predictions with benchmark ground truth."
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress console progress output."
    )

    args = parser.parse_args(argv)

    benchmark_path = Path(args.benchmark).resolve()
    predictions_path = Path(args.predictions).resolve()
    output_dir = Path(args.output_dir).resolve()

    # Integrity Rule 1: Prevent accidentally evaluating benchmark against itself or overwriting
    if benchmark_path == predictions_path:
        print(
            "ERROR: Prevention Rule Violation: --predictions cannot be the exact same file as --benchmark. "
            "Reference labels must be kept strictly separate from prediction inputs.",
            file=sys.stderr
        )
        return 1

    # Check existence
    if not benchmark_path.exists():
        print(f"ERROR: Benchmark dataset file not found: {benchmark_path}", file=sys.stderr)
        return 1
    if not predictions_path.exists():
        print(f"ERROR: Predictions file not found: {predictions_path}", file=sys.stderr)
        return 1

    # Load and validate benchmark records
    try:
        if not args.quiet:
            print(f"Loading benchmark dataset from: {benchmark_path}")
        benchmarks = load_benchmark_dataset(benchmark_path)
        if not benchmarks:
            print("ERROR: Benchmark dataset is empty.", file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"  ✓ Loaded and validated {len(benchmarks)} benchmark records.")
    except Exception as e:
        print(f"ERROR: Failed to load benchmark dataset: {e}", file=sys.stderr)
        return 1

    # Load predictions
    try:
        if not args.quiet:
            print(f"Loading predictions from: {predictions_path}")
        predictions = load_predictions_file(predictions_path)
        if not predictions:
            print("ERROR: Predictions dataset is empty.", file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"  ✓ Loaded {len(predictions)} prediction records.")
    except Exception as e:
        print(f"ERROR: Failed to load predictions: {e}", file=sys.stderr)
        return 1

    # Execute field-by-field comparison
    try:
        results, unmatched_bm, extra_preds = compare_records(
            benchmarks, predictions, match_key=args.match_key
        )
    except Exception as e:
        print(f"ERROR: Error during record comparison: {e}", file=sys.stderr)
        return 1

    # Check if any matches were found
    matched_count = len(benchmarks) - len(unmatched_bm)
    if matched_count == 0:
        print(
            f"WARNING: Zero benchmark records matched any predictions in '{predictions_path}'. "
            f"Total benchmark records: {len(benchmarks)}, Total predictions: {len(predictions)}. "
            f"Check URL/ID alignment or specify --match-key.",
            file=sys.stderr
        )
        return 2

    # Compute aggregate metrics
    eval_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    metrics = compute_evaluation_metrics(
        results=results,
        total_benchmarks=len(benchmarks),
        total_predictions=len(predictions),
        unmatched_benchmarks=len(unmatched_bm),
        extra_predictions=len(extra_preds),
        timestamp=eval_time
    )

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    file_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Paths for all 5 outputs
    # 1. Markdown report
    md_path = output_dir / f"evaluation_report_{file_ts}.md"
    latest_md = output_dir / "evaluation_report_latest.md"

    # 2. JSON metrics
    json_path = output_dir / f"evaluation_metrics_{file_ts}.json"
    latest_json = output_dir / "evaluation_metrics_latest.json"

    # 3. Field-level error CSV
    err_csv_path = output_dir / f"evaluation_errors_{file_ts}.csv"
    latest_err_csv = output_dir / "evaluation_errors_latest.csv"

    # 4. Stratified summary CSV
    sum_csv_path = output_dir / f"evaluation_summary_{file_ts}.csv"
    latest_sum_csv = output_dir / "evaluation_summary_latest.csv"

    # 5. Reproducibility record JSON
    rep_json_path = output_dir / f"evaluation_reproducibility_{file_ts}.json"
    latest_rep_json = output_dir / "evaluation_reproducibility_latest.json"

    # Generate Markdown report
    report_content = generate_markdown_report(
        metrics=metrics,
        results=results,
        benchmark_path=str(benchmark_path),
        predictions_path=str(predictions_path),
        match_key=args.match_key
    )
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    with open(latest_md, "w", encoding="utf-8") as f:
        f.write(report_content)

    # Generate JSON metrics
    export_metrics_json(metrics, json_path)
    export_metrics_json(metrics, latest_json)

    # Generate Field-level Error CSV
    export_field_errors_csv(results, err_csv_path)
    export_field_errors_csv(results, latest_err_csv)

    # Generate Stratified Summary CSV
    export_stratified_summary_csv(metrics, sum_csv_path)
    export_stratified_summary_csv(metrics, latest_sum_csv)

    # Generate Reproducibility Record
    export_reproducibility_record(
        benchmark_path=benchmark_path,
        predictions_path=predictions_path,
        output_dir=output_dir,
        match_key=args.match_key,
        metrics=metrics,
        output_file=rep_json_path
    )
    export_reproducibility_record(
        benchmark_path=benchmark_path,
        predictions_path=predictions_path,
        output_dir=output_dir,
        match_key=args.match_key,
        metrics=metrics,
        output_file=latest_rep_json
    )

    if not args.quiet:
        print("\n=======================================================")
        print("          EXTRACTION BENCHMARK EVALUATION SUMMARY       ")
        print("=======================================================")
        print(f"Matched Benchmark Records:  {metrics.matched_records_count} / {metrics.total_benchmark_records}")
        print(f"Unmatched Benchmark Ads:    {metrics.unmatched_benchmark_count}")
        print(f"Extra Predictions:          {metrics.extra_predictions_count}")
        print(f"Exact Match Advertisements: {metrics.fully_correct_records} ({metrics.exact_match_rate * 100:.2f}%) "
              f"[95% CI: {metrics.exact_match_ci_lower*100:.1f}% - {metrics.exact_match_ci_upper*100:.1f}%]")
        print(f"Macro Extraction Coverage:  {metrics.macro_coverage * 100:.2f}% (Completeness)")
        print(f"Macro Extraction Correct:   {metrics.macro_correctness * 100:.2f}% (Precision)")
        print(f"Macro Recall (Uncond):      {metrics.macro_recall * 100:.2f}%")
        print(f"Macro F1-Score:             {metrics.macro_f1 * 100:.2f}%")
        print("-------------------------------------------------------")
        print(f"1. Markdown Report:     {md_path}")
        print(f"2. Machine Metrics:     {json_path}")
        print(f"3. Field Error CSV:     {err_csv_path}")
        print(f"4. Stratified Summary:  {sum_csv_path}")
        print(f"5. Reproducibility Rec: {rep_json_path}")
        print("=======================================================\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
