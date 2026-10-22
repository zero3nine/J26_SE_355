from __future__ import annotations

import argparse
import ast
import json
import math
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "jobs_extracted.csv"
DEFAULT_ANALYSIS_DIR = PROJECT_ROOT / "data" / "analysis"

FREQ_FILE = "role_skill_frequencies.csv"      
FREQ_FILE_CLI = "role_skill_demand.csv"       
DISTINCT_FILE = "skill_distinctiveness.csv"
DIVERGENCE_FILE = "ranking_divergence.csv"
STABILITY_FILE = "distinctiveness_stability.csv"
STABILITY_SUMMARY_FILE = "distinctiveness_stability_summary.csv"

P_TOL = 1e-6          
CHI2_TOL = 1e-4       
PCT_TOL = 0.0501      
SPEARMAN_TOL = 1e-3   
COCHRAN_MIN_EXPECTED = 5.0

def _isnull(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value)) or value is pd.NA

def _close(a, b, tol) -> bool:
    if _isnull(a) and _isnull(b):
        return True
    if _isnull(a) or _isnull(b):
        return False
    if math.isinf(a) or math.isinf(b):
        return a == b
    return abs(float(a) - float(b)) <= tol

def _to_bool(value) -> bool:
    return str(value).strip().lower() in ("true", "1", "1.0")

def _parse_skills(cell) -> list:
    """Skills in a JSON-list cell, as plain strings; anything unreadable -> []."""
    if not isinstance(cell, str) or not cell.strip():
        return []
    try:
        parsed = json.loads(cell)
    except (ValueError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(s) for s in parsed if isinstance(s, str) and s != ""]

def _parse_list_cell(cell) -> list:
    """A stored Python-list string such as "['a', 'b']" -> ['a', 'b']."""
    if _isnull(cell):
        return []
    if isinstance(cell, list):
        return cell
    try:
        value = ast.literal_eval(str(cell))
        return list(value) if isinstance(value, (list, tuple, set)) else []
    except (ValueError, SyntaxError):
        return []

def _read_output(path: Path) -> pd.DataFrame | None:
    """Read an output CSV so that only truly blank cells are missing values"""
    if not path.exists():
        return None
    try:
        return pd.read_csv(path, keep_default_na=False, na_values=[""])
    except pd.errors.EmptyDataError:
        return pd.DataFrame()

def hand_expected_cells(a: int, b: int, c: int, d: int):
    n = a + b + c + d
    r1, r2, c1, c2 = a + b, c + d, a + c, b + d
    if n == 0:
        return [[0.0, 0.0], [0.0, 0.0]]
    return [[r1 * c1 / n, r1 * c2 / n], [r2 * c1 / n, r2 * c2 / n]]

def hand_yates_chi_square(a: int, b: int, c: int, d: int):
    observed = [[a, b], [c, d]]
    expected = hand_expected_cells(a, b, c, d)
    stat = 0.0
    for i in range(2):
        for j in range(2):
            diff = abs(observed[i][j] - expected[i][j])
            corrected = diff - min(0.5, diff)
            stat += corrected * corrected / expected[i][j]
    return stat, math.erfc(math.sqrt(stat / 2.0))


