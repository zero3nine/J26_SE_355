from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Role:
    id: str
    name: str
    aliases: List[str]


@dataclass(frozen=True)
class RoleTaxonomy:
    taxonomy_version: str
    name: str
    description: str
    roles: List[Role]