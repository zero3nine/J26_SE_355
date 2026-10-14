import json

import pandas as pd
import pytest
from scipy.stats import chi2_contingency, fisher_exact

from src.roles import distinctiveness as D
from src.roles import role_skill_analysis as R

def make_jobs(spec):
    """Build a postings dataframe from a compact description."""
    rows = []
    for role, lexical, semantic, how_many in spec:
        for _ in range(how_many):
            rows.append({
                "job_id": f"job_{len(rows)}",
                "role_name": role,
                "lexical_skills": json.dumps(lexical),
                "semantic_skills": json.dumps(semantic),
            })
    return pd.DataFrame(rows)


def same_skills(role, skills, how_many):
    """Shortcut: lexical and semantic found exactly the same skills."""
    return (role, skills, skills, how_many)


def pick(result, role, skill, method="lexical"):
    """Pull a single (role, skill, method) row out of a results table."""
    rows = result[(result.role_name == role) & (result.skill == skill) & (result.method == method)]
    assert len(rows) == 1, f"expected exactly one row for {role}/{skill}/{method}, got {len(rows)}"
    return rows.iloc[0]


@pytest.fixture
def big():
    """A dataset big enough for the chi-square test to be valid."""
    return make_jobs([
        same_skills("A", ["python", "git"], 30),
        same_skills("A", ["git"], 10),
        same_skills("B", ["java", "git"], 30),
        same_skills("B", ["git"], 10),
    ])

# 1. The statistical test itself

def test_large_sample_uses_chi_square_and_matches_scipy(big):
    result = D.compute_skill_distinctiveness(big)
    row = pick(result, "A", "python")

    expected_p = chi2_contingency([[30, 10], [0, 40]], correction=True)[1]

    assert row.test_used == "chi_square"
    assert row.p_value == pytest.approx(expected_p, abs=1e-6)
    assert row.significant
    assert row.direction == "over_represented"

def test_small_sample_falls_back_to_fisher_and_matches_scipy():
    jobs = make_jobs([
        same_skills("A", ["x"], 3),
        same_skills("B", ["x"], 1),
        same_skills("B", [], 4),
    ])
    row = pick(D.compute_skill_distinctiveness(jobs), "A", "x")

    assert row.test_used == "fisher_exact"
    assert row.low_expected_frequency_warning
    assert row.p_value == pytest.approx(fisher_exact([[3, 0], [1, 4]])[1], abs=1e-6)

def test_five_postings_can_never_reach_significance():
    # With only 5 postings in total the smallest p-value which can be produced is 0.10, so nothing can be < 0.05.
    # This is why a tiny dataset shows no distinctive skills.
    tiny = make_jobs([
        same_skills("A", ["x"], 2),
        same_skills("B", ["y"], 1),
        same_skills("B", [], 2),
    ])
    result = D.compute_skill_distinctiveness(tiny)
    assert (result.test_used == "fisher_exact").all()
    assert not result.significant.any()
    assert result.p_value.min() >= 0.10 - 1e-9


def test_skill_found_everywhere_is_not_distinctive(big):
    row = pick(D.compute_skill_distinctiveness(big), "A", "git")
    assert not row.significant
    assert pd.isna(row.distinctiveness_rank)


def test_significance_level_is_respected():
    jobs = make_jobs([
        same_skills("A", ["x"], 10), same_skills("A", [], 10),
        same_skills("B", ["x"], 3), same_skills("B", [], 17),
    ])
    assert pick(D.compute_skill_distinctiveness(jobs, significance_level=0.05), "A", "x").significant
    assert not pick(D.compute_skill_distinctiveness(jobs, significance_level=0.01), "A", "x").significant


def test_missing_role_column_gives_a_clear_error(big):
    with pytest.raises(ValueError, match="role_name"):
        D.compute_skill_distinctiveness(big.drop(columns="role_name"))


def test_messy_skill_cells_do_not_crash(big):
    big.loc[0, "lexical_skills"] = None
    big.loc[1, "lexical_skills"] = "not json at all"
    big.loc[2, "lexical_skills"] = '"just a string, not a list"'
    big.loc[3, "semantic_skills"] = ""
    result = D.compute_skill_distinctiveness(big)
    assert not result.empty

