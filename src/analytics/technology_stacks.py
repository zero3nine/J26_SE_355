import json
from itertools import combinations
from typing import Any, Dict, List, Optional, Set

import pandas as pd


def extract_frequent_stacks(
    jobs: List[Set[str]],
    minimum_support: float = 0.10,
    maximum_stack_size: int = 4,
    job_records: Optional[List[Dict[str, Any]]] = None,
) -> pd.DataFrame:
    """
    Find frequently occurring skill combinations (2 to 4 skills) across jobs.
    Tracks supporting jobs to enable evidence drilldown and audits.
    """
    total_jobs = len(jobs)
    base_columns = ["stack", "stack_size", "job_count", "support", "supporting_jobs"]

    if total_jobs == 0:
        return pd.DataFrame(columns=base_columns)

    combination_counts: Dict[tuple[str, ...], int] = {}
    combination_job_indices: Dict[tuple[str, ...], List[int]] = {}

    for idx, skills in enumerate(jobs):
        unique_skills = sorted(set(skills))
        if len(unique_skills) < 2:
            continue

        max_size = min(len(unique_skills), maximum_stack_size)
        for size in range(2, max_size + 1):
            for combination in combinations(unique_skills, size):
                combination_counts[combination] = combination_counts.get(combination, 0) + 1
                if combination not in combination_job_indices:
                    combination_job_indices[combination] = []
                combination_job_indices[combination].append(idx)

    rows = []
    for stack, count in combination_counts.items():
        support = count / total_jobs
        if support < minimum_support:
            continue

        indices = combination_job_indices.get(stack, [])
        supporting_info = []
        if job_records:
            for i in indices:
                if 0 <= i < len(job_records):
                    rec = job_records[i]
                    supporting_info.append({
                        "job_id": str(rec.get("job_id", f"job_{i}")),
                        "title": str(rec.get("job_title_raw", "Unknown Title")),
                        "company": str(rec.get("company", "Unknown Company")),
                        "location": str(rec.get("location_raw", "Unknown Location")),
                    })

        rows.append({
            "stack": " + ".join(stack),
            "stack_size": len(stack),
            "job_count": count,
            "support": round(support, 6),
            "supporting_jobs": json.dumps(supporting_info, ensure_ascii=False) if supporting_info else "[]",
        })

    result = pd.DataFrame(rows)
    if result.empty:
        return pd.DataFrame(columns=base_columns)

    return result.sort_values(
        ["stack_size", "job_count"],
        ascending=[False, False],
    ).reset_index(drop=True)