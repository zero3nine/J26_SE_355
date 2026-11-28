"""Read-only, filterable summaries of a published cohort. Standard library only."""
from __future__ import annotations

import json
import math
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from itertools import combinations
from pathlib import Path


class PublicationUnavailable(Exception):
    pass


def read_snapshot(path: Path) -> tuple[dict, list[dict]]:
    if not path.is_file():
        raise PublicationUnavailable("No analysis has been published yet.")
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            conn.execute("PRAGMA query_only=ON")
            metadata = {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM metadata")}
            if metadata.get("schema_version") != 1:
                raise PublicationUnavailable("This publication version is not supported.")
            jobs = {r[0]: {"id": r[0], "date": r[1], "country": r[2], "role": r[3],
                            "source": r[4], "lexical": set(), "semantic": set()}
                    for r in conn.execute("SELECT id, posted, country, role, source FROM jobs")}
            for job_id, method, skill in conn.execute("SELECT job_id, method, skill FROM job_skills"):
                if job_id in jobs and method in ("lexical", "semantic"):
                    jobs[job_id][method].add(skill)
        return metadata, list(jobs.values())
    except (sqlite3.Error, ValueError, KeyError) as exc:
        raise PublicationUnavailable("The published dataset could not be read.") from exc


def options(metadata: dict, jobs: list[dict]) -> dict:
    return {"publication": metadata, "countries": sorted({r["country"] for r in jobs}),
            "roles": sorted({r["role"] for r in jobs}), "sources": sorted({r["source"] for r in jobs}),
            "skills": sorted(set().union(*(r["lexical"] | r["semantic"] for r in jobs)))}


def published_forecast(path: Path, metadata: dict, filters: dict, skill: str) -> dict:
    full_window = (filters.get("start", metadata["date_start"]) == metadata["date_start"]
                   and filters.get("end", metadata["date_end"]) == metadata["date_end"])
    if filters.get("source") or not full_window or int(filters.get("min_jobs", 5)) != 5:
        return {"rows": [], "note": "Forecasts are published for the full observation window, all sources, and a minimum of five jobs per month. Reset those filters to view an available forecast."}
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        snapshot = json.loads(conn.execute("SELECT value FROM metadata WHERE key='snapshot_id'").fetchone()[0])
        if snapshot != metadata["snapshot_id"]:
            raise PublicationUnavailable("The publication was updated during this request. Please retry.")
        rows = [dict(r) for r in conn.execute(
            "SELECT period, rate, model, mae, evaluated_periods FROM forecasts "
            "WHERE country=? AND role=? AND method=? AND skill=? ORDER BY period",
            (filters.get("country", ""), filters.get("role", ""), filters.get("method", "semantic"), skill))]
    return {"rows": rows, "note": "Exploratory baseline estimates prepared at publication time. Model choice uses the lower one-step MAE across the latest six historical targets. Three-period future performance is not established; prediction intervals are unavailable." if rows else "This selection lacks a published forecast with at least 18 consecutive months and five eligible jobs per month."}


def filtered(jobs: list[dict], filters: dict, include_country: bool = True) -> list[dict]:
    return [r for r in jobs if (not include_country or not filters.get("country") or r["country"] == filters["country"])
            and (not filters.get("role") or r["role"] == filters["role"])
            and (not filters.get("source") or r["source"] == filters["source"])
            and (not filters.get("start") or r["date"] >= filters["start"])
            and (not filters.get("end") or r["date"] <= filters["end"])]


def month_range(start: str, end: str) -> list[str]:
    year, month = map(int, start[:7].split("-"))
    result = []
    while f"{year:04d}-{month:02d}" <= end[:7]:
        result.append(f"{year:04d}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return result


def demand(jobs: list[dict], method: str) -> list[dict]:
    counts = Counter(skill for r in jobs for skill in r[method])
    return [{"skill": skill, "count": count, "rate": round(100 * count / len(jobs), 2)}
            for skill, count in sorted(counts.items(), key=lambda x: (-x[1], x[0]))]


def timeline(jobs: list[dict], method: str, skills: list[str], minimum: int,
             start: str = "", end: str = "") -> list[dict]:
    if not jobs:
        return []
    months = month_range(start or min(r["date"] for r in jobs), end or max(r["date"] for r in jobs))
    grouped = defaultdict(list)
    for r in jobs:
        grouped[r["date"][:7]].append(r)
    result = []
    for month in months:
        group = grouped[month]
        counts = Counter(s for r in group for s in r[method])
        result.append({"period": month, "eligible": len(group),
                       "rates": {s: round(100 * counts[s] / len(group), 2)
                                 if len(group) >= minimum else None for s in skills}})
    return result


def trend_signal(points: list[dict], skill: str) -> dict:
    # Only compare two complete, adjacent three-month windows. Gaps stay missing.
    recent = [p["rates"].get(skill) for p in points[-3:]]
    prior = [p["rates"].get(skill) for p in points[-6:-3]]
    if len(recent) != 3 or len(prior) != 3 or any(v is None for v in recent + prior):
        return {"change": None, "label": "Limited history"}
    before, after = sum(prior) / 3, sum(recent) / 3
    change = round(after - before, 2)
    label = "Growing" if change > 2 else "Declining" if change < -2 else "Steady"
    if before < 5 and change > 2 and all(v > before for v in recent):
        label = "Emerging candidate"
    return {"change": change, "label": label}


def summarize(metadata: dict, jobs: list[dict], filters: dict) -> dict:
    method = filters.get("method", "semantic")
    minimum = int(filters.get("min_jobs", 5))
    scope = filtered(jobs, filters)
    ranking = demand(scope, method)
    names = [r["skill"] for r in ranking]
    selected = filters.get("skill") or (names[0] if names else "")
    all_skills = sorted(set(names + ([selected] if selected else [])))
    points = timeline(scope, method, all_skills, minimum, filters.get("start", ""), filters.get("end", ""))
    for r in ranking:
        r.update(trend_signal(points, r["skill"]))
    role_groups = defaultdict(list)
    for r in scope:
        role_groups[r["role"]].append(r)
    roles = []
    for role, group in sorted(role_groups.items()):
        top = demand(group, method)
        count = sum(selected in r[method] for r in group)
        roles.append({"role": role, "jobs": len(group), "count": count,
                      "rate": round(100 * count / len(group), 2), "skills": top[:5]})
    # Country comparison deliberately retains other filters and lifts only market.
    market_groups = defaultdict(list)
    for r in filtered(jobs, filters, include_country=False):
        market_groups[r["country"]].append(r)
    markets = []
    for country, group in sorted(market_groups.items()):
        count = sum(selected in r[method] for r in group)
        markets.append({"country": country, "jobs": len(group), "count": count,
                        "rate": round(100 * count / len(group), 2), "skills": demand(group, method)[:5]})
    counts = Counter(s for r in scope for s in r[method])
    pair_counts = Counter(pair for r in scope for pair in combinations(sorted(r[method]), 2))
    pairs = []
    for (a, b), count in pair_counts.items():
        if selected and selected not in (a, b):
            continue
        other = b if a == selected else a
        base = counts[selected] if selected else counts[a]
        pairs.append({"skill": other, "with_skill": selected or a, "count": count,
                      "support": round(100 * count / max(1, len(scope)), 2),
                      "confidence": round(100 * count / max(1, base), 2),
                      "lift": round(count * len(scope) / max(1, counts[a] * counts[b]), 2),
                      "jaccard": round(count / max(1, counts[a] + counts[b] - count), 3),
                      "pmi": round(math.log2(count * len(scope) / max(1, counts[a] * counts[b])), 3)})
    pairs.sort(key=lambda p: (-p["count"], p["skill"]))
    comparison = []
    lexical = {r["skill"]: r for r in demand(scope, "lexical")}
    semantic = {r["skill"]: r for r in demand(scope, "semantic")}
    for skill in sorted(lexical.keys() | semantic.keys()):
        a, b = lexical.get(skill, {}).get("rate", 0), semantic.get(skill, {}).get("rate", 0)
        comparison.append({"skill": skill, "lexical": a, "semantic": b, "difference": round(b - a, 2)})
    comparison.sort(key=lambda r: (-abs(r["difference"]), r["skill"]))
    return {"publication": metadata, "filters": filters, "selected_skill": selected,
            "summary": {"jobs": len(scope), "skills": len(ranking), "sources": len({r["source"] for r in scope}),
                        "skill_bearing_jobs": sum(bool(r[method]) for r in scope),
                        "months": len(points), "low_sample_months": sum(p["eligible"] < minimum for p in points)},
            "skills": ranking, "timeline": points, "roles": roles, "markets": markets,
            "relationships": pairs[:30], "comparison": comparison}
