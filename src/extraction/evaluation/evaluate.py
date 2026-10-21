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
from src.extraction.lexical import LexicalSkillExtractor
from src.extraction.semantic import SemanticSkillExtractor
from src.extraction.taxonomy import (
    get_category_for_skill,
    load_taxonomy,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_TAXONOMY_PATH = (
    PROJECT_ROOT
    / "config"
    / "skill_taxonomy.json"
)


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


def extract_predictions(
    descriptions: dict[str, str],
    extractor,
) -> set[tuple[str, str]]:
    predictions = set()

    for job_id, description in descriptions.items():
        result = extractor.extract(
            job_id=job_id,
            text=description,
        )

        for skill in result.skills:
            predictions.add(
                (job_id, skill.skill_id)
            )

    return predictions


def calculate_category_metrics(
    predictions: set[tuple[str, str]],
    ground_truth: set[tuple[str, str]],
    taxonomy,
) -> dict[str, object]:
    categories = {}

    all_skill_ids = {
        skill_id
        for _, skill_id in predictions | ground_truth
    }

    for skill_id in all_skill_ids:
        category = get_category_for_skill(
            taxonomy,
            skill_id,
        )

        if category is None:
            continue

        category_predictions = {
            pair
            for pair in predictions
            if pair[1] == skill_id
        }

        category_ground_truth = {
            pair
            for pair in ground_truth
            if pair[1] == skill_id
        }

        category_metrics = calculate_metrics(
            predicted=category_predictions,
            ground_truth=category_ground_truth,
        )

        if category.id not in categories:
            categories[category.id] = []

        categories[category.id].append(
            category_metrics
        )

    return categories


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate lexical and semantic "
            "skill extraction."
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

    parser.add_argument(
        "--semantic-threshold",
        type=float,
        required=True,
        help="Locked semantic similarity threshold.",
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

    print("Running lexical extraction...")

    lexical_extractor = LexicalSkillExtractor(
        taxonomy
    )

    lexical_predictions = extract_predictions(
        descriptions,
        lexical_extractor,
    )

    print("Running semantic extraction...")

    semantic_extractor = SemanticSkillExtractor(
        taxonomy=taxonomy,
        threshold=args.semantic_threshold,
    )

    semantic_predictions = extract_predictions(
        descriptions,
        semantic_extractor,
    )

    lexical_metrics = calculate_metrics(
        predicted=lexical_predictions,
        ground_truth=ground_truth,
    )

    semantic_metrics = calculate_metrics(
        predicted=semantic_predictions,
        ground_truth=ground_truth,
    )

    print("\nEXTRACTION COMPARISON")
    print("=" * 70)

    print(
        f"{'Metric':<20}"
        f"{'Lexical':<20}"
        f"{'Semantic':<20}"
    )

    print("-" * 70)

    print(
        f"{'True Positives':<20}"
        f"{lexical_metrics.true_positives:<20}"
        f"{semantic_metrics.true_positives:<20}"
    )

    print(
        f"{'False Positives':<20}"
        f"{lexical_metrics.false_positives:<20}"
        f"{semantic_metrics.false_positives:<20}"
    )

    print(
        f"{'False Negatives':<20}"
        f"{lexical_metrics.false_negatives:<20}"
        f"{semantic_metrics.false_negatives:<20}"
    )

    print(
        f"{'Precision':<20}"
        f"{lexical_metrics.precision:<20.4f}"
        f"{semantic_metrics.precision:<20.4f}"
    )

    print(
        f"{'Recall':<20}"
        f"{lexical_metrics.recall:<20.4f}"
        f"{semantic_metrics.recall:<20.4f}"
    )

    print(
        f"{'F1':<20}"
        f"{lexical_metrics.f1:<20.4f}"
        f"{semantic_metrics.f1:<20.4f}"
    )


if __name__ == "__main__":
    main()