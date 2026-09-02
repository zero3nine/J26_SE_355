import unittest

from src.roles.models import Role, RoleTaxonomy
from src.roles.classifier import RoleClassifier, UNCLASSIFIED_ROLE_NAME


def build_test_taxonomy():
    """A small taxonomy covering the same shape as config/role_taxonomy.json,
    kept local to this test so it doesn't depend on the real file changing.
    """
    return RoleTaxonomy(
        taxonomy_version="test",
        name="Test Role Taxonomy",
        description="",
        roles=[
            Role(
                id="software_engineer",
                name="Software Engineer / Developer",
                aliases=["software engineer", "mern stack", "full stack", "developer"],
            ),
            Role(
                id="qa_test_engineer",
                name="QA / Test Engineer",
                aliases=["qa engineer", "test engineer", "automation tester"],
            ),
            Role(
                id="devops_engineer",
                name="DevOps Engineer",
                aliases=["devops engineer", "dev-ops engineer", "site reliability engineer"],
            ),
            Role(
                id="it_support_sysadmin",
                name="IT Support / System Administrator",
                aliases=["it support", "system administrator", "administrator"],
            ),
            Role(
                id="software_architect",
                name="Software Architect",
                aliases=["software architect", "architect"],
            ),
        ],
    )


class RoleClassifierTests(unittest.TestCase):

    def setUp(self):
        self.classifier = RoleClassifier(build_test_taxonomy())

    def test_classifies_exact_role_title(self):
        role_id, role_name, alias = self.classifier.classify("QA Engineer - Automation")
        self.assertEqual(role_id, "qa_test_engineer")
        self.assertEqual(role_name, "QA / Test Engineer")

    def test_classifies_compound_title(self):
        role_id, role_name, alias = self.classifier.classify("Senior MERN Stack Developer")
        self.assertEqual(role_id, "software_engineer")

    def test_prefers_more_specific_alias_over_shorter_one(self):
        # "Software Architect" contains "architect" too, but the longer,
        # more specific alias must win regardless of which role lists it
        # or where that role sits in the taxonomy -- this is the exact
        # global-sort bug fix described in classifier.py's docstring.
        role_id, role_name, alias = self.classifier.classify("Software Architect | Colombo")
        self.assertEqual(role_id, "software_architect")
        self.assertEqual(alias, "software architect")

    def test_title_takes_priority_over_description(self):
        role_id, role_name, alias = self.classifier.classify(
            title="IT Support Engineer",
            description="Occasionally assists the software architect with documentation.",
        )
        self.assertEqual(role_id, "it_support_sysadmin")

    def test_falls_back_to_description_when_title_is_vague(self):
        role_id, role_name, alias = self.classifier.classify(
            title="IT Vacancy - Ragama",
            description="Looking for a DevOps Engineer to manage our CI/CD pipeline.",
        )
        self.assertEqual(role_id, "devops_engineer")

    def test_returns_unclassified_when_nothing_matches(self):
        role_id, role_name, alias = self.classifier.classify(
            title="IT Freshers",
            description="Basic HTML knowledge, good command of English.",
        )
        self.assertEqual(role_name, UNCLASSIFIED_ROLE_NAME)

    def test_hyphenated_variant_still_matches(self):
        role_id, role_name, alias = self.classifier.classify("Dev-Ops Engineer")
        self.assertEqual(role_id, "devops_engineer")

    def test_case_insensitive(self):
        role_id, role_name, alias = self.classifier.classify("SOFTWARE ARCHITECT")
        self.assertEqual(role_id, "software_architect")


if __name__ == "__main__":
    unittest.main()