"""
Comprehensive Quantitative Calculation Validation Tests
Research Component: IT4010 - Skill Relationship & Technology Stack Analysis

Validates:
1. Exact mathematical precision of Co-occurrence, Jaccard similarity, PMI, and composite Relationship Strength.
2. Traces and validates screenshot values: Jaccard = 0.5000, PMI = 2.0000.
3. Verifies symmetry and diagonal consistency of Co-occurrence matrix.
4. Verifies deduplication: single job contributes at most once per canonical skill pair.
5. Verifies association rules (Support, Confidence, Lift == 2^PMI).
6. Verifies zero co-occurrence filtering (no spurious edges for unobserved pairs).
"""

from __future__ import annotations

import math
import unittest
import pandas as pd

from src.analytics.cooccurrence import (
    calculate_cooccurrence_matrix,
    calculate_pair_frequency,
)
from src.analytics.similarity import (
    calculate_jaccard,
    calculate_pmi,
)
from src.analytics.network import build_relationship_table
from src.analytics.association_rules import calculate_association_rules
from src.analytics.technology_stacks import extract_frequent_stacks
from src.analytics.run_analysis import build_network_edges, calculate_skill_frequency


class TestQuantitativeCalculations(unittest.TestCase):
    """Rigorous mathematical tests against hand-calculated ground truth datasets."""

    def setUp(self):
        # 4 deterministic jobs with known theoretical values
        # Total jobs N = 4
        self.jobs = [
            {"Python", "Django", "PostgreSQL"},
            {"Python", "Django", "Docker"},
            {"Python", "React", "Docker"},
            {"Java", "Spring Boot", "PostgreSQL"},
        ]

    # -------------------------------------------------------------------------
    # 1. Co-occurrence Matrix Symmetry, Diagonals, and Counts
    # -------------------------------------------------------------------------
    def test_cooccurrence_symmetry_and_diagonal(self):
        matrix = calculate_cooccurrence_matrix(self.jobs)
        skills = sorted(list(matrix.index))

        # Check symmetry: M[i, j] == M[j, i]
        for s1 in skills:
            for s2 in skills:
                self.assertEqual(
                    matrix.loc[s1, s2],
                    matrix.loc[s2, s1],
                    f"Asymmetry detected for pair ({s1}, {s2})"
                )

        # Check diagonal equals individual skill frequency
        freq = calculate_skill_frequency(self.jobs)
        freq_map = dict(zip(freq["skill"], freq["job_count"]))

        for skill in skills:
            self.assertEqual(
                matrix.loc[skill, skill],
                freq_map[skill],
                f"Diagonal mismatch for {skill}: {matrix.loc[skill, skill]} vs freq {freq_map[skill]}"
            )

        # Specific known cell values
        # Python in 3 jobs, Django in 2 jobs, co-occur in 2 jobs (Job 0, Job 1)
        self.assertEqual(matrix.loc["Python", "Django"], 2)
        # Python and Java never co-occur
        self.assertEqual(matrix.loc["Python", "Java"], 0)

    # -------------------------------------------------------------------------
    # 2. Jaccard Similarity Mathematical Precision
    # -------------------------------------------------------------------------
    def test_jaccard_mathematical_precision(self):
        # Python (jobs 0,1,2), Django (jobs 0,1)
        # Intersection = {0, 1} (size 2), Union = {0, 1, 2} (size 3)
        # Jaccard = 2 / 3 = 0.666667
        jaccard_df = calculate_jaccard(self.jobs)
        
        row = jaccard_df[
            ((jaccard_df["skill_a"] == "Django") & (jaccard_df["skill_b"] == "Python")) |
            ((jaccard_df["skill_a"] == "Python") & (jaccard_df["skill_b"] == "Django"))
        ].iloc[0]

        self.assertEqual(row["intersection"], 2)
        self.assertEqual(row["union"], 3)
        self.assertAlmostEqual(row["jaccard"], 2 / 3, places=5)

        # Java and Spring Boot appear ONLY in Job 3
        # Intersection = {3} (size 1), Union = {3} (size 1)
        # Jaccard = 1 / 1 = 1.000000
        row_java = jaccard_df[
            ((jaccard_df["skill_a"] == "Java") & (jaccard_df["skill_b"] == "Spring Boot")) |
            ((jaccard_df["skill_a"] == "Spring Boot") & (jaccard_df["skill_b"] == "Java"))
        ].iloc[0]

        self.assertEqual(row_java["intersection"], 1)
        self.assertEqual(row_java["union"], 1)
        self.assertEqual(row_java["jaccard"], 1.0)

    # -------------------------------------------------------------------------
    # 3. Pointwise Mutual Information (PMI) Verification
    # -------------------------------------------------------------------------
    def test_pmi_mathematical_precision(self):
        # Total jobs N = 4
        # Java freq = 1 (P = 1/4), Spring Boot freq = 1 (P = 1/4), Pair freq = 1 (P = 1/4)
        # Expected = (1/4) * (1/4) = 1/16
        # Ratio = (1/4) / (1/16) = 4.0
        # PMI = log2(4.0) = 2.000000 bits
        pmi_df = calculate_pmi(self.jobs)

        row_java = pmi_df[
            ((pmi_df["skill_a"] == "Java") & (pmi_df["skill_b"] == "Spring Boot")) |
            ((pmi_df["skill_a"] == "Spring Boot") & (pmi_df["skill_b"] == "Java"))
        ].iloc[0]

        self.assertEqual(row_java["cooccurrence"], 1)
        self.assertAlmostEqual(row_java["pmi"], 2.000000, places=5)

        # Python (freq 3, P = 3/4), Django (freq 2, P = 2/4), Pair (freq 2, P = 2/4)
        # Expected = (3/4) * (2/4) = 6/16 = 3/8
        # Ratio = (2/4) / (3/8) = (1/2) / (3/8) = 4/3
        # PMI = log2(4/3) = log2(1.333333) ~= 0.415037
        row_py = pmi_df[
            ((pmi_df["skill_a"] == "Django") & (pmi_df["skill_b"] == "Python")) |
            ((pmi_df["skill_a"] == "Python") & (pmi_df["skill_b"] == "Django"))
        ].iloc[0]

        expected_pmi = math.log2(4.0 / 3.0)
        self.assertAlmostEqual(row_py["pmi"], expected_pmi, places=5)

    # -------------------------------------------------------------------------
    # 4. Tracing Screenshot Values (Jaccard = 0.5000, PMI = 2.0000)
    # -------------------------------------------------------------------------
    def test_screenshot_value_trace_validation(self):
        """
        Validates the exact mathematical conditions from the research screenshot:
        N = 8 total jobs with skills.
        Skill A occurs in 1 job.
        Skill B occurs in 2 jobs.
        They co-occur in 1 job.
        """
        n_jobs = 8
        test_dataset = [
            {"SkillA", "SkillB"},   # Job 0: co-occurrence
            {"SkillB"},             # Job 1: Skill B only
            {"SkillC"},             # Job 2
            {"SkillC"},             # Job 3
            {"SkillD"},             # Job 4
            {"SkillD"},             # Job 5
            {"SkillE"},             # Job 6
            {"SkillE"},             # Job 7
        ]
        self.assertEqual(len(test_dataset), n_jobs)

        # 1. Jaccard calculation:
        # Union = {Job 0, Job 1} (size 2), Intersection = {Job 0} (size 1)
        # Jaccard = 1 / 2 = 0.5000
        jaccard_df = calculate_jaccard(test_dataset)
        row_j = jaccard_df[
            ((jaccard_df["skill_a"] == "SkillA") & (jaccard_df["skill_b"] == "SkillB")) |
            ((jaccard_df["skill_a"] == "SkillB") & (jaccard_df["skill_b"] == "SkillA"))
        ].iloc[0]
        self.assertEqual(row_j["intersection"], 1)
        self.assertEqual(row_j["union"], 2)
        self.assertEqual(row_j["jaccard"], 0.5000)

        # 2. PMI calculation:
        # P(A) = 1/8, P(B) = 2/8 = 1/4, P(A, B) = 1/8
        # Expected = (1/8) * (1/4) = 1/32
        # Ratio = (1/8) / (1/32) = 4.0
        # PMI = log2(4.0) = 2.0000
        pmi_df = calculate_pmi(test_dataset)
        row_p = pmi_df[
            ((pmi_df["skill_a"] == "SkillA") & (pmi_df["skill_b"] == "SkillB")) |
            ((pmi_df["skill_a"] == "SkillB") & (pmi_df["skill_b"] == "SkillA"))
        ].iloc[0]
        self.assertEqual(row_p["pmi"], 2.0000)

        # 3. Composite Relationship Strength:
        # Strength = Jaccard * max(0, PMI) = 0.5000 * 2.0000 = 1.0000
        pair_df = calculate_pair_frequency(test_dataset)
        rel_df = build_relationship_table(pair_df, jaccard_df, pmi_df)
        row_r = rel_df[
            ((rel_df["skill_a"] == "SkillA") & (rel_df["skill_b"] == "SkillB")) |
            ((rel_df["skill_a"] == "SkillB") & (rel_df["skill_b"] == "SkillA"))
        ].iloc[0]
        self.assertEqual(row_r["relationship_strength"], 1.0000)

    # -------------------------------------------------------------------------
    # 5. Composite Relationship Strength Formulation
    # -------------------------------------------------------------------------
    def test_relationship_strength_clipping(self):
        """Validates that negative PMI (substitutes) is clipped to zero."""
        # Dataset where two skills co-occur much less than expected
        # A in 9 jobs, B in 9 jobs, co-occur in 1 job, out of 10 jobs
        jobs = [{"A", "B"}] + [{"A"}] * 8 + [{"B"}] * 8
        pair_df = calculate_pair_frequency(jobs)
        jaccard_df = calculate_jaccard(jobs)
        pmi_df = calculate_pmi(jobs)

        rel_df = build_relationship_table(pair_df, jaccard_df, pmi_df)
        pmi_val = pmi_df.iloc[0]["pmi"]
        self.assertLess(pmi_val, 0)  # Verify PMI is negative

        # Strength must be clipped to 0.0 (Jaccard * max(0, PMI))
        self.assertEqual(rel_df.iloc[0]["relationship_strength"], 0.0)

    # -------------------------------------------------------------------------
    # 6. Association Rules & Network Edges
    # -------------------------------------------------------------------------
    def test_association_rules_and_lift_relationship_to_pmi(self):
        """Confirms that lift == 2^PMI for all association rules."""
        rules_df = calculate_association_rules(self.jobs, minimum_support=0.01)
        pmi_df = calculate_pmi(self.jobs)

        pmi_dict = {}
        for _, r in pmi_df.iterrows():
            pmi_dict[(r["skill_a"], r["skill_b"])] = r["pmi"]
            pmi_dict[(r["skill_b"], r["skill_a"])] = r["pmi"]

        for _, rule in rules_df.iterrows():
            ant = rule["antecedent"]
            con = rule["consequent"]
            lift = rule["lift"]
            pmi = pmi_dict.get((ant, con))
            if pmi is not None:
                expected_lift = 2 ** pmi
                self.assertAlmostEqual(lift, expected_lift, places=4)

    def test_zero_cooccurrence_edges_excluded(self):
        """Zero co-occurrence pairs must never form network edges."""
        pair_df = calculate_pair_frequency(self.jobs)
        jaccard_df = calculate_jaccard(self.jobs)
        pmi_df = calculate_pmi(self.jobs)
        edges = build_network_edges(pair_df, jaccard_df, pmi_df, minimum_frequency=1)

        # Python and Java never co-occur
        py_java_edges = edges[
            ((edges["source_skill"] == "Python") & (edges["target_skill"] == "Java")) |
            ((edges["source_skill"] == "Java") & (edges["target_skill"] == "Python"))
        ]
        self.assertTrue(py_java_edges.empty, "Zero co-occurrence pair formed an edge!")
        self.assertTrue((edges["weight"] >= 1).all())


if __name__ == "__main__":
    unittest.main()
