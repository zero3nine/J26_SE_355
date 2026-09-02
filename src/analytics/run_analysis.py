"""
Skill Relationship and Technology Stack Analysis
Research Component IT23321854

Entry point for the analytics pipeline. Consumes:
    data/processed/jobs_extracted.csv

Produces:
    data/analytics/<skill_mode>/skill_frequency.csv
    data/analytics/<skill_mode>/skill_pairs.csv
    data/analytics/<skill_mode>/cooccurrence_matrix.csv
    data/analytics/<skill_mode>/jaccard_similarity.csv
    data/analytics/<skill_mode>/pmi_scores.csv
    data/analytics/<skill_mode>/association_rules.csv
    data/analytics/<skill_mode>/skill_network_edges.csv
    data/analytics/<skill_mode>/technology_stacks.csv
    data/analytics/<skill_mode>/skill_relationships.csv

Usage:
    python3 -m src.analytics.run_analysis
    python3 -m src.analytics.run_analysis --skills lexical_skills
    python3 -m src.analytics.run_analysis --skills semantic_skills
    python3 -m src.analytics.run_analysis --skills combined
    python3 -m src.analytics.run_analysis --input path/to/jobs_extracted.csv --output path/to/output/dir
"""
from __future__ import annotations

import argparse
import ast
import json
import math
from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd

