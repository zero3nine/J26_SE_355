from __future__ import annotations

import pandas as pd


def build_relationship_table(
    pair_frequency: pd.DataFrame,
    jaccard: pd.DataFrame,
    pmi: pd.DataFrame,
) -> pd.DataFrame:

    if pair_frequency.empty:
        return pd.DataFrame(
            columns=[
                "skill_a",
                "skill_b",
                "pair_count",
                "jaccard",
                "pmi",
                "relationship_strength",
            ]
        )

    result = pair_frequency.merge(
        jaccard[
            [
                "skill_a",
                "skill_b",
                "jaccard",
            ]
        ],
        on=[
            "skill_a",
            "skill_b",
        ],
        how="left",
    )

    result = result.merge(
        pmi[
            [
                "skill_a",
                "skill_b",
                "pmi",
            ]
        ],
        on=[
            "skill_a",
            "skill_b",
        ],
        how="left",
    )

    result["jaccard"] = result["jaccard"].fillna(0.0)
    result["pmi"] = result["pmi"].fillna(0.0)

    result["relationship_strength"] = (
        result["jaccard"] * result["pmi"].clip(lower=0)
    )

    result["relationship_strength"] = (
        result["relationship_strength"].round(6)
    )

    return (
        result.sort_values(
            [
                "relationship_strength",
                "pair_count",
            ],
            ascending=[False, False],
        )
        .reset_index(drop=True)
    )