from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.extraction.evaluation.ground_truth import (
    load_ground_truth,
)
from src.extraction.evaluation.metrics import (
    calculate_metrics,
)
from src.extraction.semantic import SemanticSkillExtractor
from src.extraction.taxonomy import load_taxonomy


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_TAXONOMY_PATH = (
    PROJECT_ROOT
    / "config"
    / "skill_taxonomy.json"
)

DEFAULT_THRESHOLDS = [
    0.30,
    0.35,
    0.40,
    0.45,
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
]


def load_job_descriptions(
    input_path: Path,
) -> dict[str, str]:
    df = pd.read_csv(input_path)

    required_columns = {
        "job_id",
        "job_description",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    descriptions = {}

    for _, row in df.iterrows():
        job_id = str(row["job_id"])
        description = row["job_description"]

        if pd.isna(description):
            description = ""

        descriptions[job_id] = str(description)

    return descriptions


def convert_ground_truth(
    ground_truth_path: Path,
) -> set[tuple[str, str]]:
    annotations = load_ground_truth(
        ground_truth_path
    )

    return {
        (annotation.job_id, annotation.skill_id)
        for annotation in annotations
    }


def collect_semantic_scores(
    descriptions: dict[str, str],
    extractor: SemanticSkillExtractor,
) -> dict[str, dict[str, float]]:
    scores_by_job = {}

    for job_id, description in descriptions.items():
        scores_by_job[job_id] = extractor.score(
            description
        )

    return scores_by_job


def predictions_at_threshold(
    scores_by_job: dict[str, dict[str, float]],
    threshold: float,
) -> set[tuple[str, str]]:
    predictions = set()

    for job_id, skill_scores in scores_by_job.items():
        for skill_id, similarity in skill_scores.items():
            if similarity >= threshold:
                predictions.add(
                    (job_id, skill_id)
                )

    return predictions


def calibrate_thresholds(
    scores_by_job: dict[str, dict[str, float]],
    ground_truth: set[tuple[str, str]],
    thresholds: list[float],
) -> list[dict[str, float | int]]:
    results = []

    for threshold in thresholds:
        predictions = predictions_at_threshold(
            scores_by_job=scores_by_job,
            threshold=threshold,
        )

        metrics = calculate_metrics(
            predicted=predictions,
            ground_truth=ground_truth,
        )

        results.append(
            {
                "threshold": threshold,
                "true_positives": metrics.true_positives,
                "false_positives": metrics.false_positives,
                "false_negatives": metrics.false_negatives,
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1": metrics.f1,
            }
        )

    return results


def select_best_threshold(
    results: list[dict[str, float | int]],
) -> dict[str, float | int]:
    if not results:
        raise ValueError(
            "No threshold results available."
        )

    return max(
        results,
        key=lambda result: (
            result["f1"],
            result["precision"],
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Calibrate the semantic extraction "
            "similarity threshold."
        )
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Path to cleaned jobs CSV.",
    )

    parser.add_argument(
        "ground_truth",
        type=Path,
        help="Path to ground truth CSV.",
    )

    parser.add_argument(
        "--taxonomy",
        type=Path,
        default=DEFAULT_TAXONOMY_PATH,
        help="Path to skill taxonomy JSON.",
    )

    args = parser.parse_args()

    print("Loading taxonomy...")
    taxonomy = load_taxonomy(
        args.taxonomy
    )

    print("Loading job descriptions...")
    descriptions = load_job_descriptions(
        args.input
    )

    print("Loading ground truth...")
    ground_truth = convert_ground_truth(
        args.ground_truth
    )

    print("Loading semantic model...")
    extractor = SemanticSkillExtractor(
        taxonomy=taxonomy,
    )

    print(
        f"Scoring {len(descriptions)} jobs..."
    )

    scores_by_job = collect_semantic_scores(
        descriptions=descriptions,
        extractor=extractor,
    )

    print("\nCALIBRATION RESULTS")
    print("=" * 80)

    results = calibrate_thresholds(
        scores_by_job=scores_by_job,
        ground_truth=ground_truth,
        thresholds=DEFAULT_THRESHOLDS,
    )

    print(
        f"{'Threshold':<12}"
        f"{'Precision':<12}"
        f"{'Recall':<12}"
        f"{'F1':<12}"
        f"{'TP':<8}"
        f"{'FP':<8}"
        f"{'FN':<8}"
    )

    print("-" * 80)

    for result in results:
        print(
            f"{result['threshold']:<12.2f}"
            f"{result['precision']:<12.4f}"
            f"{result['recall']:<12.4f}"
            f"{result['f1']:<12.4f}"
            f"{result['true_positives']:<8}"
            f"{result['false_positives']:<8}"
            f"{result['false_negatives']:<8}"
        )

    best = select_best_threshold(results)

    print("\nBEST THRESHOLD")
    print("=" * 80)
    print(
        f"Threshold : {best['threshold']:.2f}"
    )
    print(
        f"Precision : {best['precision']:.4f}"
    )
    print(
        f"Recall    : {best['recall']:.4f}"
    )
    print(
        f"F1        : {best['f1']:.4f}"
    )


if __name__ == "__main__":
    main()