from src.analytics.cooccurrence import (
    calculate_cooccurrence_matrix,
    calculate_pair_frequency,
)
from src.analytics.network import (
    build_relationship_table,
)
from src.analytics.similarity import (
    calculate_jaccard,
    calculate_pmi,
)
from src.analytics.association_rules import (
    calculate_association_rules,
)
from src.analytics.technology_stacks import (
    extract_frequent_stacks,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "jobs_extracted.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "analytics"

SKILL_MODES = ("lexical_skills", "semantic_skills", "combined")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_skills(value) -> set[str]:
    """
    Parse a skills field value from jobs_extracted.csv into a set of strings.

    The extraction pipeline stores skills as JSON arrays: '["python", "java"]'
    Falls back to ast.literal_eval for Python-repr lists, then returns empty
    set if unparseable.
    """
    if isinstance(value, list):
        return {str(s).strip() for s in value if str(s).strip()}

    if pd.isna(value):
        return set()

    text = str(value).strip()
    if not text or text in ("[]", "nan", "None"):
        return set()

    # JSON path (primary format produced by run_extraction.py)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return {str(s).strip() for s in parsed if str(s).strip()}
    except json.JSONDecodeError:
        pass

    # Python repr fallback
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return {str(s).strip() for s in parsed if str(s).strip()}
    except (ValueError, SyntaxError):
        pass

    return set()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_jobs(
    input_path: Path,
    skill_mode: str = "combined",
) -> tuple[list[set[str]], dict]:
    """
    Load jobs_extracted.csv and return a list of skill sets plus a report dict.

    skill_mode: "lexical_skills" | "semantic_skills" | "combined"
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path)

    required = {"job_id", "lexical_skills", "semantic_skills"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    total_rows = len(df)
    has_lexical = 0
    has_semantic = 0
    jobs: list[set[str]] = []

    for _, row in df.iterrows():
        lexical = parse_skills(row["lexical_skills"])
        semantic = parse_skills(row["semantic_skills"])

        if lexical:
            has_lexical += 1
        if semantic:
            has_semantic += 1

        if skill_mode == "lexical_skills":
            skills = lexical
        elif skill_mode == "semantic_skills":
            skills = semantic
        else:  # combined
            skills = lexical | semantic

        if skills:
            jobs.append(skills)

    all_skills = {s for job in jobs for s in job}

    report = {
        "input_path": str(input_path),
        "total_rows_in_csv": total_rows,
        "skill_mode": skill_mode,
        "jobs_with_lexical_skills": has_lexical,
        "jobs_with_semantic_skills": has_semantic,
        "jobs_with_selected_skills": len(jobs),
        "unique_skills": len(all_skills),
    }

    return jobs, report


# ---------------------------------------------------------------------------
# Skill frequency (extra output not in existing modules)
# ---------------------------------------------------------------------------

def calculate_skill_frequency(jobs: list[set[str]]) -> pd.DataFrame:
    """
    Count how often each skill appears across job advertisements.
    Returns a DataFrame sorted by frequency descending.
    """
    counts: Counter[str] = Counter()
    total = len(jobs)

    for skills in jobs:
        for skill in skills:
            counts[skill] += 1

    rows = [
        {
            "skill": skill,
            "job_count": count,
            "frequency_pct": round(count / total * 100, 2) if total > 0 else 0.0,
        }
        for skill, count in counts.most_common()
    ]

    cols = ["skill", "job_count", "frequency_pct"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Network edges (extra output, derived from pair_frequency)
# ---------------------------------------------------------------------------

def build_network_edges(
    pair_frequency: pd.DataFrame,
    jaccard: pd.DataFrame,
    pmi: pd.DataFrame,
    minimum_frequency: int = 2,
) -> pd.DataFrame:
    """
    Build a weighted edge list for a skill co-occurrence network.

    Nodes  = individual skills
    Edges  = pairs of skills that co-occur in at least minimum_frequency jobs
    Weight = co-occurrence frequency (edge thickness proxy)
    Jaccard= similarity score (alternative weight)

    This table can be imported directly into Gephi, NetworkX, or D3.js.
    """
    if pair_frequency.empty:
        return pd.DataFrame(
            columns=["source_skill", "target_skill", "weight", "pair_count", "jaccard", "pmi"]
        )

    edges = pair_frequency[
        pair_frequency["pair_count"] >= minimum_frequency
    ].copy()

    if edges.empty:
        # Relax threshold when dataset is small
        edges = pair_frequency.copy()

    edges = edges.rename(
        columns={"skill_a": "source_skill", "skill_b": "target_skill", "pair_count": "weight"}
    )
    edges["pair_count"] = edges["weight"]

    if not jaccard.empty:
        jac_lookup = jaccard.set_index(["skill_a", "skill_b"])["jaccard"].to_dict()
        edges["jaccard"] = edges.apply(
            lambda r: jac_lookup.get((r["source_skill"], r["target_skill"]),
                      jac_lookup.get((r["target_skill"], r["source_skill"]), 0.0)),
            axis=1,
        )
    else:
        edges["jaccard"] = 0.0

    if not pmi.empty:
        pmi_lookup = pmi.set_index(["skill_a", "skill_b"])["pmi"].to_dict()
        edges["pmi"] = edges.apply(
            lambda r: pmi_lookup.get((r["source_skill"], r["target_skill"]),
                      pmi_lookup.get((r["target_skill"], r["source_skill"]), 0.0)),
            axis=1,
        )
    else:
        edges["pmi"] = 0.0

    return edges[["source_skill", "target_skill", "weight", "pair_count", "jaccard", "pmi"]].sort_values(
        "weight", ascending=False
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------------

def save_results(
    output_dir: Path,
    frequency: pd.DataFrame,
    matrix: pd.DataFrame,
    pair_frequency: pd.DataFrame,
    jaccard: pd.DataFrame,
    pmi: pd.DataFrame,
    relationships: pd.DataFrame,
    association: pd.DataFrame,
    stacks: pd.DataFrame,
    network_edges: pd.DataFrame,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    frequency.to_csv(output_dir / "skill_frequency.csv", index=False)
    matrix.to_csv(output_dir / "cooccurrence_matrix.csv")
    pair_frequency.to_csv(output_dir / "skill_pairs.csv", index=False)
    jaccard.to_csv(output_dir / "jaccard_similarity.csv", index=False)
    pmi.to_csv(output_dir / "pmi_scores.csv", index=False)
    relationships.to_csv(output_dir / "skill_relationships.csv", index=False)
    association.to_csv(output_dir / "association_rules.csv", index=False)
    stacks.to_csv(output_dir / "technology_stacks.csv", index=False)
    network_edges.to_csv(output_dir / "skill_network_edges.csv", index=False)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_analysis(
    input_path: Path,
    output_dir: Path,
    skill_mode: str = "combined",
) -> dict:
    """
    Run the complete skill relationship analysis pipeline.

    Returns a summary dict that callers (e.g. Streamlit app) can display.
    """
    print(f"\n{'='*60}")
    print(f"Skill Relationship Analysis — IT23321854")
    print(f"Input : {input_path}")
    print(f"Mode  : {skill_mode}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")

    # ------------------------------------------------------------------ load
    print("Loading extracted job data...")
    jobs, report = load_jobs(input_path, skill_mode=skill_mode)

    print(f"  Total rows in CSV      : {report['total_rows_in_csv']}")
    print(f"  Jobs with lexical skills : {report['jobs_with_lexical_skills']}")
    print(f"  Jobs with semantic skills: {report['jobs_with_semantic_skills']}")
    print(f"  Jobs with selected skills: {report['jobs_with_selected_skills']}")
    print(f"  Unique skills            : {report['unique_skills']}")

    # Determine the subdirectory for this skill mode
    mode_output = output_dir / skill_mode
    mode_output.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------- empty guard
    if not jobs:
        print()
        print("⚠️  No extracted skills found.")
        print("   This is a data availability issue, not an analytics bug.")
        print("   Cause: all job descriptions in jobs_extracted.csv contain")
        print("   only the TopJobs boilerplate ('Please refer the full details')")
        print("   which contains no technical skill terms.")
        print()
        print("   Resolution: Collect IT job postings from a text-based source")
        print("   (e.g. itpro.lk), re-run the cleaning and extraction pipeline,")
        print("   then re-run this analysis.")
        print()
        print("   Saving empty CSVs with correct schemas...")

        save_results(
            mode_output,
            frequency=pd.DataFrame(columns=["skill", "job_count", "frequency_pct"]),
            matrix=pd.DataFrame(),
            pair_frequency=pd.DataFrame(columns=["skill_a", "skill_b", "pair_count"]),
            jaccard=pd.DataFrame(columns=["skill_a", "skill_b", "intersection", "union", "jaccard"]),
            pmi=pd.DataFrame(columns=["skill_a", "skill_b", "cooccurrence", "pmi"]),
            relationships=pd.DataFrame(columns=["skill_a", "skill_b", "pair_count", "jaccard", "pmi", "relationship_strength"]),
            association=pd.DataFrame(columns=["antecedent", "consequent", "pair_count", "support", "confidence", "lift"]),
            stacks=pd.DataFrame(columns=["stack", "stack_size", "job_count", "support"]),
            network_edges=pd.DataFrame(columns=["source_skill", "target_skill", "weight", "pair_count", "jaccard", "pmi"]),
        )
        report["status"] = "insufficient_data"
        return report

    # ----------------------------------------------------------- analytics
    print("\nRunning analytics...")

    print("  [1/8] Skill frequency...")
    frequency = calculate_skill_frequency(jobs)

    print("  [2/8] Co-occurrence matrix...")
    matrix = calculate_cooccurrence_matrix(jobs)

    print("  [3/8] Skill pair frequency...")
    pair_frequency = calculate_pair_frequency(jobs)

    print("  [4/8] Jaccard similarity...")
    jaccard = calculate_jaccard(jobs)

    print("  [5/8] PMI scores...")
    pmi = calculate_pmi(jobs)

    print("  [6/8] Skill relationship table...")
    relationships = build_relationship_table(pair_frequency, jaccard, pmi)

    print("  [7/8] Association rules...")
    # Lower minimum support for small datasets (floor at 2 co-occurrences)
    min_support = max(0.01, 2.0 / len(jobs))
    association = calculate_association_rules(jobs, minimum_support=min_support)

    print("  [8/8] Technology stacks...")
    min_stack_support = max(0.05, 2.0 / len(jobs))
    stacks = extract_frequent_stacks(jobs, minimum_support=min_stack_support)

    print("\nBuilding network edges...")
    network_edges = build_network_edges(pair_frequency, jaccard, pmi, minimum_frequency=1)

    # ----------------------------------------------------------- save
    print("Saving results...")
    save_results(
        mode_output,
        frequency=frequency,
        matrix=matrix,
        pair_frequency=pair_frequency,
        jaccard=jaccard,
        pmi=pmi,
        relationships=relationships,
        association=association,
        stacks=stacks,
        network_edges=network_edges,
    )

    # ----------------------------------------------------------- report
    report.update({
        "status": "complete",
        "skill_pairs": len(pair_frequency),
        "association_rules_generated": len(association) > 0,
        "technology_stacks_generated": len(stacks) > 0,
        "output_directory": str(mode_output),
    })

    print()
    print("=" * 60)
    print("Analysis complete.")
    print(f"  Unique skills     : {len(matrix.index)}")
    print(f"  Skill pairs       : {len(pair_frequency)}")
    print(f"  Association rules : {len(association)}"
          + (" (min_support={:.3f})".format(min_support) if len(association) == 0 else ""))
    print(f"  Technology stacks : {len(stacks)}")
    print(f"  Network edges     : {len(network_edges)}")
    print(f"  Output directory  : {mode_output}")

    if not frequency.empty:
        print()
        print("Top 10 skills by frequency:")
        for _, row in frequency.head(10).iterrows():
            bar = "█" * int(row["frequency_pct"] / 5)
            print(f"  {row['skill']:<25} {row['job_count']:>3} jobs  {row['frequency_pct']:>5.1f}%  {bar}")

    if not pair_frequency.empty:
        print()
        print("Top 5 co-occurring skill pairs:")
        for _, row in pair_frequency.head(5).iterrows():
            print(f"  {row['skill_a']} + {row['skill_b']}: {row['pair_count']} jobs")

    print("=" * 60)

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Skill Relationship and Technology Stack Analysis — IT23321854\n"
            "Analyses lexical_skills and semantic_skills from jobs_extracted.csv"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to jobs_extracted.csv (default: data/processed/jobs_extracted.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output directory root (default: data/analytics/)",
    )
    parser.add_argument(
        "--skills",
        choices=SKILL_MODES,
        default="combined",
        help=(
            "Which skill field to analyse:\n"
            "  lexical_skills  — keyword-matched skills only\n"
            "  semantic_skills — embedding-matched skills only\n"
            "  combined        — union of both (default)\n"
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="run_all",
        help="Run analysis for all three skill modes: lexical, semantic, combined.",
    )

    args = parser.parse_args()

    if args.run_all:
        for mode in SKILL_MODES:
            run_analysis(
                input_path=args.input,
                output_dir=args.output,
                skill_mode=mode,
            )
    else:
        run_analysis(
            input_path=args.input,
            output_dir=args.output,
            skill_mode=args.skills,
        )


if __name__ == "__main__":
    main()