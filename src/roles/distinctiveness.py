from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact

DEFAULT_SIGNIFICANCE_LEVEL = 0.05
DEFAULT_N_RESAMPLES = 30
DEFAULT_TOP_K = 5
DEFAULT_RANDOM_STATE = 42

METHOD_COLUMNS = {
    "lexical": "lexical_skills",
    "semantic": "semantic_skills",
}

def _parse_skill_list(value) -> list:
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, ValueError):
        return []


def _explode_skills(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """(job_id, role_name, skill) long table for one skill-extraction method."""
    long_df = df[["job_id", "role_name", column]].copy()
    long_df["skill"] = long_df[column].apply(_parse_skill_list)
    long_df = long_df.explode("skill")
    long_df = long_df.dropna(subset=["skill"])
    long_df = long_df[long_df["skill"] != ""]
    return long_df[["job_id", "role_name", "skill"]]

# Chi-square distinctiveness test

@dataclass
class _ContingencyCounts:
    a: int  # in-role, has skill
    b: int  # in-role, lacks skill
    c: int  # other roles, has skill
    d: int  # other roles, lacks skill


def _contingency_counts(
    role_job_ids: set, other_job_ids: set, skill_job_ids: set
) -> _ContingencyCounts:
    a = len(role_job_ids & skill_job_ids)
    b = len(role_job_ids) - a
    c = len(other_job_ids & skill_job_ids)
    d = len(other_job_ids) - c
    return _ContingencyCounts(a=a, b=b, c=c, d=d)


def _chi_square_row(role_name: str, skill: str, method: str, counts: _ContingencyCounts) -> dict:
    table = [[counts.a, counts.b], [counts.c, counts.d]]
    row_totals = [counts.a + counts.b, counts.c + counts.d]
    col_totals = [counts.a + counts.c, counts.b + counts.d]
    grand_total = sum(row_totals)

    in_role_rate = counts.a / row_totals[0] if row_totals[0] else 0.0
    other_role_rate = counts.c / row_totals[1] if row_totals[1] else 0.0
    direction = "over_represented" if in_role_rate > other_role_rate else "under_represented"

    expected = [
        [row_totals[0] * col_totals[0] / grand_total, row_totals[0] * col_totals[1] / grand_total],
        [row_totals[1] * col_totals[0] / grand_total, row_totals[1] * col_totals[1] / grand_total],
    ] if grand_total else [[0, 0], [0, 0]]
    low_expected_frequency_warning = any(cell < 5 for row in expected for cell in row)

    # Cochran's rule for 2x2 tables: chi-square's p-value is only a reliable
    # approximation when every expected cell count is >= 5. Below that, fall
    # back to Fisher's exact test, which computes the exact p-value directly
    # (via the hypergeometric distribution) and is valid at any sample size.
    chi2_stat = None
    odds_ratio = None
    if grand_total == 0 or row_totals[0] == 0 or row_totals[1] == 0:
        p_value = float("nan")
        test_used = "none"
    elif low_expected_frequency_warning:
        odds_ratio, p_value = fisher_exact(table, alternative="two-sided")
        test_used = "fisher_exact"
    else:
        chi2_stat, p_value, _dof, _exp = chi2_contingency(table, correction=True)
        test_used = "chi_square"

    return {
        "role_name": role_name,
        "skill": skill,
        "method": method,
        "in_role_job_count": row_totals[0],
        "in_role_skill_count": counts.a,
        "in_role_pct": round(in_role_rate * 100, 1),
        "other_roles_job_count": row_totals[1],
        "other_roles_skill_count": counts.c,
        "other_roles_pct": round(other_role_rate * 100, 1),
        "chi2_statistic": round(chi2_stat, 4) if chi2_stat is not None and pd.notna(chi2_stat) else None,
        "odds_ratio": round(odds_ratio, 4) if odds_ratio is not None and pd.notna(odds_ratio) else None,
        "p_value": round(p_value, 6) if pd.notna(p_value) else None,
        "test_used": test_used,
        "direction": direction,
        "low_expected_frequency_warning": low_expected_frequency_warning,
    }


def compute_skill_distinctiveness(
    role_df: pd.DataFrame,
    method_columns: dict | None = None,
    significance_level: float = DEFAULT_SIGNIFICANCE_LEVEL,
) -> pd.DataFrame:
    """Runs the chi-square distinctiveness test for every (role, skill,
    method) combination found in role_df, for each skill the role
    actually mentions at least once.
    """
    if "role_name" not in role_df.columns:
        raise ValueError(
            "role_name column not found, call classify_roles() before "
            "compute_skill_distinctiveness()."
        )

    method_columns = method_columns or METHOD_COLUMNS
    rows = []

    for method, column in method_columns.items():
        if column not in role_df.columns:
            continue

        long_df = _explode_skills(role_df, column)
        if long_df.empty:
            continue

        job_ids_by_role = {
            role: set(group["job_id"])
            for role, group in role_df.groupby("role_name")
        }
        all_job_ids = set(role_df["job_id"])

        for role_name, role_job_ids in job_ids_by_role.items():
            other_job_ids = all_job_ids - role_job_ids
            role_skills = long_df[long_df["role_name"] == role_name]["skill"].unique()

            for skill in role_skills:
                skill_job_ids = set(long_df[long_df["skill"] == skill]["job_id"])
                counts = _contingency_counts(role_job_ids, other_job_ids, skill_job_ids)
                rows.append(_chi_square_row(role_name, skill, method, counts))

    result = pd.DataFrame(rows)
    if result.empty:
        return pd.DataFrame(columns=[
            "role_name", "skill", "method", "in_role_job_count", "in_role_skill_count",
            "in_role_pct", "other_roles_job_count", "other_roles_skill_count",
            "other_roles_pct", "chi2_statistic", "odds_ratio", "p_value", "test_used", "significant", "direction",
            "low_expected_frequency_warning", "distinctiveness_rank",
        ])

    result["significant"] = result["p_value"] < significance_level
    result = _rank_distinctive_skills(result)
    return result.sort_values(
        ["role_name", "method", "distinctiveness_rank", "p_value"],
        na_position="last",
    ).reset_index(drop=True)


def _rank_distinctive_skills(chi_df: pd.DataFrame) -> pd.DataFrame:
    """Assigns distinctiveness_rank within each (role_name, method) group, 
    among rows that are both significant and over-represented. All other rows get rank = NaN, 
    they are kept in the output, just not ranked, so the full test result stays visible."""
    chi_df = chi_df.copy()
    chi_df["distinctiveness_rank"] = np.nan

    is_distinctive = chi_df["significant"] & (chi_df["direction"] == "over_represented")

    for (role_name, method), group in chi_df[is_distinctive].groupby(["role_name", "method"]):
        ordered = group.sort_values(
            ["p_value", "chi2_statistic"], ascending=[True, False]
        )
        ranks = pd.Series(range(1, len(ordered) + 1), index=ordered.index)
        chi_df.loc[ranks.index, "distinctiveness_rank"] = ranks

    return chi_df

# Distinctiveness-ranking vs frequency-ranking divergence

def compare_rankings(
    distinctiveness_df: pd.DataFrame,
    freq_df: pd.DataFrame,
    top_k: int = DEFAULT_TOP_K,
) -> pd.DataFrame:
    """Compares the chi-square distinctiveness ranking against the plain
    frequency-based baseline ranking (freq_df, from
    role_skill_analysis.build_role_skill_frequency_table), per
    (role_name, method).
    """
    rows = []

    for (role_name, method), freq_group in freq_df.groupby(["role_name", "method"]):
        freq_ranked = freq_group.sort_values("job_count", ascending=False).reset_index(drop=True)
        freq_ranked["frequency_rank"] = freq_ranked.index + 1

        distinct_group = distinctiveness_df[
            (distinctiveness_df["role_name"] == role_name)
            & (distinctiveness_df["method"] == method)
        ]

        merged = freq_ranked.merge(
            distinct_group[["skill", "p_value", "chi2_statistic", "distinctiveness_rank", "direction"]],
            on="skill",
            how="left",
        )

        # Spearman correlation needs a complete, comparable rank order on both sides, rank all skills common to both methods by p-value
        # (ascending) as a stand-in distinctiveness order, since
        # distinctiveness_rank itself is only defined for the
        # significant + over-represented subset.
        comparable = merged.dropna(subset=["p_value"]).copy()
        spearman_rho = None
        if len(comparable) >= 2:
            comparable["p_value_rank"] = comparable["p_value"].rank(method="average")
            spearman_rho = round(
                comparable["frequency_rank"].corr(comparable["p_value_rank"], method="spearman"), 3
            )

        freq_top_k = set(freq_ranked.head(top_k)["skill"])
        distinct_top_k = set(
            distinct_group.dropna(subset=["distinctiveness_rank"])
            .sort_values("distinctiveness_rank")
            .head(top_k)["skill"]
        )
        overlap = freq_top_k & distinct_top_k
        overlap_pct = round(len(overlap) / top_k * 100, 1) if top_k else None

        rows.append({
            "role_name": role_name,
            "method": method,
            "skills_compared": len(comparable),
            "spearman_rho": spearman_rho,
            "top_k": top_k,
            "frequency_top_k": sorted(freq_top_k),
            "distinctiveness_top_k": sorted(distinct_top_k),
            "top_k_overlap_count": len(overlap),
            "top_k_overlap_pct": overlap_pct,
        })

    return pd.DataFrame(rows).sort_values(["role_name", "method"]).reset_index(drop=True)

# Resampling stability check 

def resample_distinctiveness_stability(
    role_df: pd.DataFrame,
    method_columns: dict | None = None,
    significance_level: float = DEFAULT_SIGNIFICANCE_LEVEL,
    n_resamples: int = DEFAULT_N_RESAMPLES,
    top_k: int = DEFAULT_TOP_K,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bootstrap-resamples the job postings (with replacement, same
    sample size) n_resamples times, re-runs the chi-square
    distinctiveness test on each resample, and records how often each
    skill lands in its role's top-K distinctive skills across those
    resamples."""
    rng = np.random.default_rng(random_state)
    method_columns = method_columns or METHOD_COLUMNS

    original = compute_skill_distinctiveness(role_df, method_columns, significance_level)

    original_top_k = (
        original.dropna(subset=["distinctiveness_rank"])
        .sort_values(["role_name", "method", "distinctiveness_rank"])
        .groupby(["role_name", "method"])
        .head(top_k)
    )

    if original_top_k.empty:
        empty_stability = pd.DataFrame(columns=[
            "role_name", "method", "skill", "times_in_top_k", "n_resamples", "stability_pct",
        ])
        empty_summary = pd.DataFrame(columns=[
            "role_name", "method", "n_resamples", "top_k", "mean_top_k_stability_pct",
        ])
        return empty_stability, empty_summary

    hit_counts = {
        (row.role_name, row.method, row.skill): 0
        for row in original_top_k.itertuples()
    }

    n_jobs = len(role_df)
    for _ in range(n_resamples):
        sample_idx = rng.integers(0, n_jobs, size=n_jobs)
        resampled_df = role_df.iloc[sample_idx].reset_index(drop=True)
        resampled_df["job_id"] = [f"resample_{i}" for i in range(len(resampled_df))]

        resampled_result = compute_skill_distinctiveness(
            resampled_df, method_columns, significance_level
        )
        resampled_top_k = (
            resampled_result.dropna(subset=["distinctiveness_rank"])
            .sort_values(["role_name", "method", "distinctiveness_rank"])
            .groupby(["role_name", "method"])
            .head(top_k)
        )
        resampled_keys = set(
            zip(resampled_top_k["role_name"], resampled_top_k["method"], resampled_top_k["skill"])
        )
        for key in hit_counts:
            if key in resampled_keys:
                hit_counts[key] += 1

    stability_rows = [
        {
            "role_name": role_name,
            "method": method,
            "skill": skill,
            "times_in_top_k": hits,
            "n_resamples": n_resamples,
            "stability_pct": round(hits / n_resamples * 100, 1),
        }
        for (role_name, method, skill), hits in hit_counts.items()
    ]
    skill_stability_df = pd.DataFrame(stability_rows).sort_values(
        ["role_name", "method", "stability_pct"], ascending=[True, True, False]
    ).reset_index(drop=True)

    role_summary_df = (
        skill_stability_df.groupby(["role_name", "method"])["stability_pct"]
        .mean()
        .round(1)
        .reset_index(name="mean_top_k_stability_pct")
    )
    role_summary_df["n_resamples"] = n_resamples
    role_summary_df["top_k"] = top_k
    role_summary_df = role_summary_df[
        ["role_name", "method", "n_resamples", "top_k", "mean_top_k_stability_pct"]
    ]

    return skill_stability_df, role_summary_df

BOTH_COLUMN = "both_skills"


def add_both_method(role_df: pd.DataFrame, freq_df: pd.DataFrame):
    """Adds a third method, "both": a posting counts for a skill only when
    the lexical and semantic methods both found it in that same posting"""
    if not {"lexical_skills", "semantic_skills"} <= set(role_df.columns):
        return role_df, freq_df

    role_df = role_df.copy()
    role_df[BOTH_COLUMN] = [
        json.dumps(sorted(set(_parse_skill_list(lex)) & set(_parse_skill_list(sem))))
        for lex, sem in zip(role_df["lexical_skills"], role_df["semantic_skills"])
    ]

    long_df = _explode_skills(role_df, BOTH_COLUMN)
    counts = long_df.groupby(["role_name", "skill"]).size().reset_index(name="job_count")
    totals = role_df.groupby("role_name")["job_id"].count()
    counts["method"] = "both"
    counts["total_jobs_in_role"] = counts["role_name"].map(totals)
    counts["pct_of_role"] = (counts["job_count"] / counts["total_jobs_in_role"] * 100).round(1)

    base = freq_df[freq_df["method"] != "both"] if "method" in freq_df.columns else freq_df
    freq_df = pd.concat([base, counts[list(base.columns)]], ignore_index=True)
    return role_df, freq_df

# Orchestration: one call to produce everything the UI/CLI needs

def run_distinctiveness_analysis(
    role_df: pd.DataFrame,
    freq_df: pd.DataFrame,
    method_columns: dict | None = None,
    significance_level: float = DEFAULT_SIGNIFICANCE_LEVEL,
    n_resamples: int = DEFAULT_N_RESAMPLES,
    top_k: int = DEFAULT_TOP_K,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> dict:
    """Runs the full distinctiveness pipeline and returns all three
    result tables plus a short text report, ready for either the
    Streamlit tab or run_role_analysis.py to consume.
    """
    if method_columns is None:
        role_df, freq_df = add_both_method(role_df, freq_df)
        method_columns = dict(METHOD_COLUMNS)
        if BOTH_COLUMN in role_df.columns:
            method_columns["both"] = BOTH_COLUMN
    
    distinctiveness_df = compute_skill_distinctiveness(
        role_df, method_columns, significance_level
    )
    ranking_divergence_df = compare_rankings(distinctiveness_df, freq_df, top_k)
    stability_df, stability_summary_df = resample_distinctiveness_stability(
        role_df, method_columns, significance_level, n_resamples, top_k, random_state
    )

    n_pairs_tested = len(distinctiveness_df)
    n_distinctive = int(distinctiveness_df["distinctiveness_rank"].notna().sum())
    n_low_expected = int(distinctiveness_df["low_expected_frequency_warning"].sum())
    n_fisher = int((distinctiveness_df["test_used"] == "fisher_exact").sum())

    report_lines = [
        f"Skill-role pairs tested: {n_pairs_tested}",
        f"Pairs flagged as statistically distinctive (p < {significance_level}, over-represented): {n_distinctive}",
        f"Pairs with an expected-cell-count < 5 warning (chi-square validity assumption at risk): {n_low_expected}",
        f"Fisher's exact test used instead (expected cell counts < 5, per Cochran's rule): {n_fisher} pairs",
    ]
    if n_pairs_tested and n_low_expected / n_pairs_tested > 0.5:
        report_lines.append(
            "More than half of all pairs triggered the low-expected-frequency warning -- "
            "treat p-values as indicative only until the dataset is larger."
        )

    return {
        "distinctiveness": distinctiveness_df,
        "ranking_divergence": ranking_divergence_df,
        "stability": stability_df,
        "stability_summary": stability_summary_df,
        "report": "\n".join(report_lines),
    }

# Plain-language labels for the UI
# Pure presentation helpers: they turn the raw statistics produced above into
# wording a non-statistician can read. They never change any computed value,
# and the original numbers/names are always kept in brackets alongside.

STRONG_P_VALUE = 0.01
STABILITY_RELIABLE_PCT = 80.0
STABILITY_SOMEWHAT_PCT = 50.0
AGREEMENT_HIGH_RHO = 0.7
AGREEMENT_MEDIUM_RHO = 0.4

def _fmt_p(p_value) -> str:
    return f"{p_value:.4g}"

def distinctiveness_verdict(
    p_value,
    direction: str,
    significance_level: float = DEFAULT_SIGNIFICANCE_LEVEL,
    in_role_skill_count: int | None = None,
    in_role_job_count: int | None = None,
) -> str:
    """Plain-language verdict for one skill-role pair"""
    if p_value is None or pd.isna(p_value):
        return "Not enough data"
    evidence = []
    if in_role_skill_count is not None and in_role_job_count is not None:
        evidence.append(f"{int(in_role_skill_count)} of {int(in_role_job_count)} postings")
    evidence.append(f"p = {_fmt_p(p_value)}")
    suffix = f" ({', '.join(evidence)})"
    if p_value >= significance_level:
        return "Not distinctive" + suffix
    if direction == "under_represented":
        return "Less common here than elsewhere" + suffix
    if p_value < min(STRONG_P_VALUE, significance_level):
        return "Strongly distinctive" + suffix
    return "Distinctive" + suffix


def times_more_common(
    in_role_skill_count: int,
    in_role_job_count: int,
    other_roles_skill_count: int,
    other_roles_job_count: int,
) -> str:
    """How many times more common the skill is in this role than in all
    other roles combined."""
    in_rate = in_role_skill_count / in_role_job_count if in_role_job_count else 0.0
    other_rate = other_roles_skill_count / other_roles_job_count if other_roles_job_count else 0.0

    if in_rate == 0 and other_rate == 0:
        return "-"
    if other_rate == 0:
        return "Only appears in this role"
    if in_rate == 0:
        return "Never appears in this role"

    ratio = in_rate / other_rate
    if round(ratio, 1) == 1.0:
        return "About the same"
    if ratio > 1:
        return f"{ratio:.1f}x more common"
    return f"{1 / ratio:.1f}x less common"


def stability_label(stability_pct) -> str:
    """Reliable / Somewhat reliable / Unstable"""
    if stability_pct is None or pd.isna(stability_pct):
        return "-"
    if stability_pct >= STABILITY_RELIABLE_PCT:
        label = "Reliable"
    elif stability_pct >= STABILITY_SOMEWHAT_PCT:
        label = "Somewhat reliable"
    else:
        label = "Unstable"
    return f"{label} ({stability_pct}%)"


def agreement_label(spearman_rho) -> str:
    """How closely the distinctiveness ranking agrees with plain frequency
    counting. Low agreement means the test is surfacing something frequency counting alone misses."""
    if spearman_rho is None or pd.isna(spearman_rho):
        return "Not enough data"
    if spearman_rho >= AGREEMENT_HIGH_RHO:
        label = "High agreement"
    elif spearman_rho >= AGREEMENT_MEDIUM_RHO:
        label = "Medium agreement"
    else:
        label = "Low agreement"
    return f"{label} (ρ = {spearman_rho})"