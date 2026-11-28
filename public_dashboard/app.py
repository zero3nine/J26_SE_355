"""Read-only WSGI app. Run locally: python -m public_dashboard.app."""
from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from .data import PublicationUnavailable, options, published_forecast, read_snapshot, summarize

STATIC = Path(__file__).with_name("static")
DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "public" / "dashboard.sqlite3"

STATIC_ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/theme.js": ("theme.js", "application/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
}


def _analysis_query(query_string, available, metadata):
    query = parse_qs(query_string, keep_blank_values=True)
    allowed = {"country", "role", "source", "start", "end", "method", "skill", "min_jobs", "view"}
    if set(query) - allowed or any(len(values) != 1 for values in query.values()):
        raise ValueError("Unsupported or repeated filter.")
    filters = {key: values[0] for key, values in query.items() if key != "view"}
    filters.setdefault("method", "semantic")
    if filters["method"] not in ("lexical", "semantic"):
        raise ValueError("Choose lexical or semantic extraction.")
    for key, values in (("country", available["countries"]), ("role", available["roles"]),
                        ("source", available["sources"]), ("skill", available["skills"])):
        if filters.get(key) and filters[key] not in values:
            raise ValueError(f"Unknown {key}.")
    for key in ("start", "end"):
        if filters.get(key):
            date.fromisoformat(filters[key])
            if not metadata["date_start"] <= filters[key] <= metadata["date_end"]:
                raise ValueError("Dates must be within this publication's observation window.")
    if filters.get("start", metadata["date_start"]) > filters.get("end", metadata["date_end"]):
        raise ValueError("The start date must be before the end date.")
    minimum = int(filters.get("min_jobs", 5))
    if not 1 <= minimum <= 10000:
        raise ValueError("Minimum sample must be between 1 and 10000.")
    return query, filters


def _export_csv(view, result, metadata, filters):
    if view not in ("skills", "roles", "markets", "relationships", "comparison", "timeline", "forecasts"):
        raise ValueError("Unknown export view.")
    rows = result["forecast"]["rows"] if view == "forecasts" else result[view]
    if view == "timeline":
        selected_skill = filters.get("skill")
        rows = [
            {"period": point["period"], "eligible_jobs": point["eligible"], "skill": skill, "demand_rate_pct": rate}
            for point in rows
            for skill, rate in point["rates"].items()
            if not selected_skill or skill == selected_skill
        ]
    else:
        rows = [{k: v for k, v in r.items() if k != "skills"} for r in rows]
    # Include context on every row so downloaded findings remain interpretable.
    context = {
        "snapshot_id": metadata["snapshot_id"],
        "synthetic": metadata["is_synthetic"],
        "method": filters["method"],
        "scope": json.dumps(filters, sort_keys=True),
    }
    rows = [{**context, **r} for r in rows]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]) if rows else list(context))
    writer.writeheader()
    for row in rows:
        # Spreadsheet formula injection protection for arbitrary labels.
        safe_row = {}
        for key, value in row.items():
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                value = "'" + value
            safe_row[key] = value
        writer.writerow(safe_row)
    return output.getvalue().encode("utf-8-sig")


def create_app(db_path: Path | None = None):
    target = Path(db_path or os.environ.get("DASHBOARD_DB", DEFAULT_DB))

    def application(environ, start_response):
        headers = [("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "same-origin"),
                   ("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"),
                   ("Cache-Control", "no-store")]

        def respond(status, content, mime="application/json; charset=utf-8", extra=()):
            body = content if isinstance(content, bytes) else json.dumps(content, allow_nan=False).encode()
            start_response(status, headers + [("Content-Type", mime), ("Content-Length", str(len(body)))] + list(extra))
            return [b"" if environ.get("REQUEST_METHOD") == "HEAD" else body]

        if environ.get("REQUEST_METHOD") not in ("GET", "HEAD"):
            return respond("405 Method Not Allowed", {"error": "This dashboard is read-only."}, extra=[("Allow", "GET, HEAD")])
        path = environ.get("PATH_INFO", "/")
        if path in STATIC_ASSETS:
            filename, mime = STATIC_ASSETS[path]
            return respond("200 OK", (STATIC / filename).read_bytes(), mime)
        if path not in ("/api/options", "/api/analysis", "/api/export", "/healthz"):
            return respond("404 Not Found", {"error": "Page not found."})
        try:
            metadata, jobs = read_snapshot(target)
            if path == "/healthz":
                return respond("200 OK", {"status": "ok", "snapshot_id": metadata["snapshot_id"]})
            available = options(metadata, jobs)
            if path == "/api/options":
                return respond("200 OK", available)
            query, filters = _analysis_query(environ.get("QUERY_STRING", ""), available, metadata)
            result = summarize(metadata, jobs, filters)
            result["forecast"] = published_forecast(target, metadata, filters, result["selected_skill"])
            if path == "/api/export":
                view = query.get("view", ["skills"])[0]
                return respond(
                    "200 OK", _export_csv(view, result, metadata, filters), "text/csv; charset=utf-8",
                    [("Content-Disposition", f'attachment; filename="skillscope-{view}.csv"')],
                )
            return respond("200 OK", result)
        except PublicationUnavailable as exc:
            return respond("503 Service Unavailable", {"error": str(exc)})
        except (ValueError, TypeError) as exc:
            return respond("400 Bad Request", {"error": str(exc)})
        except Exception:
            logging.exception("Public dashboard request failed")
            return respond("500 Internal Server Error", {"error": "Analysis is temporarily unavailable. Please retry."})
    return application


application = create_app()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    with make_server(args.host, args.port, create_app(args.database)) as server:
        print(f"Dashboard: http://{args.host}:{args.port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
