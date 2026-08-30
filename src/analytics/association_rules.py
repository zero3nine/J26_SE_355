from __future__ import annotations

import pandas as pd


def calculate_association_rules(
    jobs: pd.DataFrame,
    minimum_support: float = 0.05,
) -> pd.DataFrame:
    """
    Generate pairwise association rules.

    For A -> B:

    support    = P(A and B)
    confidence = P(A and B) / P(A)
    lift       = confidence / P(B)
    """

    total_jobs = len(jobs)

    if total_jobs == 0:
        return pd.DataFrame()

    skill_counts: dict[str, int] = {}
    pair_counts: dict[tuple[str, str], int] = {}

    for skills in jobs["skills"]:
        unique_skills = sorted(set(skills))

        for skill in unique_skills:
            skill_counts[skill] = (
                skill_counts.get(skill, 0) + 1
            )

        for i, skill_a in enumerate(unique_skills):
            for skill_b in unique_skills[i + 1:]:
                pair = (skill_a, skill_b)

                pair_counts[pair] = (
                    pair_counts.get(pair, 0) + 1
                )

    rows = []

    for (skill_a, skill_b), pair_count in pair_counts.items():

        support = pair_count / total_jobs

        if support < minimum_support:
            continue

        p_a = skill_counts[skill_a] / total_jobs
        p_b = skill_counts[skill_b] / total_jobs

        confidence_a_to_b = support / p_a
        confidence_b_to_a = support / p_b

        lift_a_to_b = (
            confidence_a_to_b / p_b
            if p_b > 0
            else 0
        )

        lift_b_to_a = (
            confidence_b_to_a / p_a
            if p_a > 0
            else 0
        )

        rows.append(
            {
                "antecedent": skill_a,
                "consequent": skill_b,
                "pair_count": pair_count,
                "support": support,
                "confidence": confidence_a_to_b,
                "lift": lift_a_to_b,
            }
        )

        rows.append(
            {
                "antecedent": skill_b,
                "consequent": skill_a,
                "pair_count": pair_count,
                "support": support,
                "confidence": confidence_b_to_a,
                "lift": lift_b_to_a,
            }
        )

    result = pd.DataFrame(rows)

    if result.empty:
        return pd.DataFrame(
            columns=[
                "antecedent",
                "consequent",
                "pair_count",
                "support",
                "confidence",
                "lift",
            ]
        )

    return result.sort_values(
        ["lift", "confidence"],
        ascending=False,
    ).reset_index(drop=True)