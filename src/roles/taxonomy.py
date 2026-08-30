import json
from pathlib import Path

from .models import Role, RoleTaxonomy


def load_role_taxonomy(path: str | Path) -> RoleTaxonomy:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Role taxonomy file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    roles = [
        Role(
            id=role_data["id"],
            name=role_data["name"],
            aliases=role_data.get("aliases", []),
        )
        for role_data in data["roles"]
    ]

    return RoleTaxonomy(
        taxonomy_version=data["taxonomy_version"],
        name=data["name"],
        description=data["description"],
        roles=roles,
    )