def hand_fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p-value: the total probability of every table
    (with the same row and column totals) that is no more likely than the one
    observed, using the hypergeometric distribution."""
    r1, r2, c1 = a + b, c + d, a + c
    n = r1 + r2
    denominator = math.comb(n, c1)

    def pmf(x: int) -> float:
        return math.comb(r1, x) * math.comb(r2, c1 - x) / denominator

    observed = pmf(a)
    low, high = max(0, c1 - r2), min(r1, c1)
    total = sum(pmf(x) for x in range(low, high + 1) if pmf(x) <= observed * (1 + 1e-7))
    return min(1.0, total)


def hand_test(a: int, b: int, c: int, d: int):
    r1, r2 = a + b, c + d
    expected = hand_expected_cells(a, b, c, d)
    low_expected = any(cell < COCHRAN_MIN_EXPECTED for row in expected for cell in row)
    if (r1 + r2) == 0 or r1 == 0 or r2 == 0:
        return "none", float("nan"), None, low_expected
    if low_expected:
        return "fisher_exact", hand_fisher_two_sided(a, b, c, d), None, low_expected
    stat, p = hand_yates_chi_square(a, b, c, d)
    return "chi_square", p, stat, low_expected

# Check recorder

class _Recorder:
    def __init__(self):
        self.rows = []

    def check(self, group, file, role, skill, method, field, expected, actual, ok, note=""):
        self.rows.append({
            "group": group, "file": file, "role": role, "skill": skill,
            "method": method, "field": field,
            "expected": expected, "actual": actual,
            "status": "PASS" if ok else "FAIL", "note": note,
        })

    def equal(self, group, file, role, skill, method, field, expected, actual, tol=None, note=""):
        if tol is None:
            ok = (_isnull(expected) and _isnull(actual)) or (expected == actual)
        else:
            ok = _close(expected, actual, tol)
        self.check(group, file, role, skill, method, field, expected, actual, ok, note)

# Independent recount from the input postings

def _recount(role_df: pd.DataFrame):
    """From the input postings only, build everything the output should contain."""
    jobs_by_role: dict = {}
    for job_id, role in zip(role_df["job_id"], role_df["role_name"]):
        jobs_by_role.setdefault(role, set()).add(job_id)
    all_jobs = set(role_df["job_id"])

    lex, sem = {}, {}
    if "lexical_skills" in role_df.columns:
        lex = {j: set(_parse_skills(c)) for j, c in zip(role_df["job_id"], role_df["lexical_skills"])}
    if "semantic_skills" in role_df.columns:
        sem = {j: set(_parse_skills(c)) for j, c in zip(role_df["job_id"], role_df["semantic_skills"])}

    per_job = {}
    if lex:
        per_job["lexical"] = lex
    if sem:
        per_job["semantic"] = sem
    if lex and sem:
        # "Confirmed by both methods": a posting counts only if BOTH found it there.
        per_job["both"] = {j: lex[j] & sem[j] for j in lex}

    role_of = dict(zip(role_df["job_id"], role_df["role_name"]))
    per_method = {}
    for method, job_skills in per_job.items():
        skill_jobs, role_skills = {}, {}
        for job_id, skills in job_skills.items():
            for skill in skills:
                skill_jobs.setdefault(skill, set()).add(job_id)
                role_skills.setdefault(role_of[job_id], set()).add(skill)
        per_method[method] = {"skill_jobs": skill_jobs, "role_skills": role_skills}
    return jobs_by_role, all_jobs, per_method

def _expected_tables(role_df):
    """Expected 2x2 counts for every (role, skill, method) the role mentions."""
    jobs_by_role, all_jobs, per_method = _recount(role_df)
    expected = {}
    for method, info in per_method.items():
        for role, skills in info["role_skills"].items():
            role_jobs = jobs_by_role[role]
            other_jobs = all_jobs - role_jobs
            for skill in skills:
                has = info["skill_jobs"][skill]
                a = len(role_jobs & has)
                b = len(role_jobs) - a
                c = len(other_jobs & has)
                d = len(other_jobs) - c
                expected[(role, skill, method)] = (a, b, c, d)
    return expected, jobs_by_role, per_method

# Check groups

def _audit_input(rec, role_df):
    g = "0 Input preconditions"
    for col in ("job_id", "role_name"):
        rec.check(g, "input", "-", "-", "-", f"column {col}", "present",
                  "present" if col in role_df.columns else "missing", col in role_df.columns)
    if "job_id" in role_df.columns:
        dupes = int(role_df["job_id"].duplicated().sum())
        rec.check(g, "input", "-", "-", "-", "job_id unique", 0, dupes, dupes == 0,
                  "duplicate job_ids would make counts ambiguous")

def _audit_frequency(rec, freq_out, role_df, expected_tables, jobs_by_role, f=FREQ_FILE):
    g = "1 Demand counts and percentages"
    if freq_out is None or freq_out.empty:
        rec.check(g, f, "-", "-", "-", "file", "present and non-empty", "missing or empty", False)
        return
    expected = {}
    for (role, skill, method), (a, b, c, d) in expected_tables.items():
        if method in ("lexical", "semantic"):
            expected[(role, skill, method)] = (a, len(jobs_by_role[role]))

    seen = set()
    for _, row in freq_out.iterrows():
        key = (row["role_name"], row["skill"], row["method"])
        if key in seen:
            rec.check(g, f, *key, "row unique", "once", "duplicate", False)
            continue
        seen.add(key)
        if key not in expected:
            rec.check(g, f, *key, "row exists in recount", "no such row", "unexpected row", False)
            continue
        count, total = expected[key]
        rec.equal(g, f, *key, "job_count", count, int(row["job_count"]))
        rec.equal(g, f, *key, "total_jobs_in_role", total, int(row["total_jobs_in_role"]))
        rec.equal(g, f, *key, "pct_of_role", round(count / total * 100, 1), row["pct_of_role"], tol=PCT_TOL)
    for key in expected:
        if key not in seen:
            rec.check(g, f, *key, "row present", "row expected", "row missing", False)

def _audit_distinctiveness(rec, dist, expected_tables, significance_level):
    g = "2 Statistical calculations"
    f = DISTINCT_FILE
    if dist is None or dist.empty:
        rec.check(g, f, "-", "-", "-", "file", "present and non-empty", "missing or empty",
                  len(expected_tables) == 0, "empty is only valid if no skills were extracted")
        return

    seen = set()
    for _, row in dist.iterrows():
        role, skill, method = row["role_name"], row["skill"], row["method"]
        key = (role, skill, method)
        if key in seen:
            rec.check(g, f, *key, "row unique", "once", "duplicate", False)
            continue
        seen.add(key)
        if key not in expected_tables:
            rec.check(g, f, *key, "row exists in recount", "no such row", "unexpected row", False)
            continue

        a, b, c, d = expected_tables[key]
        r1, r2 = a + b, c + d
        # 2a. contingency counts and percentages recounted from the postings
        rec.equal(g, f, *key, "in_role_job_count", r1, int(row["in_role_job_count"]))
        rec.equal(g, f, *key, "in_role_skill_count", a, int(row["in_role_skill_count"]))
        rec.equal(g, f, *key, "other_roles_job_count", r2, int(row["other_roles_job_count"]))
        rec.equal(g, f, *key, "other_roles_skill_count", c, int(row["other_roles_skill_count"]))
        in_rate = a / r1 if r1 else 0.0
        other_rate = c / r2 if r2 else 0.0
        rec.equal(g, f, *key, "in_role_pct", round(in_rate * 100, 1), row["in_role_pct"], tol=PCT_TOL)
        rec.equal(g, f, *key, "other_roles_pct", round(other_rate * 100, 1), row["other_roles_pct"], tol=PCT_TOL)
        rec.equal(g, f, *key, "direction",
                  "over_represented" if in_rate > other_rate else "under_represented", row["direction"])

        # 2b. test choice (Cochran's rule) and p-value, from the hand formulas
        test, p, chi2, low = hand_test(a, b, c, d)
        rec.equal(g, f, *key, "test_used", test, row["test_used"])
        rec.equal(g, f, *key, "low_expected_frequency_warning", low,
                  _to_bool(row["low_expected_frequency_warning"]))
        rec.equal(g, f, *key, "p_value", p, row["p_value"], tol=P_TOL)
        if test == "chi_square":
            rec.equal(g, f, *key, "chi2_statistic", chi2, row["chi2_statistic"], tol=CHI2_TOL)
        else:
            rec.check(g, f, *key, "chi2_statistic", "blank", row["chi2_statistic"], _isnull(row["chi2_statistic"]))
        if not _isnull(row["p_value"]):
            rec.check(g, f, *key, "p_value in [0,1]", "0 <= p <= 1", row["p_value"],
                      0.0 <= float(row["p_value"]) <= 1.0)
        # 2c. significance flag follows the stated threshold
        expected_sig = (not math.isnan(p)) and p < significance_level
        rec.equal(g, f, *key, "significant", expected_sig, _to_bool(row["significant"]),
                  note=f"threshold p < {significance_level}")

    for key in expected_tables:
        if key not in seen:
            rec.check(g, f, *key, "row present", "row expected", "row missing", False)


def _audit_rank_invariants(rec, dist):
    g = "3 Ranking invariants"
    f = DISTINCT_FILE
    if dist is None or dist.empty:
        return
    # A skill is ranked exactly when it is significant AND over-represented.
    for _, row in dist.iterrows():
        key = (row["role_name"], row["skill"], row["method"])
        should_rank = _to_bool(row["significant"]) and row["direction"] == "over_represented"
        has_rank = not _isnull(row["distinctiveness_rank"])
        rec.equal(g, f, *key, "distinctiveness_rank assigned", should_rank, has_rank,
                  note="ranked <=> significant and over-represented")
    # Within each role and method: ranks are 1..n with no gaps, best p-value first.
    for (role, method), group in dist.groupby(["role_name", "method"]):
        ranked = group.dropna(subset=["distinctiveness_rank"]).sort_values("distinctiveness_rank")
        n = len(ranked)
        got = [int(r) for r in ranked["distinctiveness_rank"]]
        rec.equal(g, f, role, "(all ranked skills)", method, "ranks are 1..n", list(range(1, n + 1)), got)
        pvals = [float(p) for p in ranked["p_value"]]
        ordered = all(pvals[i] <= pvals[i + 1] + 1e-12 for i in range(len(pvals) - 1))
        rec.check(g, f, role, "(all ranked skills)", method, "rank order follows p-value",
                  "p non-decreasing with rank", pvals, ordered)
    # "Confirmed by both methods" can never exceed either single method.
    index = {(r["role_name"], r["skill"], r["method"]): r for _, r in dist.iterrows()}
    for (role, skill, method), row in index.items():
        if method != "both":
            continue
        for other in ("lexical", "semantic"):
            o = index.get((role, skill, other))
            if o is None:
                rec.check(g, f, role, skill, "both", f"both <= {other}", f"{other} row exists",
                          "missing", False)
                continue
            rec.check(g, f, role, skill, "both", f"in_role_skill_count <= {other}",
                      f"<= {int(o['in_role_skill_count'])}", int(row["in_role_skill_count"]),
                      int(row["in_role_skill_count"]) <= int(o["in_role_skill_count"]))


def _audit_divergence(rec, div, dist, expected_tables, jobs_by_role):
    g = "4 Frequency-baseline comparison"
    f = DIVERGENCE_FILE
    if div is None:
        rec.check(g, f, "-", "-", "-", "file", "present", "missing", False)
        return
    # frequency counts per (role, method) recounted, including the 'both' method
    freq_counts = {}
    for (role, skill, method), (a, b, c, d) in expected_tables.items():
        freq_counts.setdefault((role, method), {})[skill] = a

    seen = set()
    for _, row in div.iterrows():
        role, method, k = row["role_name"], row["method"], int(row["top_k"])
        key = (role, method)
        seen.add(key)
        counts = freq_counts.get(key)
        if counts is None:
            rec.check(g, f, role, "-", method, "row exists in recount", "no such role/method",
                      "unexpected row", False)
            continue
        dgroup = dist[(dist["role_name"] == role) & (dist["method"] == method)] if dist is not None else pd.DataFrame()
        # skills compared = skills that received a p-value
        n_with_p = int(dgroup["p_value"].notna().sum()) if not dgroup.empty else 0
        rec.equal(g, f, role, "-", method, "skills_compared", n_with_p, int(row["skills_compared"]))
        # frequency top-K: the listed skills must carry the K largest counts (tie-safe)
        listed_freq = _parse_list_cell(row["frequency_top_k"])
        want = sorted(counts.values(), reverse=True)[:k]
        got = sorted((counts.get(s, -1) for s in listed_freq), reverse=True)
        rec.equal(g, f, role, "-", method, "frequency_top_k counts", want, got)
        # distinctiveness top-K: skills holding rank 1..K in the distinctiveness output
        listed_dist = _parse_list_cell(row["distinctiveness_top_k"])
        ranked = dgroup.dropna(subset=["distinctiveness_rank"]) if not dgroup.empty else dgroup
        want_dist = sorted(ranked[ranked["distinctiveness_rank"] <= k]["skill"]) if not ranked.empty else []
        rec.equal(g, f, role, "-", method, "distinctiveness_top_k", want_dist, sorted(listed_dist))
        overlap = len(set(listed_freq) & set(listed_dist))
        rec.equal(g, f, role, "-", method, "top_k_overlap_count", overlap, int(row["top_k_overlap_count"]))
        rec.equal(g, f, role, "-", method, "top_k_overlap_pct", round(overlap / k * 100, 1),
                  row["top_k_overlap_pct"], tol=PCT_TOL)
        rho = row["spearman_rho"]
        if int(row["skills_compared"]) < 2:
            rec.check(g, f, role, "-", method, "spearman_rho", "blank (fewer than 2 skills)", rho, _isnull(rho))
        elif not _isnull(rho):
            rec.check(g, f, role, "-", method, "spearman_rho in [-1,1]", "-1 <= rho <= 1", rho,
                      -1.0 - SPEARMAN_TOL <= float(rho) <= 1.0 + SPEARMAN_TOL)
    for key in freq_counts:
        if key not in seen:
            rec.check(g, f, key[0], "-", key[1], "row present", "row expected", "row missing", False)

def _audit_stability(rec, stab, summary, dist, div):
    g = "5 Stability table consistency"
    fs, fsum = STABILITY_FILE, STABILITY_SUMMARY_FILE
    if stab is None or summary is None:
        rec.check(g, fs, "-", "-", "-", "file", "present", "missing", False)
        return
    top_k = int(div["top_k"].iloc[0]) if (div is not None and not div.empty) else None
    # which skills should be tracked
    expected_keys = set()
    if dist is not None and not dist.empty and top_k is not None:
        ranked = dist.dropna(subset=["distinctiveness_rank"])
        for _, r in ranked[ranked["distinctiveness_rank"] <= top_k].iterrows():
            expected_keys.add((r["role_name"], r["method"], r["skill"]))

    seen = set()
    n_values = set()
    for _, row in stab.iterrows():
        key = (row["role_name"], row["method"], row["skill"])
        role, method, skill = key
        seen.add(key)
        n = int(row["n_resamples"])
        times = int(row["times_in_top_k"])
        n_values.add(n)
        rec.check(g, fs, role, skill, method, "skill is in original top-K",
                  "in original ranked top-K", "present" if key in expected_keys else "absent",
                  key in expected_keys)
        rec.check(g, fs, role, skill, method, "0 <= times_in_top_k <= n_resamples",
                  f"0..{n}", times, 0 <= times <= n)
        rec.equal(g, fs, role, skill, method, "stability_pct", round(times / n * 100, 1),
                  row["stability_pct"], tol=PCT_TOL)
    for key in expected_keys:
        if key not in seen:
            rec.check(g, fs, key[0], key[2], key[1], "row present", "row expected", "row missing", False)
    rec.check(g, fs, "-", "-", "-", "same n_resamples on every row", "one value",
              sorted(n_values), len(n_values) <= 1)

    # summary = mean of the per-skill stability values, per role and method
    for _, srow in summary.iterrows():
        role, method = srow["role_name"], srow["method"]
        sub = stab[(stab["role_name"] == role) & (stab["method"] == method)]
        if sub.empty:
            rec.check(g, fsum, role, "-", method, "mean_top_k_stability_pct", "skills exist", "none", False)
            continue
        rec.equal(g, fsum, role, "-", method, "mean_top_k_stability_pct",
                  round(float(sub["stability_pct"].mean()), 1), srow["mean_top_k_stability_pct"], tol=PCT_TOL)
        rec.equal(g, fsum, role, "-", method, "n_resamples", int(sub["n_resamples"].iloc[0]), int(srow["n_resamples"]))
        if top_k is not None:
            rec.equal(g, fsum, role, "-", method, "top_k", top_k, int(srow["top_k"]))
    summary_keys = {(r["role_name"], r["method"]) for _, r in summary.iterrows()}
    for (role, method) in {(k[0], k[1]) for k in seen}:
        if (role, method) not in summary_keys:
            rec.check(g, fsum, role, "-", method, "row present", "row expected", "row missing", False)

def _frames_match(rec, group, file, expected_df, actual_df, keys, label_cols=("role_name", "skill", "method")):
    """Compare a regenerated table with the stored one, cell by cell."""
    if expected_df is None or actual_df is None:
        rec.check(group, file, "-", "-", "-", "table", "present", "missing", False)
        return
    exp = expected_df.copy()
    act = actual_df.copy()
    for col in keys:
        exp[col] = exp[col].astype(str)
        act[col] = act[col].astype(str)
    merged = exp.merge(act, on=keys, how="outer", suffixes=("__exp", "__act"), indicator=True)
    value_cols = [c for c in exp.columns if c not in keys and c in act.columns]

    def label(row):
        parts = {c: row.get(c, "-") for c in label_cols}
        return parts.get("role_name", "-"), parts.get("skill", "-"), parts.get("method", "-")

    for _, row in merged.iterrows():
        role, skill, method = label(row)
        if row["_merge"] != "both":
            rec.check(group, file, role, skill, method, "row present in both runs", "both",
                      row["_merge"], False)
            continue
        for col in value_cols:
            e, a = row[f"{col}__exp"], row[f"{col}__act"]
            if isinstance(e, (list, tuple)) or isinstance(a, (list, tuple)):
                ok = str(list(e)) == str(a if not isinstance(a, (list, tuple)) else list(a))
            elif isinstance(e, (int, float, bool)) and not isinstance(e, str) and not _isnull(e) and not _isnull(a):
                try:
                    ok = _close(float(e), float(a), 1e-6)
                except (TypeError, ValueError):
                    ok = str(e) == str(a)
            else:
                ok = (_isnull(e) and _isnull(a)) or str(e) == str(a)
            rec.check(group, file, role, skill, method, col, e, a, ok)

def _audit_reproducibility(rec, role_df, outputs, significance_level, seed, freq_name=FREQ_FILE):
    g = "6 Reproducibility (re-run, same seed)"
    from src.roles.distinctiveness import run_distinctiveness_analysis
    from src.roles.role_skill_analysis import build_role_skill_frequency_table

    div = outputs["div"]
    stab_summary = outputs["stab_summary"]
    if div is None or div.empty:
        rec.check(g, "-", "-", "-", "-", "re-run", "output to compare", "no divergence output", False)
        return
    top_k = int(div["top_k"].iloc[0])
    if stab_summary is not None and not stab_summary.empty:
        n_resamples = int(stab_summary["n_resamples"].iloc[0])
    elif outputs["stab"] is not None and not outputs["stab"].empty:
        n_resamples = int(outputs["stab"]["n_resamples"].iloc[0])
    else:
        from src.roles.distinctiveness import DEFAULT_N_RESAMPLES
        n_resamples = DEFAULT_N_RESAMPLES

    freq_df = build_role_skill_frequency_table(role_df)
    result = run_distinctiveness_analysis(
        role_df, freq_df, significance_level=significance_level,
        n_resamples=n_resamples, top_k=top_k, random_state=seed,
    )
    _frames_match(rec, g, freq_name, freq_df, outputs["freq"], ["role_name", "skill", "method"])
    _frames_match(rec, g, DISTINCT_FILE, result["distinctiveness"], outputs["dist"],
                  ["role_name", "skill", "method"])
    _frames_match(rec, g, DIVERGENCE_FILE, result["ranking_divergence"], outputs["div"],
                  ["role_name", "method"])
    _frames_match(rec, g, STABILITY_FILE, result["stability"], outputs["stab"],
                  ["role_name", "skill", "method"])
    _frames_match(rec, g, STABILITY_SUMMARY_FILE, result["stability_summary"], outputs["stab_summary"],
                  ["role_name", "method"])

# Public entry points

def run_audit(
    role_df: pd.DataFrame,
    analysis_dir: Path = DEFAULT_ANALYSIS_DIR,
    significance_level: float = 0.05,
    seed: int = 42,
    check_reproducibility: bool = True,
) -> dict:
    """Audit the output files in analysis_dir against role_df (the role-classified
    input postings). Returns {"checks": DataFrame, "summary": dict, "text": str}."""
    analysis_dir = Path(analysis_dir)
    rec = _Recorder()
    _audit_input(rec, role_df)

    # The page and the command-line tool name the frequency table differently.
    freq_name = FREQ_FILE if (analysis_dir / FREQ_FILE).exists() or not (analysis_dir / FREQ_FILE_CLI).exists() else FREQ_FILE_CLI
    outputs = {
        "freq": _read_output(analysis_dir / freq_name),
        "dist": _read_output(analysis_dir / DISTINCT_FILE),
        "div": _read_output(analysis_dir / DIVERGENCE_FILE),
        "stab": _read_output(analysis_dir / STABILITY_FILE),
        "stab_summary": _read_output(analysis_dir / STABILITY_SUMMARY_FILE),
    }
    missing = [name for name, df in outputs.items() if df is None]
    inputs_ok = {"job_id", "role_name"} <= set(role_df.columns)

    if missing or not inputs_ok:
        for name in missing:
            rec.check("0 Input preconditions", name, "-", "-", "-", "output file", "present", "missing", False)
    else:
        expected_tables, jobs_by_role, _ = _expected_tables(role_df)
        _audit_frequency(rec, outputs["freq"], role_df, expected_tables, jobs_by_role, freq_name)
        _audit_distinctiveness(rec, outputs["dist"], expected_tables, significance_level)
        _audit_rank_invariants(rec, outputs["dist"])
        _audit_divergence(rec, outputs["div"], outputs["dist"], expected_tables, jobs_by_role)
        _audit_stability(rec, outputs["stab"], outputs["stab_summary"], outputs["dist"], outputs["div"])
        if check_reproducibility:
            _audit_reproducibility(rec, role_df, outputs, significance_level, seed, freq_name)

    checks = pd.DataFrame(rec.rows)
    summary = _summarise(checks, outputs, len(role_df))
    return {"checks": checks, "summary": summary, "text": _render_text(checks, summary)}

def _summarise(checks: pd.DataFrame, outputs: dict, n_postings: int) -> dict:
    executed = len(checks)
    failed = int((checks["status"] == "FAIL").sum()) if executed else 0
    by_group = []
    if executed:
        for group, sub in checks.groupby("group"):
            by_group.append({
                "group": group, "executed": len(sub),
                "failed": int((sub["status"] == "FAIL").sum()),
            })
    records = {
        name: (0 if df is None else len(df)) for name, df in outputs.items()
    }
    return {
        "input_postings": n_postings,
        "output_rows": records,
        "output_rows_total": sum(records.values()),
        "checks_executed": executed,
        "checks_failed": failed,
        "passed": executed > 0 and failed == 0,
        "by_group": by_group,
    }

def _render_text(checks: pd.DataFrame, summary: dict, max_failures: int = 25) -> str:
    lines = [
        "AUTOMATED OUTPUT AUDIT - role skill demand and distinctiveness",
        "=" * 64,
        f"Input postings audited : {summary['input_postings']}",
        f"Output rows audited : {summary['output_rows_total']}  {summary['output_rows']}",
        f"Checks executed : {summary['checks_executed']}",
        f"Checks failed : {summary['checks_failed']}",
        f"RESULT : {'PASS' if summary['passed'] else 'FAIL'}",
        "",
        "By check group:",
    ]
    for item in summary["by_group"]:
        status = "ok  " if item["failed"] == 0 else "FAIL"
        lines.append(f"  [{status}] {item['group']}: {item['executed']} checks, {item['failed']} failed")
    failures = checks[checks["status"] == "FAIL"] if len(checks) else checks
    if len(failures):
        lines += ["", f"Failures (first {min(max_failures, len(failures))} of {len(failures)}):"]
        for _, f in failures.head(max_failures).iterrows():
            lines.append(
                f"  - {f['file']} | role={f['role']} | skill={f['skill']} | method={f['method']} | "
                f"field={f['field']} | expected={f['expected']} | actual={f['actual']}"
            )
    lines += [
        "",
        "Scope: this audit verifies the output against the input postings and the",
        "documented formulas. It does not verify the extracted skills or the role",
        "assignments themselves. Group 6 re-runs the pipeline and shows consistency only.",
    ]
    return "\n".join(lines)

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Audit the role-skill analysis output files.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--significance", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-reproducibility", action="store_true")
    args = parser.parse_args(argv)

    from src.roles.role_skill_analysis import classify_roles

    if not args.input.exists():
        print(f"Input file not found: {args.input}")
        return 2
    role_df = classify_roles(pd.read_csv(args.input))
    result = run_audit(
        role_df, args.analysis_dir, args.significance, args.seed,
        check_reproducibility=not args.skip_reproducibility,
    )
    args.analysis_dir.mkdir(parents=True, exist_ok=True)
    result["checks"].to_csv(args.analysis_dir / "audit_report.csv", index=False, encoding="utf-8")
    (args.analysis_dir / "audit_summary.txt").write_text(result["text"], encoding="utf-8")
    print(result["text"])
    print(f"\nFull check list written to {args.analysis_dir / 'audit_report.csv'}")
    return 0 if result["summary"]["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())