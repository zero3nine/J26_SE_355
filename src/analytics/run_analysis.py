from __future__ import annotations

import argparse
import ast
import json
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

DEFAULT_INPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "jobs_extracted.csv"
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
)


def parse_skills(value) -> set[str]:

    if pd.isna(value):
        return set()

    if isinstance(value, list):
        return {
            str(skill).strip()
            for skill in value
            if str(skill).strip()
        }

    text = str(value).strip()

    if not text:
        return set()

    try:
        parsed = json.loads(text)

        if isinstance(parsed, list):
            return {
                str(skill).strip()
                for skill in parsed
                if str(skill).strip()
            }

    except json.JSONDecodeError:
        pass

    try:
        parsed = ast.literal_eval(text)

        if isinstance(parsed, list):
            return {
                str(skill).strip()
                for skill in parsed
                if str(skill).strip()
            }

    except (ValueError, SyntaxError):
        pass

    return set()


def load_jobs(
    input_path: Path,
) -> list[set[str]]:

    df = pd.read_csv(input_path)

    required_columns = {
        "job_id",
        "lexical_skills",
        "semantic_skills",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    jobs = []

    for _, row in df.iterrows():

        lexical = parse_skills(
            row["lexical_skills"]
        )

        semantic = parse_skills(
            row["semantic_skills"]
        )

        combined = lexical | semantic

        if combined:
            jobs.append(combined)

    return jobs


def save_results(
    output_dir: Path,
    matrix: pd.DataFrame,
    pair_frequency: pd.DataFrame,
    jaccard: pd.DataFrame,
    pmi: pd.DataFrame,
    relationships: pd.DataFrame,
    association: pd.DataFrame,
    stacks: pd.DataFrame,
) -> None:

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    matrix.to_csv(
        output_dir
        / "skill_cooccurrence_matrix.csv"
    )

    pair_frequency.to_csv(
        output_dir
        / "skill_pair_frequency.csv",
        index=False,
    )

    jaccard.to_csv(
        output_dir
        / "skill_jaccard_similarity.csv",
        index=False,
    )

    pmi.to_csv(
        output_dir
        / "skill_pmi.csv",
        index=False,
    )

    relationships.to_csv(
        output_dir
        / "skill_relationships.csv",
        index=False,
    )

    association.to_csv(
        output_dir
        / "skill_association_rules.csv",
        index=False,
    )

    stacks.to_csv(
        output_dir
        / "frequent_technology_stacks.csv",
        index=False,
    )


def run_analysis(
    input_path: Path,
    output_dir: Path,
) -> None:

    print("Loading extracted job data...")

    jobs = load_jobs(input_path)

    print(
        f"Jobs with extracted skills: {len(jobs)}"
    )

    if not jobs:
        print()
        print(
            "No extracted skills were found."
        )
        print(
            "Analytics cannot produce relationships "
            "until skill extraction returns data."
        )
        print()

        empty_matrix = pd.DataFrame()

        empty_pairs = pd.DataFrame(
            columns=[
                "skill_a",
                "skill_b",
                "frequency",
            ]
        )

        empty_jaccard = pd.DataFrame(
            columns=[
                "skill_a",
                "skill_b",
                "intersection",
                "union",
                "jaccard",
            ]
        )

        empty_pmi = pd.DataFrame(
            columns=[
                "skill_a",
                "skill_b",
                "cooccurrence",
                "pmi",
            ]
        )

        empty_relationships = pd.DataFrame(
            columns=[
                "skill_a",
                "skill_b",
                "frequency",
                "jaccard",
                "pmi",
                "relationship_strength",
            ]
        )

        empty_association = pd.DataFrame(
            columns=[
                "antecedent",
                "consequent",
                "pair_count",
                "support",
                "confidence",
                "lift",
            ]
        )

        empty_stacks = pd.DataFrame(
            columns=[
                "stack",
                "stack_size",
                "job_count",
                "support",
            ]
        )

        save_results(
            output_dir,
            empty_matrix,
            empty_pairs,
            empty_jaccard,
            empty_pmi,
            empty_relationships,
            empty_association,
            empty_stacks,
        )

        return

    print("Calculating co occurrence matrix...")

    matrix = calculate_cooccurrence_matrix(
        jobs
    )

    print("Calculating skill pair frequency...")

    pair_frequency = calculate_pair_frequency(
        jobs
    )

    print("Calculating Jaccard similarity...")

    jaccard = calculate_jaccard(
        jobs
    )

    print("Calculating PMI...")

    pmi = calculate_pmi(
        jobs
    )

    print("Building skill relationships...")

    relationships = build_relationship_table(
        pair_frequency,
        jaccard,
        pmi,
    )

    print("Generating association rules...")

    association = calculate_association_rules(
        jobs
    )

    print("Extracting frequent technology stacks...")

    stacks = extract_frequent_stacks(
        jobs
    )

    save_results(
        output_dir,
        matrix,
        pair_frequency,
        jaccard,
        pmi,
        relationships,
        association,
        stacks,
    )

    print()
    print("Analysis completed.")
    print(
        f"Unique skills: {len(matrix.index)}"
    )
    print(
        f"Skill pairs: {len(pair_frequency)}"
    )
    print(
        f"Output directory: {output_dir}"
    )


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Skill relationship analysis"
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    run_analysis(
        input_path=args.input,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()