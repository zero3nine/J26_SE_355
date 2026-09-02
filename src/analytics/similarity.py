from __future__ import annotations

from collections import Counter
from itertools import combinations

import pandas as pd


def calculate_jaccard(
    jobs: list[set[str]],
) -> pd.DataFrame:

    skills = sorted(
        {
            skill
            for job in jobs
            for skill in job
        }
    )

    rows = []

    skill_job_sets = {}

    for skill in skills:
        skill_job_sets[skill] = {
            index
            for index, job in enumerate(jobs)
            if skill in job
        }

    for skill_a, skill_b in combinations(skills, 2):

        set_a = skill_job_sets[skill_a]
        set_b = skill_job_sets[skill_b]

        intersection = len(set_a & set_b)
        union = len(set_a | set_b)

        if union == 0:
            jaccard = 0.0
        else:
            jaccard = intersection / union

        rows.append(
            {
                "skill_a": skill_a,
                "skill_b": skill_b,
                "intersection": intersection,
                "union": union,
                "jaccard": round(jaccard, 6),
            }
        )

    columns = [
        "skill_a",
        "skill_b",
        "intersection",
        "union",
        "jaccard",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    return (
        pd.DataFrame(rows)
        .sort_values(
            "jaccard",
            ascending=False,
        )
        .reset_index(drop=True)
    )


def calculate_pmi(
    jobs: list[set[str]],
) -> pd.DataFrame:

    total_jobs = len(jobs)

    if total_jobs == 0:
        return pd.DataFrame(
            columns=[
                "skill_a",
                "skill_b",
                "cooccurrence",
                "pmi",
            ]
        )

    skill_frequency: Counter[str] = Counter()
    pair_frequency: Counter[tuple[str, str]] = Counter()

    for job in jobs:

        unique_skills = sorted(set(job))

        for skill in unique_skills:
            skill_frequency[skill] += 1

        for skill_a, skill_b in combinations(
            unique_skills,
            2,
        ):
            pair_frequency[(skill_a, skill_b)] += 1

    rows = []

    for (skill_a, skill_b), pair_count in pair_frequency.items():

        probability_a = skill_frequency[skill_a] / total_jobs
        probability_b = skill_frequency[skill_b] / total_jobs
        probability_ab = pair_count / total_jobs

        expected = probability_a * probability_b

        if expected == 0:
            pmi = 0.0
        else:
            import math

            pmi = math.log2(
                probability_ab / expected
            )

        rows.append(
            {
                "skill_a": skill_a,
                "skill_b": skill_b,
                "cooccurrence": pair_count,
                "pmi": round(pmi, 6),
            }
        )

    columns = [
        "skill_a",
        "skill_b",
        "cooccurrence",
        "pmi",
    ]

    if not rows:
        return pd.DataFrame(columns=columns)

    return (
        pd.DataFrame(rows)
        .sort_values(
            "pmi",
            ascending=False,
        )
        .reset_index(drop=True)
    )