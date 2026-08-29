import argparse
from pathlib import Path

import pandas as pd

from src.extraction.semantic import SemanticSkillExtractor
from src.extraction.taxonomy import load_taxonomy


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_TAXONOMY_PATH = (
    PROJECT_ROOT
    / "config"
    / "skill_taxonomy.json"
)


def run_semantic_extraction(
    input_path: Path,
    taxonomy_path: Path,
    threshold: float,
) -> pd.DataFrame:
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

    taxonomy = load_taxonomy(taxonomy_path)

    extractor = SemanticSkillExtractor(
        taxonomy=taxonomy,
        threshold=threshold,
    )

    results = []

    for _, row in df.iterrows():
        job_id = str(row["job_id"])
        description = row["job_description"]

        if pd.isna(description):
            description = ""

        result = extractor.extract(
            job_id=job_id,
            text=str(description),
        )

        for skill in result.skills:
            results.append(
                {
                    "job_id": result.job_id,
                    "skill_id": skill.skill_id,
                    "confidence": skill.confidence,
                }
            )

    return pd.DataFrame(
        results,
        columns=["job_id", "skill_id", "confidence"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run semantic skill extraction on cleaned job data."
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Path to cleaned jobs CSV.",
    )

    parser.add_argument(
        "--taxonomy",
        type=Path,
        default=DEFAULT_TAXONOMY_PATH,
        help="Path to skill taxonomy JSON.",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.50,
        help="Semantic similarity threshold.",
    )

    args = parser.parse_args()

    predictions = run_semantic_extraction(
        input_path=args.input,
        taxonomy_path=args.taxonomy,
        threshold=args.threshold,
    )

    print("\nSEMANTIC EXTRACTION RESULTS")
    print("=" * 60)

    for job_id, group in predictions.groupby("job_id"):
        print(f"\nJOB: {job_id}")

        for _, row in group.iterrows():
            print(
                f"  - {row['skill_id']}"
                f" (confidence={row['confidence']:.4f})"
            )

    print("\n" + "=" * 60)
    print(
        f"Jobs with extracted skills: "
        f"{predictions['job_id'].nunique()}"
    )
    print(
        f"Total skill predictions: "
        f"{len(predictions)}"
    )


if __name__ == "__main__":
    main()