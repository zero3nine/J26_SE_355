"""Stage a saved ITPro public widget response for the historical CSV importer."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup


TECHNICAL_CATEGORIES = frozenset({
    "AI and Data", "DevOps and Cloud", "Hardware and Networking",
    "Mobile Development", "Quality Assurance", "Software Development",
    "Software Engineering", "Web Development",
})
ADJACENT_TITLE = re.compile(
    r"\b(?:IT|ICT|cyber[\s-]*security|information technology|"
    r"database administrator|system(?:s)? (?:administrator|engineer)|"
    r"network (?:administrator|engineer)|technical support|"
    r"software|data (?:engineer|scientist|analyst)|DevOps|UI\s*[/&-]\s*UX|"
    r"ERP (?:consultant|engineer)|cloud engineer|QA|quality assurance|"
    r"(?:(?:full[\s-]?stack|back[\s-]?end|front[\s-]?end|web|mobile|"
    r"WordPress|React|Java|PHP|Python)\s+(?:engineer|developer|designer)))\b",
    re.IGNORECASE,
)
PROMOTIONAL_TITLE = re.compile(
    r"\b(?:sales|recruiter|marketing|customer service|data entry|graphic design)\b",
    re.IGNORECASE,
)
CONTACT = re.compile(
    r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|"
    r"(?<!\w)(?:\+94[\s.-]*|0)(?:\d[\s.-]*){8}\d(?!\w)"
)
VACANCY_ID = re.compile(r"[1-9][0-9]{0,11}")
VACANCY_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
OUTPUT_FIELDS = (
    "source_platform", "source_job_id", "source_url", "job_title_raw",
    "company_raw", "country_raw", "location_raw", "employment_type_raw",
    "posted_date_raw", "posting_date_source", "source_category", "job_description_raw",
)


def normalize_feed(payload: str, as_of: date) -> tuple[list[dict[str, str]], Counter[str]]:
    """Use publisher IDs, categories, and creation dates to screen one feed snapshot."""
    content = payload.strip()
    if content.startswith("var jobs = ") and content.endswith(";"):
        content = content.removeprefix("var jobs = ").removesuffix(";")
    adverts = json.loads(content)
    if not isinstance(adverts, list) or not all(isinstance(advert, dict) for advert in adverts):
        raise ValueError("Expected an ITPro job array.")

    exclusions: Counter[str] = Counter()
    accepted: dict[str, dict[str, str]] = {}
    for advert in adverts:
        row, reason = _normalize_advert(advert, as_of)
        if row is None:
            exclusions[reason] += 1
        elif row["source_job_id"] in accepted:
            exclusions["duplicate"] += 1
        else:
            accepted[row["source_job_id"]] = row
    return list(accepted.values()), exclusions


def _normalize_advert(advert: dict, as_of: date) -> tuple[dict[str, str] | None, str]:
    def value(key: str) -> str:
        raw = advert.get(key)
        return str(raw).strip() if isinstance(raw, (str, int)) else ""

    identifier = value("id")
    slug = value("url_title")
    title = value("title")
    company = value("company")
    if not (VACANCY_ID.fullmatch(identifier) and VACANCY_SLUG.fullmatch(slug) and title and company):
        return None, "identity"

    try:
        posting_date = datetime.strptime(value("created_on"), "%Y-%m-%d %H:%M:%S").date()
    except ValueError:
        return None, "date"
    if posting_date > as_of:
        return None, "date"

    category = value("category_name")
    if not is_technical_advert(title, category):
        return None, "role"

    description = clean_advert_text(value("description"))
    if len(description) < 140 or len(description.split()) < 25:
        return None, "text"

    return {
        "source_platform": "itpro.lk",
        "source_job_id": identifier,
        "source_url": f"https://itpro.lk/job/{identifier}/{slug}",
        "job_title_raw": title,
        "company_raw": company,
        "country_raw": "Sri Lanka",
        "location_raw": value("location"),
        "employment_type_raw": value("type_name"),
        "posted_date_raw": posting_date.isoformat(),
        "posting_date_source": "ITPro widget created_on",
        "source_category": category,
        "job_description_raw": description,
    }, ""


def is_technical_advert(title: str, category: str) -> bool:
    return not PROMOTIONAL_TITLE.search(title) and (
        category in TECHNICAL_CATEGORIES or ADJACENT_TITLE.search(title) is not None
    )


def clean_advert_text(description_html: str) -> str:
    """Extract plain text and omit direct recruiter contact details."""
    soup = BeautifulSoup(description_html, "html.parser")
    for element in soup.find_all(["script", "style", "iframe", "noscript"]):
        element.decompose()
    text = html.unescape(soup.get_text(" ", strip=True))
    return " ".join(CONTACT.sub("[contact removed]", text).split())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Saved ITPro widget response")
    parser.add_argument("output", type=Path, help="New historical-import CSV path")
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    args = parser.parse_args()

    payload = args.input.read_bytes()
    rows, excluded = normalize_feed(payload.decode("utf-8-sig"), args.as_of)
    with args.output.open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({
        "input_sha256": hashlib.sha256(payload).hexdigest(),
        "staged_rows": len(rows),
        "excluded": excluded,
        "month_counts": dict(sorted(Counter(row["posted_date_raw"][:7] for row in rows).items())),
    }, indent=2))


if __name__ == "__main__":
    main()
