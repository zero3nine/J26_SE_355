"""Offline publication contract. Never imported by the public request handler."""
from __future__ import annotations

import hashlib
import json
import os
import random
import sqlite3
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
METHODS = ("lexical", "semantic")
SCHEMA = """
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE jobs (
    id TEXT PRIMARY KEY, posted TEXT NOT NULL, country TEXT NOT NULL,
    role TEXT NOT NULL, source TEXT NOT NULL
);
CREATE TABLE job_skills (
    job_id TEXT NOT NULL REFERENCES jobs(id), method TEXT NOT NULL,
    skill TEXT NOT NULL, PRIMARY KEY(job_id, method, skill)
);
CREATE INDEX scope ON jobs(country, role, posted);
CREATE INDEX mentions ON job_skills(method, skill, job_id);
CREATE TABLE forecasts (
    country TEXT NOT NULL, role TEXT NOT NULL, method TEXT NOT NULL,
    skill TEXT NOT NULL, period TEXT NOT NULL, rate REAL NOT NULL,
    model TEXT NOT NULL, mae REAL NOT NULL, evaluated_periods INTEGER NOT NULL,
    PRIMARY KEY(country, role, method, skill, period)
);
"""


def forecast_rows(records: list[dict]) -> list[tuple]:
    """Materialize simple, chronologically evaluated baseline forecasts offline.

    Require at least 18 consecutive calendar months with >=5 eligible jobs.
    Scores describe one-step historical errors, not multi-step certainty.
    """
    from .data import month_range, timeline
    result = []
    jobs = [{**r, "date": r["posting_date"], **{m: set(r[m]) for m in METHODS}} for r in records]
    for country in [""] + sorted({r["country"] for r in records}):
        for role in [""] + sorted({r["role"] for r in records}):
            scope = [r for r in jobs if (not country or r["country"] == country) and (not role or r["role"] == role)]
            if not scope:
                continue
            for method in METHODS:
                skills = sorted(set().union(*(r[method] for r in scope)))
                points = timeline(scope, method, skills, 5)
                if len(points) < 18 or any(p["eligible"] < 5 for p in points):
                    continue
                last_year, last_month = map(int, points[-1]["period"].split("-"))
                next_month = f"{last_year+1}-01" if last_month == 12 else f"{last_year}-{last_month+1:02d}"
                future = month_range(next_month, f"{last_year+1}-12")[:3]
                for skill in skills:
                    rates = [p["rates"][skill] for p in points]
                    targets = list(range(max(12, len(rates)-6), len(rates)))
                    errors = {
                        "Last-value baseline": sum(abs(rates[i]-rates[i-1]) for i in targets) / len(targets),
                        "Three-month average": sum(abs(rates[i]-sum(rates[i-3:i])/3) for i in targets) / len(targets),
                    }
                    model = min(errors, key=errors.get)
                    rate = rates[-1] if model == "Last-value baseline" else sum(rates[-3:])/3
                    result.extend((country, role, method, skill, p, round(rate, 2), model,
                                   round(errors[model], 3), len(targets)) for p in future)
    return result


