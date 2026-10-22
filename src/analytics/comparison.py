"""
Cross-Method Extraction Comparison Module.
Implements Section 4.9 and Section 5 of the Individual Research Component:
- Compares Lexical, Semantic, and Combined extraction methods on the same population.
- Computes skill overlap, Venn intersections, rank shifts, and stack stability.
- Evaluates relationship consistency across extraction paradigms.
- Discloses ground-truth evaluation status transparently.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import pandas as pd


def compare_extraction_methods(
    run_dir: Path,
    jobs_df: pd.DataFrame,
) -> dict:
    """
    Load outputs from lexical_skills, semantic_skills, and combined subdirectories
    under run_dir and generate comparative metrics.
    """
    total_postings = len(jobs_df)
    methods = ["lexical_skills", "semantic_skills", "combined"]
    data: Dict[str, Dict[str, Any]] = {}

    for m in methods:
        m_dir = run_dir / m
        freq_file = m_dir / "skill_frequency.csv"
        pairs_file = m_dir / "skill_pairs.csv"
        stacks_file = m_dir / "technology_stacks.csv"
        rules_file = m_dir / "association_rules.csv"
        edges_file = m_dir / "skill_network_edges.csv"

        df_freq = pd.read_csv(freq_file) if freq_file.exists() else pd.DataFrame()
        df_pairs = pd.read_csv(pairs_file) if pairs_file.exists() else pd.DataFrame()
        df_stacks = pd.read_csv(stacks_file) if stacks_file.exists() else pd.DataFrame()
        df_rules = pd.read_csv(rules_file) if rules_file.exists() else pd.DataFrame()
        df_edges = pd.read_csv(edges_file) if edges_file.exists() else pd.DataFrame()

        skills_set = set(df_freq["skill"].tolist()) if not df_freq.empty and "skill" in df_freq.columns else set()
        pairs_set = {
            f"{row['skill_a']} + {row['skill_b']}"
            for _, row in df_pairs.iterrows()
        } if not df_pairs.empty and "skill_a" in df_pairs.columns else set()

        stacks_set = set(df_stacks["stack"].tolist()) if not df_stacks.empty and "stack" in df_stacks.columns else set()

        data[m] = {
            "df_freq": df_freq,
            "df_pairs": df_pairs,
            "df_stacks": df_stacks,
            "df_rules": df_rules,
            "df_edges": df_edges,
            "skills": skills_set,
            "pairs": pairs_set,
            "stacks": stacks_set,
            "unique_skills_count": len(skills_set),
            "pair_count": len(pairs_set),
            "stack_count": len(stacks_set),
            "rule_count": len(df_rules),
            "edge_count": len(df_edges),
        }

    s_lex = data["lexical_skills"]["skills"]
    s_sem = data["semantic_skills"]["skills"]
    s_comb = data["combined"]["skills"]

    common_all_skills = sorted(s_lex & s_sem & s_comb)
    lexical_only_skills = sorted(s_lex - s_sem)
    semantic_only_skills = sorted(s_sem - s_lex)

    # Technology stack stability across methods
    st_lex = data["lexical_skills"]["stacks"]
    st_sem = data["semantic_skills"]["stacks"]
    st_comb = data["combined"]["stacks"]

    stable_stacks = sorted(st_lex & st_sem & st_comb)
    lex_only_stacks = sorted(st_lex - st_sem)
    sem_only_stacks = sorted(st_sem - st_lex)
    comb_only_stacks = sorted(st_comb - (st_lex | st_sem))

    # Skill pairs stability
    p_lex = data["lexical_skills"]["pairs"]
    p_sem = data["semantic_skills"]["pairs"]
    p_comb = data["combined"]["pairs"]

    consistent_pairs = sorted(p_lex & p_sem & p_comb)
    lex_only_pairs = sorted(p_lex - p_sem)
    sem_only_pairs = sorted(p_sem - p_lex)

    # Top skill rank comparison table
    df_comb_freq = data["combined"]["df_freq"]
    top_comb_skills = df_comb_freq["skill"].head(15).tolist() if not df_comb_freq.empty and "skill" in df_comb_freq.columns else []

    lex_rank_map = {s: i + 1 for i, s in enumerate(data["lexical_skills"]["df_freq"]["skill"].tolist())} if not data["lexical_skills"]["df_freq"].empty else {}
    sem_rank_map = {s: i + 1 for i, s in enumerate(data["semantic_skills"]["df_freq"]["skill"].tolist())} if not data["semantic_skills"]["df_freq"].empty else {}

    rank_shifts: List[Dict[str, Any]] = []
    for rank_c, skill in enumerate(top_comb_skills, 1):
        r_lex = lex_rank_map.get(skill, "N/A")
        r_sem = sem_rank_map.get(skill, "N/A")
        rank_shifts.append({
            "skill": skill,
            "rank_combined": rank_c,
            "rank_lexical": r_lex,
            "rank_semantic": r_sem,
            "found_in_lexical": skill in s_lex,
            "found_in_semantic": skill in s_sem,
        })

    # Summary table across methods
    method_metrics = [
        {
            "method": "Lexical Extraction",
            "unique_skills": data["lexical_skills"]["unique_skills_count"],
            "skill_pairs": data["lexical_skills"]["pair_count"],
            "association_rules": data["lexical_skills"]["rule_count"],
            "technology_stacks": data["lexical_skills"]["stack_count"],
            "network_edges": data["lexical_skills"]["edge_count"],
            "ground_truth_f1": "Unavailable (No Human Annotation)",
        },
        {
            "method": "Semantic Extraction",
            "unique_skills": data["semantic_skills"]["unique_skills_count"],
            "skill_pairs": data["semantic_skills"]["pair_count"],
            "association_rules": data["semantic_skills"]["rule_count"],
            "technology_stacks": data["semantic_skills"]["stack_count"],
            "network_edges": data["semantic_skills"]["edge_count"],
            "ground_truth_f1": "Unavailable (No Human Annotation)",
        },
        {
            "method": "Combined Extraction",
            "unique_skills": data["combined"]["unique_skills_count"],
            "skill_pairs": data["combined"]["pair_count"],
            "association_rules": data["combined"]["rule_count"],
            "technology_stacks": data["combined"]["stack_count"],
            "network_edges": data["combined"]["edge_count"],
            "ground_truth_f1": "Unavailable (No Human Annotation)",
        },
    ]

    overlap_dict = {
        "total_lexical_unique": len(s_lex),
        "total_semantic_unique": len(s_sem),
        "total_combined_unique": len(s_comb),
        "common_to_all_three": common_all_skills,
        "concordant_all_3": common_all_skills,
        "lexical_only": lexical_only_skills,
        "semantic_only": semantic_only_skills,
        "combined_total": sorted(s_comb),
    }

    stability_dict = {
        "stable_stacks": stable_stacks,
        "stable_across_all_3": stable_stacks,
        "lexical_only_stacks": lex_only_stacks,
        "lexical_only": lex_only_stacks,
        "semantic_only_stacks": sem_only_stacks,
        "semantic_only": sem_only_stacks,
        "combined_emergent_stacks": comb_only_stacks,
    }

    disclaimer_text = (
        "Academic Disclosure: In the absence of independently double-annotated ground-truth "
        "test sets, precision, recall, and F1 scores are reported as unavailable. "
        "To calculate rigorous F1 scores, a stratified gold-standard sample of Sri Lankan IT job "
        "advertisements must be manually coded by independent domain experts and measured against "
        "the extraction outputs."
    )

    return {
        "method_metrics": method_metrics,
        "skill_overlap": overlap_dict,
        "venn_skill_breakdown": overlap_dict,
        "relationship_overlap": {
            "consistent_pairs": consistent_pairs,
            "lexical_only_pairs": lex_only_pairs,
            "semantic_only_pairs": sem_only_pairs,
        },
        "technology_stack_stability": stability_dict,
        "rank_shifts": rank_shifts,
        "top_skill_rank_shifts": rank_shifts,
        "evaluation_disclaimer": disclaimer_text,
        "ground_truth_evaluation": disclaimer_text,
    }
