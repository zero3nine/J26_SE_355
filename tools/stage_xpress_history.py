"""Stage saved public XpressJobs detail responses with dates and location evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from src.scraping.itpro_feed import OUTPUT_FIELDS, clean_advert_text, is_technical_advert


VACANCY_ID = re.compile(r"[1-9][0-9]{0,11}")
DETAIL_BASE = "https://xpress.jobs/api/jobs/publishedJob?jobId="
TECHNICAL_SECTORS = {"it", "it-hware"}
LOCAL_REGIONS = {
    "central province", "eastern province", "north central province", "north western province",
    "northern province", "sabaragamuwa province", "southern province", "uva province", "western province",
}
SITEMAP_REPLAY = re.compile(
    r"https://web\.archive\.org/web/(\d{14})id_/https?://(?:www\.)?xpress\.jobs/sitemap\.xml"
)
MAX_RESPONSE_BYTES = 600_000
FIELDS = OUTPUT_FIELDS + ("publisher_detail_url", "publisher_created_date", "publisher_sha256", "discovery_url")


def sri_lankan_locations(location: str) -> bool:
    groups = [group.strip().casefold() for group in location.split(";") if group.strip()]
    local = False
    for group in groups:
        if group == "work from home / hybrid, remote work":
            continue
        if group in {"island wide, all provinces", "sri lanka"}:
            local = True
            continue
        parts = [part.strip() for part in group.split(",")]
        if len(parts) != 2 or not parts[0] or parts[1] not in LOCAL_REGIONS:
            return False
        local = True
    return local


def stage_detail(vacancy: str, body: bytes, as_of: date) -> tuple[dict[str, str] | None, str]:
    try:
        job = json.loads(body)
    except (ValueError, UnicodeError):
        return None, "invalid JSON"
    if not isinstance(job, dict):
        return None, "invalid JSON"

    item = job.get("jobItem")
    if (not VACANCY_ID.fullmatch(vacancy) or not isinstance(item, dict)
            or str(job.get("jobId")) != vacancy or str(item.get("jobId")) != vacancy):
        return None, "identity"

    title = str(job.get("jobTitle") or "").strip()
    company = str(item.get("organizationName") or "").strip()
    if not title or not company or company.casefold() == "unknown" or job.get("isRedirected"):
        return None, "identity"
    location = str(item.get("locations") or "").strip()
    if not sri_lankan_locations(location):
        return None, "location"
    sectors = job.get("sectors") or []
    if not isinstance(sectors, list) or not all(isinstance(sector, dict) for sector in sectors):
        return None, "invalid JSON"
    sector_codes = {str(sector.get("friendlyName") or "") for sector in sectors}
    technical_category = "Software Engineering" if sector_codes & TECHNICAL_SECTORS else ""
    if not is_technical_advert(title, technical_category):
        return None, "role"
    created = job.get("createdDate")
    try:
        posted = datetime.fromisoformat(created).date()
        expiry = item.get("expiryDateOnWebsite")
        if posted > as_of or (expiry and datetime.fromisoformat(expiry).date() < posted):
            return None, "date"
    except (TypeError, ValueError):
        return None, "date"

    description = clean_advert_text(str(job.get("jobInfo") or ""))
    if len(description) < 140 or len(description.split()) < 25:
        return None, "text"
    employment_type = str(item.get("jobType") or "").strip()
    categories = ", ".join(str(sector.get("sectorName") or "").strip()
                           for sector in sectors if sector.get("sectorName"))
    if any(value.lstrip().startswith(("=", "+", "-", "@"))
           for value in (title, company, description, location, employment_type, categories)):
        return None, "spreadsheet prefix"
    return {
        "source_platform": "xpress.jobs",
        "source_job_id": vacancy,
        "source_url": f"https://xpress.jobs/jobs/view/{vacancy}",
        "job_title_raw": title,
        "company_raw": company,
        "country_raw": "Sri Lanka",
        "location_raw": location,
        "employment_type_raw": employment_type,
        "posted_date_raw": posted.isoformat(),
        "posting_date_source": "XpressJobs publishedJob createdDate",
        "source_category": categories,
        "job_description_raw": description,
        "publisher_detail_url": DETAIL_BASE + vacancy,
        "publisher_created_date": created,
        "publisher_sha256": hashlib.sha256(body).hexdigest(),
    }, ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New historical-import CSV path")
    parser.add_argument("manifest", type=Path, help="Local JSONL capture log")
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    excluded: Counter[str] = Counter()
    rows: dict[str, dict[str, str]] = {}
    directory = args.manifest.parent.resolve()
    with args.manifest.open(encoding="utf-8") as manifest:
        for line in manifest:
            attempt = json.loads(line)
            if attempt["status"] != 200:
                excluded[f"response {attempt['status']}"] += 1
                continue
            vacancy = attempt["id"]
            filename = f"{vacancy}.json"
            if (not VACANCY_ID.fullmatch(vacancy) or attempt["file"] != filename
                    or attempt["publisher_url"] != DETAIL_BASE + vacancy):
                raise ValueError("Invalid publisher response manifest entry")
            capture = directory / filename
            if capture.is_symlink():
                raise ValueError("Response file must be local to the manifest directory")
            with capture.open("rb") as source:
                body = source.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                excluded["response size"] += 1
                continue
            if hashlib.sha256(body).hexdigest() != attempt["sha256"]:
                raise ValueError(f"Publisher response hash mismatch for vacancy {vacancy}")
            discovery = str(attempt.get("discovery") or "")
            sitemap = SITEMAP_REPLAY.fullmatch(discovery)
            latest_date = args.as_of
            if sitemap:
                capture_date = datetime.strptime(sitemap[1], "%Y%m%d%H%M%S").date()
                latest_date = min(capture_date, latest_date)
            row, reason = stage_detail(vacancy, body, latest_date)
            if row is None:
                excluded[reason] += 1
                continue
            if vacancy in rows:
                excluded["duplicate"] += 1
                continue
            row["discovery_url"] = discovery if discovery.startswith("https://") else ""
            rows[vacancy] = row

    with args.output.open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows.values(), key=lambda row: (row["posted_date_raw"], row["source_job_id"])))
    print(json.dumps({
        "staged_rows": len(rows),
        "excluded": excluded,
        "month_counts": dict(sorted(Counter(row["posted_date_raw"][:7] for row in rows.values()).items())),
    }, indent=2))


if __name__ == "__main__":
    main()
