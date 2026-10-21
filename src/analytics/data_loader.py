from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "job_id",
    "lexical_skills",
    "semantic_skills",
}


def parse_skill_list(value) -> list[str]:
    """
    Convert a CSV skill-list value into a clean Python list.
    """

    if value is None or pd.isna(value):
        return []

    if isinstance(value, list):
        return sorted(set(str(item) for item in value))

    text = str(value).strip()

    if not text or text == "[]":
        return []

    # JSON format
    try:
        parsed = json.loads(text)

        if isinstance(parsed, list):
            return sorted(
                set(str(item).strip() for item in parsed if str(item).strip())
            )
    except (json.JSONDecodeError, TypeError):
        pass

    # Python list format
    try:
        parsed = ast.literal_eval(text)

        if isinstance(parsed, list):
            return sorted(
                set(str(item).strip() for item in parsed if str(item).strip())
            )
    except (ValueError, SyntaxError):
        pass

    return []


def load_extracted_jobs(
    input_path: Path,
    skill_column: str = "semantic_skills",
) -> pd.DataFrame:
    """
    Load the extracted job dataset.

    skill_column can be:
        semantic_skills
        lexical_skills
    """

    df = pd.read_csv(input_path)

    missing = REQUIRED_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if skill_column not in {
        "lexical_skills",
        "semantic_skills",
    }:
        raise ValueError(
            "skill_column must be lexical_skills or semantic_skills"
        )

    result = df[
        [
            "job_id",
            "job_title_raw",
            "company",
            "country",
            "location_raw",
            "posted_date",
            skill_column,
        ]
    ].copy()

    result["skills"] = result[skill_column].apply(parse_skill_list)

    result = result.drop(columns=[skill_column])

    return result


def filter_jobs_with_skills(
    df: pd.DataFrame,
    minimum_skills: int = 1,
) -> pd.DataFrame:
    """
    Keep advertisements containing at least the requested
    number of extracted skills.
    """

    return df[
        df["skills"].apply(len) >= minimum_skills
    ].copy()