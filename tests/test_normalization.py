"""
Automated Unit Tests for Canonical Skill Normalization
Research Component: IT4010 - Skill Relationship & Technology Stack Analysis

Validates:
1. Alias mapping for key languages, frameworks, databases, and tools.
2. Case, whitespace, and punctuation invariance (e.g. JS, js, Javascript, JAVASCRIPT -> JavaScript).
3. Technology boundary preservation (Java != JavaScript, Node.js != JavaScript, TypeScript != JavaScript).
4. Substring isolation (Java does not match JavaScript).
5. Context-sensitive resolution for ambiguous abbreviations (e.g. TS -> TypeScript only with supportive context).
6. Intra-job canonical deduplication.
7. Category mappings and canonical ID conversions.
"""

from __future__ import annotations

import unittest
from src.extraction.normalization import (
    SkillNormalizer,
    get_skill_category,
    normalize_skill,
    normalize_skill_id,
    normalize_skill_set,
)


class TestCanonicalSkillNormalization(unittest.TestCase):
    """Test suite for Phase 1 Canonical Skill Normalization."""

    def setUp(self):
        self.normalizer = SkillNormalizer()

    # -------------------------------------------------------------------------
    # 1. JavaScript Aliases
    # -------------------------------------------------------------------------
    def test_javascript_alias_variants(self):
        aliases = ["JS", "js", "Javascript", "JAVASCRIPT", "JavaScript", "ecmascript", "es6"]
        for alias in aliases:
            canonical = normalize_skill(alias)
            self.assertEqual(canonical, "JavaScript", f"Failed for JavaScript alias: {alias}")

    # -------------------------------------------------------------------------
    # 2. Frameworks & Libraries (Node.js, React, .NET)
    # -------------------------------------------------------------------------
    def test_nodejs_alias_variants(self):
        aliases = ["NodeJS", "Node.js", "node js", "nodejs", "NODE.JS"]
        for alias in aliases:
            canonical = normalize_skill(alias)
            self.assertEqual(canonical, "Node.js", f"Failed for Node.js alias: {alias}")

    def test_react_alias_variants(self):
        aliases = ["ReactJS", "React.js", "React JS", "react", "reactjs", "REACT"]
        for alias in aliases:
            canonical = normalize_skill(alias)
            self.assertEqual(canonical, "React", f"Failed for React alias: {alias}")

    def test_dotnet_alias_variants(self):
        aliases = [".NET", "dotnet", "dot net", ".net core", "asp.net", "asp.net core"]
        for alias in aliases:
            canonical = normalize_skill(alias)
            self.assertEqual(canonical, ".NET", f"Failed for .NET alias: {alias}")

    # -------------------------------------------------------------------------
    # 3. Databases (PostgreSQL, MongoDB)
    # -------------------------------------------------------------------------
    def test_postgresql_alias_variants(self):
        aliases = ["PostgreSQL", "postgres", "Postgre SQL", "psql", "POSTGRESQL"]
        for alias in aliases:
            canonical = normalize_skill(alias)
            self.assertEqual(canonical, "PostgreSQL", f"Failed for PostgreSQL alias: {alias}")

    def test_mongodb_alias_variants(self):
        aliases = ["MongoDB", "mongo db", "mongo", "mongodb", "MONGODB"]
        for alias in aliases:
            canonical = normalize_skill(alias)
            self.assertEqual(canonical, "MongoDB", f"Failed for MongoDB alias: {alias}")

    # -------------------------------------------------------------------------
    # 4. Programming Languages (C#, C++, Python, PHP)
    # -------------------------------------------------------------------------
    def test_csharp_alias_variants(self):
        aliases = ["C Sharp", "C#", "csharp", "c-sharp", "CSHARP"]
        for alias in aliases:
            canonical = normalize_skill(alias)
            self.assertEqual(canonical, "C#", f"Failed for C# alias: {alias}")

    def test_cpp_alias_variants(self):
        aliases = ["C++", "cpp", "c plus plus"]
        for alias in aliases:
            canonical = normalize_skill(alias)
            self.assertEqual(canonical, "C++", f"Failed for C++ alias: {alias}")

    def test_python_alias_variants(self):
        aliases = ["Python", "python 3", "python3", "py"]
        for alias in aliases:
            canonical = normalize_skill(alias)
            self.assertEqual(canonical, "Python", f"Failed for Python alias: {alias}")

    # -------------------------------------------------------------------------
    # 5. Web & Markup (HTML5, CSS3)
    # -------------------------------------------------------------------------
    def test_html_css_alias_variants(self):
        self.assertEqual(normalize_skill("HTML5"), "HTML")
        self.assertEqual(normalize_skill("html"), "HTML")
        self.assertEqual(normalize_skill("CSS3"), "CSS")
        self.assertEqual(normalize_skill("css"), "CSS")

    # -------------------------------------------------------------------------
    # 6. Ambiguous Abbreviation: TS (TypeScript)
    # -------------------------------------------------------------------------
    def test_typescript_explicit_and_contextual(self):
        # Explicit name always maps to TypeScript
        self.assertEqual(normalize_skill("TypeScript"), "TypeScript")
        self.assertEqual(normalize_skill("typescript"), "TypeScript")

        # TS with supportive context confirms TypeScript
        context_tech = "Full stack web developer proficient in React and TS"
        self.assertEqual(normalize_skill("TS", context=context_tech), "TypeScript")
        self.assertEqual(normalize_skill("ts", context=context_tech), "TypeScript")

        # Lowercase 'ts' without supportive context must be rejected
        context_unrelated = "Position requires excellent communication and ts skills"
        self.assertIsNone(normalize_skill("ts", context=context_unrelated))

        # Empty context with lowercase 'ts' must be rejected
        self.assertIsNone(normalize_skill("ts", context=""))

    # -------------------------------------------------------------------------
    # 7. Negative Cases & Technology Boundary Preservation
    # -------------------------------------------------------------------------
    def test_java_never_merged_with_javascript(self):
        java_canonical = normalize_skill("Java")
        js_canonical = normalize_skill("JavaScript")
        self.assertEqual(java_canonical, "Java")
        self.assertEqual(js_canonical, "JavaScript")
        self.assertNotEqual(java_canonical, js_canonical)

    def test_nodejs_never_merged_with_javascript(self):
        node_canonical = normalize_skill("Node.js")
        js_canonical = normalize_skill("JavaScript")
        self.assertEqual(node_canonical, "Node.js")
        self.assertEqual(js_canonical, "JavaScript")
        self.assertNotEqual(node_canonical, js_canonical)

    def test_typescript_never_merged_with_javascript(self):
        ts_canonical = normalize_skill("TypeScript")
        js_canonical = normalize_skill("JavaScript")
        self.assertEqual(ts_canonical, "TypeScript")
        self.assertEqual(js_canonical, "JavaScript")
        self.assertNotEqual(ts_canonical, js_canonical)

    # -------------------------------------------------------------------------
    # 8. Intra-Job Canonical Deduplication
    # -------------------------------------------------------------------------
    def test_canonical_deduplication_within_job(self):
        # A single job listing mentioning multiple aliases for the same technology
        raw_job_skills = [
            "JS", "JavaScript", "js", "Javascript",
            "React", "ReactJS", "react.js",
            "PostgreSQL", "postgres",
            "C#", "csharp",
        ]
        canonical_set = normalize_skill_set(raw_job_skills)
        expected = {"JavaScript", "React", "PostgreSQL", "C#"}
        self.assertEqual(canonical_set, expected)
        # Verify exactly one count per technology
        self.assertEqual(len(canonical_set), 4)

    # -------------------------------------------------------------------------
    # 9. Category Assignment & ID Resolution
    # -------------------------------------------------------------------------
    def test_category_assignment(self):
        self.assertEqual(get_skill_category("Python"), "Programming Languages")
        self.assertEqual(get_skill_category("JavaScript"), "Programming Languages")
        self.assertEqual(get_skill_category("React"), "Frameworks & Libraries")
        self.assertEqual(get_skill_category("Node.js"), "Frameworks & Libraries")
        self.assertEqual(get_skill_category("PostgreSQL"), "Databases")
        self.assertEqual(get_skill_category("Docker"), "Cloud & Infrastructure")
        self.assertEqual(get_skill_category("Git"), "DevOps & CI/CD")
        self.assertEqual(get_skill_category("Software Testing"), "Testing & QA")

    def test_canonical_id_lookup(self):
        self.assertEqual(normalize_skill_id("C#"), "csharp")
        self.assertEqual(normalize_skill_id("csharp"), "csharp")
        self.assertEqual(normalize_skill_id("Node.js"), "nodejs")
        self.assertEqual(normalize_skill_id("PostgreSQL"), "postgresql")
        self.assertEqual(normalize_skill_id("JavaScript"), "javascript")

    # -------------------------------------------------------------------------
    # 10. Substring Isolation & False Co-occurrence Prevention
    # -------------------------------------------------------------------------
    def test_substring_isolation_java_in_javascript(self):
        """Verifies that text mentioning JavaScript does not trigger Java extraction."""
        from src.extraction.lexical import LexicalSkillExtractor
        from src.extraction.taxonomy import load_taxonomy
        from pathlib import Path

        tax = load_taxonomy(Path("config/skill_taxonomy.json"))
        extractor = LexicalSkillExtractor(tax)

        text = "We are seeking a senior JavaScript developer with React experience."
        result = extractor.extract(job_id="sub_test", text=text)
        extracted = {s.skill_id for s in result.skills}

        self.assertIn("javascript", extracted)
        self.assertNotIn("java", extracted, "Unsafe substring match: 'java' extracted from 'JavaScript'!")

    def test_deduplication_prevents_false_cooccurrence_pairs(self):
        """
        When a job advert mentions both 'JS' and 'JavaScript', canonical normalization
        and deduplication must prevent ('JavaScript', 'JS') from forming a false co-occurrence pair.
        """
        from src.analytics.cooccurrence import calculate_pair_frequency

        raw_job = ["JS", "JavaScript", "js", "Javascript"]
        canonical_job = normalize_skill_set(raw_job)

        # After normalization and deduplication, exactly 1 canonical skill remains
        self.assertEqual(canonical_job, {"JavaScript"})

    # -------------------------------------------------------------------------
    # 11. C, C++, C# Technology Boundaries
    # -------------------------------------------------------------------------
    def test_c_cpp_csharp_boundaries(self):
        c_norm = normalize_skill("C")
        cpp_norm = normalize_skill("C++")
        csharp_norm = normalize_skill("C#")
        
        self.assertEqual(c_norm, "C")
        self.assertEqual(cpp_norm, "C++")
        self.assertEqual(csharp_norm, "C#")
        
        # Verify strict separation
        self.assertNotEqual(c_norm, cpp_norm)
        self.assertNotEqual(c_norm, csharp_norm)
        self.assertNotEqual(cpp_norm, csharp_norm)

    # -------------------------------------------------------------------------
    # 12. Java, Jakarta EE, and JavaScript Separation
    # -------------------------------------------------------------------------
    def test_java_jakarta_ee_javascript_separation(self):
        java_norm = normalize_skill("Java")
        jakarta_norm = normalize_skill("Jakarta EE")
        j2ee_norm = normalize_skill("J2EE")
        js_norm = normalize_skill("JavaScript")

        self.assertEqual(java_norm, "Java")
        self.assertEqual(jakarta_norm, "Jakarta EE")
        self.assertEqual(j2ee_norm, "Jakarta EE")
        self.assertEqual(js_norm, "JavaScript")

        # Distinct technologies must not be merged
        self.assertNotEqual(java_norm, jakarta_norm)
        self.assertNotEqual(java_norm, js_norm)
        self.assertNotEqual(jakarta_norm, js_norm)

    # -------------------------------------------------------------------------
    # 13. Audit Terms Method
    # -------------------------------------------------------------------------
    def test_normalization_audit_reporting(self):
        from src.extraction.normalization import audit_skill_terms
        
        sample_terms = ["JavaScript", "JS", "NodeJS", "Python", "UnknownFictionalTool123"]
        audit = audit_skill_terms(sample_terms)
        
        self.assertEqual(audit["total_terms"], 5)
        self.assertEqual(audit["mapped_count"], 4)
        self.assertEqual(audit["unmapped_count"], 1)
        self.assertIn("UnknownFictionalTool123", audit["unmapped_terms"])
    # -------------------------------------------------------------------------
    # 14. React vs React Native Separation
    # -------------------------------------------------------------------------
    def test_react_vs_react_native_separation(self):
        react = normalize_skill("React")
        react_js = normalize_skill("react.js")
        react_native = normalize_skill("React Native")
        react_native_hyphen = normalize_skill("react-native")

        self.assertEqual(react, "React")
        self.assertEqual(react_js, "React")
        self.assertEqual(react_native, "React Native")
        self.assertEqual(react_native_hyphen, "React Native")

        # Distinct technologies must not be merged
        self.assertNotEqual(react, react_native)

    # -------------------------------------------------------------------------
    # 15. Placeholder Rejection
    # -------------------------------------------------------------------------
    def test_placeholders_never_treated_as_skills(self):
        placeholders = ["None", "null", "nan", "N/A", "undefined", "empty", "[]", ""]
        for p in placeholders:
            self.assertIsNone(normalize_skill(p), f"Placeholder was treated as skill: {p}")

    # -------------------------------------------------------------------------
    # 16. Explainable Rule Resolution
    # -------------------------------------------------------------------------
    def test_resolve_term_with_rule(self):
        can, rule = self.normalizer.resolve_term_with_rule("JS")
        self.assertEqual(can, "JavaScript")
        self.assertEqual(rule, "Verified Taxonomy Alias Match")

        can, rule = self.normalizer.resolve_term_with_rule("Python")
        self.assertEqual(can, "Python")
        self.assertEqual(rule, "Canonical Identity Match")

        can, rule = self.normalizer.resolve_term_with_rule("react.js")
        self.assertEqual(can, "React")
        self.assertEqual(rule, "Verified Taxonomy Alias Match")

        can, rule = self.normalizer.resolve_term_with_rule("node_js")
        self.assertEqual(can, "Node.js")
        self.assertEqual(rule, "Punctuation & Whitespace Normalization")


if __name__ == "__main__":
    unittest.main()



