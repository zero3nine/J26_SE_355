import json
from pathlib import Path

import pandas as pd

from src.roles.taxonomy import load_role_taxonomy
from src.roles.classifier import RoleClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROLE_TAXONOMY_PATH = PROJECT_ROOT / "config" / "role_taxonomy.json"


def classify_roles(df: pd.DataFrame, taxonomy_path: Path = DEFAULT_ROLE_TAXONOMY_PATH) -> pd.DataFrame:
    """Adds role_id/role_name columns to an already skill-extracted
    dataframe, by classifying each job's title, falling back to its description."""
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
    """Parses a lexical_skills/semantic_skills cell back into a
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
    the same underlying jobs, so the two can be compared directly per
    role."""
    if "role_name" not in df.columns:
        raise ValueError(
            "role_name column not found, call classify_roles() before "
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

# Role x skill matrix 

MATRIX_MODES = ("lexical", "semantic", "both")

SHADE_RGB = (59, 130, 246)
SHADE_MIN_ALPHA = 0.15
SHADE_MAX_ALPHA = 0.80

def _skill_set(value) -> set:
    return {str(item).strip() for item in _parse_skill_list(value) if str(item).strip()}

def build_role_skill_matrix(df: pd.DataFrame, mode: str = "lexical") -> pd.DataFrame:
    """Returns a skills by roles matrix of whole number posting counts from
    a role-classified dataframe"""
    if mode not in MATRIX_MODES:
        raise ValueError(f"mode must be one of {MATRIX_MODES}, got {mode!r}")
    if "role_name" not in df.columns:
        raise ValueError(
            "role_name column not found, call classify_roles() before "
            "build_role_skill_matrix()."
        )

    all_roles = sorted(df["role_name"].unique())
    empty_cells = pd.Series("", index=df.index)
    lexical_cells = df.get("lexical_skills", empty_cells)
    semantic_cells = df.get("semantic_skills", empty_cells)

    pairs = []
    for role_name, lexical_value, semantic_value in zip(
        df["role_name"], lexical_cells, semantic_cells
    ):
        if mode == "lexical":
            skills = _skill_set(lexical_value)
        elif mode == "semantic":
            skills = _skill_set(semantic_value)
        else:
            skills = _skill_set(lexical_value) & _skill_set(semantic_value)
        pairs.extend((role_name, skill) for skill in skills)

    if not pairs:
        return pd.DataFrame(columns=all_roles, dtype=int)

    matrix = (
        pd.DataFrame(pairs, columns=["role_name", "skill"])
        .groupby(["skill", "role_name"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=all_roles, fill_value=0)
        .astype(int)
        .sort_index()
    )
    order = matrix.sum(axis=1).sort_values(ascending=False, kind="stable").index
    matrix = matrix.loc[order]
    matrix.index.name = "skill"
    return matrix


def label_roles_with_totals(matrix: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """Renames each role column to e.g. 'DevOps Engineer (4 postings)' so
    readers can judge each count against the size of the role."""
    totals = df.groupby("role_name")["job_id"].count().to_dict()

    def label(role_name: str) -> str:
        n = totals.get(role_name, 0)
        return f"{role_name} ({n} posting{'' if n == 1 else 's'})"

    return matrix.rename(columns=label)


def _cell_shade(value, max_value) -> str:
    if not max_value or value <= 0:
        return ""
    alpha = SHADE_MIN_ALPHA + (SHADE_MAX_ALPHA - SHADE_MIN_ALPHA) * (value / max_value)
    r, g, b = SHADE_RGB
    return f"background-color: rgba({r}, {g}, {b}, {alpha:.2f})"


def style_role_skill_matrix(matrix: pd.DataFrame):
    max_value = int(matrix.to_numpy().max()) if matrix.size else 0
    styler = matrix.style.format("{:d}")
    apply_cellwise = getattr(styler, "map", None) or styler.applymap  # pandas >= 2.1 / older
    return apply_cellwise(lambda v: _cell_shade(v, max_value))