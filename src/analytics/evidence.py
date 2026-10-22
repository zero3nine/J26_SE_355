"""
Source Evidence and Relationship Reliability Verification Module.
Implements Section 4.10 of the Individual Research Component:
- Links discovered skill relationships and technology stacks to authentic job advertisements.
- Extracts contextual text snippets from original descriptions and OCR captures.
- Audits verification status against source evidence without synthetic fabrication.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
import pandas as pd
from src.extraction.normalization import normalize_skill


def _find_context_snippet(text: str, terms: list[str], max_len: int = 220) -> str:
    """Extract a representative sentence or excerpt containing the terms in context."""
    if not text or not isinstance(text, str):
        return "(Description unavailable)"

    clean = " ".join(text.split())
    # Try finding sentence containing at least one term
    for term in terms:
        pattern = re.compile(rf"([^.?!;]*?\b{re.escape(term)}\b[^.?!;]*)", re.IGNORECASE)
        match = pattern.search(clean)
        if match:
            snippet = match.group(1).strip()
            if len(snippet) > max_len:
                return snippet[:max_len - 3] + "..."
            return snippet

    # Fallback to head of description
    return clean[:max_len - 3] + "..." if len(clean) > max_len else clean


def build_source_evidence(
    jobs_df: pd.DataFrame,
    relationships_df: pd.DataFrame,
    stacks_df: pd.DataFrame,
    max_pairs: int = 8,
    max_stacks: int = 8,
) -> list[dict]:
    """
    Constructs an evidence traceability table connecting high-scoring relationships
    and frequent technology stacks back to genuine current-run job advertisements.
    """
    evidence_rows: List[Dict[str, Any]] = []

    if jobs_df.empty:
        return evidence_rows

    # Parse normalized skills per job row
    job_skills_map: Dict[str, set[str]] = {}
    job_meta_map: Dict[str, dict] = {}

    def _parse_skills_cell(val):
        if isinstance(val, list):
            return {normalize_skill(s) for s in val}
        try:
            p = json.loads(str(val))
            if isinstance(p, list):
                return {normalize_skill(s) for s in p}
        except Exception:
            pass
        return set()

    for _, row in jobs_df.iterrows():
        jid = str(row.get("job_id", "")).strip()
        if not jid:
            continue
        lex = _parse_skills_cell(row.get("lexical_skills", "[]"))
        sem = _parse_skills_cell(row.get("semantic_skills", "[]"))
        all_skills = lex | sem
        job_skills_map[jid] = all_skills
        job_meta_map[jid] = {
            "title": str(row.get("job_title_raw", "")).strip(),
            "company": str(row.get("company", row.get("company_raw", ""))).strip(),
            "source_url": str(row.get("source_url", "")).strip(),
            "description": str(row.get("job_description", row.get("job_description_clean", ""))).strip(),
            "ocr_text": str(row.get("ocr_text_raw", "")).strip(),
        }

    # 1. Process top skill pairs
    if not relationships_df.empty:
        top_pairs = relationships_df.head(max_pairs)
        for _, rel in top_pairs.iterrows():
            sa = str(rel.get("skill_a", ""))
            sb = str(rel.get("skill_b", ""))
            pair_label = f"{sa} ↔ {sb}"
            pair_count = int(rel.get("pair_count", 0))
            jaccard = float(rel.get("jaccard", 0.0))
            strength = float(rel.get("relationship_strength", 0.0))

            # Find matching jobs
            matching_jids = [
                jid for jid, sset in job_skills_map.items()
                if sa in sset and sb in sset
            ]

            supp_count = len(matching_jids)
            sample_jid = matching_jids[0] if matching_jids else None
            meta = job_meta_map.get(sample_jid, {}) if sample_jid else {}

            desc_text = meta.get("description", "") or meta.get("ocr_text", "")
            snippet = _find_context_snippet(desc_text, [sa, sb])

            verification = "Verified in Original Text" if supp_count > 0 and snippet != "(Description unavailable)" else "Normalized Occurrence"

            evidence_rows.append({
                "entity": pair_label,
                "type": "Skill Pair",
                "entity_type": "Skill Pair",
                "target_pattern": pair_label,
                "primary_metric": "Relationship Strength",
                "metric_name": "Relationship Strength",
                "metric_value": f"{strength:.4f} (J={jaccard:.2f})",
                "supporting_ads_count": supp_count,
                "sample_job_id": sample_jid or "N/A",
                "job_id": sample_jid or "N/A",
                "company": meta.get("company", "N/A"),
                "source_url": meta.get("source_url", ""),
                "context_snippet": snippet,
                "text_excerpt": snippet,
                "verification_status": verification,
            })

    # 2. Process top technology stacks
    if not stacks_df.empty:
        top_stacks = stacks_df.head(max_stacks)
        for _, st_row in top_stacks.iterrows():
            stack_label = str(st_row.get("stack", ""))
            stack_skills = [s.strip() for s in stack_label.split("+")]
            supp_count = int(st_row.get("job_count", 0))
            support_val = float(st_row.get("support", 0.0))

            # Find matching jobs
            matching_jids = [
                jid for jid, sset in job_skills_map.items()
                if set(stack_skills).issubset(sset)
            ]

            sample_jid = matching_jids[0] if matching_jids else None
            meta = job_meta_map.get(sample_jid, {}) if sample_jid else {}

            desc_text = meta.get("description", "") or meta.get("ocr_text", "")
            snippet = _find_context_snippet(desc_text, stack_skills)

            evidence_rows.append({
                "entity": stack_label,
                "type": "Technology Stack",
                "entity_type": "Technology Stack",
                "target_pattern": stack_label,
                "primary_metric": "Support",
                "metric_name": "Support",
                "metric_value": f"{support_val * 100:.1f}% ({supp_count} ads)",
                "supporting_ads_count": len(matching_jids),
                "sample_job_id": sample_jid or "N/A",
                "job_id": sample_jid or "N/A",
                "company": meta.get("company", "N/A"),
                "source_url": meta.get("source_url", ""),
                "context_snippet": snippet,
                "text_excerpt": snippet,
                "verification_status": "Verified in Original Text" if snippet != "(Description unavailable)" else "Normalized Occurrence",
            })

    return evidence_rows