def publish(records: list[dict], output: Path, metadata: dict) -> dict:
    """Validate a matched, reviewed cohort and atomically replace its snapshot.

    Both skill lists are mandatory, including empty lists for completed extractions
    with no skills. Private job text and source URLs never enter the public schema.
    """
    if not records:
        raise ValueError("A publication must contain at least one job.")
    if not metadata.get("title") or not metadata.get("provenance"):
        raise ValueError("A title and provenance are required.")
    seen = set()
    cleaned = []
    for row in records:
        job_id = str(row.get("job_id", "")).strip()
        if not job_id or job_id in seen:
            raise ValueError("Job IDs must be non-empty and unique.")
        seen.add(job_id)
        posted = date.fromisoformat(str(row["posting_date"]))
        if posted > date.today():
            raise ValueError("Future posting dates cannot be published.")
        values = {key: str(row.get(key, "")).strip() for key in ("country", "role", "source")}
        if not all(values.values()):
            raise ValueError("Every job needs country, role, and source labels.")
        methods = {}
        for method in METHODS:
            skills = row.get(method)
            if not isinstance(skills, list) or any(not isinstance(s, str) or not s.strip() for s in skills):
                raise ValueError(f"{method} must be a completed canonical skill list, possibly empty.")
            methods[method] = sorted({s.strip() for s in skills})
        cleaned.append({"job_id": job_id, "posting_date": posted.isoformat(), **values, **methods})
    cleaned.sort(key=lambda r: r["job_id"])
    digest = hashlib.sha256(json.dumps(cleaned, sort_keys=True).encode()).hexdigest()
    meta = {**metadata, "schema_version": SCHEMA_VERSION, "snapshot_id": digest[:16],
            "input_sha256": digest, "generated_at": datetime.now(timezone.utc).isoformat(),
            "job_count": len(cleaned), "date_start": min(r["posting_date"] for r in cleaned),
            "date_end": max(r["posting_date"] for r in cleaned),
            "is_synthetic": bool(metadata.get("is_synthetic", False)),
            "eligibility": "Reviewed dated IT advertisements with both extraction methods completed; zero-skill jobs retained."}
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".publication-", suffix=".sqlite3", dir=output.parent)
    os.close(handle)
    try:
        conn = sqlite3.connect(name)
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript(SCHEMA)
            with conn:
                conn.executemany("INSERT INTO metadata VALUES (?, ?)",
                                 [(k, json.dumps(v)) for k, v in meta.items()])
                for row in cleaned:
                    # Public IDs cannot reveal source identifiers or URLs.
                    public_id = hashlib.sha256(row["job_id"].encode()).hexdigest()
                    conn.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?)",
                                 (public_id, row["posting_date"], row["country"], row["role"], row["source"]))
                    conn.executemany("INSERT INTO job_skills VALUES (?, ?, ?)",
                                     [(public_id, method, skill) for method in METHODS for skill in row[method]])
                conn.executemany("INSERT INTO forecasts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", forecast_rows(cleaned))
            conn.execute("VACUUM")
        finally:
            conn.close()
        # Sanitized public snapshot must be readable by the unprivileged
        # container user when the host publishes it through a directory mount.
        os.chmod(name, 0o644)
        for attempt in range(10):
            try:
                os.replace(name, output)
                break
            except PermissionError:
                # Windows readers briefly lock the old file. Retry the atomic
                # operation; never truncate or delete the active publication.
                if attempt == 9:
                    raise
                time.sleep(0.1)
    finally:
        Path(name).unlink(missing_ok=True)
    return meta


def synthetic_records() -> list[dict]:
    """Deterministic 36-month fixture with role, market, and method variation."""
    rng = random.Random(355)
    profiles = {
        "Software development": ["JavaScript", "TypeScript", "React", "Node.js", "Python", "Django", "SQL", "Git"],
        "Data & AI": ["Python", "SQL", "Pandas", "PyTorch", "TensorFlow", "AWS", "Docker"],
        "Cloud & DevOps": ["AWS", "Docker", "Kubernetes", "Linux", "Terraform", "Python", "Git"],
        "Quality assurance": ["Selenium", "Java", "Python", "SQL", "Git", "Playwright"],
        "Mobile development": ["Flutter", "Dart", "React Native", "JavaScript", "Git", "Firebase"],
    }
    countries = {"Sri Lanka": (42, ["Topjobs", "ITPro"]), "Singapore": (32, ["MyCareersFuture"]),
                 "Malaysia": (27, ["Regional sample MY"]), "India": (35, ["Shine", "TimesJobs"])}
    rows = []
    for month in range(36):
        # Fixed window ends in the latest complete month at this fixture's
        # creation (October 2026), independent of the execution date.
        year, mon = divmod(2023 * 12 + 10 + month, 12)
        mon += 1
        for country, (count, sources) in countries.items():
            for i in range(count):
                role = list(profiles)[rng.randrange(len(profiles))]
                skills = set()
                for skill in profiles[role]:
                    probability = .56
                    if skill in {"TypeScript", "PyTorch", "Kubernetes", "Playwright", "Terraform"}:
                        probability = .15 + .018 * month
                    if skill in {"Java", "TensorFlow"}:
                        probability = .72 - .012 * month
                    if country == "Singapore" and skill in {"AWS", "Kubernetes", "Python"}:
                        probability += .15
                    if country == "Sri Lanka" and skill in {"React", "JavaScript", "Django"}:
                        probability += .12
                    if rng.random() < probability:
                        skills.add(skill)
                # Real zero-skill observations remain in both denominators.
                if i == 0:
                    skills = set()
                lexical = {s for s in sorted(skills) if rng.random() > .14}
                semantic = {s for s in sorted(skills) if rng.random() > .05}
                rows.append({"job_id": f"demo-{country}-{month}-{i}",
                             "posting_date": date(year, mon, 1 + i % 27).isoformat(),
                             "country": country, "role": role, "source": sources[i % len(sources)],
                             "lexical": sorted(lexical), "semantic": sorted(semantic)})
    return rows
