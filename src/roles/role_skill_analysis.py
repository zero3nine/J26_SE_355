import json
from pathlib import Path

import pandas as pd

from src.roles.taxonomy import load_role_taxonomy
from src.roles.classifier import RoleClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROLE_TAXONOMY_PATH = PROJECT_ROOT / "config" / "role_taxonomy.json"


def classify_roles(df: pd.DataFrame, taxonomy_path: Path = DEFAULT_ROLE_TAXONOMY_PATH) -> pd.DataFrame:
    """Adds role_id/role_name columns to an already skill-extracted
    dataframe (i.e. the output of src.extraction.run_extraction), by
    classifying each job's title, falling back to its description.
    """
    taxonomy = load_role_taxonomy(taxonomy_path)
    classifier = RoleClassifier(taxonomy)

    role_ids = []
    role_names = []

    for _, row in df.iterrows():
        title = str(row.get("job_title_raw", "") or "")
        description = str(row.get("job_description", "") or "")

        role_id, role_name, _matched_alias = classifier.classify(title, description)
        role_ids.append(role_id)
        role_names.append(role_name)

    result = df.copy()
    result["role_id"] = role_ids
    result["role_name"] = role_names
    return result


def _parse_skill_list(value):
    """Parses a lexical_skills/semantic_skills cell (written by
    run_extraction as a JSON-encoded list of skill ids) back into a
    Python list, tolerating blank/NaN cells.
    """
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, ValueError):
        return []


def build_role_skill_frequency_table(df: pd.DataFrame) -> pd.DataFrame:
    """Builds a long (role_name, skill, method, job_count) table from a
    role-classified, skill-extracted dataframe.

    One row per unique (role, skill, method) combination, with the
    count and percentage of that role's jobs where that method found
    that skill. Both "lexical" and "semantic" rows are produced from
    the SAME underlying jobs, so the two can be compared directly per
    role -- this is what feeds the combined lexical-vs-semantic chart.
    """
    if "role_name" not in df.columns:
        raise ValueError(
            "role_name column not found -- call classify_roles() before "
            "build_role_skill_frequency_table()."
        )

    role_totals = df.groupby("role_name")["job_id"].count().to_dict()

    method_tables = []

    for method, column in (("lexical", "lexical_skills"), ("semantic", "semantic_skills")):
        if column not in df.columns:
            continue

        long_df = df[["job_id", "role_name", column]].copy()
        long_df["skill"] = long_df[column].apply(_parse_skill_list)
        long_df = long_df.explode("skill")
        long_df = long_df.dropna(subset=["skill"])
        long_df = long_df[long_df["skill"] != ""]

        counts = (
            long_df.groupby(["role_name", "skill"])
            .size()
            .reset_index(name="job_count")
        )
        counts["method"] = method
        counts["total_jobs_in_role"] = counts["role_name"].map(role_totals)
        counts["pct_of_role"] = (counts["job_count"] / counts["total_jobs_in_role"] * 100).round(1)
        method_tables.append(counts)

    if not method_tables:
        return pd.DataFrame(
            columns=["role_name", "skill", "method", "job_count", "total_jobs_in_role", "pct_of_role"]
        )

    combined = pd.concat(method_tables, ignore_index=True)
    return combined.sort_values(
        ["role_name", "method", "job_count"], ascending=[True, True, False]
    )