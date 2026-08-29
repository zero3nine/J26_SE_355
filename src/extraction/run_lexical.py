import argparse
from pathlib import Path

import pandas as pd

from src.extraction.lexical import LexicalSkillExtractor
from src.extraction.taxonomy import load_taxonomy


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_TAXONOMY_PATH = (
    PROJECT_ROOT
    / "config"
    / "skill_taxonomy.json"
)


def run_lexical_extraction(
    input_path: Path,
    taxonomy_path: Path,
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
    extractor = LexicalSkillExtractor(taxonomy)

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
                }
            )

    return pd.DataFrame(
        results,
        columns=["job_id", "skill_id"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run lexical skill extraction on cleaned job data."
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

    args = parser.parse_args()

    predictions = run_lexical_extraction(
        input_path=args.input,
        taxonomy_path=args.taxonomy,
    )

    print("\nLEXICAL EXTRACTION RESULTS")
    print("=" * 60)

    for job_id, group in predictions.groupby("job_id"):
        print(f"\nJOB: {job_id}")

        for skill_id in group["skill_id"]:
            print(f"  - {skill_id}")

    print("\n" + "=" * 60)
    print(f"Jobs with extracted skills: {predictions['job_id'].nunique()}")
    print(f"Total skill predictions: {len(predictions)}")


if __name__ == "__main__":
    main()