"""Job-level provenance for research scopes and reviewed publication."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


# The bundled forecast fixture uses a reserved example.com URL namespace.
# Recognize it even on legacy read-only databases and re-imported CSV files.
SYNTHETIC_FIXTURE_PREFIX = "https://example.com/synthetic-temporal-test/"
DATA_PROVENANCE = ("unreviewed", "empirical", "synthetic")


def job_provenance(row: Mapping) -> str:
    for field in ("source_url", "job_url", "url"):
        if str(row.get(field, "")).strip().casefold().startswith(SYNTHETIC_FIXTURE_PREFIX):
            return "synthetic"
    declared = str(row.get("data_provenance", "")).strip().casefold()
    return declared if declared in DATA_PROVENANCE else "unreviewed"


def provenance_series(jobs: pd.DataFrame) -> pd.Series:
    return pd.Series(
        [job_provenance(row) for row in jobs.to_dict("records")],
        index=jobs.index,
        dtype="string",
    )


def exclude_synthetic_jobs(jobs: pd.DataFrame) -> pd.DataFrame:
    return jobs.loc[provenance_series(jobs).ne("synthetic")].copy()
