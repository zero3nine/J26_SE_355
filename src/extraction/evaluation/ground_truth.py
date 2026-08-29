import csv
from pathlib import Path

from .models import GroundTruthSkill


def load_ground_truth(
    path: str | Path,
) -> list[GroundTruthSkill]:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Ground truth file not found: {path}"
        )

    ground_truth = []

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        required_columns = {
            "job_id",
            "skill_id",
        }

        if not required_columns.issubset(reader.fieldnames or []):
            raise ValueError(
                "Ground truth CSV must contain "
                "'job_id' and 'skill_id' columns."
            )

        for row in reader:
            ground_truth.append(
                GroundTruthSkill(
                    job_id=row["job_id"],
                    skill_id=row["skill_id"],
                )
            )

    return ground_truth