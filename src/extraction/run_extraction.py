from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.extraction.lexical import LexicalSkillExtractor
from src.extraction.semantic import SemanticSkillExtractor
from src.extraction.taxonomy import load_taxonomy


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_TAXONOMY_PATH = (
    PROJECT_ROOT
    / "config"
    / "skill_taxonomy.json"
)


def run_extraction(
    input_path: Path,
    taxonomy_path: Path,
    semantic_threshold: float,
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

    lexical_extractor = LexicalSkillExtractor(
        taxonomy
    )

    semantic_extractor = SemanticSkillExtractor(
        taxonomy=taxonomy,
        threshold=semantic_threshold,
    )

    lexical_results = []
    semantic_results = []

    for _, row in df.iterrows():
        job_id = str(row["job_id"])
        description = row["job_description"]

        if pd.isna(description):
            description = ""

        description = str(description)

        lexical_result = lexical_extractor.extract(
            job_id=job_id,
            text=description,
        )

        semantic_result = semantic_extractor.extract(
            job_id=job_id,
            text=description,
        )

        lexical_results.append(
            {
                skill.skill_id
                for skill in lexical_result.skills
            }
        )

        semantic_results.append(
            {
                skill.skill_id
                for skill in semantic_result.skills
            }
        )

    enriched = df.copy()

    enriched["lexical_skills"] = [
        json.dumps(
            sorted(skills),
            ensure_ascii=False,
        )
        for skills in lexical_results
    ]

    enriched["semantic_skills"] = [
        json.dumps(
            sorted(skills),
            ensure_ascii=False,
        )
        for skills in semantic_results
    ]

    return enriched


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run lexical and semantic skill extraction "
            "and produce an enriched job dataset."
        )
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Path to cleaned jobs CSV.",
    )

    parser.add_argument(
        "output",
        type=Path,
        help="Path for enriched jobs CSV.",
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
        default=0.45,
        help="Semantic similarity threshold.",
    )

    args = parser.parse_args()

    enriched = run_extraction(
        input_path=args.input,
        taxonomy_path=args.taxonomy,
        semantic_threshold=args.semantic_threshold,
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    enriched.to_csv(
        args.output,
        index=False,
    )

    print(
        f"Saved enriched dataset to: {args.output}"
    )


if __name__ == "__main__":
    main()