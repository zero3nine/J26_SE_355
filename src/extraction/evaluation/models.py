from dataclasses import dataclass


@dataclass(frozen=True)
class GroundTruthSkill:
    job_id: str
    skill_id: str