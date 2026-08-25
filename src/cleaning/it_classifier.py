"""
IT Job Relevance Classifier.

Dynamically loads inclusion, exclusion, and ambiguous keywords from config/it_keywords.txt
and evaluates job titles to classify their relevance to the research study.
"""

import pathlib


class ITClassifier:
    """Classifies job titles based on IT keywords to filter out non-IT roles."""

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

    def load_keywords(self):
        """Parses the configuration file for sectioned keywords."""
        if not self.config_file.exists():
            # Soft fallback to basic defaults if config is missing
            self.inclusions = ["software", "developer", "engineer", "qa", "quality assurance", "test"]
            self.exclusions = ["graphic", "sales", "marketing", "multimedia"]
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
                    # Strip out labels (e.g. "graphic | graphic designer" -> "graphic")
                    kw = line.split("|")[0].strip().lower() if "|" in line else line.lower()
                    self.exclusions.append(kw)
                elif current_section == "AMBIGUOUS KEYWORDS":
                    self.ambiguous.append(line.lower())

    def evaluate_title(self, title: str):
        """Evaluates a job title to determine IT relevance.

        Returns:
            (is_it: bool, is_ambiguous: bool, reason: str)
            - is_it=True: It's a valid or ambiguous IT job.
            - is_it=False: It's a non-IT job to be excluded.
        """
        if not title or not isinstance(title, str):
            return True, True, "ambiguous - empty or invalid title type"

        title_lower = title.lower()

        # 1. Check exclusions first
        for exc in self.exclusions:
            if exc in title_lower:
                # Exception check: if it also matches a key IT inclusion word (e.g. "Salesforce Developer")
                # we keep it.
                has_inclusion = any(inc in title_lower for inc in self.inclusions)
                if not has_inclusion:
                    return False, False, f"Non-IT role: matches exclusion keyword '{exc}'"

        # 2. Check inclusions
        is_included = any(inc in title_lower for inc in self.inclusions)

        # 3. Check ambiguity
        # Even if included, check if it contains ambiguous words (e.g. "QA Intern", "Product Designer")
        is_ambig = False
        if is_included:
            if any(amb in title_lower for amb in self.ambiguous):
                is_ambig = True
        else:
            # Not explicitly included, but could be ambiguous IT (e.g. "Project Manager", "IT Executive")
            if any(amb in title_lower for amb in self.ambiguous) or "it" in title_lower.split():
                is_ambig = True

        if is_ambig:
            return True, True, "ambiguous - flagged for manual review"
        elif is_included:
            return True, False, ""
        else:
            return False, False, "Non-IT role: does not match IT inclusion criteria"