# 2. Ranking rules

def test_only_significant_over_represented_skills_get_a_rank(big):
    result = D.compute_skill_distinctiveness(big)
    ranked = result.dropna(subset=["distinctiveness_rank"])

    assert not ranked.empty
    assert ranked.significant.all()
    assert (ranked.direction == "over_represented").all()

def test_ranks_are_ordered_by_p_value_within_each_role_and_method():
    # A has two distinctive skills; python (30/40) should beat sql (20/40) because it is the stronger signal.
    jobs = make_jobs([
        same_skills("A", ["python", "sql"], 20),
        same_skills("A", ["python"], 10),
        same_skills("A", [], 10),
        same_skills("B", [], 40),
    ])
    result = D.compute_skill_distinctiveness(jobs)
    top = result[(result.role_name == "A") & (result.method == "lexical")].dropna(
        subset=["distinctiveness_rank"]
    ).sort_values("distinctiveness_rank")

    assert list(top.skill) == ["python", "sql"]
    assert list(top.distinctiveness_rank) == [1, 2]


def test_under_represented_skill_is_never_ranked_even_if_significant():
    # java is common in B and rare in A. For role A that is a significant
    # difference, but in the wrong direction, so it must not be called a
    # distinctive skill of A.
    jobs = make_jobs([
        same_skills("A", ["java"], 2),
        same_skills("A", [], 38),
        same_skills("B", ["java"], 38),
        same_skills("B", [], 2),
    ])
    row = pick(D.compute_skill_distinctiveness(jobs), "A", "java")
    assert row.significant
    assert row.direction == "under_represented"
    assert pd.isna(row.distinctiveness_rank)

# 3. Comparison with the plain frequency baseline

def test_ranking_comparison_spots_the_disagreement(big):
    # For role A, plain frequency says: git (40) first, python (30) second.
    # The distinctiveness test says python is the interesting one and git is
    # noise. So the two rankings should be perfectly opposite (rho = -1) and
    # only "python" should be shared in the top-K.
    distinct = D.compute_skill_distinctiveness(big)
    freq = R.build_role_skill_frequency_table(big)
    comparison = D.compare_rankings(distinct, freq, top_k=5)

    row = comparison[(comparison.role_name == "A") & (comparison.method == "lexical")].iloc[0]
    assert row.spearman_rho == pytest.approx(-1.0)
    assert row.skills_compared == 2
    assert row.frequency_top_k == ["git", "python"]
    assert row.distinctiveness_top_k == ["python"]
    assert row.top_k_overlap_count == 1
    assert row.top_k_overlap_pct == 20.0     

# 4. Bootstrap stability

def test_strong_signal_is_stable_under_resampling(big):
    stability, summary = D.resample_distinctiveness_stability(big, n_resamples=15)

    row = stability[(stability.role_name == "A") & (stability.method == "lexical") & (stability.skill == "python")].iloc[0]
    assert row.stability_pct == 100.0
    assert row.times_in_top_k == 15
    assert row.n_resamples == 15

    s = summary[(summary.role_name == "A") & (summary.method == "lexical")].iloc[0]
    assert s.mean_top_k_stability_pct == 100.0


def test_same_seed_gives_identical_results(big):
    first, _ = D.resample_distinctiveness_stability(big, n_resamples=10, random_state=42)
    second, _ = D.resample_distinctiveness_stability(big, n_resamples=10, random_state=42)
    pd.testing.assert_frame_equal(first, second)


def test_stability_returns_empty_tables_when_nothing_is_distinctive():
    tiny = make_jobs([same_skills("A", ["x"], 2), same_skills("B", [], 3)])
    stability, summary = D.resample_distinctiveness_stability(tiny, n_resamples=5)
    assert stability.empty and summary.empty
    assert "stability_pct" in stability.columns

# 5. Confirmed by both methods

