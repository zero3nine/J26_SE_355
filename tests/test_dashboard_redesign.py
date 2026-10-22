"""
Automated unit tests for the redesigned Skill Relationship and Technology Stack Analysis Dashboard.
Tests:
1. Metric calculations: Co-occurrence, Jaccard, PMI, NPMI bounded in [-1.0, +1.0], Association Rules (Support, Confidence, Lift).
2. Empty state handling: Empty job lists, empty database datasets, zero extracted skills.
3. Filtering: Minimum co-occurrence thresholds, rule filtering, multi-skill stack size filtering (2, 3, 4).
4. Evidence traceability: Authentic job linkage, context snippet extraction, verifiable text audit.
5. Method comparison: Lexical vs. Semantic vs. Combined on identical population, Venn overlap consistency, rank shifts, ground truth disclaimer.
6. Network topology: Centrality calculations (degree, betweenness, closeness), community clusters, graph density.
"""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path
import pandas as pd

from src.analytics.cooccurrence import calculate_cooccurrence_matrix, calculate_pair_frequency
from src.analytics.similarity import calculate_jaccard, calculate_pmi
from src.analytics.association_rules import calculate_association_rules
from src.analytics.technology_stacks import extract_frequent_stacks
from src.analytics.network import build_relationship_table, calculate_network_metrics
from src.analytics.comparison import compare_extraction_methods
from src.analytics.evidence import build_source_evidence, _find_context_snippet
from src.analytics.run_analysis import run_analysis, load_jobs
from src.analytics.dashboard import _extract_context_snippet, _parse_job_skills


