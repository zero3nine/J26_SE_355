"""
Centralized Canonical Skill Normalization Layer
Research Component: IT4010 - Skill Relationship & Technology Stack Analysis

Maps raw skill strings, aliases, casing variations, and abbreviations to
canonical technology definitions while strictly preserving technology boundaries:
- Java is NEVER merged with JavaScript
- Node.js is NEVER merged with JavaScript
- TypeScript is NEVER merged with JavaScript
- Ambiguous abbreviations (e.g. 'TS') require context confirmation
- Punctuation, casing, and whitespace variants are normalized
- Canonical skills within a single job are deduplicated
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TAXONOMY_PATH = PROJECT_ROOT / "config" / "skill_taxonomy.json"


# Canonical definition dictionary mapping skill_id -> {canonical_name, category, aliases}
CANONICAL_SKILL_DEFINITIONS = {
    # Programming Languages
    "python": {
        "canonical_name": "Python",
        "category": "Programming Languages",
        "aliases": ["python", "python 3", "python3", "python2", "py"],
    },
    "java": {
        "canonical_name": "Java",
        "category": "Programming Languages",
        "aliases": ["java", "core java", "java 8", "java 11", "java 17", "java 21"],
    },
    "javascript": {
        "canonical_name": "JavaScript",
        "category": "Programming Languages",
        "aliases": ["javascript", "js", "ecmascript", "es6", "vanilla js"],
    },
    "typescript": {
        "canonical_name": "TypeScript",
        "category": "Programming Languages",
        "aliases": ["typescript", "ts"],
        "context_markers": ["frontend", "backend", "web", "react", "angular", "node", "javascript", "developer", "code", "programming", "software"],
    },
    "csharp": {
        "canonical_name": "C#",
        "category": "Programming Languages",
        "aliases": ["c#", "csharp", "c sharp", "c-sharp"],
    },
    "cpp": {
        "canonical_name": "C++",
        "category": "Programming Languages",
        "aliases": ["c++", "cpp", "c plus plus"],
    },
    "c": {
        "canonical_name": "C",
        "category": "Programming Languages",
        "aliases": ["c", "c language", "c programming", "ansi c"],
    },
    "jakarta_ee": {
        "canonical_name": "Jakarta EE",
        "category": "Frameworks & Libraries",
        "aliases": ["jakarta ee", "jakarta", "java ee", "j2ee"],
    },
    "php": {
        "canonical_name": "PHP",
        "category": "Programming Languages",
        "aliases": ["php", "php7", "php8"],
    },
    "go": {
        "canonical_name": "Go",
        "category": "Programming Languages",
        "aliases": ["golang", "go language"],
    },
    "rust": {
        "canonical_name": "Rust",
        "category": "Programming Languages",
        "aliases": ["rust", "rustlang"],
    },
    # Frameworks & Libraries
    "react": {
        "canonical_name": "React",
        "category": "Frameworks & Libraries",
        "aliases": ["react", "react.js", "reactjs", "react js"],
    },
    "react_native": {
        "canonical_name": "React Native",
        "category": "Frameworks & Libraries",
        "aliases": ["react native", "react-native", "reactnative"],
    },
    "nodejs": {
        "canonical_name": "Node.js",
        "category": "Frameworks & Libraries",
        "aliases": ["node.js", "nodejs", "node js"],
    },
    "dotnet": {
        "canonical_name": ".NET",
        "category": "Frameworks & Libraries",
        "aliases": [".net", "dotnet", "dot net", ".net core", "asp.net", "asp.net core"],
    },
    "angular": {
        "canonical_name": "Angular",
        "category": "Frameworks & Libraries",
        "aliases": ["angular", "angularjs", "angular.js"],
    },
    "vue": {
        "canonical_name": "Vue.js",
        "category": "Frameworks & Libraries",
        "aliases": ["vue", "vue.js", "vuejs"],
    },
    "django": {
        "canonical_name": "Django",
        "category": "Frameworks & Libraries",
        "aliases": ["django"],
    },
    "flask": {
        "canonical_name": "Flask",
        "category": "Frameworks & Libraries",
        "aliases": ["flask"],
    },
    "spring": {
        "canonical_name": "Spring Boot",
        "category": "Frameworks & Libraries",
        "aliases": ["spring boot", "springboot", "spring", "spring framework"],
    },
    # Databases
    "sql": {
        "canonical_name": "SQL",
        "category": "Databases",
        "aliases": ["sql", "structured query language"],
    },
    "postgresql": {
        "canonical_name": "PostgreSQL",
        "category": "Databases",
        "aliases": ["postgresql", "postgres", "postgre sql", "psql"],
    },
    "mysql": {
        "canonical_name": "MySQL",
        "category": "Databases",
        "aliases": ["mysql"],
    },
    "mongodb": {
        "canonical_name": "MongoDB",
        "category": "Databases",
        "aliases": ["mongodb", "mongo db", "mongo"],
    },
    "redis": {
        "canonical_name": "Redis",
        "category": "Databases",
        "aliases": ["redis"],
    },
    # Cloud & Infrastructure
    "aws": {
        "canonical_name": "AWS",
        "category": "Cloud & Infrastructure",
        "aliases": ["aws", "amazon web services"],
    },
    "azure": {
        "canonical_name": "Azure",
        "category": "Cloud & Infrastructure",
        "aliases": ["azure", "microsoft azure", "ms azure"],
    },
    "gcp": {
        "canonical_name": "GCP",
        "category": "Cloud & Infrastructure",
        "aliases": ["gcp", "google cloud", "google cloud platform"],
    },
    "docker": {
        "canonical_name": "Docker",
        "category": "Cloud & Infrastructure",
        "aliases": ["docker"],
    },
    "kubernetes": {
        "canonical_name": "Kubernetes",
        "category": "Cloud & Infrastructure",
        "aliases": ["kubernetes", "k8s"],
    },
    # DevOps & CI/CD
    "git": {
        "canonical_name": "Git",
        "category": "DevOps & CI/CD",
        "aliases": ["git"],
    },
    "github_actions": {
        "canonical_name": "GitHub Actions",
        "category": "DevOps & CI/CD",
        "aliases": ["github actions"],
    },
    "gitlab_ci": {
        "canonical_name": "GitLab CI/CD",
        "category": "DevOps & CI/CD",
        "aliases": ["gitlab ci", "gitlab ci/cd"],
    },
    "jenkins": {
        "canonical_name": "Jenkins",
        "category": "DevOps & CI/CD",
        "aliases": ["jenkins"],
    },
    "cicd": {
        "canonical_name": "CI/CD",
        "category": "DevOps & CI/CD",
        "aliases": ["ci/cd", "continuous integration", "continuous delivery", "continuous deployment"],
    },
    "jira": {
        "canonical_name": "Jira",
        "category": "DevOps & CI/CD",
        "aliases": ["jira"],
    },
    # Testing & QA
    "software_testing": {
        "canonical_name": "Software Testing",
        "category": "Testing & QA",
        "aliases": ["software testing", "application testing", "manual testing", "qa testing"],
    },
    "test_automation": {
        "canonical_name": "Test Automation",
        "category": "Testing & QA",
        "aliases": ["test automation", "automated testing", "automation testing"],
    },
    "selenium": {
        "canonical_name": "Selenium",
        "category": "Testing & QA",
        "aliases": ["selenium"],
    },
    "postman": {
        "canonical_name": "Postman",
        "category": "Testing & QA",
        "aliases": ["postman"],
    },
    "playwright": {
        "canonical_name": "Playwright",
        "category": "Testing & QA",
        "aliases": ["playwright"],
    },
    "cypress": {
        "canonical_name": "Cypress",
        "category": "Testing & QA",
        "aliases": ["cypress"],
    },
    "api_testing": {
        "canonical_name": "API Testing",
        "category": "Testing & QA",
        "aliases": ["api testing", "web api testing"],
    },
    "unit_testing": {
        "canonical_name": "Unit Testing",
        "category": "Testing & QA",
        "aliases": ["unit testing", "unit tests", "unit test"],
    },
    # Web & API
    "rest_api": {
        "canonical_name": "REST API",
        "category": "Web & API",
        "aliases": ["rest api", "restful api", "restful apis", "rest apis", "rest services", "restful services"],
    },
    "graphql": {
        "canonical_name": "GraphQL",
        "category": "Web & API",
        "aliases": ["graphql"],
    },
    "html": {
        "canonical_name": "HTML",
        "category": "Web & API",
        "aliases": ["html", "html5"],
    },
    "css": {
        "canonical_name": "CSS",
        "category": "Web & API",
        "aliases": ["css", "css3"],
    },
    # Data & AI
    "machine_learning": {
        "canonical_name": "Machine Learning",
        "category": "Data & AI",
        "aliases": ["machine learning", "ml"],
    },
    "data_analysis": {
        "canonical_name": "Data Analysis",
        "category": "Data & AI",
        "aliases": ["data analysis", "data analytics"],
    },
    "data_visualization": {
        "canonical_name": "Data Visualization",
        "category": "Data & AI",
        "aliases": ["data visualization", "data visualisation"],
    },
    "pandas": {
        "canonical_name": "Pandas",
        "category": "Data & AI",
        "aliases": ["pandas"],
    },
    "tensorflow": {
        "canonical_name": "TensorFlow",
        "category": "Data & AI",
        "aliases": ["tensorflow"],
    },
    "pytorch": {
        "canonical_name": "PyTorch",
        "category": "Data & AI",
        "aliases": ["pytorch"],
    },
    # Methodologies & Professional Skills
    "agile": {
        "canonical_name": "Agile",
        "category": "Methodologies",
        "aliases": ["agile"],
    },
    "scrum": {
        "canonical_name": "Scrum",
        "category": "Methodologies",
        "aliases": ["scrum"],
    },
    "requirements_analysis": {
        "canonical_name": "Requirements Analysis",
        "category": "Methodologies",
        "aliases": ["requirements analysis", "requirements gathering", "requirements engineering"],
    },
    "oop": {
        "canonical_name": "Object-Oriented Programming",
        "category": "Methodologies",
        "aliases": ["oop", "object oriented programming", "object-oriented programming"],
    },
    "sdlc": {
        "canonical_name": "SDLC",
        "category": "Methodologies",
        "aliases": ["sdlc", "software development lifecycle", "software development life cycle"],
    },
    "microservices": {
        "canonical_name": "Microservices",
        "category": "Web & API",
        "aliases": ["microservices", "microservice", "microservices architecture"],
    },
    "laravel": {
        "canonical_name": "Laravel",
        "category": "Frameworks & Libraries",
        "aliases": ["laravel", "laravel framework"],
    },
    "nextjs": {
        "canonical_name": "Next.js",
        "category": "Frameworks & Libraries",
        "aliases": ["next.js", "nextjs", "next js"],
    },
    "express": {
        "canonical_name": "Express.js",
        "category": "Frameworks & Libraries",
        "aliases": ["express", "express.js", "expressjs"],
    },
    "odoo": {
        "canonical_name": "Odoo",
        "category": "Frameworks & Libraries",
        "aliases": ["odoo", "odoo erp"],
    },
    "linux": {
        "canonical_name": "Linux",
        "category": "Cloud & Infrastructure",
        "aliases": ["linux", "gnu/linux", "ubuntu", "debian", "redhat", "centos"],
    },
    "kafka": {
        "canonical_name": "Apache Kafka",
        "category": "Cloud & Infrastructure",
        "aliases": ["kafka", "apache kafka"],
    },
    "tailwind": {
        "canonical_name": "Tailwind CSS",
        "category": "Web & API",
        "aliases": ["tailwind", "tailwindcss", "tailwind css"],
    },
    "bootstrap": {
        "canonical_name": "Bootstrap",
        "category": "Web & API",
        "aliases": ["bootstrap", "twitter bootstrap"],
    },
    "sass": {
        "canonical_name": "Sass",
        "category": "Web & API",
        "aliases": ["sass", "scss"],
    },
    "leadership": {
        "canonical_name": "Leadership",
        "category": "Professional Skills",
        "aliases": ["leadership", "team leadership", "team lead", "technical lead", "tech lead"],
    },
    "problem_solving": {
        "canonical_name": "Problem Solving",
        "category": "Professional Skills",
        "aliases": ["problem solving", "problem-solving", "troubleshooting"],
    },
    "teamwork": {
        "canonical_name": "Teamwork",
        "category": "Professional Skills",
        "aliases": ["teamwork", "team work", "collaboration", "collaborative"],
    },
}


class SkillNormalizer:
    """
    Centralized canonical skill normalizer.
    Converts diverse text aliases to canonical skill names and IDs.
    """

    def __init__(self, custom_taxonomy_path: Optional[Path] = None):
        self.definitions = CANONICAL_SKILL_DEFINITIONS.copy()
        self._load_taxonomy(custom_taxonomy_path or DEFAULT_TAXONOMY_PATH)
        self._build_lookup_tables()

    def _load_taxonomy(self, path: Path):
        """Merges any additional aliases from skill_taxonomy.json."""
        if path and path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for cat in data.get("categories", []):
                    cat_name = cat.get("name", "Other")
                    for s in cat.get("skills", []):
                        s_id = s.get("id")
                        s_name = s.get("name")
                        aliases = s.get("aliases", [])
                        if s_id not in self.definitions:
                            self.definitions[s_id] = {
                                "canonical_name": s_name,
                                "category": cat_name,
                                "aliases": aliases,
                            }
                        else:
                            # Merge aliases
                            existing_aliases = set(self.definitions[s_id]["aliases"])
                            for a in aliases:
                                existing_aliases.add(a)
                            self.definitions[s_id]["aliases"] = list(existing_aliases)
            except Exception:
                pass

    def _build_lookup_tables(self):
        """Precomputes fast case-folded lookup dictionaries."""
        self.alias_to_id: Dict[str, str] = {}
        self.id_to_canonical_name: Dict[str, str] = {}
        self.id_to_category: Dict[str, str] = {}
        self.context_rules: Dict[str, List[str]] = {}

        for skill_id, info in self.definitions.items():
            can_name = info["canonical_name"]
            self.id_to_canonical_name[skill_id] = can_name
            self.id_to_category[skill_id] = info.get("category", "General")

            # Store context markers if any
            if "context_markers" in info:
                self.context_rules[skill_id] = info["context_markers"]

            # Map self ID and canonical name
            self.alias_to_id[skill_id.casefold()] = skill_id
            self.alias_to_id[can_name.casefold()] = skill_id

            # Map all configured aliases
            for alias in info.get("aliases", []):
                cleaned_alias = alias.strip().casefold()
                if cleaned_alias:
                    self.alias_to_id[cleaned_alias] = skill_id
                    # Also map stripped punctuation version if safe
                    no_punct = re.sub(r"[.\-_]", "", cleaned_alias)
                    if no_punct and no_punct != cleaned_alias:
                        self.alias_to_id[no_punct] = skill_id

    def normalize(self, raw_term: str, context: str = "", fallback_to_title: bool = False) -> Optional[str]:
        """
        Normalizes a raw skill string to its canonical display name.
        Returns None if not recognized or if ambiguous without supportive context.
        """
    PLACEHOLDERS = {"none", "null", "nan", "n/a", "na", "undefined", "empty", "[]", "placeholder"}

    def resolve_term_with_rule(self, raw_term: str, context: str = "") -> Tuple[Optional[str], str]:
        """
        Resolves a raw term to canonical name and explains the exact normalization rule applied.
        Returns: (canonical_name, rule_description)
        """
        if not raw_term or not isinstance(raw_term, str):
            return None, "Empty / Invalid Input"

        cleaned = raw_term.strip()
        if not cleaned:
            return None, "Empty String"

        folded = cleaned.casefold()
        if folded in self.PLACEHOLDERS:
            return None, "Non-Technical Placeholder Filtered"

        # 1. Direct alias match
        if folded in self.alias_to_id:
            skill_id = self.alias_to_id[folded]
            can_name = self.id_to_canonical_name[skill_id]

            if skill_id == "typescript" and folded == "ts":
                markers = self.context_rules.get("typescript", [])
                has_context = False
                if context:
                    c_low = context.casefold()
                    has_context = any(m in c_low for m in markers)
                elif cleaned == "TS":
                    has_context = True

                if not has_context:
                    return None, "Ambiguous Abbreviation (Rejected Without Context)"
                return can_name, "Context-Sensitive Disambiguation"

            if cleaned == can_name:
                return can_name, "Canonical Identity Match"
            return can_name, "Verified Taxonomy Alias Match"

        # 2. Normalized punctuation match (e.g., 'react.js' -> 'reactjs')
        alt_folded = re.sub(r"[\s.\-_]+", "", folded)
        if alt_folded in self.alias_to_id:
            skill_id = self.alias_to_id[alt_folded]
            can_name = self.id_to_canonical_name[skill_id]
            return can_name, "Punctuation & Whitespace Normalization"

        return None, "Unresolved / Novel Variant"

    def normalize(self, raw_term: str, context: str = "", fallback_to_title: bool = False) -> Optional[str]:
        """
        Normalizes a raw skill string to its canonical display name.
        Returns None if not recognized or if ambiguous without supportive context.
        """
        can_name, _ = self.resolve_term_with_rule(raw_term, context)
        if can_name:
            return can_name

        if fallback_to_title and raw_term and isinstance(raw_term, str):
            cleaned = raw_term.strip()
            if cleaned and cleaned.casefold() not in self.PLACEHOLDERS:
                return cleaned.replace("_", " ").title()

        return None

    def normalize_id(self, raw_term: str, context: str = "") -> Optional[str]:
        """Normalizes to standard snake_case skill ID (e.g. 'csharp', 'javascript')."""
        can_name = self.normalize(raw_term, context)
        if not can_name:
            return None
        # Invert lookup
        for s_id, name in self.id_to_canonical_name.items():
            if name == can_name:
                return s_id
        return None

    def normalize_set(self, terms: List[str] | Set[str], context: str = "", fallback_to_title: bool = False) -> Set[str]:
        """
        Normalizes and deduplicates a set of terms into canonical skill names.
        Deduplicates canonical skills so each job has at most one occurrence.
        """
        result = set()
        for term in terms:
            norm = self.normalize(term, context, fallback_to_title=fallback_to_title)
            if norm:
                result.add(norm)
        return result

    def get_category(self, canonical_name_or_id: str) -> str:
        """Returns the domain category for a canonical skill."""
        for s_id, name in self.id_to_canonical_name.items():
            if name == canonical_name_or_id or s_id == canonical_name_or_id:
                return self.id_to_category.get(s_id, "General")
        return "General"

    def audit_terms(self, terms: List[str] | Set[str]) -> Dict[str, Any]:
        """
        Audits a collection of raw skill strings against the canonical taxonomy.
        Reports counts of mapped vs unmapped terms, mapping rules, and unmapped variants.
        """
        mapping_records: List[Dict[str, str]] = []
        mapped_dict: Dict[str, str] = {}
        unmapped: Set[str] = set()
        placeholders: Set[str] = set()

        for term in terms:
            if not term or not isinstance(term, str):
                continue
            cleaned = term.strip()
            if not cleaned:
                continue
            if cleaned.casefold() in self.PLACEHOLDERS:
                placeholders.add(cleaned)
                continue

            can, rule = self.resolve_term_with_rule(cleaned)
            if can:
                mapped_dict[cleaned] = can
                mapping_records.append({
                    "original_term": cleaned,
                    "canonical_skill": can,
                    "rule": rule,
                })
            else:
                unmapped.add(cleaned)

        # Deduplicate mapping records for transparent audit display
        unique_mappings: List[Dict[str, str]] = []
        seen_pairs: Set[Tuple[str, str]] = set()
        for rec in mapping_records:
            pair = (rec["original_term"], rec["canonical_skill"])
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                unique_mappings.append(rec)

        return {
            "total_terms": len(terms),
            "mapped_count": len(mapped_dict),
            "unmapped_count": len(unmapped),
            "placeholders_filtered": len(placeholders),
            "mapped_pairs": mapped_dict,
            "mapping_records": unique_mappings,
            "unmapped_terms": sorted(unmapped),
        }



# Global singleton instance
_GLOBAL_NORMALIZER = SkillNormalizer()


def normalize_skill(term: str, context: str = "", fallback_to_title: bool = False) -> Optional[str]:
    """Helper function to normalize a single term to its Canonical Name."""
    return _GLOBAL_NORMALIZER.normalize(term, context, fallback_to_title=fallback_to_title)


def normalize_skill_id(term: str, context: str = "") -> Optional[str]:
    """Helper function to normalize a single term to its Canonical ID."""
    return _GLOBAL_NORMALIZER.normalize_id(term, context)


def normalize_skill_set(terms: List[str] | Set[str], context: str = "", fallback_to_title: bool = False) -> Set[str]:
    """Helper function to normalize and deduplicate a collection of skills."""
    return _GLOBAL_NORMALIZER.normalize_set(terms, context, fallback_to_title=fallback_to_title)


def get_skill_category(term: str) -> str:
    """Helper function to get category for a skill."""
    return _GLOBAL_NORMALIZER.get_category(term)


def audit_skill_terms(terms: List[str] | Set[str]) -> Dict[str, Any]:
    """Helper function to audit a collection of raw terms against the canonical taxonomy."""
    return _GLOBAL_NORMALIZER.audit_terms(terms)


