"""Stage ITPro descriptions from an existing local clone of the public job tracker."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.scraping.itpro_feed import OUTPUT_FIELDS, clean_advert_text


TRACKER_URL = "https://github.com/Senadeera-NK/sri-lanka-software-jobs"
ITPRO_URL = re.compile(r"https://itpro\.lk/job/([1-9][0-9]*)/([a-z0-9]+(?:-[a-z0-9]+)*)/?")
COLOMBO = ZoneInfo("Asia/Colombo")
FIELDS = OUTPUT_FIELDS + (
    "tracker_first_commit", "tracker_confirming_commit", "tracker_observation_date",
    "tracker_confirming_date", "tracker_posting_timestamp",
)


def stage_snapshots(
    snapshots: Iterable[tuple[str, date, Iterable[dict]]],
) -> tuple[list[dict[str, str]], Counter[str]]:
    counts: Counter[str] = Counter()
    timestamps: dict[str, set[tuple[int, ...]]] = defaultdict(set)
    sightings: dict[str, dict[date, tuple[str, dict[str, str]]]] = defaultdict(dict)
    for commit, committed_date, adverts in snapshots:
        for advert in adverts:
            if advert.get("source") != "ITPro.lk":
                counts["other source"] += 1
                continue
            match = ITPRO_URL.fullmatch(advert.get("link") or "")
            title = str(advert.get("title") or "").strip()
            company = str(advert.get("company") or "").strip()
            if not match or not title or not company or company.casefold() == "unknown":
                counts["identity"] += 1
                continue

            posted = advert.get("datePosted")
            scraped = advert.get("scrapedDate")
            try:
                if len(posted) not in (6, 7) or not all(type(value) is int for value in posted):
                    raise ValueError("Unexpected posting timestamp")
                if len(posted) == 7 and not 0 <= posted[6] < 1_000_000_000:
                    raise ValueError("Invalid timestamp precision")
                posting_time = datetime(*posted[:6])
                observed_date = date(*scraped)
                if posting_time.date() > observed_date or abs(committed_date - observed_date) > timedelta(days=1):
                    raise ValueError("Dates disagree with the snapshot")
            except (TypeError, ValueError, OverflowError):
                counts["dates"] += 1
                continue

            vacancy, slug = match.groups()
            timestamps[vacancy].add(tuple(posted))
            description = clean_advert_text(str(advert.get("description") or ""))
            if len(description) < 140 or len(description.split()) < 25:
                counts["short text"] += 1
                continue
            if any(value.lstrip().startswith(("=", "+", "-", "@")) for value in (title, company, description)):
                counts["spreadsheet prefix"] += 1
                continue
            sightings[vacancy].setdefault(observed_date, (commit, {
                "source_platform": "itpro.lk",
                "source_job_id": vacancy,
                "source_url": f"https://itpro.lk/job/{vacancy}/{slug}",
                "job_title_raw": title,
                "company_raw": company,
                "country_raw": "Sri Lanka",
                "posted_date_raw": posting_time.date().isoformat(),
                "posting_date_source": "ITPro mysql_date via public tracker (stable across snapshots)",
                "job_description_raw": description,
                "tracker_posting_timestamp": json.dumps(posted),
            }))

    rows = []
    for vacancy, observations in sightings.items():
        if len(timestamps[vacancy]) != 1:
            counts["conflicting timestamps"] += 1
            continue
        if len(observations) < 2:
            counts["single observation day"] += 1
            continue
        first, confirming = sorted(observations)[:2]
        first_commit, row = observations[first]
        rows.append(row | {
            "tracker_first_commit": first_commit,
            "tracker_confirming_commit": observations[confirming][0],
            "tracker_observation_date": first.isoformat(),
            "tracker_confirming_date": confirming.isoformat(),
        })
    return sorted(rows, key=lambda row: (row["posted_date_raw"], row["source_job_id"])), counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path, help="Existing local tracker clone")
    parser.add_argument("output", type=Path, help="New historical-import CSV path")
    parser.add_argument("--revision", required=True, help="Full tracker commit hash to pin the export")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("--revision must be a full Git SHA-1")

    def git(*command: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(args.repository), *command], timeout=30)

    history = git("log", "--first-parent", "--reverse", "--format=%H %aI", args.revision, "--", "jobs.json")
    invalid_snapshots = 0

    def read_snapshots():
        nonlocal invalid_snapshots
        for line in history.decode("ascii").splitlines():
            commit, stamped = line.split()
            raw = git("cat-file", "blob", f"{commit}:jobs.json")
            try:
                adverts = json.loads(raw)
                if not isinstance(adverts, list) or not all(isinstance(row, dict) for row in adverts):
                    raise ValueError("Expected a tracker job array")
            except ValueError:
                invalid_snapshots += 1
                continue
            committed_date = datetime.fromisoformat(stamped).astimezone(COLOMBO).date()
            yield commit, committed_date, adverts

    rows, excluded = stage_snapshots(read_snapshots())
    with args.output.open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({
        "source": TRACKER_URL,
        "revision": args.revision,
        "snapshots": len(history.splitlines()),
        "invalid_snapshots": invalid_snapshots,
        "staged_rows": len(rows),
        "excluded": excluded,
        "month_counts": dict(sorted(Counter(row["posted_date_raw"][:7] for row in rows).items())),
    }, indent=2))


if __name__ == "__main__":
    main()