def test_both_method_keeps_only_skills_found_by_lexical_and_semantic_in_the_same_posting():
    jobs = make_jobs([
        ("A", ["python", "git"], ["python", "aws"], 4), # agree on python only
        ("B", ["java"], ["go"], 4), # agree on nothing
    ])
    freq = R.build_role_skill_frequency_table(jobs)
    jobs_out, freq_out = D.add_both_method(jobs, freq)

    assert json.loads(jobs_out.loc[0, D.BOTH_COLUMN]) == ["python"]
    assert json.loads(jobs_out.loc[5, D.BOTH_COLUMN]) == []

    both_rows = freq_out[freq_out.method == "both"]
    assert list(both_rows.skill) == ["python"]
    assert both_rows.iloc[0].job_count == 4


def test_both_method_is_a_per_posting_intersection_not_a_union_of_totals():
    # Lexical finds python in posting 1, semantic finds python in posting 2.
    # Neither posting has BOTH methods agreeing, so both must find nothing,
    # even though each method found python once overall.
    jobs = pd.DataFrame([
        {"job_id": "p1", "role_name": "A", "lexical_skills": '["python"]', "semantic_skills": "[]"},
        {"job_id": "p2", "role_name": "A", "lexical_skills": "[]", "semantic_skills": '["python"]'},
    ])
    out, freq = D.add_both_method(jobs, R.build_role_skill_frequency_table(jobs))
    assert (freq.method == "both").sum() == 0

# 6. End-to-end tests

def test_full_run_returns_every_table_and_includes_all_three_methods(big):
    freq = R.build_role_skill_frequency_table(big)
    out = D.run_distinctiveness_analysis(big, freq, n_resamples=5)

    assert set(out) == {"distinctiveness", "ranking_divergence", "stability", "stability_summary", "report"}
    assert set(out["distinctiveness"].method) == {"lexical", "semantic", "both"}


def test_report_numbers_match_the_tables(big):
    freq = R.build_role_skill_frequency_table(big)
    out = D.run_distinctiveness_analysis(big, freq, n_resamples=5)
    table = out["distinctiveness"]

    assert f"Skill-role pairs tested: {len(table)}" in out["report"]
    assert f"over-represented): {int(table.distinctiveness_rank.notna().sum())}" in out["report"]
    assert f"{int((table.test_used == 'fisher_exact').sum())} pairs" in out["report"]

# 7. Plain-language labels

def test_verdict_wording_for_each_situation():
    assert D.distinctiveness_verdict(0.005, "over_represented", 0.05, 3, 4) == "Strongly distinctive (3 of 4 postings, p = 0.005)"
    assert D.distinctiveness_verdict(0.03, "over_represented").startswith("Distinctive")
    assert D.distinctiveness_verdict(0.30, "over_represented").startswith("Not distinctive")
    assert D.distinctiveness_verdict(0.001, "under_represented").startswith("Less common here")
    assert D.distinctiveness_verdict(float("nan"), "over_represented") == "Not enough data"
    assert D.distinctiveness_verdict(None, "over_represented") == "Not enough data"

# 8. Skills-by-roles matrix

@pytest.fixture
def matrix_jobs():
    """A small dataset with two roles and a few skills, for testing the matrix builder."""
    return pd.DataFrame([
        {"job_id": "1", "role_name": "DevOps", "lexical_skills": '["docker","aws"]', "semantic_skills": '["docker","k8s"]'},
        {"job_id": "2", "role_name": "DevOps", "lexical_skills": '["docker"]', "semantic_skills": '["docker"]'},
        {"job_id": "3", "role_name": "Backend", "lexical_skills": '["python"]', "semantic_skills": '["python","sql"]'},
        {"job_id": "4", "role_name": "Backend", "lexical_skills": '["sql"]', "semantic_skills": "[]"},
    ])


def test_matrix_both_requires_agreement_inside_the_same_posting(matrix_jobs):
    m = R.build_role_skill_matrix(matrix_jobs, "both")
    assert m.loc["docker", "DevOps"] == 2
    assert m.loc["python", "Backend"] == 1
    assert "sql" not in m.index