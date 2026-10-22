
import argparse
from pathlib import Path

import pandas as pd

from src.extraction.lexical import LexicalSkillExtractor
from src.extraction.taxonomy import load_taxonomy


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_TAXONOMY_PATH = (
    PROJECT_ROOT / "config" / "skill_taxonomy.json"
)


def build_extraction_text(row: pd.Series) -> str:
    """Combine available text fields used for skill extraction."""
    text_parts = []

    for column in ("job_description", "requirements"):
        if column not in row.index:
            continue

        value = row[column]

        if pd.notna(value):
            value = str(value).strip()

            if value:
                text_parts.append(value)

    return "\n".join(text_parts)


def run_lexical_extraction(
    input_path: Path,
    taxonomy_path: Path,
) -> pd.DataFrame:
    df = pd.read_csv(input_path)

    required_columns = {"job_id", "job_description"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if df["job_id"].isna().any():
        raise ValueError("Input dataset contains missing job_id values.")

    taxonomy = load_taxonomy(taxonomy_path)
    extractor = LexicalSkillExtractor(taxonomy)

    results = []

    for _, row in df.iterrows():
        job_id = str(row["job_id"]).strip()
        text = build_extraction_text(row)

        if not text:
            continue

        result = extractor.extract(
            job_id=job_id,
            text=text,
        )

        for skill in result.skills:
            results.append(
                {
                    "job_id": result.job_id,
                    "skill_id": skill.skill_id,
                }
            )

    predictions = pd.DataFrame(
        results,
        columns=["job_id", "skill_id"],
    )

    return predictions.drop_duplicates(
        subset=["job_id", "skill_id"]
    ).reset_index(drop=True)


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

    if predictions.empty:
        print("No skills were extracted.")
    else:
        for job_id, group in predictions.groupby("job_id"):
            print(f"\nJOB: {job_id}")

            for skill_id in group["skill_id"]:
                print(f"  - {skill_id}")

    print("\n" + "=" * 60)
    print(
        f"Jobs in input dataset: "
        f"{pd.read_csv(args.input, usecols=['job_id']).shape[0]:,}"
    )
    print(
        f"Jobs with extracted skills: "
        f"{predictions['job_id'].nunique():,}"
    )
    print(f"Total skill predictions: {len(predictions):,}")
    print(
        f"Distinct skills predicted: "
        f"{predictions['skill_id'].nunique():,}"
    )


if __name__ == "__main__":
    main()
