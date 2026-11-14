"""Publish an isolated public snapshot; run this locally, outside the public app.

Demo: python -m tools.publish_dashboard --synthetic
Real: python -m tools.publish_dashboard --master data/master_jobs.sqlite3
      --run-id RUN --cohort reviewed_cohort.csv --title "Reviewed sample"
      --provenance "Collection/review protocol and observation window"
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from public_dashboard.publication import publish, synthetic_records

ROOT = Path(__file__).resolve().parents[1]


def from_master(master: Path, run_id: str, cohort: Path) -> tuple[list[dict], dict]:
    """The cohort CSV explicitly attests successful completion of both methods.

    The legacy database has no per-job completion log. Do not infer completion
    from missing mentions or use every master job as a denominator automatically.
    Required CSV columns: job_id, lexical_completed, semantic_completed.
    """
    with cohort.open(encoding="utf-8-sig", newline="") as file:
        cohort_rows = list(csv.DictReader(file))
    if not cohort_rows:
        raise ValueError("The reviewed cohort is empty.")
    ids = []
    for row in cohort_rows:
        if any(str(row.get(f"{method}_completed", "")).strip().lower() not in ("true", "1", "yes")
               for method in ("lexical", "semantic")):
            raise ValueError("Every cohort row must confirm both extractions completed, including zero-skill jobs.")
        if not row.get("job_id") or row["job_id"] in ids:
            raise ValueError("Cohort IDs must be non-empty and unique.")
        ids.append(row["job_id"])
    id_set = set(ids)
    with closing(sqlite3.connect(master.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN")
        run = conn.execute("SELECT * FROM extraction_runs WHERE run_id=?", (run_id,)).fetchone()
        if not run:
            raise ValueError("The selected extraction run does not exist.")
        # One read transaction prevents mixing data states during export.
        jobs = {r["job_id"]: dict(r) for r in conn.execute("SELECT * FROM jobs") if r["job_id"] in id_set}
        if set(ids) != set(jobs):
            raise ValueError("Some cohort IDs do not exist in the master database.")
        skill_map = {}
        for r in conn.execute("SELECT es.job_id, es.method, s.canonical_name AS name "
                              "FROM extracted_skills es LEFT JOIN skills s ON s.skill_id=es.canonical_skill_id "
                              "WHERE es.run_id=? AND es.method IN ('lexical','semantic')", (run_id,)):
            if r["job_id"] not in id_set:
                continue
            if not r["name"]:
                raise ValueError("The cohort has unmapped skill mentions. Review their canonical taxonomy mapping before publication.")
            skill_map.setdefault((r["job_id"], r["method"]), set()).add(r["name"])
        from src.roles.classifier import RoleClassifier
        from src.roles.taxonomy import load_role_taxonomy
        classifier = RoleClassifier(load_role_taxonomy(ROOT / "config" / "role_taxonomy.json"))
        records = []
        for job_id in ids:
            row = jobs[job_id]
            if row.get("classification_status") != "it":
                raise ValueError(f"Cohort contains a job not classified as IT: {job_id}")
            _, role, _ = classifier.classify(row.get("job_title") or "", row.get("job_description") or "")
            records.append({"job_id": job_id, "posting_date": row["posting_date"],
                            "country": row["country"], "source": row["source_platform"],
                            "role": role, **{m: sorted(skill_map.get((job_id, m), set())) for m in ("lexical", "semantic")}})
    import hashlib
    config = {"run_id": run_id, "model": run["model_name"], "model_version": run["model_version"],
              "threshold": run["semantic_threshold"], "taxonomy_version": run["taxonomy_version"],
              "cohort_sha256": hashlib.sha256(cohort.read_bytes()).hexdigest(),
              "role_taxonomy_sha256": hashlib.sha256((ROOT / "config/role_taxonomy.json").read_bytes()).hexdigest()}
    return records, {"extraction_run": config, "configuration": json.dumps(config, sort_keys=True)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/public/dashboard.sqlite3")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--synthetic", action="store_true")
    source.add_argument("--master", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--cohort", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--provenance")
    args = parser.parse_args()
    if args.synthetic:
        records = synthetic_records()
        metadata = {"title": "SkillScope demonstration · November 2023–October 2026", "is_synthetic": True,
                    "provenance": "Deterministic synthetic advertisements generated with seed 355. No scraped records or empirical findings.",
                    "configuration": "Synthetic v1; seed=355; 36 months; 4 markets; 5 career areas; matched lexical/semantic cohorts."}
    else:
        if not all((args.run_id, args.cohort, args.title, args.provenance)):
            parser.error("Real publication requires --run-id, --cohort, --title, and --provenance.")
        if args.master.resolve() == args.output.resolve():
            parser.error("Publication output must not overwrite the master database.")
        records, metadata = from_master(args.master, args.run_id, args.cohort)
        metadata.update(title=args.title, provenance=args.provenance, is_synthetic=False)
    result = publish(records, args.output, metadata)
    print(f"Published {result['job_count']:,} jobs to {args.output.resolve()}")
    print(f"Snapshot: {result['snapshot_id']} · synthetic={result['is_synthetic']}")


if __name__ == "__main__":
    main()
