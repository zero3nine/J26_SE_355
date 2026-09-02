"""
Tests for analytics component IT23321854.
Covers: skill parsing, co-occurrence, pair counting, Jaccard,
        PMI edge cases, association rule thresholds, network edges,
        technology stacks, and lexical vs. semantic column selection.
"""
from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

import pandas as pd

from src.analytics.run_analysis import (
    parse_skills,
    load_jobs,
    calculate_skill_frequency,
    build_network_edges,
)
from src.analytics.cooccurrence import (
    calculate_cooccurrence_matrix,
    calculate_pair_frequency,
)
from src.analytics.similarity import (
    calculate_jaccard,
    calculate_pmi,
)
from src.analytics.association_rules import calculate_association_rules
from src.analytics.technology_stacks import extract_frequent_stacks
from src.analytics.network import build_relationship_table


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

JOBS_3 = [
    {"python", "django", "postgresql"},
    {"python", "flask", "postgresql"},
    {"java", "spring", "postgresql"},
]

JOBS_SINGLE_SKILL = [{"python"}, {"java"}]

JOBS_EMPTY: list[set[str]] = []

JOBS_ONE_JOB = [{"python", "django"}]


# ---------------------------------------------------------------------------
# parse_skills
# ---------------------------------------------------------------------------

class TestParseSkills(unittest.TestCase):

    def test_json_list(self):
        val = '["python", "java", "aws"]'
        result = parse_skills(val)
        self.assertEqual(result, {"python", "java", "aws"})

    def test_python_repr_list(self):
        val = "['python', 'java']"
        result = parse_skills(val)
        self.assertEqual(result, {"python", "java"})

    def test_empty_json_array(self):
        result = parse_skills("[]")
        self.assertEqual(result, set())

    def test_nan_value(self):
        result = parse_skills(float("nan"))
        self.assertEqual(result, set())

    def test_none_string(self):
        result = parse_skills("None")
        self.assertEqual(result, set())

    def test_already_a_list(self):
        result = parse_skills(["python", "docker"])
        self.assertEqual(result, {"python", "docker"})

    def test_whitespace_stripped(self):
        result = parse_skills('["  python  ", "  java  "]')
        self.assertEqual(result, {"python", "java"})

    def test_empty_strings_excluded(self):
        result = parse_skills('["python", "", "  "]')
        self.assertEqual(result, {"python"})

    def test_single_skill(self):
        result = parse_skills('["docker"]')
        self.assertEqual(result, {"docker"})


# ---------------------------------------------------------------------------
# load_jobs — lexical vs. semantic column selection
# ---------------------------------------------------------------------------

