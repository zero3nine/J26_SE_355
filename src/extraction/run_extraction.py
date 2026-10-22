
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

from src.extraction.input_text import build_extraction_text


def _extraction_text(row: pd.Series) -> tuple[str, str]:
    """Backward-compatible wrapper around the shared extraction text builder."""
    return build_extraction_text(row)


def run_extraction(
    input_path: Path | pd.DataFrame | str | None = None,
    taxonomy_path: Path = DEFAULT_TAXONOMY_PATH,
    semantic_threshold: float = 0.58,
    batch_id: str | None = None,
    persist_to_db: bool = False,
    db_path: Path | str | None = None,
    input_df: pd.DataFrame | None = None,
    **kwargs,
) -> pd.DataFrame:
    """
    Run lexical and semantic extraction.

    Supply either:
      - input_df: jobs loaded from the master database, or
      - input_path: a CSV file or DataFrame.

    The returned dataframe preserves the original job columns and adds
    lexical_skills and semantic_skills as JSON-encoded lists.
    """
    if input_df is not None:
        df = input_df.copy()
    elif isinstance(input_path, pd.DataFrame):
        df = input_path.copy()
    elif input_path is not None:
        df = pd.read_csv(input_path)
    else:
        raise ValueError(
            "Provide either input_df or input_path."
        )

    # Harmonize title and company columns between database and CSV formats
    if "job_title_raw" not in df.columns and "job_title" in df.columns:
        df["job_title_raw"] = df["job_title"]
    elif "job_title" not in df.columns and "job_title_raw" in df.columns:
        df["job_title"] = df["job_title_raw"]

    if "company" not in df.columns and "company_name" in df.columns:
        df["company"] = df["company_name"]
    elif "company_name" not in df.columns and "company" in df.columns:
        df["company_name"] = df["company"]

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

    if df.empty:
        enriched = df.copy()
        if "skill_provenance" not in enriched.columns:
            enriched["skill_provenance"] = []
        if "lexical_skills" not in enriched.columns:
            enriched["lexical_skills"] = []
        if "semantic_skills" not in enriched.columns:
            enriched["semantic_skills"] = []
        if batch_id and "collection_batch_id" not in enriched.columns:
            enriched["collection_batch_id"] = []
        return enriched

    taxonomy = load_taxonomy(taxonomy_path)

    lexical_extractor = LexicalSkillExtractor(taxonomy)
    semantic_extractor = SemanticSkillExtractor(
        taxonomy=taxonomy,
        threshold=semantic_threshold,
    )

    lexical_results = []
    semantic_results = []
    provenances = []

    for _, row in df.iterrows():
        job_id = str(row["job_id"])

        # Use title as fallback when description is boilerplate/empty
        text, prov = _extraction_text(row)
        provenances.append(prov)

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

    enriched["skill_provenance"] = provenances

    enriched["lexical_skills"] = [
        json.dumps(skills, ensure_ascii=False)
        for skills in lexical_results
    ]
    enriched["semantic_skills"] = [
        json.dumps(skills, ensure_ascii=False)
        for skills in semantic_results
    ]

    if batch_id and "collection_batch_id" not in enriched.columns:
        enriched["collection_batch_id"] = batch_id

    if persist_to_db:
        try:
            from src.database.repository import (
                seed_skills_taxonomy,
                record_extraction_run,
                store_extracted_skills,
            )
            seed_skills_taxonomy(taxonomy_path=taxonomy_path, db_path=db_path)
            run_id = record_extraction_run(
                run_type="lexical_semantic_hybrid",
                model_name="all-MiniLM-L6-v2",
                model_version="1.0",
                taxonomy_version="0.1.0",
                semantic_threshold=semantic_threshold,
                source_batch_id=batch_id,
                notes=f"Extraction threshold {semantic_threshold}",
                db_path=db_path,
            )
            store_extracted_skills(
                enriched, run_id=run_id, method="lexical",
                skills_column="lexical_skills", db_path=db_path, taxonomy_path=taxonomy_path
            )
            store_extracted_skills(
                enriched, run_id=run_id, method="semantic",
                skills_column="semantic_skills", db_path=db_path, taxonomy_path=taxonomy_path
            )
            enriched["extraction_run_id"] = run_id
        except Exception as db_err:
            print(f"Warning: Could not persist extraction to SQLite database: {db_err}")

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

    parser.add_argument(
        "--persist-db",
        action="store_true",
        help="Persist extraction run and extracted skills into the master SQLite database.",
    )

    args = parser.parse_args()

    enriched = run_extraction(
        input_path=args.input,
        taxonomy_path=args.taxonomy,
        semantic_threshold=args.semantic_threshold,
        persist_to_db=args.persist_db,
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
