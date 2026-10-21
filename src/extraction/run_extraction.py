
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
    PROJECT_ROOT / "config" / "skill_taxonomy.json"
)

# Phrases indicating a boilerplate or placeholder job description.
_BOILERPLATE_MARKERS = (
    "please refer the full details",
    "refer the full details",
    "please see the full job description",
    "please refer to the full details",
)


def _is_boilerplate(text: str) -> bool:
    """Return True when text contains a known placeholder phrase."""
    normalised = text.casefold()
    return any(
        marker in normalised
        for marker in _BOILERPLATE_MARKERS
    )


def _safe_text(value) -> str:
    """Convert missing values to an empty string."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _extraction_text(row: pd.Series) -> str:
    """
    Use the job description unless it is empty or boilerplate.
    Fall back to the job title when necessary.
    """
    description = _safe_text(row.get("job_description", ""))
    title = _safe_text(
        row.get("job_title_raw", row.get("job_title", ""))
    )

    if not description or _is_boilerplate(description):
        return f"{title} {description}".strip()

    return description


def run_extraction(
    input_path: Path | None = None,
    taxonomy_path: Path = DEFAULT_TAXONOMY_PATH,
    semantic_threshold: float = 0.45,
    input_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Run lexical and semantic extraction.

    Supply either:
      - input_df: jobs loaded from the master database, or
      - input_path: a CSV file.

    The returned dataframe preserves the original job columns and adds
    lexical_skills and semantic_skills as JSON-encoded lists.
    """
    if input_df is not None:
        df = input_df.copy()
    elif input_path is not None:
        df = pd.read_csv(input_path)
    else:
        raise ValueError(
            "Provide either input_df or input_path."
        )

    required_columns = {"job_id", "job_description"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if not 0.0 <= semantic_threshold <= 1.0:
        raise ValueError(
            "semantic_threshold must be between 0.0 and 1.0."
        )

    # Normalize title/company names for the existing UI and fallback logic.
    if "job_title_raw" not in df.columns and "job_title" in df.columns:
        df["job_title_raw"] = df["job_title"]

    if "company" not in df.columns and "company_name" in df.columns:
        df["company"] = df["company_name"]

    taxonomy = load_taxonomy(taxonomy_path)

    lexical_extractor = LexicalSkillExtractor(taxonomy)
    semantic_extractor = SemanticSkillExtractor(
        taxonomy=taxonomy,
        threshold=semantic_threshold,
    )

    lexical_results = []
    semantic_results = []

    for _, row in df.iterrows():
        job_id = str(row["job_id"])
        text = _extraction_text(row)

        lexical_result = lexical_extractor.extract(
            job_id=job_id,
            text=text,
        )
        semantic_result = semantic_extractor.extract(
            job_id=job_id,
            text=text,
        )

        lexical_results.append(
            sorted({
                skill.skill_id
                for skill in lexical_result.skills
            })
        )
        semantic_results.append(
            sorted({
                skill.skill_id
                for skill in semantic_result.skills
            })
        )

    enriched = df.copy()

    enriched["lexical_skills"] = [
        json.dumps(skills, ensure_ascii=False)
        for skills in lexical_results
    ]
    enriched["semantic_skills"] = [
        json.dumps(skills, ensure_ascii=False)
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
        help="Path to input jobs CSV.",
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
        encoding="utf-8",
    )

    print(f"Saved enriched dataset to: {args.output}")


if __name__ == "__main__":
    main()
