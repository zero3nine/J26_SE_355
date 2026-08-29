"""
IT Job Relevance Classifier.

Dynamically loads inclusion, exclusion, and ambiguous keywords from config/it_keywords.txt
and evaluates job titles, categories, skills, and descriptions to classify their relevance.
"""

import pathlib
import re
import json


class ITClassifier:
    """Classifies job relevance based on multiple weighted signals."""

    CLASSIFIER_VERSION = "2.0.0"
    RULES_VERSION = "2.0.0"

    def __init__(self, config_path=None):
        if config_path is None:
            project_root = pathlib.Path(__file__).resolve().parent.parent.parent
            self.config_file = project_root / "config" / "it_keywords.txt"
        else:
            self.config_file = pathlib.Path(config_path)

        self.inclusions = []
        self.exclusions = []
        self.ambiguous = []
        self.load_keywords()

        # Generic titles that require technical evidence to be considered IT
        self.generic_titles = {
            "intern", "trainee", "associate", "consultant", "manager",
            "director", "coordinator", "co-ordinator", "executive", "officer"
        }

        # Strong inclusion terms that can override exclusions (e.g. "Salesforce Developer")
        self.strong_overrides = {
            "developer", "engineer", "qa", "programmer", "architect", "software",
            "devops", "sre", "sysadmin", "fullstack", "frontend", "backend"
        }

    def load_keywords(self):
        """Parses the configuration file for sectioned keywords."""
        if not self.config_file.exists():
            # Soft fallback to basic defaults if config is missing
            self.inclusions = ["software", "developer", "engineer", "qa", "quality assurance", "test"]
            self.exclusions = ["graphic", "sales", "marketing", "multimedia", "operator"]
            self.ambiguous = ["manager", "intern", "trainee", "associate"]
            return

        current_section = None
        with open(self.config_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("##"):
                    current_section = line.replace("##", "").strip().upper()
                    continue
                if line.startswith("#"):
                    continue

                if current_section == "INCLUSION KEYWORDS":
                    self.inclusions.append(line.lower())
                elif current_section == "EXCLUSION KEYWORDS":
                    kw = line.split("|")[0].strip().lower() if "|" in line else line.lower()
                    self.exclusions.append(kw)
                elif current_section == "AMBIGUOUS KEYWORDS":
                    self.ambiguous.append(line.lower())

    def _matches_token(self, text: str, pattern: str) -> bool:
        """Helper to match a pattern using word/token boundaries."""
        if not text or not pattern:
            return False
        # Escape pattern and search using word boundaries
        regex_pattern = r"\b" + re.escape(pattern.lower()) + r"\b"
        return bool(re.search(regex_pattern, text.lower()))

    def classify(self, title: str, category: str = "", skills: str = "", description: str = "") -> dict:
        """Evaluates multiple signals to classify a job.

        Returns:
            dict containing:
                - status: "it" | "non_it" | "ambiguous" | "insufficient_data"
                - is_it: bool (True for "it" or "ambiguous" to keep in review, False for "non_it" to exclude)
                - explanation: dict with matching details and score
                - decision_basis: str
        """
        title = (title or "").strip()
        category = (category or "").strip()
        skills = (skills or "").strip()
        description = (description or "").strip()

        if not title and not description:
            explanation = {
                "matched_title_signals": [],
                "matched_category_signals": [],
                "matched_technical_requirements": [],
                "exclusion_signals": ["Empty title and description"],
                "final_score": 0.0,
                "decision_basis": "Insufficient data provided for classification.",
                "manual_review_reason": "Empty job record fields."
            }
            return {
                "status": "insufficient_data",
                "is_it": False,
                "explanation": explanation,
                "decision_basis": "Empty job record fields."
            }

        title_lower = title.lower()

        # 1. Exclusion Signals Check
        matched_exclusions = []
        for exc in self.exclusions:
            if self._matches_token(title_lower, exc):
                # Check for strong inclusion overrides
                has_override = any(self._matches_token(title_lower, ovr) for ovr in self.strong_overrides)
                if not has_override:
                    matched_exclusions.append(exc)

        if matched_exclusions:
            explanation = {
                "matched_title_signals": [],
                "matched_category_signals": [],
                "matched_technical_requirements": [],
                "exclusion_signals": matched_exclusions,
                "final_score": 0.0,
                "decision_basis": f"Excluded due to title matching non-IT keywords: {matched_exclusions}",
                "manual_review_reason": ""
            }
            return {
                "status": "non_it",
                "is_it": False,
                "explanation": explanation,
                "decision_basis": f"Non-IT role: matched exclusions {matched_exclusions}"
            }

        # 2. Gather Signal Metrics
        matched_inclusions_title = [inc for inc in self.inclusions if self._matches_token(title_lower, inc)]
        matched_ambiguous_title = [amb for amb in self.ambiguous if self._matches_token(title_lower, amb)]
        is_generic_title = any(self._matches_token(title_lower, gen) for gen in self.generic_titles)

        # Technical Evidence Gathered
        # Technical evidence: finding specific inclusion keywords in skills/description
        matched_tech_skills = [inc for inc in self.inclusions if self._matches_token(skills, inc)]
        matched_tech_desc = [inc for inc in self.inclusions if self._matches_token(description, inc)]
        
        # Category matches
        category_lower = category.lower()
        matched_categories = [inc for inc in self.inclusions if self._matches_token(category_lower, inc)]
        if "it" in category_lower.split() or "software" in category_lower or "technology" in category_lower:
            if "information technology" not in matched_categories:
                matched_categories.append("it/software")

        # 3. Calculate Weighted Scores
        title_score = 0.0
        category_score = 0.0
        skills_score = 0.0
        desc_score = 0.0

        # Title Weight (0.5 max)
        if matched_inclusions_title:
            if is_generic_title:
                # If title is generic (e.g. "Software Intern" or "IT Consultant")
                # we require tech evidence to confirm it.
                if matched_tech_skills or matched_tech_desc:
                    title_score = 0.4
                else:
                    title_score = 0.2
            else:
                title_score = 0.5
        elif is_generic_title:
            # Title is generic with no direct inclusion keyword (e.g. "Trainee")
            if matched_tech_skills or matched_tech_desc:
                title_score = 0.2
            else:
                title_score = 0.05
        else:
            # Check if title contains general IT hints like "IT" as standalone word
            if "it" in title_lower.split():
                title_score = 0.3

        # Category Weight (0.2 max)
        if matched_categories:
            category_score = 0.2

        # Skills Weight (0.2 max)
        if matched_tech_skills:
            skills_score = 0.2
        elif skills.strip():
            # Some text but no direct keywords
            skills_score = 0.05

        # Description Weight (0.1 max)
        if matched_tech_desc:
            desc_score = 0.1
        elif description.strip():
            desc_score = 0.02

        total_score = title_score + category_score + skills_score + desc_score

        # 4. Final Classification Decision
        status = "non_it"
        manual_review_reason = ""
        decision_basis = ""

        if total_score >= 0.4:
            # Check for ambiguity factors (e.g., interns, trainees, ambiguous title keywords)
            if matched_ambiguous_title or is_generic_title:
                status = "ambiguous"
                manual_review_reason = f"Generic or ambiguous title keyword: {matched_ambiguous_title or list(self.generic_titles & set(title_lower.split()))}"
                decision_basis = "Flagged for review because title contains generic/ambiguous roles despite IT score."
            else:
                status = "it"
                decision_basis = "Classified as IT due to strong technical matches."
        elif total_score >= 0.15:
            status = "ambiguous"
            manual_review_reason = "Low classification score, needs verification"
            decision_basis = "Flagged for manual review due to partial IT matching signals."
        else:
            status = "non_it"
            decision_basis = "Classified as Non-IT due to low match scores."

        # Double check: "Generic 'Trainee' is marked ambiguous unless technical evidence exists."
        # If it's a generic trainee with no tech evidence:
        if is_generic_title and not matched_inclusions_title and not matched_tech_skills and not matched_tech_desc:
            status = "ambiguous"
            manual_review_reason = "Generic title without technical evidence"
            decision_basis = "Generic trainee/intern role without technical matching evidence."

        explanation = {
            "matched_title_signals": matched_inclusions_title,
            "matched_category_signals": matched_categories,
            "matched_technical_requirements": list(set(matched_tech_skills + matched_tech_desc)),
            "exclusion_signals": [],
            "final_score": float(f"{total_score:.2f}"),
            "decision_basis": decision_basis,
            "manual_review_reason": manual_review_reason
        }

        return {
            "status": status,
            "is_it": status in ("it", "ambiguous"),
            "explanation": explanation,
            "decision_basis": decision_basis
        }

    def evaluate_title(self, title: str):
        """Deprecated compatibility method to match old pipeline interface.

        Returns:
            (is_it: bool, is_ambiguous: bool, reason: str)
        """
        res = self.classify(title)
        is_it = res["status"] in ("it", "ambiguous")
        is_ambig = res["status"] == "ambiguous"
        reason = ""
        if is_ambig:
            reason = "ambiguous - flagged for manual review"
        elif not is_it:
            excs = res["explanation"].get("exclusion_signals", [])
            if excs:
                reason = f"Non-IT role: matches exclusion keyword '{excs[0]}'"
            else:
                reason = res["explanation"]["decision_basis"]
        return is_it, is_ambig, reason

