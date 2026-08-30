from __future__ import annotations

from collections import Counter
from itertools import combinations

import pandas as pd


def calculate_pair_frequency(
    jobs: list[set[str]],
) -> pd.DataFrame:

    pair_counts: Counter[tuple[str, str]] = Counter()

    for skills in jobs:
        unique_skills = sorted(set(skills))

        for skill_a, skill_b in combinations(unique_skills, 2):
            pair_counts[(skill_a, skill_b)] += 1

    rows = []

    for (skill_a, skill_b), frequency in pair_counts.items():
        rows.append(
            {
                "skill_a": skill_a,
                "skill_b": skill_b,
                "frequency": frequency,
            }
        )

    columns = [
        "skill_a",
        "skill_b",
        "frequency",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    return (
        pd.DataFrame(rows)
        .sort_values(
            ["frequency", "skill_a", "skill_b"],
            ascending=[False, True, True],
        )
        .reset_index(drop=True)
    )


def calculate_cooccurrence_matrix(
    jobs: list[set[str]],
) -> pd.DataFrame:

    skills = sorted(
        {
            skill
            for job in jobs
            for skill in job
        }
    )

    matrix = pd.DataFrame(
        0,
        index=skills,
        columns=skills,
        dtype=int,
    )

    for job in jobs:
        unique_skills = sorted(set(job))

        for skill_a, skill_b in combinations(unique_skills, 2):
            matrix.loc[skill_a, skill_b] += 1
            matrix.loc[skill_b, skill_a] += 1

        for skill in unique_skills:
            matrix.loc[skill, skill] += 1

    return matrix