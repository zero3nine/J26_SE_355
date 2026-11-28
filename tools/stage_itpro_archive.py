"""Stage downloaded ITPro Wayback replays with original dates and evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from src.scraping.extractors.jsonld import JsonLdExtractor
from src.scraping.itpro_feed import OUTPUT_FIELDS, clean_advert_text, is_technical_advert
from src.scraping.models import ExtractionResult


ITPRO_URL = r"https?://(?:www\.)?itpro\.lk/job/([1-9][0-9]*)/([a-z0-9-]+)/?"
REPLAY_URL = re.compile(r"https://web\.archive\.org/web/(\d{14})(?:id_)?/(" + ITPRO_URL + ")")
COLOMBO = ZoneInfo("Asia/Colombo")
MAX_CAPTURE_BYTES = 3_000_000
FIELDS = OUTPUT_FIELDS + ("archive_url", "capture_timestamp", "archive_sha256")


def stage_capture(archive_url: str, body: bytes) -> tuple[dict[str, str] | None, str]:
    """Validate a replay and keep its original vacancy identity and posting date."""
    match = REPLAY_URL.fullmatch(archive_url)
    if not match:
        return None, "replay URL"
    timestamp, original, vacancy, slug = match.groups()
    try:
        capture_at = datetime.strptime(timestamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None, "capture timestamp"

    canonical_url = f"https://itpro.lk/job/{vacancy}/{slug}"
    page = body.decode("utf-8", errors="replace")
    extracted = JsonLdExtractor().extract(
        original, page, ExtractionResult.create_for_url(original, "itpro-wayback"),
    )
    title = html.unescape(html.unescape(extracted.job_title_raw))
    company = html.unescape(html.unescape(extracted.company_raw))
    categories = html.unescape(extracted.industry_raw)
    if not title or not company:
        return None, "no structured advert"
    if extracted.source_job_id and extracted.source_job_id != vacancy:
        return None, "vacancy identity"
    if not is_technical_advert(title, categories):
        return None, "role"
    if extracted.country_raw.casefold() not in {"", "lk", "sri lanka"}:
        return None, "country"
    try:
        posted_date = datetime.fromisoformat(extracted.posted_date_raw).date()
    except ValueError:
        return None, "posting date"
    if posted_date > capture_at.astimezone(COLOMBO).date():
        return None, "posting date after capture"

    description = clean_advert_text(extracted.job_description_raw)
    if len(description) < 140 or len(description.split()) < 25:
        return None, "text"
    return {
        "source_platform": "itpro.lk",
        "source_job_id": vacancy,
        "source_url": canonical_url,
        "job_title_raw": title,
        "company_raw": company,
        "country_raw": "Sri Lanka",
        "location_raw": extracted.location_raw,
        "employment_type_raw": extracted.employment_type_raw,
        "posted_date_raw": posted_date.isoformat(),
        "posting_date_source": "archived ITPro JobPosting datePosted",
        "source_category": categories,
        "job_description_raw": description,
        "archive_url": archive_url,
        "capture_timestamp": capture_at.isoformat(),
        "archive_sha256": hashlib.sha256(body).hexdigest(),
    }, ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New historical-import CSV path")
    parser.add_argument("manifests", type=Path, nargs="+", help="Local JSONL capture logs")
    args = parser.parse_args()

    rows: dict[str, dict[str, str]] = {}
    excluded: Counter[str] = Counter()
    for manifest in args.manifests:
        with manifest.open(encoding="utf-8") as source:
            for line in source:
                attempt = json.loads(line)
                if attempt.get("source", "itpro") != "itpro":
                    continue
                if attempt["status"] != 200:
                    excluded[f"replay {attempt['status']}"] += 1
                    continue
                filename = attempt["file"]
                if Path(filename).name != filename:
                    raise ValueError("Replay filenames must be relative to their manifest directory.")
                capture_path = manifest.parent / filename
                with capture_path.open("rb") as capture:
                    body = capture.read(MAX_CAPTURE_BYTES + 1)
                if len(body) > MAX_CAPTURE_BYTES:
                    excluded["capture size"] += 1
                    continue
                row, reason = stage_capture(attempt.get("archive_url", attempt.get("replay_url", "")), body)
                if row is None:
                    excluded[reason] += 1
                    continue
                identifier = row["source_job_id"]
                if identifier in rows:
                    excluded["duplicate"] += 1
                    if row["capture_timestamp"] >= rows[identifier]["capture_timestamp"]:
                        continue
                rows[identifier] = row

    with args.output.open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows.values(), key=lambda row: (row["posted_date_raw"], row["source_job_id"])))
    print(json.dumps({
        "staged_rows": len(rows), "excluded": excluded,
        "month_counts": dict(sorted(Counter(row["posted_date_raw"][:7] for row in rows.values()).items())),
    }, indent=2))


if __name__ == "__main__":
    main()
