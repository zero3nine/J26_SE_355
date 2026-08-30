from __future__ import annotations

from itertools import combinations

import pandas as pd


def extract_frequent_stacks(
    jobs: pd.DataFrame,
    minimum_support: float = 0.10,
    maximum_stack_size: int = 4,
) -> pd.DataFrame:
    """
    Find frequently occurring skill combinations.

    This identifies recurring technology ecosystems.
    """

    total_jobs = len(jobs)

    if total_jobs == 0:
        return pd.DataFrame(
            columns=[
                "stack",
                "stack_size",
                "job_count",
                "support",
            ]
        )

    combination_counts: dict[tuple[str, ...], int] = {}

    for skills in jobs["skills"]:

        unique_skills = sorted(set(skills))

        if len(unique_skills) < 2:
            continue

        max_size = min(
            len(unique_skills),
            maximum_stack_size,
        )

        for size in range(2, max_size + 1):

            for combination in combinations(
                unique_skills,
                size,
            ):
                combination_counts[combination] = (
                    combination_counts.get(
                        combination,
                        0,
                    )
                    + 1
                )

    rows = []

    for stack, count in combination_counts.items():

        support = count / total_jobs

        if support < minimum_support:
            continue

        rows.append(
            {
                "stack": " + ".join(stack),
                "stack_size": len(stack),
                "job_count": count,
                "support": support,
            }
        )

    result = pd.DataFrame(rows)

    if result.empty:
        return pd.DataFrame(
            columns=[
                "stack",
                "stack_size",
                "job_count",
                "support",
            ]
        )

    return result.sort_values(
        ["stack_size", "job_count"],
        ascending=[False, False],
    ).reset_index(drop=True)