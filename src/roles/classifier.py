from src.roles.models import RoleTaxonomy

UNCLASSIFIED_ROLE_ID = "unclassified"
UNCLASSIFIED_ROLE_NAME = "Unclassified"


class RoleClassifier:
    """Rule-based classifier: assigns a job posting to one IT role
    category by matching its title (falling back to its description)
    against each role's alias phrases.

    This is the lexical baseline for role classification -- the same
    kind of keyword matching LexicalSkillExtractor uses for skills, and
    it shares the same limitation named in the TAF's literature review:
    it can't recognise a role phrased in a way no alias anticipated. A
    semantic role classifier (built on the same SemanticEmbedder already
    used for skills) is the natural next step, mirroring how skill
    extraction has both a lexical and a semantic implementation.
    """

    def __init__(self, taxonomy: RoleTaxonomy):
        # Flatten every (alias, role) pair across ALL roles and sort
        # globally by alias length, longest first. This matters: sorting
        # each role's aliases individually (then checking role by role)
        # would let a short alias in an earlier-listed role ("architect"
        # under a hypothetical role) win over a longer, more specific
        # alias belonging to a later-listed role ("software architect").
        # A single global sort guarantees the most specific phrase
        # anywhere in the whole taxonomy is always checked first,
        # regardless of which role it belongs to or where that role
        # happens to sit in the taxonomy file.
        self._alias_role_pairs = sorted(
            (
                (alias.lower(), role)
                for role in taxonomy.roles
                for alias in role.aliases
            ),
            key=lambda pair: len(pair[0]),
            reverse=True,
        )

    def classify(self, title: str, description: str = ""):
        """Returns (role_id, role_name, matched_alias). Falls back to
        the description only if the title matches nothing -- the title
        is the strongest, least noisy signal for what a job actually is.
        """
        title_lower = (title or "").lower()
        role, alias = self._match(title_lower)
        if role:
            return role.id, role.name, alias

        description_lower = (description or "").lower()
        role, alias = self._match(description_lower)
        if role:
            return role.id, role.name, alias

        return UNCLASSIFIED_ROLE_ID, UNCLASSIFIED_ROLE_NAME, ""

    def _match(self, text: str):
        for alias, role in self._alias_role_pairs:
            if alias in text:
                return role, alias
        return None, ""