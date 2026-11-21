"""Trace skill pairs and technology stacks to their supporting advertisements."""
from __future__ import annotations

import json
import re

import pandas as pd

from src.analytics.run_analysis import load_jobs, parse_skills
from src.extraction.normalization import normalize_skill_set


def _term_match(text: str, term: str) -> re.Match | None:
    # Preserve punctuation in names such as C++, C#, and .NET.
    return re.search(rf"(?<!\w){re.escape(term)}(?![\w+#])", text, re.IGNORECASE)


def _find_context_snippet(text: str, terms: list[str], max_len: int = 220) -> str:
    """Return an excerpt around the matching terms, or the start of the text."""
    if not isinstance(text, str) or not text.strip():
        return "(Description unavailable)"

    clean = " ".join(text.split())
    if len(clean) <= max_len:
        return clean

    matches = [match for term in terms if (match := _term_match(clean, term))]
    begin = min((match.start() for match in matches), default=0)
    end = max((match.end() for match in matches), default=0)
    excerpt_length = max_len - 6
    start = max(0, begin - max(0, (excerpt_length - (end - begin)) // 2))
    stop = start + excerpt_length
    return ("..." if start else "") + clean[start:stop] + ("..." if stop < len(clean) else "")


def load_evidence_jobs(jobs_df: pd.DataFrame, skill_mode: str) -> list[dict]:
    """Associate each source row with the very same normalized skills used in the analysis."""
    if jobs_df.empty:
        return []
    skill_sets, _ = load_jobs(jobs_df, skill_mode=skill_mode, include_jobs_without_skills=True)
    return [row | {"skills": skills} for row, skills in zip(jobs_df.to_dict("records"), skill_sets)]


def source_excerpt(job: dict, terms: list[str], skill_mode: str, max_len: int = 220) -> tuple[str, str]:
    """Return source text and state whether every skill is visible in the excerpt."""
    excerpts = [
        _find_context_snippet(job[field], terms, max_len)
        for field in ("job_description", "job_description_clean", "requirements", "ocr_text_raw")
        if isinstance(job.get(field), str) and job[field].strip()
    ]
    for excerpt in excerpts:
        if terms and all(_term_match(excerpt, term) for term in terms):
            return excerpt, "Verified in Original Text"

    excerpt = excerpts[0] if excerpts else "(Description unavailable)"
    if skill_mode == "semantic_skills" or (
        skill_mode == "combined"
        and not set(terms).issubset(normalize_skill_set(parse_skills(job.get("lexical_skills")), fallback_to_title=True))
    ):
        return excerpt, "Inferred by semantic extraction"
    return excerpt, "Text match unverified"


def _evidence_record(
    jobs: list[dict], terms: list[str], label: str, entity_type: str,
    metric: str, value: str, skill_mode: str,
) -> dict:
    required = set(terms)
    matching = [job for job in jobs if required.issubset(job["skills"])] if required else []
    sample = {}
    snippet, verification = "(Description unavailable)", "Text match unverified"
    for index, job in enumerate(matching):
        excerpt, status = source_excerpt(job, terms, skill_mode)
        if index == 0 or status == "Verified in Original Text":
            sample, snippet, verification = job, excerpt, status
        if status == "Verified in Original Text":
            break

    sample_id = str(sample.get("job_id", "N/A"))
    return {
        "entity": label,
        "type": entity_type,
        "entity_type": entity_type,
        "target_pattern": label,
        "primary_metric": metric,
        "metric_name": metric,
        "metric_value": value,
        "supporting_ads_count": len(matching),
        "supporting_job_ids": [str(job["job_id"]) for job in matching],
        "sample_job_id": sample_id,
        "job_id": sample_id,
        "company": sample.get("company", sample.get("company_raw", "N/A")),
        "source_url": sample.get("source_url", ""),
        "context_snippet": snippet,
        "text_excerpt": snippet,
        "verification_status": verification,
    }


def build_source_evidence(
    jobs_df: pd.DataFrame,
    relationships_df: pd.DataFrame,
    stacks_df: pd.DataFrame,
    max_pairs: int = 8,
    max_stacks: int = 8,
    *,
    skill_mode: str = "combined",
) -> list[dict]:
    """Connect pairs and stacks to job rows in the selected analysis representation."""
    jobs = load_evidence_jobs(jobs_df, skill_mode)
    if not jobs:
        return []

    evidence = []
    for _, pair in relationships_df.head(max_pairs).iterrows():
        first, second = str(pair["skill_a"]), str(pair["skill_b"])
        value = f"{float(pair.get('relationship_strength', 0)):.4f} (J={float(pair.get('jaccard', 0)):.2f})"
        evidence.append(_evidence_record(
            jobs, [first, second], f"{first} ↔ {second}", "Skill Pair", "Relationship Strength", value, skill_mode,
        ))

    for _, stack in stacks_df.head(max_stacks).iterrows():
        name = str(stack["stack"])
        value = f"{float(stack.get('support', 0)) * 100:.1f}% ({int(stack.get('job_count', 0))} ads)"
        evidence.append(_evidence_record(
            jobs, name.split(" + "), name, "Technology Stack", "Support", value, skill_mode,
        ))
    return evidence


def source_evidence_csv(records: list[dict]) -> str:
    """Serialize supporting IDs and keep untrusted text literal in spreadsheet readers."""
    def literal_cell(value):
        if isinstance(value, str) and (value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(("=", "+", "-", "@"))):
            return "'" + value
        return value

    export = pd.DataFrame(records)
    export["supporting_job_ids"] = export["supporting_job_ids"].map(json.dumps)
    return export.map(literal_cell).to_csv(index=False)