class TestLoadJobs(unittest.TestCase):

    def _make_csv(self, tmp_path: Path) -> Path:
        data = {
            "job_id": ["j1", "j2", "j3"],
            "job_title_raw": ["Dev A", "Dev B", "Dev C"],
            "company": ["X", "Y", "Z"],
            "country": ["LK", "LK", "LK"],
            "location_raw": ["Colombo", "Colombo", "Colombo"],
            "job_description": ["desc1", "desc2", "desc3"],
            "posted_date": ["2026-01-01"] * 3,
            "source_platform": ["itpro.lk"] * 3,
            "source_url": ["https://itpro.lk/1", "https://itpro.lk/2", "https://itpro.lk/3"],
            "scraped_at": ["2026-01-01T00:00:00+00:00"] * 3,
            "lexical_skills": [
                '["python", "django"]',
                '["java", "spring"]',
                '[]',
            ],
            "semantic_skills": [
                '["aws", "docker"]',
                '["kubernetes", "docker"]',
                '["python"]',
            ],
        }
        path = tmp_path / "jobs_extracted.csv"
        pd.DataFrame(data).to_csv(path, index=False)
        return path

    def test_lexical_mode(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = self._make_csv(Path(tmp))
            jobs, report = load_jobs(path, skill_mode="lexical_skills")
            # j3 has empty lexical → excluded
            self.assertEqual(len(jobs), 2)
            self.assertIn("python", jobs[0])
            self.assertEqual(report["jobs_with_lexical_skills"], 2)

    def test_semantic_mode(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = self._make_csv(Path(tmp))
            jobs, report = load_jobs(path, skill_mode="semantic_skills")
            # all three have semantic skills
            self.assertEqual(len(jobs), 3)
            self.assertEqual(report["jobs_with_semantic_skills"], 3)

    def test_combined_mode(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = self._make_csv(Path(tmp))
            jobs, report = load_jobs(path, skill_mode="combined")
            # j3 has semantic only → should be included
            self.assertEqual(len(jobs), 3)
            # j3 combined should have {"python"}
            self.assertIn("python", jobs[2])

    def test_missing_columns_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "bad.csv"
            pd.DataFrame({"job_id": [1], "job_title_raw": ["X"]}).to_csv(bad_path, index=False)
            with self.assertRaises(ValueError):
                load_jobs(bad_path)

    def test_file_not_found_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_jobs(Path("/nonexistent/path/jobs_extracted.csv"))


# ---------------------------------------------------------------------------
# Skill frequency
# ---------------------------------------------------------------------------

class TestSkillFrequency(unittest.TestCase):

    def test_frequency_counts(self):
        freq = calculate_skill_frequency(JOBS_3)
        freq_dict = dict(zip(freq["skill"], freq["job_count"]))
        self.assertEqual(freq_dict["postgresql"], 3)
        self.assertEqual(freq_dict["python"], 2)
        self.assertEqual(freq_dict["java"], 1)

    def test_sorted_descending(self):
        freq = calculate_skill_frequency(JOBS_3)
        counts = list(freq["job_count"])
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_frequency_pct_sums_to_reasonable(self):
        freq = calculate_skill_frequency(JOBS_3)
        # postgresql appears in all 3 of 3 jobs → 100%
        pct = freq[freq["skill"] == "postgresql"]["frequency_pct"].iloc[0]
        self.assertAlmostEqual(pct, 100.0)

    def test_empty_jobs_returns_empty_frame(self):
        freq = calculate_skill_frequency(JOBS_EMPTY)
        self.assertTrue(freq.empty)

    def test_single_skill_per_job(self):
        freq = calculate_skill_frequency(JOBS_SINGLE_SKILL)
        self.assertEqual(len(freq), 2)  # python and java, each once


# ---------------------------------------------------------------------------
# Co-occurrence
# ---------------------------------------------------------------------------

class TestCooccurrence(unittest.TestCase):

    def test_matrix_shape(self):
        matrix = calculate_cooccurrence_matrix(JOBS_3)
        all_skills = {s for j in JOBS_3 for s in j}
        self.assertEqual(set(matrix.index), all_skills)
        self.assertEqual(set(matrix.columns), all_skills)

    def test_matrix_diagonal(self):
        # Diagonal = how many times the skill appears alone
        matrix = calculate_cooccurrence_matrix(JOBS_3)
        self.assertEqual(matrix.loc["postgresql", "postgresql"], 3)
        self.assertEqual(matrix.loc["python", "python"], 2)

    def test_matrix_symmetry(self):
        matrix = calculate_cooccurrence_matrix(JOBS_3)
        for a in matrix.index:
            for b in matrix.columns:
                self.assertEqual(matrix.loc[a, b], matrix.loc[b, a])

    def test_pair_frequency_count(self):
        pairs = calculate_pair_frequency(JOBS_3)
        # python+postgresql appear together in jobs 0 and 1
        row = pairs[(pairs["skill_a"] == "postgresql") & (pairs["skill_b"] == "python")]
        if row.empty:
            row = pairs[(pairs["skill_a"] == "python") & (pairs["skill_b"] == "postgresql")]
        self.assertFalse(row.empty)
        self.assertEqual(row.iloc[0]["pair_count"], 2)

    def test_pair_frequency_empty_jobs(self):
        pairs = calculate_pair_frequency(JOBS_EMPTY)
        self.assertTrue(pairs.empty)

    def test_pair_frequency_single_skill_per_job(self):
        # No pairs possible when each job has only one skill
        pairs = calculate_pair_frequency(JOBS_SINGLE_SKILL)
        self.assertTrue(pairs.empty)

    def test_empty_matrix(self):
        matrix = calculate_cooccurrence_matrix(JOBS_EMPTY)
        self.assertTrue(matrix.empty)


# ---------------------------------------------------------------------------
# Jaccard similarity
# ---------------------------------------------------------------------------

class TestJaccard(unittest.TestCase):

    def test_jaccard_range(self):
        jaccard = calculate_jaccard(JOBS_3)
        self.assertTrue((jaccard["jaccard"] >= 0).all())
        self.assertTrue((jaccard["jaccard"] <= 1).all())

    def test_jaccard_known_value(self):
        # python occurs in jobs 0,1 — postgresql in 0,1,2
        # intersection = {0,1}, union = {0,1,2} → J = 2/3
        jaccard = calculate_jaccard(JOBS_3)
        row = jaccard[
            ((jaccard["skill_a"] == "python") & (jaccard["skill_b"] == "postgresql")) |
            ((jaccard["skill_a"] == "postgresql") & (jaccard["skill_b"] == "python"))
        ]
        self.assertFalse(row.empty)
        self.assertAlmostEqual(row.iloc[0]["jaccard"], 2 / 3, places=4)

    def test_jaccard_empty_jobs(self):
        jaccard = calculate_jaccard(JOBS_EMPTY)
        self.assertTrue(jaccard.empty)

    def test_jaccard_single_job(self):
        # With one job, union = intersection for all pairs → J = 1.0
        jaccard = calculate_jaccard(JOBS_ONE_JOB)
        self.assertTrue((jaccard["jaccard"] == 1.0).all())

    def test_jaccard_sorted_descending(self):
        jaccard = calculate_jaccard(JOBS_3)
        vals = list(jaccard["jaccard"])
        self.assertEqual(vals, sorted(vals, reverse=True))


# ---------------------------------------------------------------------------
# PMI (edge cases: zero probability, log2(0))
# ---------------------------------------------------------------------------

class TestPMI(unittest.TestCase):

    def test_pmi_no_division_by_zero(self):
        """Skills that never co-occur must not produce division by zero."""
        jobs = [{"python"}, {"java"}]  # no co-occurrences
        pmi = calculate_pmi(jobs)
        # No pairs → empty result is correct
        self.assertTrue(pmi.empty)

    def test_pmi_no_log_of_zero(self):
        """PMI should never call log2(0) — all returned pmi values must be finite."""
        pmi = calculate_pmi(JOBS_3)
        if not pmi.empty:
            self.assertTrue(pmi["pmi"].apply(lambda v: math.isfinite(v)).all())

    def test_pmi_non_negative_for_always_cooccurring(self):
        """Skills that always appear together should have non-negative PMI.
        PMI = log2(P(A,B) / P(A)*P(B)). When all 3 jobs have {python, django},
        P(A)=1, P(B)=1, P(A,B)=1, so PMI=log2(1/1)=0 which is correct.
        """
        jobs = [
            {"python", "django"},
            {"python", "django"},
            {"python", "django"},
        ]
        pmi = calculate_pmi(jobs)
        if not pmi.empty:
            row = pmi[
                ((pmi["skill_a"] == "python") & (pmi["skill_b"] == "django")) |
                ((pmi["skill_a"] == "django") & (pmi["skill_b"] == "python"))
            ]
            if not row.empty:
                self.assertGreaterEqual(row.iloc[0]["pmi"], 0)

    def test_pmi_empty_jobs_returns_empty(self):
        pmi = calculate_pmi(JOBS_EMPTY)
        self.assertTrue(pmi.empty)

    def test_pmi_columns(self):
        pmi = calculate_pmi(JOBS_3)
        if not pmi.empty:
            self.assertIn("skill_a", pmi.columns)
            self.assertIn("skill_b", pmi.columns)
            self.assertIn("pmi", pmi.columns)


# ---------------------------------------------------------------------------
# Association rules — thresholds
# ---------------------------------------------------------------------------

class TestAssociationRules(unittest.TestCase):

    def test_minimum_support_filters_rare_pairs(self):
        # With support=0.99, only pairs appearing in nearly all jobs pass
        rules = calculate_association_rules(JOBS_3, minimum_support=0.99)
        # No pair appears in all 3 jobs simultaneously (each pair in at most 2)
        self.assertTrue(rules.empty)

    def test_low_support_produces_rules(self):
        rules = calculate_association_rules(JOBS_3, minimum_support=0.01)
        self.assertFalse(rules.empty)

    def test_confidence_in_range(self):
        rules = calculate_association_rules(JOBS_3, minimum_support=0.01)
        if not rules.empty:
            self.assertTrue((rules["confidence"] >= 0).all())
            self.assertTrue((rules["confidence"] <= 1).all())

    def test_lift_positive(self):
        rules = calculate_association_rules(JOBS_3, minimum_support=0.01)
        if not rules.empty:
            self.assertTrue((rules["lift"] >= 0).all())

    def test_support_correct(self):
        # python+postgresql appear in 2 of 3 jobs → support = 2/3 ≈ 0.667
        rules = calculate_association_rules(JOBS_3, minimum_support=0.01)
        if not rules.empty:
            relevant = rules[
                ((rules["antecedent"] == "python") & (rules["consequent"] == "postgresql")) |
                ((rules["antecedent"] == "postgresql") & (rules["consequent"] == "python"))
            ]
            if not relevant.empty:
                self.assertAlmostEqual(relevant.iloc[0]["support"], 2 / 3, places=4)

    def test_empty_jobs_returns_empty(self):
        rules = calculate_association_rules(JOBS_EMPTY, minimum_support=0.01)
        self.assertTrue(rules.empty)

    def test_single_job_no_rules_above_threshold(self):
        # With one job, every pair has support=1.0 → passes any threshold
        rules = calculate_association_rules(JOBS_ONE_JOB, minimum_support=0.5)
        # Should produce some rules (python→django and django→python)
        self.assertFalse(rules.empty)


# ---------------------------------------------------------------------------
# Technology stacks
# ---------------------------------------------------------------------------

class TestTechnologyStacks(unittest.TestCase):

    def test_stacks_found(self):
        stacks = extract_frequent_stacks(JOBS_3, minimum_support=0.01)
        self.assertFalse(stacks.empty)

    def test_stacks_support_in_range(self):
        stacks = extract_frequent_stacks(JOBS_3, minimum_support=0.01)
        if not stacks.empty:
            self.assertTrue((stacks["support"] >= 0).all())
            self.assertTrue((stacks["support"] <= 1).all())

    def test_minimum_support_filters(self):
        stacks = extract_frequent_stacks(JOBS_3, minimum_support=0.99)
        # No combination appears in all 3 jobs (except postgresql alone, but size ≥ 2)
        self.assertTrue(stacks.empty)

    def test_stack_size_at_least_2(self):
        stacks = extract_frequent_stacks(JOBS_3, minimum_support=0.01)
        if not stacks.empty:
            self.assertTrue((stacks["stack_size"] >= 2).all())

    def test_empty_jobs_returns_empty(self):
        stacks = extract_frequent_stacks(JOBS_EMPTY, minimum_support=0.01)
        self.assertTrue(stacks.empty)

    def test_single_skill_per_job_no_stacks(self):
        stacks = extract_frequent_stacks(JOBS_SINGLE_SKILL, minimum_support=0.01)
        self.assertTrue(stacks.empty)


# ---------------------------------------------------------------------------
# Network edges
# ---------------------------------------------------------------------------

class TestNetworkEdges(unittest.TestCase):

    def test_edges_produced(self):
        pairs = calculate_pair_frequency(JOBS_3)
        jaccard = calculate_jaccard(JOBS_3)
        pmi = calculate_pmi(JOBS_3)
        edges = build_network_edges(pairs, jaccard, pmi, minimum_frequency=1)
        self.assertFalse(edges.empty)

    def test_edges_columns(self):
        pairs = calculate_pair_frequency(JOBS_3)
        jaccard = calculate_jaccard(JOBS_3)
        pmi = calculate_pmi(JOBS_3)
        edges = build_network_edges(pairs, jaccard, pmi, minimum_frequency=1)
        self.assertIn("source_skill", edges.columns)
        self.assertIn("target_skill", edges.columns)
        self.assertIn("weight", edges.columns)
        self.assertIn("pair_count", edges.columns)
        self.assertIn("jaccard", edges.columns)
        self.assertIn("pmi", edges.columns)

    def test_edges_sorted_by_weight(self):
        pairs = calculate_pair_frequency(JOBS_3)
        jaccard = calculate_jaccard(JOBS_3)
        pmi = calculate_pmi(JOBS_3)
        edges = build_network_edges(pairs, jaccard, pmi, minimum_frequency=1)
        weights = list(edges["weight"])
        self.assertEqual(weights, sorted(weights, reverse=True))

    def test_empty_pairs_returns_empty(self):
        edges = build_network_edges(
            pd.DataFrame(columns=["skill_a", "skill_b", "pair_count"]),
            pd.DataFrame(columns=["skill_a", "skill_b", "jaccard"]),
            pd.DataFrame(columns=["skill_a", "skill_b", "pmi"]),
            minimum_frequency=1,
        )
        self.assertTrue(edges.empty)

    def test_jaccard_in_range(self):
        pairs = calculate_pair_frequency(JOBS_3)
        jaccard = calculate_jaccard(JOBS_3)
        pmi = calculate_pmi(JOBS_3)
        edges = build_network_edges(pairs, jaccard, pmi, minimum_frequency=1)
        if not edges.empty:
            self.assertTrue((edges["jaccard"] >= 0).all())
            self.assertTrue((edges["jaccard"] <= 1).all())


# ---------------------------------------------------------------------------
# Skill relationship table (network.py)
# ---------------------------------------------------------------------------

class TestRelationshipTable(unittest.TestCase):

    def test_relationship_columns(self):
        pairs = calculate_pair_frequency(JOBS_3)
        jaccard = calculate_jaccard(JOBS_3)
        pmi = calculate_pmi(JOBS_3)
        rel = build_relationship_table(pairs, jaccard, pmi)
        for col in ["skill_a", "skill_b", "pair_count", "jaccard", "pmi", "relationship_strength"]:
            self.assertIn(col, rel.columns)

    def test_empty_pairs_returns_empty(self):
        rel = build_relationship_table(
            pd.DataFrame(columns=["skill_a", "skill_b", "pair_count"]),
            pd.DataFrame(columns=["skill_a", "skill_b", "intersection", "union", "jaccard"]),
            pd.DataFrame(columns=["skill_a", "skill_b", "cooccurrence", "pmi"]),
        )
        self.assertTrue(rel.empty)

    def test_relationship_strength_non_negative(self):
        pairs = calculate_pair_frequency(JOBS_3)
        jaccard = calculate_jaccard(JOBS_3)
        pmi = calculate_pmi(JOBS_3)
        rel = build_relationship_table(pairs, jaccard, pmi)
        if not rel.empty:
            self.assertTrue((rel["relationship_strength"] >= 0).all())


if __name__ == "__main__":
    unittest.main()
