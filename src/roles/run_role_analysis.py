from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.roles.role_skill_analysis import classify_roles, build_role_skill_frequency_table
from src.roles.distinctiveness import (
    DEFAULT_N_RESAMPLES,
    DEFAULT_RANDOM_STATE,
    DEFAULT_SIGNIFICANCE_LEVEL,
    DEFAULT_TOP_K,
    run_distinctiveness_analysis,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "jobs_extracted.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "analysis"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Role-Based Skill Demand Segmentation and Distinctiveness Analysis "
            "— IT23136410"
        ),
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to jobs_extracted.csv (default: data/processed/jobs_extracted.csv)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output directory (default: data/analysis/)")
    parser.add_argument("--significance", type=float, default=DEFAULT_SIGNIFICANCE_LEVEL, help=f"Chi-square significance threshold (default: {DEFAULT_SIGNIFICANCE_LEVEL})")
    parser.add_argument("--resamples", type=int, default=DEFAULT_N_RESAMPLES, help=f"Number of bootstrap resamples for the stability check (default: {DEFAULT_N_RESAMPLES})")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help=f"Top-K distinctive skills per role used for divergence/stability (default: {DEFAULT_TOP_K})")
    parser.add_argument("--random-state", type=int, default=DEFAULT_RANDOM_STATE, help=f"Random seed for resampling, for reproducible results (default: {DEFAULT_RANDOM_STATE})")
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Input file not found: {args.input}\n"
            "Run collection, cleaning and skill extraction first "
            "(see the 'Extract Skills' tab / src.extraction.run_extraction)."
        )

    print(f"\n{'='*60}")
    print("Role-Based Skill Demand Segmentation and Distinctiveness Analysis")
    print("Research Component IT23136410")
    print(f"Input : {args.input}")
    print(f"Output: {args.output}")
    print(f"{'='*60}\n")

    df = pd.read_csv(args.input)
    required = {"job_id", "job_title_raw", "job_description", "lexical_skills", "semantic_skills"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {args.input}: {sorted(missing)}")

    print("Classifying job postings into role categories...")
    role_df = classify_roles(df)
    print(role_df["role_name"].value_counts().to_string())

    print("\nBuilding role x skill frequency table (baseline)...")
    freq_df = build_role_skill_frequency_table(role_df)

    print(
        f"\nRunning chi-square distinctiveness test "
        f"(significance={args.significance}, top_k={args.top_k})..."
    )
    print(f"Running {args.resamples} bootstrap resamples for stability check...")
    result = run_distinctiveness_analysis(
        role_df,
        freq_df,
        significance_level=args.significance,
        n_resamples=args.resamples,
        top_k=args.top_k,
        random_state=args.random_state,
    )

    args.output.mkdir(parents=True, exist_ok=True)
    freq_df.to_csv(args.output / "role_skill_demand.csv", index=False, encoding="utf-8")
    result["distinctiveness"].to_csv(
        args.output / "skill_distinctiveness.csv", index=False, encoding="utf-8"
    )
    result["ranking_divergence"].to_csv(
        args.output / "ranking_divergence.csv", index=False, encoding="utf-8"
    )
    result["stability"].to_csv(
        args.output / "distinctiveness_stability.csv", index=False, encoding="utf-8"
    )
    result["stability_summary"].to_csv(
        args.output / "distinctiveness_stability_summary.csv", index=False, encoding="utf-8"
    )

    print()
    print("=" * 60)
    print(result["report"])
    print()
    print("Wrote:")
    print(f"{args.output / 'role_skill_demand.csv'}")
    print(f"{args.output / 'skill_distinctiveness.csv'}")
    print(f"{args.output / 'ranking_divergence.csv'}")
    print(f"{args.output / 'distinctiveness_stability.csv'}")
    print(f"{args.output / 'distinctiveness_stability_summary.csv'}")
    print("=" * 60)


if __name__ == "__main__":
    main()