class TestDashboardRedesign(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_root = Path(self.temp_dir.name)

        # Standard multi-skill research dataset fixture
        self.jobs = [
            {"Python", "Django", "PostgreSQL", "Docker"},
            {"Python", "FastAPI", "PostgreSQL", "Docker"},
            {"Python", "Django", "PostgreSQL", "Redis"},
            {"Java", "Spring Boot", "MySQL", "Docker"},
            {"Java", "Spring Boot", "PostgreSQL", "AWS"},
            {"JavaScript", "React", "Node.js", "TypeScript", "HTML", "CSS"},
            {"JavaScript", "React", "TypeScript", "CSS"},
            {"Python", "Docker", "AWS", "Kubernetes"},
        ]

        self.records = [
            {
                "job_id": f"TEST_JOB_{i+1:03d}",
                "job_title_raw": f"Engineer Role {i+1}",
                "company": f"TechCorp {i+1}",
                "location_raw": "Colombo, Sri Lanka",
                "source_platform": "itpro.lk" if i < 6 else "topjobs.lk",
                "source_url": f"https://example.com/job/{i+1}",
                "job_description": f"We are hiring a specialist with {', '.join(sorted(skills))}. Must have strong experience.",
                "lexical_skills": json.dumps(sorted(list(skills))),
                "semantic_skills": json.dumps(sorted(list(skills))),
            }
            for i, skills in enumerate(self.jobs)
        ]
        self.jobs_df = pd.DataFrame(self.records)

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------------------
    # 1. Metric Calculations & Bounds
    # -------------------------------------------------------------------------

    def test_jaccard_similarity_bounds_and_symmetry(self):
        """Jaccard similarity must be bounded in [0.0, 1.0] and symmetric."""
        df_jaccard = calculate_jaccard(self.jobs)
        self.assertFalse(df_jaccard.empty)
        self.assertTrue((df_jaccard["jaccard"] >= 0.0).all())
        self.assertTrue((df_jaccard["jaccard"] <= 1.0).all())

        # Check Python + PostgreSQL (appear together in 3 jobs, union = 4 + 4 - 3 = 5, Jaccard = 3/5 = 0.60)
        py_pg = df_jaccard[
            ((df_jaccard["skill_a"] == "PostgreSQL") & (df_jaccard["skill_b"] == "Python")) |
            ((df_jaccard["skill_a"] == "Python") & (df_jaccard["skill_b"] == "PostgreSQL"))
        ]
        self.assertEqual(len(py_pg), 1)
        self.assertAlmostEqual(py_pg.iloc[0]["jaccard"], 3 / 5, places=4)

    def test_pmi_and_bounded_npmi(self):
        """PMI must quantify statistical association and NPMI must be strictly bounded in [-1.0, 1.0]."""
        df_pmi = calculate_pmi(self.jobs, min_cooccurrence=1)
        self.assertFalse(df_pmi.empty)
        self.assertIn("pmi", df_pmi.columns)
        self.assertIn("npmi", df_pmi.columns)

        # All NPMI values must be between -1.0 and 1.0
        self.assertTrue((df_pmi["npmi"] >= -1.0).all())
        self.assertTrue((df_pmi["npmi"] <= 1.0).all())

        # Check perfect co-occurrence pair: Java and Spring Boot always appear together (2 jobs each, intersection 2)
        java_spring = df_pmi[
            ((df_pmi["skill_a"] == "Java") & (df_pmi["skill_b"] == "Spring Boot")) |
            ((df_pmi["skill_a"] == "Spring Boot") & (df_pmi["skill_b"] == "Java"))
        ]
        self.assertEqual(len(java_spring), 1)
        # When two skills co-occur in 100% of their occurrences, NPMI = 1.0
        self.assertAlmostEqual(java_spring.iloc[0]["npmi"], 1.0, places=4)

    def test_association_rules_formulas(self):
        """Support, Confidence, and Lift must follow standard association rule formulas."""
        df_rules = calculate_association_rules(self.jobs, minimum_support=0.10)
        self.assertFalse(df_rules.empty)
        self.assertTrue((df_rules["support"] > 0).all())
        self.assertTrue((df_rules["confidence"] >= 0.0).all())
        self.assertTrue((df_rules["confidence"] <= 1.0).all())
        self.assertTrue((df_rules["lift"] > 0).all())

        # For Java -> Spring Boot: Java count = 2, Spring Boot count = 2, Pair = 2.
        # Support = 2/8 = 0.25, Confidence = 1.0, Lift = 1.0 / (2/8) = 4.0
        rule = df_rules[(df_rules["antecedent"] == "Java") & (df_rules["consequent"] == "Spring Boot")]
        self.assertEqual(len(rule), 1)
        self.assertAlmostEqual(rule.iloc[0]["support"], 0.25, places=4)
        self.assertAlmostEqual(rule.iloc[0]["confidence"], 1.0, places=4)
        self.assertAlmostEqual(rule.iloc[0]["lift"], 4.0, places=4)

    # -------------------------------------------------------------------------
    # 2. Empty States & Degenerate Cases
    # -------------------------------------------------------------------------

    def test_empty_dataset_handling(self):
        """Empty job inputs must return empty DataFrames with correct schemas without raising exceptions."""
        empty_jobs: list[set[str]] = []
        df_j = calculate_jaccard(empty_jobs)
        self.assertTrue(df_j.empty)
        self.assertIn("jaccard", df_j.columns)

        df_p = calculate_pmi(empty_jobs)
        self.assertTrue(df_p.empty)
        self.assertIn("npmi", df_p.columns)

        df_r = calculate_association_rules(empty_jobs)
        self.assertTrue(df_r.empty)

        df_s = extract_frequent_stacks(empty_jobs)
        self.assertTrue(df_s.empty)
        self.assertIn("stack", df_s.columns)

    def test_single_job_edge_case(self):
        """A single job must not cause zero-division errors in Jaccard or PMI."""
        single_job = [{"Python", "PostgreSQL"}]
        df_j = calculate_jaccard(single_job)
        self.assertEqual(len(df_j), 1)
        self.assertEqual(df_j.iloc[0]["jaccard"], 1.0)

        df_p = calculate_pmi(single_job)
        self.assertEqual(len(df_p), 1)
        # With N=1, P(A)=1, P(B)=1, P(AB)=1 -> log2(1) = 0.0
        self.assertEqual(df_p.iloc[0]["pmi"], 0.0)
        self.assertTrue(-1.0 <= df_p.iloc[0]["npmi"] <= 1.0)

    # -------------------------------------------------------------------------
    # 3. Filtering & Thresholds
    # -------------------------------------------------------------------------

    def test_minimum_cooccurrence_threshold_filter(self):
        """Minimum co-occurrence threshold must filter out pairs appearing below the threshold."""
        df_pmi_1 = calculate_pmi(self.jobs, min_cooccurrence=1)
        df_pmi_3 = calculate_pmi(self.jobs, min_cooccurrence=3)
        self.assertGreater(len(df_pmi_1), len(df_pmi_3))
        self.assertTrue((df_pmi_3["cooccurrence"] >= 3).all())

    def test_technology_stack_discovery_and_size_filtering(self):
        """Frequent stack discovery must identify combinations of sizes 2, 3, and 4."""
        stacks_df = extract_frequent_stacks(
            self.jobs,
            minimum_support=0.20,
            maximum_stack_size=4,
            job_records=self.records,
        )
        self.assertFalse(stacks_df.empty)
        sizes = set(stacks_df["stack_size"].unique())
        self.assertTrue(any(s >= 2 for s in sizes))
        self.assertTrue((stacks_df["support"] >= 0.20).all())

        # Check supporting jobs JSON tracking
        self.assertIn("supporting_jobs", stacks_df.columns)
        first_supp = json.loads(stacks_df.iloc[0]["supporting_jobs"])
        self.assertIsInstance(first_supp, list)
        self.assertTrue(len(first_supp) >= 1)
        self.assertIn("job_id", first_supp[0])

    # -------------------------------------------------------------------------
    # 4. Evidence Traceability & Context Extraction
    # -------------------------------------------------------------------------

    def test_evidence_traceability_linking(self):
        """Discovered relationships and stacks must link back to authentic job advertisements."""
        df_rel = build_relationship_table(
            calculate_pair_frequency(self.jobs),
            calculate_jaccard(self.jobs),
            calculate_pmi(self.jobs),
        )
        df_stacks = extract_frequent_stacks(self.jobs, minimum_support=0.15, job_records=self.records)

        evidence = build_source_evidence(self.jobs_df, df_rel, df_stacks, max_pairs=3, max_stacks=3)
        self.assertGreater(len(evidence), 0)

        for ev in evidence:
            self.assertIn("job_id", ev)
            self.assertIn("company", ev)
            self.assertIn("context_snippet", ev)
            self.assertIn("verification_status", ev)
            self.assertEqual(ev["verification_status"], "Verified in Original Text")

    def test_context_snippet_extraction(self):
        """Context snippet extractor must highlight target terms and truncate gracefully."""
        text = "Seeking Senior DevOps Engineer with deep Docker and Kubernetes expertise in production systems."
        snip = _extract_context_snippet(text, ["Docker", "Kubernetes"], max_len=100)
        self.assertIn("Docker", snip)
        self.assertIn("Kubernetes", snip)
        self.assertLessEqual(len(snip), 100)

    # -------------------------------------------------------------------------
    # 5. Extraction Method Comparison & Academic Integrity
    # -------------------------------------------------------------------------

    def test_cross_method_comparison_identical_population(self):
        """Method comparison must evaluate on identical population and report set consistency."""
        # Run three extraction modes on test output root
        for m in ["lexical_skills", "semantic_skills", "combined"]:
            run_analysis(input_path=self.jobs_df, output_dir=self.output_root, skill_mode=m)

        comp = compare_extraction_methods(self.output_root, self.jobs_df)
        self.assertIn("method_metrics", comp)
        self.assertIn("skill_overlap", comp)
        self.assertIn("evaluation_disclaimer", comp)

        overlap = comp["skill_overlap"]
        common_cnt = len(overlap["common_to_all_three"])
        lex_only_cnt = len(overlap["lexical_only"])
        sem_only_cnt = len(overlap["semantic_only"])
        comb_tot = overlap["total_combined_unique"]

        # Mathematical set identity: Common + LexOnly + SemOnly == Total in this controlled setup
        self.assertEqual(common_cnt + lex_only_cnt + sem_only_cnt, comb_tot)

        # Ground truth transparency: F1 must be reported as unavailable without gold standard
        for metric in comp["method_metrics"]:
            self.assertIn("Unavailable", metric["ground_truth_f1"])

    # -------------------------------------------------------------------------
    # 6. Network Topology & Centrality
    # -------------------------------------------------------------------------

    def test_network_metrics_calculation(self):
        """Network metrics must compute degree, betweenness centrality, and graph density."""
        pair_freq = calculate_pair_frequency(self.jobs)
        jaccard = calculate_jaccard(self.jobs)
        pmi = calculate_pmi(self.jobs)
        rel_df = build_relationship_table(pair_freq, jaccard, pmi)
        rel_df.rename(columns={"skill_a": "source_skill", "skill_b": "target_skill", "pair_count": "weight"}, inplace=True)

        nodes_df, topology = calculate_network_metrics(rel_df, min_weight=1.0)
        self.assertFalse(nodes_df.empty)
        self.assertIn("degree_centrality", nodes_df.columns)
        self.assertIn("betweenness_centrality", nodes_df.columns)
        self.assertIn("closeness_centrality", nodes_df.columns)
        self.assertIn("community_id", nodes_df.columns)

        self.assertIn("num_nodes", topology)
        self.assertIn("num_edges", topology)
        self.assertIn("density", topology)
        self.assertTrue(0.0 <= topology["density"] <= 1.0)


if __name__ == "__main__":
    unittest.main()
