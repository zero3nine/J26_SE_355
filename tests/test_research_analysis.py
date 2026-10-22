"""
Automated Test Suite for Individual Research Analytics Framework.
Research Component: IT4010 - Skill Relationship & Technology Stack Analysis
Student ID: IT23321854 / Project ID: J26_SE_355

Validates:
1. Co-occurrence matrix and Jaccard similarity calculations.
2. PMI and bounded Normalized PMI (NPMI) with rare-pair threshold filtering.
3. Association rule mining (support, confidence, lift).
4. Network construction, edge weighting, degree/betweenness/closeness centrality, and community clustering.
5. OCR source analysis: Ingestion funnel, yield %, text length distributions, and record traceability.
6. Cross-method comparison: Lexical vs. Semantic vs. Combined on identical ad population, Venn overlap, rank shifts, stack stability.
7. Source evidence traceability: Context snippet extraction and verifiable ad linkage.
8. Comprehensive research analysis execution: Artifact persistence and schema integrity.
9. Empty dataset and insufficient data handling.
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
from src.analytics.ocr_analysis import analyze_ocr_source
from src.analytics.comparison import compare_extraction_methods
from src.analytics.evidence import build_source_evidence, _find_context_snippet
from src.analytics.run_analysis import run_analysis, run_comprehensive_analysis, build_network_edges


class TestResearchAnalysisSuite(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_root = Path(self.temp_dir.name)

        # Create a sample multi-job dataset for research testing
        self.sample_jobs = [
            {"Python", "Django", "PostgreSQL", "Docker", "REST API"},
            {"Python", "FastAPI", "PostgreSQL", "Docker"},
            {"Java", "Spring Boot", "MySQL", "Docker", "REST API"},
            {"Java", "Spring Boot", "PostgreSQL", "AWS"},
            {"JavaScript", "React", "Node.js", "TypeScript", "HTML", "CSS"},
            {"JavaScript", "React", "TypeScript", "CSS"},
            {"Python", "Django", "Docker", "AWS"},
            {"Python", "PostgreSQL", "Docker"},
        ]

        self.sample_records = [
            {
                "job_id": f"JOB_{i+1:03d}",
                "job_title_raw": title,
                "company": company,
                "location_raw": "Colombo",
                "country": "Sri Lanka",
                "source_platform": src,
                "description_type": dtype,
                "job_description": desc,
                "ocr_text_raw": ocr_t,
                "ocr_status": ocr_s,
                "ocr_confidence": ocr_c,
                "advert_image_urls": img_url,
                "lexical_skills": json.dumps(list(skills)),
                "semantic_skills": json.dumps(list(skills)),
                "collection_batch_id": "RUN_TEST_2026",
            }
            for i, (skills, title, company, src, dtype, desc, ocr_t, ocr_s, ocr_c, img_url) in enumerate([
                (self.sample_jobs[0], "Senior Python Engineer", "Acme IT", "topjobs", "text", "Looking for Senior Python Engineer with Django, PostgreSQL, Docker, and REST API.", "", "not_applicable", 0.0, ""),
                (self.sample_jobs[1], "Backend Developer", "TechSys", "itpro", "text", "Backend Developer experienced in Python, FastAPI, Docker, and PostgreSQL databases.", "", "not_applicable", 0.0, ""),
                (self.sample_jobs[2], "Java Software Engineer", "Virtusa", "topjobs", "image", "Please refer full details", "Java Software Engineer required. Skills: Java, Spring Boot, MySQL, Docker, REST API.", "success", 92.5, "https://topjobs.lk/img/adv1.jpg"),
                (self.sample_jobs[3], "Enterprise Java Dev", "IFS", "itpro", "text", "Java Developer with Spring Boot, PostgreSQL, and AWS cloud experience.", "", "not_applicable", 0.0, ""),
                (self.sample_jobs[4], "Frontend Developer", "WSO2", "topjobs", "text", "Modern Frontend Developer with JavaScript, React, Node.js, TypeScript, HTML, and CSS.", "", "not_applicable", 0.0, ""),
                (self.sample_jobs[5], "React Specialist", "Sysco Labs", "topjobs", "image", "Please refer full details", "React Developer needed. Expert in JavaScript, React, TypeScript, and CSS styling.", "success", 88.0, "https://topjobs.lk/img/adv2.jpg"),
                (self.sample_jobs[6], "Python Cloud Architect", "CodeGen", "itpro", "text", "Python Cloud Architect with Django, Docker, and AWS deployments.", "", "not_applicable", 0.0, ""),
                (self.sample_jobs[7], "Data Platform Dev", "Pearson", "topjobs", "image", "Please refer full details", "Short notice", "success", 40.0, "https://topjobs.lk/img/adv3.jpg"),
            ])
        ]
        self.df_sample = pd.DataFrame(self.sample_records)

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------------------
    # 1. Co-occurrence & Jaccard Calculations
    # -------------------------------------------------------------------------

    def test_01_cooccurrence_and_jaccard(self):
        """Test co-occurrence matrix symmetry and accurate Jaccard similarity scores."""
        matrix = calculate_cooccurrence_matrix(self.sample_jobs)
        self.assertIsInstance(matrix, pd.DataFrame)
        self.assertEqual(matrix.loc["Python", "Docker"], matrix.loc["Docker", "Python"])
        self.assertEqual(matrix.loc["Python", "Docker"], 4)

        df_jaccard = calculate_jaccard(self.sample_jobs)
        self.assertFalse(df_jaccard.empty)
        row_py_dock = df_jaccard[
            ((df_jaccard["skill_a"] == "Python") & (df_jaccard["skill_b"] == "Docker")) |
            ((df_jaccard["skill_a"] == "Docker") & (df_jaccard["skill_b"] == "Python"))
        ]
        self.assertEqual(len(row_py_dock), 1)
        j_val = row_py_dock.iloc[0]["jaccard"]
        # Python appears in 4 jobs, Docker in 5 jobs. Intersection = 4, Union = 4 + 5 - 4 = 5. Jaccard = 4/5 = 0.80
        self.assertAlmostEqual(j_val, 0.80, places=2)

    # -------------------------------------------------------------------------
    # 2. PMI & Bounded NPMI with Rare Pair Filtering
    # -------------------------------------------------------------------------

    def test_02_pmi_and_bounded_npmi(self):
        """Test Pointwise Mutual Information and bounded NPMI [-1, 1] with rare-pair filter."""
        df_pmi = calculate_pmi(self.sample_jobs, min_cooccurrence=2)
        self.assertFalse(df_pmi.empty)

        for _, row in df_pmi.iterrows():
            pmi_val = row["pmi"]
            npmi_val = row["npmi"]
            self.assertIsInstance(pmi_val, float)
            self.assertIsInstance(npmi_val, float)
            self.assertGreaterEqual(npmi_val, -1.0)
            self.assertLessEqual(npmi_val, 1.0)
            self.assertGreaterEqual(row["cooccurrence"], 2)

        # Verify Java and Spring Boot have high PMI
        row_java_spring = df_pmi[
            ((df_pmi["skill_a"] == "Java") & (df_pmi["skill_b"] == "Spring Boot")) |
            ((df_pmi["skill_a"] == "Spring Boot") & (df_pmi["skill_b"] == "Java"))
        ]
        self.assertEqual(len(row_java_spring), 1)
        self.assertGreater(row_java_spring.iloc[0]["pmi"], 0.0)

    # -------------------------------------------------------------------------
    # 3. Association Rules Mining
    # -------------------------------------------------------------------------

    def test_03_association_rules_metrics(self):
        """Test directional association rules: Support, Confidence, Lift."""
        df_rules = calculate_association_rules(self.sample_jobs, minimum_support=0.20)
        self.assertFalse(df_rules.empty)
        for _, r in df_rules.iterrows():
            self.assertGreaterEqual(r["support"], 0.20)
            self.assertIsInstance(r["confidence"], float)
            self.assertIsInstance(r["lift"], float)
            self.assertGreater(r["lift"], 0.0)

    # -------------------------------------------------------------------------
    # 4. Network Construction & Centrality Metrics
    # -------------------------------------------------------------------------

    def test_04_network_topology_and_centrality(self):
        """Test NetworkX graph metrics, centrality measures, and modularity communities."""
        df_pairs = calculate_pair_frequency(self.sample_jobs)
        df_jac = calculate_jaccard(self.sample_jobs)
        df_pmi = calculate_pmi(self.sample_jobs, min_cooccurrence=1)
        df_rel = build_relationship_table(df_pairs, df_jac, df_pmi)
        df_edges = build_network_edges(df_pairs, df_jac, df_pmi, minimum_frequency=1)
        self.assertFalse(df_edges.empty)

        nodes_df, topology = calculate_network_metrics(df_edges, min_weight=1.0)
        self.assertIn("density", topology)
        self.assertGreater(topology["density"], 0.0)

        self.assertFalse(nodes_df.empty)
        self.assertIn("degree_centrality", nodes_df.columns)
        self.assertIn("betweenness_centrality", nodes_df.columns)
        self.assertIn("closeness_centrality", nodes_df.columns)
        self.assertIn("community_id", nodes_df.columns)
        self.assertIn("category", nodes_df.columns)

        # Docker should have high degree centrality as it connects multiple stacks
        docker_row = nodes_df[nodes_df["skill"] == "Docker"]
        self.assertEqual(len(docker_row), 1)
        self.assertGreater(docker_row.iloc[0]["degree_centrality"], 0.0)

    # -------------------------------------------------------------------------
    # 5. OCR Source Analysis Funnel
    # -------------------------------------------------------------------------

    def test_05_ocr_source_analysis(self):
        """Test OCR processing funnel, text diagnostics, yield %, and traceable records."""
        ocr_rep = analyze_ocr_source(self.df_sample)
        self.assertEqual(ocr_rep["total_advertisements"], 8)
        self.assertEqual(ocr_rep["image_ads_collected"], 3)
        self.assertEqual(ocr_rep["ocr_processed_success"], 3)
        self.assertEqual(ocr_rep["ocr_usable_text"], 2)  # 2 ads have >= 20 chars
        self.assertEqual(ocr_rep["ocr_with_extracted_skills"], 3)
        self.assertAlmostEqual(ocr_rep["ocr_yield_pct"], (3 / 3) * 100, places=1)

        stats = ocr_rep["text_length_stats"]
        self.assertGreater(stats["mean"], 0.0)
        self.assertEqual(len(ocr_rep["traceable_records"]), 3)
        self.assertIn("ground_truth_status", ocr_rep)

    # -------------------------------------------------------------------------
    # 6. Cross-Method Comparison
    # -------------------------------------------------------------------------

    def test_06_cross_method_comparison(self):
        """Test multi-method comparative analytics across Lexical, Semantic, and Combined."""
        run_dir = self.output_root / "run_comp_test"
        # Run all three methods
        run_analysis(self.df_sample, run_dir, skill_mode="lexical_skills", run_id="TEST_RUN")
        run_analysis(self.df_sample, run_dir, skill_mode="semantic_skills", run_id="TEST_RUN")
        run_analysis(self.df_sample, run_dir, skill_mode="combined", run_id="TEST_RUN")

        comp_rep = compare_extraction_methods(run_dir, self.df_sample)
        self.assertIn("method_metrics", comp_rep)
        self.assertIn("venn_skill_breakdown", comp_rep)
        self.assertIn("top_skill_rank_shifts", comp_rep)
        self.assertIn("technology_stack_stability", comp_rep)
        self.assertIn("ground_truth_evaluation", comp_rep)

        self.assertEqual(len(comp_rep["method_metrics"]), 3)
        self.assertIn("stable_across_all_3", comp_rep["technology_stack_stability"])

    # -------------------------------------------------------------------------
    # 7. Source Evidence Traceability
    # -------------------------------------------------------------------------

    def test_07_source_evidence_traceability(self):
        """Test extraction of source snippets and verification without synthetic fabrication."""
        comb_dir = self.output_root / "run_ev_test" / "combined"
        comb_dir.mkdir(parents=True, exist_ok=True)
        run_analysis(self.df_sample, self.output_root / "run_ev_test", skill_mode="combined", run_id="TEST_RUN")

        df_rel = pd.read_csv(comb_dir / "skill_relationships.csv")
        df_st = pd.read_csv(comb_dir / "technology_stacks.csv")

        evidence = build_source_evidence(self.df_sample, df_rel, df_st, max_pairs=3, max_stacks=3)
        self.assertIsInstance(evidence, list)
        self.assertGreater(len(evidence), 0)

        for ev in evidence:
            self.assertIn("entity", ev)
            self.assertIn("job_id", ev)
            self.assertIn("text_excerpt", ev)
            self.assertIn("verification_status", ev)
            self.assertNotEqual(ev["text_excerpt"], "")

        # Test snippet extraction helper
        snippet = _find_context_snippet("We need an engineer who knows Python and Django for our web services.", ["Python", "Django"])
        self.assertIn("Python", snippet)

    # -------------------------------------------------------------------------
    # 8. Comprehensive Analysis Pipeline End-to-End
    # -------------------------------------------------------------------------

    def test_08_run_comprehensive_analysis_execution(self):
        """Test full execution of run_comprehensive_analysis and artifact persistence."""
        comp_output = self.output_root / "run_full_research"
        master_rep = run_comprehensive_analysis(
            input_path=self.df_sample,
            output_dir=comp_output,
            run_id="RESEARCH_EVAL_RUN_01",
            raw_df=self.df_sample,
            internal_df=self.df_sample,
            min_support=0.10,
        )

        self.assertEqual(master_rep["run_id"], "RESEARCH_EVAL_RUN_01")
        self.assertIn("lexical_skills", master_rep)
        self.assertIn("semantic_skills", master_rep)
        self.assertIn("combined", master_rep)
        self.assertIn("ocr_analysis", master_rep)
        self.assertIn("comparison", master_rep)
        self.assertIn("source_evidence", master_rep)

        # Verify filesystem artifacts
        self.assertTrue((comp_output / "lexical_skills" / "skill_network_nodes.csv").exists())
        self.assertTrue((comp_output / "semantic_skills" / "skill_network_nodes.csv").exists())
        self.assertTrue((comp_output / "combined" / "skill_network_nodes.csv").exists())
        self.assertTrue((comp_output / "ocr_analysis.json").exists())
        self.assertTrue((comp_output / "comparison_analysis.json").exists())
        self.assertTrue((comp_output / "source_evidence.json").exists())
        self.assertTrue((comp_output / "consolidated_report.json").exists())

    # -------------------------------------------------------------------------
    # 9. Empty and Insufficient Dataset Handling
    # -------------------------------------------------------------------------

    def test_09_empty_and_insufficient_datasets(self):
        """Test pipeline behavior when given zero records or postings without skills."""
        empty_dir = self.output_root / "run_empty"
        empty_df = pd.DataFrame(columns=["job_id", "lexical_skills", "semantic_skills", "source_url"])

        master_empty = run_comprehensive_analysis(
            input_path=empty_df,
            output_dir=empty_dir,
            run_id="EMPTY_RUN",
        )
        self.assertEqual(master_empty["total_eligible_ads"], 0)
        self.assertEqual(master_empty["status"], "insufficient_data")

        # Verify OCR analysis on empty input returns safe zero-schema
        ocr_empty = analyze_ocr_source(empty_df)
        self.assertEqual(ocr_empty["total_advertisements"], 0)
        self.assertEqual(ocr_empty["ocr_yield_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
