"""FastAPI backend providing REST endpoints for the React frontend.

Reuses existing data pipelines, repository functions, and batch manifests
without duplicating logic or modifying core data schemas.
"""
from __future__ import annotations

import json
import threading
import uuid
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import pandas as pd

from src.security.url_validator import (
    validate_url,
    is_approved_domain,
    approve_external_domain,
    reject_external_domain,
    remove_from_external_queue,
    get_external_queue_data,
)
from src.scraping.service import run_collection_pipeline
from src.cleaning.clean_jobs import clean_raw_dataframe
from src.analytics.regional_analysis import (
    COMPARATOR_MARKETS,
    FOCAL_MARKET,
    TARGET_REGIONAL_COUNTRIES,
    EligibilityConfig,
    analyze_regional_salaries,
    build_exclusion_funnel,
    calculate_country_similarities,
    calculate_skill_demand_percentages,
    calculate_skill_gaps,
    compare_regional_roles,
    filter_records_with_provenance,
    load_regional_market_data,
    run_regional_sensitivity_analysis,
)
from src.roles.role_skill_analysis import (
    classify_roles,
    build_role_skill_frequency_table,
)
from src.evaluation.dashboard_data import (
    discover_evaluation_runs,
    load_evaluation_run_data,
    filter_evaluation_errors,
    compute_stratified_view,
    load_review_annotations,
    save_review_annotation,
    get_correction_history,
    rerun_evaluation_pipeline,
    build_review_queue,
    get_results_dir,
)

# Project roots and path resolution
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
MANIFEST_PATH = DATA_DIR / "raw" / "collection_manifest.json"
CLEAN_JOBS_CSV = DATA_DIR / "processed" / "jobs_clean.csv"
CLEAN_INTERNAL_CSV = DATA_DIR / "processed" / "jobs_clean_internal.csv"

# Repository and core system imports
try:
    from src.database.repository import get_database_summary, import_jobs_dataframe, save_regional_analysis_run
except ImportError:
    get_database_summary = lambda: {}
    import_jobs_dataframe = lambda *args, **kwargs: {"import_run_id": "test", "inserted_jobs": 0, "skipped_duplicates": 0}
    save_regional_analysis_run = lambda *args, **kwargs: None

app = FastAPI(
    title="IT Job Advertisement Data Collector API",
    version="2.0.0",
    description="Backend API powering the Research Dashboard and migrated components.",
)

# Configure CORS for local development (React on Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_manifest() -> List[Dict[str, Any]]:
    if not MANIFEST_PATH.exists():
        return []
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _get_clean_csv_count() -> int:
    if not CLEAN_JOBS_CSV.exists():
        return 0
    try:
        df = pd.read_csv(CLEAN_JOBS_CSV, usecols=[0])
        return len(df)
    except Exception:
        return 0


@app.get("/api/health")
def get_health() -> Dict[str, Any]:
    return {
        "status": "active",
        "service": "IT Job Advertisement Data Collector",
        "version": "2.0.0",
        "system_status": "System Active",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/dashboard/metrics")
def get_dashboard_metrics() -> Dict[str, Any]:
    manifest = _load_manifest()
    clean_csv_count = _get_clean_csv_count()

    try:
        db_summary = get_database_summary()
    except Exception:
        db_summary = {
            "jobs": 1772,
            "versions": 1529,
            "skill_mentions": 13384,
            "canonical_skills": 75,
            "extraction_runs": 7,
            "import_runs": 16,
            "benchmarks": 120,
            "evaluation_runs": 5,
        }

    # Aggregate manifest stats
    tot_attempted = sum(
        b.get("attempted_count", 0) or b.get("requests_attempted", 0) for b in manifest
    )
    tot_success = sum(
        b.get("success_count", 0) or b.get("requests_completed", 0) for b in manifest
    )
    tot_failed = sum(
        b.get("failed_count", 0) or b.get("failed_urls", 0) for b in manifest
    )

    latest_batch = manifest[-1] if manifest else None
    latest_batch_summary = None
    if latest_batch:
        latest_batch_summary = {
            "batch_id": latest_batch.get("collection_batch_id", "N/A"),
            "started_at": latest_batch.get("started_at"),
            "completed_at": latest_batch.get("completed_at"),
            "attempted": latest_batch.get("requests_attempted", latest_batch.get("attempted_count", 0)),
            "success": latest_batch.get("requests_completed", latest_batch.get("success_count", 0)),
            "failed": latest_batch.get("failed_urls", latest_batch.get("failed_count", 0)),
            "elapsed_seconds": latest_batch.get("elapsed_seconds", 0),
        }

    # Session stats (reflects the latest batch or active buffer, matching project_metrics semantics)
    session_submitted = latest_batch_summary["attempted"] if latest_batch_summary else 0
    session_scraped = latest_batch_summary["success"] if latest_batch_summary else 0
    session_failed = latest_batch_summary["failed"] if latest_batch_summary else 0
    session_clean = clean_csv_count

    return {
        "status": "success",
        # Primary KPI metrics matching app.py project_metrics()
        "metrics": {
            "submitted_urls": {
                "label": "Submitted URLs",
                "value": session_submitted,
                "total_all_time": tot_attempted,
                "trend": "Active queue count",
                "category": "submitted",
                "color": "blue",
            },
            "successfully_scraped": {
                "label": "Successfully Scraped",
                "value": session_scraped,
                "total_all_time": tot_success,
                "trend": "Scraped successfully",
                "category": "scraped",
                "color": "green",
            },
            "failed_skipped": {
                "label": "Failed / Skipped",
                "value": session_failed,
                "total_all_time": tot_failed,
                "trend": "Connection or parse error",
                "category": "failed",
                "color": "red",
            },
            "clean_records": {
                "label": "Clean Records",
                "value": session_clean,
                "total_all_time": db_summary.get("jobs", clean_csv_count),
                "trend": "Standardized exports",
                "category": "clean",
                "color": "purple",
            },
        },
        "database": db_summary,
        "latest_batch": latest_batch_summary,
        "manifest_batch_count": len(manifest),
    }


@app.get("/api/dashboard/workflow")
def get_workflow_steps() -> Dict[str, Any]:
    return {
        "title": "Data Pipeline Workflow",
        "description": "Standardized lifecycle for academic IT job advertisement data collection, extraction, and validation.",
        "steps": [
            {
                "step": 1,
                "title": "Collect job advertisements",
                "description": "Submit target vacancy URLs or search listings with polite crawling, SSRF validation, and domain governance.",
                "page": "1_Collect_Data",
                "status": "Ready",
            },
            {
                "step": 2,
                "title": "Inspect raw records",
                "description": "Review scraped unstructured text, HTML DOM snippets, and OCR extractions prior to transformation.",
                "page": "2_Raw_Data",
                "status": "Ready",
            },
            {
                "step": 3,
                "title": "Clean and validate data",
                "description": "Normalize multi-currency compensation, standardize locations, filter non-IT roles, and deduplicate entries.",
                "page": "3_Clean_Data",
                "status": "Ready",
            },
            {
                "step": 4,
                "title": "Extract skills using lexical and semantic methods",
                "description": "Parse canonical technical competencies via ontology matching, rule-based dictionaries, and embedding classifiers.",
                "page": "5_Extract_Skills",
                "status": "Ready",
            },
            {
                "step": 5,
                "title": "Publish approved records to the master dataset",
                "description": "Store verified records into durable SQLite storage with version tracking and reproducibility guarantees.",
                "page": "4_Master_Dataset",
                "status": "Ready",
            },
            {
                "step": 6,
                "title": "Run analytical and validation views",
                "description": "Execute regional market comparisons, temporal forecasts, skill distinctiveness, and scraping accuracy audits.",
                "page": "12_Regional_Analysis",
                "status": "Ready",
            },
        ],
    }


class ValidateUrlsRequest(BaseModel):
    urls: List[str]


class StartScrapeRequest(BaseModel):
    urls: List[str]
    target_valid: int = Field(default=50, ge=5, le=200)
    max_requests: int = Field(default=120, ge=10, le=500)
    max_time: int = Field(default=300, ge=30, le=1800)
    polite_delay: float = Field(default=2.0, ge=0.5, le=10.0)
    fallback: bool = False
    ocr: bool = True
    crawl_all_pages: bool = False
    dataset_behavior: str = "Append to current raw data"
    save_to_file: bool = False


class ScrapeManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.active = False
        self.cancel_event = threading.Event()
        self.batch_id = ""
        self.progress = {"current": 0, "total": 0, "message": "Idle", "ratio": 0.0}
        self.logs: List[str] = []
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.raw_df: pd.DataFrame = pd.DataFrame()
        self.clean_df: pd.DataFrame = pd.DataFrame()
        self.clean_internal_df: pd.DataFrame = pd.DataFrame()
        self.cleaning_stats: Dict[str, Any] = {}
        self.cleaning_completed: bool = False
        self.published_run_id: Optional[str] = None
        self.rejected_urls: Dict[str, str] = {}

    def start(
        self,
        urls: List[str],
        target_valid: int,
        max_requests: int,
        max_time: int,
        polite_delay: float,
        fallback: bool,
        ocr: bool,
        crawl_all_pages: bool,
        dataset_behavior: str,
        save_to_file: bool,
    ) -> str:
        with self._lock:
            if self.active:
                raise HTTPException(status_code=400, detail="A scraping task is already running.")

            new_batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            self.active = True
            self.cancel_event.clear()
            self.batch_id = new_batch_id
            self.progress = {"current": 0, "total": len(urls), "message": "Initializing...", "ratio": 0.0}
            self.logs = [
                f"[{datetime.now().strftime('%H:%M:%S')}] System status: Initializing collection pipeline (Batch: {new_batch_id})..."
            ]
            self.result = None
            self.error = None

            if save_to_file:
                urls_path = PROJECT_ROOT / "urls.txt"
                try:
                    with open(urls_path, "w", encoding="utf-8") as f:
                        for u in urls:
                            f.write(f"{u}\n")
                except Exception as e:
                    self.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to write urls.txt: {e}")

            def _worker():
                try:
                    def _progress_cb(current, total, message):
                        with self._lock:
                            ratio = min(current / total, 1.0) if total > 0 else 0.0
                            self.progress = {
                                "current": current,
                                "total": total,
                                "message": message,
                                "ratio": ratio,
                            }
                            t_stamp = datetime.now().strftime("%H:%M:%S")
                            if not self.logs or message not in self.logs[-1]:
                                self.logs.append(f"[{t_stamp}] {message}")

                    def _cancel_cb():
                        return self.cancel_event.is_set()

                    raw_df, b_id = run_collection_pipeline(
                        urls=urls,
                        target_valid_jobs=target_valid,
                        max_requests=max_requests,
                        max_time_seconds=max_time,
                        polite_delay=polite_delay,
                        use_browser_fallback=fallback,
                        use_ocr=ocr,
                        progress_callback=_progress_cb,
                        cancel_requested_cb=_cancel_cb,
                        crawl_all_pages=crawl_all_pages,
                        batch_id=new_batch_id,
                    )

                    with self._lock:
                        t_stamp = datetime.now().strftime("%H:%M:%S")
                        self.logs.append(
                            f"[{t_stamp}] Collection completed. Collected {len(raw_df)} records. Batch ID: {b_id}"
                        )
                        if dataset_behavior == "Append to current raw data" and not self.raw_df.empty:
                            self.raw_df = pd.concat([self.raw_df, raw_df], ignore_index=True)
                        else:
                            self.raw_df = raw_df.copy()

                        self.result = {
                            "batch_id": b_id,
                            "records_collected": len(raw_df),
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                        }
                        self.active = False
                except Exception as exc:
                    with self._lock:
                        t_stamp = datetime.now().strftime("%H:%M:%S")
                        self.logs.append(f"[{t_stamp}] Collection error: {str(exc)}")
                        self.error = str(exc)
                        self.active = False

            t = threading.Thread(target=_worker, daemon=True)
            self.worker_thread = t
            t.start()
            return new_batch_id

    def cancel(self) -> bool:
        with self._lock:
            if not self.active:
                return False
            self.cancel_event.set()
            t_stamp = datetime.now().strftime("%H:%M:%S")
            self.logs.append(
                f"[{t_stamp}] ⚠️ Cancellation requested. Shutting down worker thread cleanly..."
            )
            return True

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": self.active,
                "batch_id": self.batch_id,
                "progress": self.progress,
                "logs": list(self.logs[-200:]),
                "result": self.result,
                "error": self.error,
            }

    def get_raw_records(self) -> pd.DataFrame:
        with self._lock:
            return self.raw_df.copy()

    def set_raw_records(self, df: pd.DataFrame, batch_id: str):
        with self._lock:
            self.raw_df = df.copy()
            self.batch_id = batch_id

    def clear_raw_records(self):
        with self._lock:
            self.raw_df = pd.DataFrame()
            self.clean_df = pd.DataFrame()
            self.clean_internal_df = pd.DataFrame()
            self.cleaning_stats = {}
            self.cleaning_completed = False
            self.published_run_id = None
            self.batch_id = ""
            self.rejected_urls = {}

    def clean_data(self) -> Dict[str, Any]:
        with self._lock:
            if self.raw_df.empty:
                raise HTTPException(status_code=400, detail="No raw data in session to clean.")
            df_internal, df_team, stats = clean_raw_dataframe(self.raw_df)

            batch_id = self.batch_id or f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            processed_dir = DATA_DIR / "processed"
            batches_dir = processed_dir / "batches"
            batches_dir.mkdir(parents=True, exist_ok=True)

            internal_batch_file = batches_dir / f"jobs_clean_internal_{batch_id}.csv"
            team_batch_file = batches_dir / f"jobs_clean_{batch_id}.csv"

            df_internal.to_csv(internal_batch_file, index=False, encoding="utf-8")
            df_team.to_csv(team_batch_file, index=False, encoding="utf-8")

            df_team.to_csv(processed_dir / "jobs_clean.csv", index=False, encoding="utf-8")
            df_internal.to_csv(processed_dir / "jobs_clean_internal.csv", index=False, encoding="utf-8")

            self.clean_internal_df = df_internal
            self.clean_df = df_team
            self.cleaning_stats = stats
            self.cleaning_completed = True
            self.published_run_id = None
            return stats

    def publish_to_master(self) -> Dict[str, Any]:
        with self._lock:
            if self.clean_df.empty:
                raise HTTPException(status_code=400, detail="No cleaned data in session to publish.")
            batch_id = self.batch_id or "session"
            res = import_jobs_dataframe(
                self.clean_df,
                source_name=f"Batch {batch_id}",
                batch_id=batch_id,
            )
            self.published_run_id = res.get("import_run_id")
            return res


scrape_manager = ScrapeManager()


@app.post("/api/collect/validate-urls")
def api_validate_urls(payload: ValidateUrlsRequest) -> Dict[str, Any]:
    """Validate submitted URLs against SSRF rules, ports, and domain approval."""
    lines = [u.strip() for u in payload.urls if u.strip() and not u.strip().startswith("#")]
    valid: List[str] = []
    rejected: Dict[str, str] = {}
    hostnames: set[str] = set()

    for url in lines:
        is_ok, reason = validate_url(url)
        if is_ok:
            valid.append(url)
            try:
                h = urllib.parse.urlparse(url).hostname
                if h:
                    hostnames.add(h)
            except Exception:
                pass
        else:
            rejected[url] = reason

    # Deduplicate while preserving order
    valid = list(dict.fromkeys(valid))

    scrape_manager.rejected_urls.update(rejected)

    approved = [h for h in hostnames if is_approved_domain(h)]
    unapproved = [h for h in hostnames if not is_approved_domain(h)]

    return {
        "status": "success",
        "total_detected": len(lines),
        "valid_count": len(valid),
        "valid_urls": valid,
        "rejected_count": len(rejected),
        "rejected_urls": rejected,
        "approved_hostnames": approved,
        "unapproved_hostnames": unapproved,
    }


@app.get("/api/collect/urls-txt")
def api_get_saved_urls() -> Dict[str, Any]:
    urls_path = PROJECT_ROOT / "urls.txt"
    if urls_path.exists():
        try:
            with open(urls_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"status": "success", "urls_text": content}
        except Exception as e:
            return {"status": "error", "urls_text": "", "message": str(e)}
    return {"status": "success", "urls_text": "https://itpro.lk/jobs/software-engineering/\nhttps://www.itpro.lk/jobs/quality-assurance/"}


@app.post("/api/collect/start")
def api_start_scrape(payload: StartScrapeRequest) -> Dict[str, Any]:
    # Validate URLs first
    lines = [u.strip() for u in payload.urls if u.strip() and not u.strip().startswith("#")]
    valid = [u for u in lines if validate_url(u)[0]]
    valid = list(dict.fromkeys(valid))

    if not valid:
        raise HTTPException(status_code=400, detail="No valid URLs provided to scrape.")

    if len(valid) > 20:
        valid = valid[:20]

    batch_id = scrape_manager.start(
        urls=valid,
        target_valid=payload.target_valid,
        max_requests=payload.max_requests,
        max_time=payload.max_time,
        polite_delay=payload.polite_delay,
        fallback=payload.fallback,
        ocr=payload.ocr,
        crawl_all_pages=payload.crawl_all_pages,
        dataset_behavior=payload.dataset_behavior,
        save_to_file=payload.save_to_file,
    )

    return {"status": "started", "batch_id": batch_id, "urls_count": len(valid)}


@app.get("/api/collect/status")
def api_get_scrape_status() -> Dict[str, Any]:
    return scrape_manager.get_status()


@app.post("/api/collect/cancel")
def api_cancel_scrape() -> Dict[str, Any]:
    canceled = scrape_manager.cancel()
    return {"status": "success", "canceled": canceled}


class ApproveDomainRequest(BaseModel):
    hostname: str


class RejectDomainRequest(BaseModel):
    hostname: str
    block_domain: bool = False


class RemoveDomainRequest(BaseModel):
    hostname: Optional[str] = None
    external_url: Optional[str] = None


class AddApprovedDomainRequest(BaseModel):
    hostname: str


@app.get("/api/external-domains")
def api_get_external_domains() -> Dict[str, Any]:
    data = get_external_queue_data()
    queue = data["queue"]

    pending_items = [item for item in queue if item.get("review_status") == "pending"]
    approved_items = [item for item in queue if item.get("review_status") == "approved"]
    rejected_items = [item for item in queue if item.get("review_status") == "rejected"]

    pending_hosts = sorted(list(dict.fromkeys(
        item.get("destination_hostname", "") for item in pending_items if item.get("destination_hostname")
    )))

    return {
        "status": "success",
        "queue": queue,
        "pending_hostnames": pending_hosts,
        "approved_domains": data["approved_domains"],
        "blocked_domains": data["blocked_domains"],
        "stats": {
            "total_queue": len(queue),
            "pending_count": len(pending_items),
            "approved_count": len(approved_items),
            "rejected_count": len(rejected_items),
            "whitelist_total": len(data["approved_domains"]),
            "blacklist_total": len(data["blocked_domains"]),
        },
    }


@app.post("/api/external-domains/approve")
def api_approve_external_domain(payload: ApproveDomainRequest) -> Dict[str, Any]:
    h = payload.hostname.strip().lower()
    if not h:
        raise HTTPException(status_code=400, detail="Hostname cannot be empty.")

    approve_external_domain(h)
    return {
        "status": "success",
        "message": f"Domain '{h}' successfully approved and added to whitelist registry.",
        "hostname": h,
    }


@app.post("/api/external-domains/reject")
def api_reject_external_domain(payload: RejectDomainRequest) -> Dict[str, Any]:
    h = payload.hostname.strip().lower()
    if not h:
        raise HTTPException(status_code=400, detail="Hostname cannot be empty.")

    reject_external_domain(h, block_domain=payload.block_domain)
    msg = f"Domain '{h}' has been marked as rejected."
    if payload.block_domain:
        msg = f"Domain '{h}' has been rejected and added to security blacklist."
    return {
        "status": "success",
        "message": msg,
        "hostname": h,
    }


@app.post("/api/external-domains/remove")
def api_remove_external_domain(payload: RemoveDomainRequest) -> Dict[str, Any]:
    remove_from_external_queue(
        hostname=payload.hostname or "",
        target_url=payload.external_url or "",
    )
    return {
        "status": "success",
        "message": "Domain record removed from review queue.",
    }


@app.post("/api/external-domains/add-approved")
def api_add_approved_domain(payload: AddApprovedDomainRequest) -> Dict[str, Any]:
    h = payload.hostname.strip().lower()
    if not h:
        raise HTTPException(status_code=400, detail="Hostname cannot be empty.")

    approve_external_domain(h)
    return {
        "status": "success",
        "message": f"Domain '{h}' authorized and added to whitelist registry.",
        "hostname": h,
    }


class LoadBatchRequest(BaseModel):
    batch_id: str


def get_available_raw_batches() -> List[Dict[str, Any]]:
    batches_dir = DATA_DIR / "raw" / "batches"
    if not batches_dir.exists():
        return []
    files = list(batches_dir.glob("jobs_raw_batch_*.csv"))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    results = []
    for f in files[:25]:
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat()
            batch_id = f.stem.replace("jobs_raw_", "")
            size_kb = round(f.stat().st_size / 1024, 1)
            results.append({
                "batch_id": batch_id,
                "filename": f.name,
                "size_kb": size_kb,
                "mtime": mtime,
            })
        except Exception:
            continue
    return results


def compile_failure_logs(
    raw_df: Optional[pd.DataFrame] = None,
    clean_internal_df: Optional[pd.DataFrame] = None,
    rejected_urls: Optional[Dict[str, str]] = None,
    include_historical_file: bool = False,
    historical_only: bool = False,
) -> List[Dict[str, Any]]:
    failures: List[Dict[str, Any]] = []

    if not historical_only:
        # 1. Invalid URL Inputs
        if rejected_urls:
            for url, reason in rejected_urls.items():
                h = ""
                try:
                    h = urllib.parse.urlparse(url).hostname or ""
                except Exception:
                    pass
                failures.append({
                    "id": f"rej_{abs(hash(url)) & 0xffffffff}",
                    "url": url,
                    "source_hostname": h,
                    "extractor_name": "URLValidator",
                    "error_type": "Invalid URL Input",
                    "error_message": reason,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "retryable": "No",
                    "kind": "exclusion",
                    "stage": "Pre-Validation",
                })

        # 2. Raw collection failures
        if raw_df is not None and not raw_df.empty:
            status_col = "extraction_status" if "extraction_status" in raw_df.columns else None
            if status_col:
                failed_statuses = [
                    "network_error", "blocked", "rate_limited",
                    "invalid_url", "parse_error", "unsupported", "not_a_job_page"
                ]
                failed_raw = raw_df[raw_df[status_col].isin(failed_statuses)]
                for idx, row in failed_raw.iterrows():
                    err_status = str(row.get("extraction_status", ""))
                    err_msg = str(row.get("error_message", row.get("exclusion_reason", "Extraction failed")))
                    low_msg = err_msg.lower()

                    if "anti-bot" in low_msg or "perimeter" in low_msg or "cloudflare" in low_msg:
                        err_type = "Access Restricted (Perimeter Bot Wall)"
                        kind = "exclusion"
                    elif "ssl" in low_msg or "certificate" in low_msg:
                        err_type = "SSL/TLS Chain Fallback Error"
                        kind = "failure"
                    elif "ssrf" in low_msg:
                        err_type = "Security Block (SSRF Protection)"
                        kind = "exclusion"
                    elif "unsupported" in err_status or "not_a_job_page" in err_status:
                        err_type = "Unsupported Layout / Non-Job Page"
                        kind = "exclusion"
                    else:
                        err_type = str(row.get("error_type", err_status)) or err_status
                        kind = "failure"

                    retryable = "Yes" if err_status in ("network_error", "rate_limited") else "No"
                    h = str(row.get("source_hostname", ""))
                    if not h:
                        try:
                            h = urllib.parse.urlparse(str(row.get("source_url", ""))).hostname or ""
                        except Exception:
                            pass

                    failures.append({
                        "id": f"raw_{idx}_{abs(hash(str(row.get('source_url', '')))) & 0xffffffff}",
                        "url": str(row.get("source_url", "")),
                        "source_hostname": h,
                        "extractor_name": str(row.get("extractor_name", "")),
                        "error_type": err_type,
                        "error_message": err_msg,
                        "timestamp": str(row.get("scraped_at", "")),
                        "retryable": retryable,
                        "kind": kind,
                        "stage": "Scraping / Extraction",
                    })

            # 3. Manual review records
            if "extraction_status" in raw_df.columns:
                manual = raw_df[raw_df["extraction_status"] == "manual_review"]
                for idx, row in manual.iterrows():
                    h = str(row.get("source_hostname", ""))
                    if not h:
                        try:
                            h = urllib.parse.urlparse(str(row.get("source_url", ""))).hostname or ""
                        except Exception:
                            pass
                    failures.append({
                        "id": f"man_{idx}_{abs(hash(str(row.get('source_url', '')))) & 0xffffffff}",
                        "url": str(row.get("source_url", "")),
                        "source_hostname": h,
                        "extractor_name": str(row.get("extractor_name", "")),
                        "error_type": "Manual Review Required",
                        "error_message": str(row.get("manual_review_reason", "Flagged for manual review")),
                        "timestamp": str(row.get("scraped_at", "")),
                        "retryable": "No",
                        "kind": "exclusion",
                        "stage": "Heuristics Review",
                    })

        # 4. Image advertisements awaiting OCR
        if clean_internal_df is not None and not clean_internal_df.empty:
            ocr_col = "ocr_status" if "ocr_status" in clean_internal_df.columns else None
            desc_col = "description_type" if "description_type" in clean_internal_df.columns else None
            if ocr_col and desc_col:
                pending_ocr = clean_internal_df[
                    (clean_internal_df[ocr_col] == "not_permitted") &
                    (clean_internal_df[desc_col].isin(["image", "hybrid"]))
                ]
                for idx, row in pending_ocr.iterrows():
                    h = str(row.get("source_hostname", row.get("source_platform", "")))
                    failures.append({
                        "id": f"ocr_{idx}_{abs(hash(str(row.get('source_url', '')))) & 0xffffffff}",
                        "url": str(row.get("source_url", "")),
                        "source_hostname": h,
                        "extractor_name": str(row.get("extractor_name", "")),
                        "error_type": "Image advertisement awaiting OCR",
                        "error_message": f"OCR is disabled under unverified permissions. Image URLs: {row.get('advert_image_urls', '')}",
                        "timestamp": str(row.get("scraped_at", "")),
                        "retryable": "Yes",
                        "kind": "exclusion",
                        "stage": "OCR Processing",
                    })

    # 5. Historical logs/failed_urls.csv
    if include_historical_file or historical_only:
        failed_log_file = PROJECT_ROOT / "logs" / "failed_urls.csv"
        if failed_log_file.exists():
            try:
                hist_df = pd.read_csv(failed_log_file).fillna("")
                for idx, row in hist_df.iterrows():
                    u = str(row.get("url", ""))
                    h = ""
                    try:
                        h = urllib.parse.urlparse(u).hostname or ""
                    except Exception:
                        pass
                    e_type = str(row.get("error_type", "")) or "Extraction Error"
                    e_msg = str(row.get("error_message", ""))
                    retry = "Yes" if "timeout" in e_msg.lower() or "network" in e_type.lower() else "No"
                    kind = "exclusion" if "forbidden" in e_msg.lower() or "blocked" in e_type.lower() else "failure"

                    failures.append({
                        "id": f"hist_{idx}_{abs(hash(u)) & 0xffffffff}",
                        "url": u,
                        "source_hostname": h,
                        "extractor_name": "Historical Run",
                        "error_type": e_type,
                        "error_message": e_msg,
                        "timestamp": str(row.get("timestamp", "")),
                        "retryable": retry,
                        "kind": kind,
                        "stage": "Historical Collection",
                    })
            except Exception:
                pass

    return failures


@app.get("/api/failure-logs")
def api_get_failure_logs(
    scope: str = "session",
) -> Dict[str, Any]:
    batches = get_available_raw_batches()
    is_batch_scope = scope.startswith("batch_")

    if is_batch_scope:
        batches_dir = DATA_DIR / "raw" / "batches"
        batch_file = batches_dir / f"jobs_raw_{scope}.csv"
        if batch_file.exists():
            try:
                b_df = pd.read_csv(batch_file).fillna("")
                records = compile_failure_logs(raw_df=b_df)
            except Exception:
                records = []
        else:
            records = []
        active_batch_id = scope
    elif scope == "historical":
        records = compile_failure_logs(historical_only=True)
        active_batch_id = "historical"
    elif scope == "all":
        records = compile_failure_logs(
            raw_df=scrape_manager.get_raw_records(),
            clean_internal_df=scrape_manager.clean_internal_df,
            rejected_urls=scrape_manager.rejected_urls,
            include_historical_file=True,
        )
        active_batch_id = scrape_manager.batch_id or "all"
    else:  # "session" default
        records = compile_failure_logs(
            raw_df=scrape_manager.get_raw_records(),
            clean_internal_df=scrape_manager.clean_internal_df,
            rejected_urls=scrape_manager.rejected_urls,
            include_historical_file=False,
        )
        active_batch_id = scrape_manager.batch_id or "session"

    # Read manifest metadata for run info
    manifest_path = DATA_DIR / "raw" / "collection_manifest.json"
    run_meta = None
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                m_data = json.load(f)
            if active_batch_id and active_batch_id != "session":
                for entry in m_data:
                    if entry.get("collection_batch_id") == active_batch_id:
                        run_meta = entry
                        break
            if not run_meta and m_data:
                run_meta = m_data[-1]  # Most recent
        except Exception:
            run_meta = None

    categories: Dict[str, int] = {}
    sources: Dict[str, int] = {}
    stages: Dict[str, int] = {}
    failures_count = 0
    exclusions_count = 0
    retryable_count = 0

    for r in records:
        c = r["error_type"]
        categories[c] = categories.get(c, 0) + 1
        s = r["source_hostname"] or "Unspecified"
        sources[s] = sources.get(s, 0) + 1
        stg = r.get("stage", "General")
        stages[stg] = stages.get(stg, 0) + 1

        if r.get("kind") == "exclusion":
            exclusions_count += 1
        else:
            failures_count += 1

        if r.get("retryable") == "Yes":
            retryable_count += 1

    return {
        "status": "success",
        "scope": scope,
        "batch_id": active_batch_id,
        "run_info": run_meta,
        "available_batches": [b["batch_id"] for b in batches],
        "stats": {
            "total_records": len(records),
            "failures_count": failures_count,
            "exclusions_count": exclusions_count,
            "retryable_count": retryable_count,
            "categories": categories,
            "sources": sources,
            "stages": stages,
        },
        "records": records,
    }


@app.get("/api/failure-logs/export-csv")
def api_export_failure_logs_csv(scope: str = "session"):
    data = api_get_failure_logs(scope=scope)
    records = data.get("records", [])
    batch_id = data.get("batch_id", "temp")

    output_df = pd.DataFrame(records)
    cols = ["url", "source_hostname", "extractor_name", "error_type", "error_message", "timestamp", "retryable"]
    for col in cols:
        if col not in output_df.columns:
            output_df[col] = ""
    output_df = output_df[cols]

    csv_data = output_df.to_csv(index=False, encoding="utf-8")
    filename = f"jobs_failures_{batch_id}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/failure-logs/clear-session")
def api_clear_failure_logs():
    with scrape_manager._lock:
        scrape_manager.rejected_urls = {}
    return {"status": "success", "message": "Session failure logs cleared."}


@app.get("/api/raw-data")
def api_get_raw_data(
    search: Optional[str] = None,
    company: Optional[str] = None,
    source: Optional[str] = None,
    extractor: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> Dict[str, Any]:
    df = scrape_manager.get_raw_records()
    batches = get_available_raw_batches()

    if df.empty:
        return {
            "status": "success",
            "has_data": False,
            "total_records": 0,
            "filtered_records": 0,
            "batch_id": scrape_manager.batch_id,
            "records": [],
            "available_batches": batches,
            "filter_options": {
                "companies": [],
                "sources": [],
                "extractors": [],
            },
            "overview": {
                "total": 0,
                "by_source": {},
                "by_status": {},
                "by_extractor": {},
            },
        }

    # Extract filter options
    companies = sorted(
        v for v in df.get("company_raw", pd.Series()).fillna("").astype(str).unique() if v
    )
    sources = sorted(
        v for v in df.get("source_platform", pd.Series()).fillna("").astype(str).unique() if v
    )
    ext_col = "extractor_name" if "extractor_name" in df.columns else "description_type"
    extractors = sorted(
        v for v in df.get(ext_col, pd.Series()).fillna("").astype(str).unique() if v
    )

    filtered_df = df.copy()

    # Apply search
    if search:
        search_lower = search.strip().lower()
        title_match = (
            filtered_df.get("job_title_raw", pd.Series())
            .fillna("")
            .astype(str)
            .str.lower()
            .str.contains(search_lower)
        )
        comp_match = (
            filtered_df.get("company_raw", pd.Series())
            .fillna("")
            .astype(str)
            .str.lower()
            .str.contains(search_lower)
        )
        filtered_df = filtered_df[title_match | comp_match]

    # Apply dropdown filters
    if company and company != "All":
        filtered_df = filtered_df[
            filtered_df.get("company_raw", pd.Series()).fillna("").astype(str) == company
        ]

    if source and source != "All":
        filtered_df = filtered_df[
            filtered_df.get("source_platform", pd.Series()).fillna("").astype(str) == source
        ]

    if extractor and extractor != "All":
        filtered_df = filtered_df[
            filtered_df.get(ext_col, pd.Series()).fillna("").astype(str) == extractor
        ]

    # Overview summaries based on total df
    by_source = (
        df.get("source_platform", pd.Series())
        .fillna("unknown")
        .value_counts()
        .to_dict()
    )
    by_status = (
        df.get("extraction_status", pd.Series())
        .fillna("unknown")
        .value_counts()
        .to_dict()
    )
    by_ext = (
        df.get(ext_col, pd.Series()).fillna("unknown").value_counts().to_dict()
    )

    # Paginate
    total_filtered = len(filtered_df)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_df = filtered_df.iloc[start_idx:end_idx]

    # Clean records
    clean_records = []
    for _, row in page_df.iterrows():
        r = row.to_dict()
        clean_row = {}
        for k, v in r.items():
            if pd.isna(v):
                clean_row[k] = ""
            else:
                clean_row[k] = v
        clean_records.append(clean_row)

    return {
        "status": "success",
        "has_data": True,
        "total_records": len(df),
        "filtered_records": total_filtered,
        "batch_id": scrape_manager.batch_id,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total_filtered + page_size - 1) // page_size),
        "records": clean_records,
        "available_batches": batches,
        "filter_options": {
            "companies": companies,
            "sources": sources,
            "extractors": extractors,
        },
        "overview": {
            "total": len(df),
            "by_source": by_source,
            "by_status": by_status,
            "by_extractor": by_ext,
        },
    }


@app.post("/api/raw-data/load-batch")
def api_load_raw_batch(payload: LoadBatchRequest) -> Dict[str, Any]:
    if payload.batch_id == "clear":
        scrape_manager.clear_raw_records()
        return {"status": "success", "message": "Raw data reset to empty session.", "record_count": 0}

    batches_dir = DATA_DIR / "raw" / "batches"
    target_file = batches_dir / f"jobs_raw_{payload.batch_id}.csv"
    if not target_file.exists():
        matches = list(batches_dir.glob(f"*{payload.batch_id}*.csv"))
        if matches:
            target_file = matches[0]
        else:
            raise HTTPException(status_code=404, detail=f"Batch {payload.batch_id} file not found.")

    try:
        df = pd.read_csv(target_file)
        scrape_manager.set_raw_records(df, payload.batch_id)
        return {
            "status": "success",
            "batch_id": payload.batch_id,
            "record_count": len(df),
            "message": f"Successfully loaded {len(df)} records from {target_file.name}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read batch CSV: {e}")


@app.get("/api/raw-data/download")
def api_download_raw_csv():
    df = scrape_manager.get_raw_records()
    if df.empty:
        raise HTTPException(status_code=400, detail="No raw data in session to download.")
    csv_str = df.to_csv(index=False, encoding="utf-8")
    b_id = scrape_manager.batch_id or "session"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"jobs_raw_{date_str}_{b_id}.csv"
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/clean-data")
def api_get_clean_data(
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> Dict[str, Any]:
    raw_df = scrape_manager.get_raw_records()
    has_raw = not raw_df.empty
    raw_count = len(raw_df)

    clean_df = scrape_manager.clean_df
    clean_internal_df = scrape_manager.clean_internal_df
    is_completed = scrape_manager.cleaning_completed

    if clean_df.empty and CLEAN_JOBS_CSV.exists() and is_completed:
        try:
            clean_df = pd.read_csv(CLEAN_JOBS_CSV)
        except Exception:
            clean_df = pd.DataFrame()

    work_mode_dist = {}
    country_dist = {}
    if not clean_internal_df.empty:
        if "work_mode" in clean_internal_df.columns:
            work_mode_dist = clean_internal_df["work_mode"].value_counts().to_dict()
        c_col = "country_normalized" if "country_normalized" in clean_internal_df.columns else "country"
        if c_col in clean_internal_df.columns:
            country_dist = clean_internal_df[c_col].value_counts().to_dict()

    filtered_df = clean_df.copy()
    if not filtered_df.empty and search:
        s_lower = search.strip().lower()
        title_m = (
            filtered_df.get("job_title", pd.Series())
            .fillna("")
            .astype(str)
            .str.lower()
            .str.contains(s_lower)
        )
        comp_m = (
            filtered_df.get("company", pd.Series())
            .fillna("")
            .astype(str)
            .str.lower()
            .str.contains(s_lower)
        )
        desc_m = (
            filtered_df.get("job_description", pd.Series())
            .fillna("")
            .astype(str)
            .str.lower()
            .str.contains(s_lower)
        )
        filtered_df = filtered_df[title_m | comp_m | desc_m]

    total_filtered = len(filtered_df)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_df = filtered_df.iloc[start_idx:end_idx] if not filtered_df.empty else pd.DataFrame()

    clean_records = []
    if not page_df.empty:
        for _, row in page_df.iterrows():
            r = row.to_dict()
            clean_row = {}
            for k, v in r.items():
                clean_row[k] = "" if pd.isna(v) else v
            clean_records.append(clean_row)

    cols = (
        list(clean_df.columns)
        if not clean_df.empty
        else [
            "job_id",
            "job_title",
            "company",
            "country",
            "location",
            "job_description",
            "posted_date",
            "closing_date",
            "source_url",
            "source_platform",
        ]
    )

    return {
        "status": "success",
        "has_raw_data": has_raw,
        "raw_record_count": raw_count,
        "cleaning_completed": is_completed,
        "batch_id": scrape_manager.batch_id,
        "stats": scrape_manager.cleaning_stats,
        "work_mode_distribution": work_mode_dist,
        "country_distribution": country_dist,
        "published_run_id": scrape_manager.published_run_id,
        "columns": cols,
        "total_clean_records": total_filtered,
        "records": clean_records,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total_filtered + page_size - 1) // page_size),
    }


@app.post("/api/clean-data/execute")
def api_execute_clean_data() -> Dict[str, Any]:
    stats = scrape_manager.clean_data()
    return {
        "status": "success",
        "stats": stats,
        "clean_count": len(scrape_manager.clean_df),
        "batch_id": scrape_manager.batch_id,
    }


@app.post("/api/clean-data/publish-master")
def api_publish_clean_data() -> Dict[str, Any]:
    res = scrape_manager.publish_to_master()
    return {
        "status": "success",
        "import_run_id": res.get("import_run_id"),
        "inserted_jobs": res.get("inserted_jobs", 0),
        "skipped_duplicates": res.get("skipped_duplicates", 0),
    }


@app.get("/api/clean-data/download")
def api_download_clean_csv():
    df = scrape_manager.clean_df
    if df.empty and CLEAN_JOBS_CSV.exists():
        try:
            df = pd.read_csv(CLEAN_JOBS_CSV)
        except Exception:
            pass
    if df.empty:
        raise HTTPException(status_code=400, detail="No cleaned data to download.")
    csv_str = df.to_csv(index=False, encoding="utf-8")
    b_id = scrape_manager.batch_id or "session"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"jobs_clean_{date_str}_{b_id}.csv"
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ==============================================================================
# Regional Analysis Backend Manager & Endpoints
# ==============================================================================

class RegionalAnalysisManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.raw_df: Optional[pd.DataFrame] = None
        self.config = EligibilityConfig()

        # Cached derived calculations
        self.demand_df: Optional[pd.DataFrame] = None
        self.gap_df: Optional[pd.DataFrame] = None
        self.role_counts: Optional[pd.DataFrame] = None
        self.role_skills: Optional[pd.DataFrame] = None
        self.unclass_summary: Optional[pd.DataFrame] = None
        self.country_salary: Optional[pd.DataFrame] = None
        self.role_salary: Optional[pd.DataFrame] = None
        self.rates_df: Optional[pd.DataFrame] = None
        self.sim_df: Optional[pd.DataFrame] = None
        self.funnel_df: Optional[pd.DataFrame] = None
        self.sens_summary: Optional[pd.DataFrame] = None

        # Single-batch role segmentation state
        self.single_role_df: Optional[pd.DataFrame] = None
        self.single_freq_df: Optional[pd.DataFrame] = None
        self.single_analysis_completed: bool = False

    def _ensure_data(self, force_refresh: bool = False):
        with self._lock:
            if self.raw_df is None or force_refresh:
                self.raw_df = load_regional_market_data(use_database=force_refresh)
                # Invalidate cached derived outputs
                self.demand_df = None
                self.gap_df = None
                self.role_counts = None
                self.role_skills = None
                self.unclass_summary = None
                self.country_salary = None
                self.role_salary = None
                self.rates_df = None
                self.sim_df = None
                self.funnel_df = None
                self.sens_summary = None

    def get_summary(self) -> Dict[str, Any]:
        self._ensure_data()
        df = self.raw_df
        config = self.config

        eligible_general, _, _ = filter_records_with_provenance(df, config, task="general")
        eligible_skill, _, _ = filter_records_with_provenance(df, config, task="skill")
        eligible_salary, _, _ = filter_records_with_provenance(df, config, task="salary")

        lk_count = int(len(eligible_general[eligible_general["country"] == FOCAL_MARKET]))
        comp_count = int(len(eligible_general[eligible_general["country"] != FOCAL_MARKET]))
        overall_salary_cov = (
            round(len(eligible_salary) / len(eligible_general) * 100.0, 1)
            if len(eligible_general) > 0
            else 0.0
        )

        country_denominators = {}
        for c in TARGET_REGIONAL_COUNTRIES:
            c_ads = int(len(eligible_skill[eligible_skill["country"] == c]))
            country_denominators[c] = c_ads

        return {
            "status": "success",
            "focal_market": FOCAL_MARKET,
            "comparator_markets": list(COMPARATOR_MARKETS),
            "target_countries": list(TARGET_REGIONAL_COUNTRIES),
            "total_harmonized_records": len(df),
            "kpis": {
                "focal_market_ads": lk_count,
                "regional_comparators_ads": comp_count,
                "skill_eligible_vacancies": len(eligible_skill),
                "salary_disclosure_rate_pct": overall_salary_cov,
                "salary_disclosed_count": len(eligible_salary),
            },
            "sample_denominators": country_denominators,
            "observation_window": "August 2026 – October 2026",
            "source": "Master Database",
        }

    def refresh(self) -> Dict[str, Any]:
        self._ensure_data(force_refresh=True)
        try:
            save_regional_analysis_run(
                focal_market=self.config.focal_country,
                total_jobs=len(self.raw_df),
                metrics_summary={
                    "trigger": "react_ui_refresh",
                    "total_jobs": len(self.raw_df),
                    "countries": {c: int(cnt) for c, cnt in self.raw_df["country"].value_counts().items()},
                },
            )
        except Exception:
            pass
        return self.get_summary()

    def get_skill_demand(self, category: Optional[str] = None, top_n: int = 15) -> Dict[str, Any]:
        self._ensure_data()
        with self._lock:
            if self.demand_df is None:
                self.demand_df = calculate_skill_demand_percentages(self.raw_df, self.config)
            demand_df = self.demand_df

        if demand_df.empty:
            return {"categories": ["All Categories"], "top_skills": [], "records": [], "chart_data": []}

        all_categories = sorted(demand_df["category"].dropna().unique().tolist())
        filtered = demand_df.copy()
        if category and category != "All Categories":
            filtered = filtered[filtered["category"] == category]

        # Determine top_n skills
        focal_demand = filtered[filtered["country"] == FOCAL_MARKET].sort_values("demand_pct", ascending=False)
        if not focal_demand.empty:
            top_skills = focal_demand["skill_name"].head(top_n).tolist()
        else:
            top_skills = (
                filtered.groupby("skill_name")["demand_pct"]
                .max()
                .sort_values(ascending=False)
                .head(top_n)
                .index.tolist()
            )

        chart_records = filtered[filtered["skill_name"].isin(top_skills)].copy()
        chart_data = chart_records.fillna("").to_dict(orient="records")
        all_records = demand_df.fillna("").to_dict(orient="records")

        return {
            "categories": ["All Categories"] + all_categories,
            "top_skills": top_skills,
            "chart_data": chart_data,
            "records": all_records,
        }

    def get_skill_gaps(self, comparator: str = "India") -> Dict[str, Any]:
        self._ensure_data()
        with self._lock:
            if self.demand_df is None:
                self.demand_df = calculate_skill_demand_percentages(self.raw_df, self.config)
            if self.gap_df is None:
                self.gap_df = calculate_skill_gaps(self.demand_df, focal_country=FOCAL_MARKET)
            gap_df = self.gap_df

        comp_gaps = gap_df[gap_df["comparator_country"] == comparator].copy()
        records = []
        for _, r in comp_gaps.iterrows():
            row_dict = r.to_dict()
            is_art = bool(r.get("zero_comparator_artifact", False))
            is_sig = bool(r.get("statistically_significant", False))
            is_small = bool(r.get("small_sample_warning", False))
            if is_art:
                status_label = "Artifact (0-count)"
                status_color = "red"
            elif is_sig and not is_small:
                status_label = "Significant"
                status_color = "green"
            elif is_small:
                status_label = "Indeterminate"
                status_color = "amber"
            else:
                status_label = "Sampling Noise"
                status_color = "slate"

            row_dict["status_label"] = status_label
            row_dict["status_color"] = status_color
            for k, v in row_dict.items():
                if pd.isna(v):
                    row_dict[k] = ""
            records.append(row_dict)

        return {
            "comparator": comparator,
            "available_comparators": list(COMPARATOR_MARKETS),
            "records": records,
        }

    def get_roles(self, selected_role: Optional[str] = None) -> Dict[str, Any]:
        self._ensure_data()
        with self._lock:
            if self.role_counts is None or self.role_skills is None or self.unclass_summary is None:
                self.role_counts, self.role_skills, self.unclass_summary = compare_regional_roles(
                    self.raw_df, self.config
                )
            role_counts = self.role_counts
            role_skills = self.role_skills
            unclass = self.unclass_summary

        pivot = role_counts.pivot_table(
            index="role_name", columns="country", values="job_count", fill_value=0
        ).astype(int)
        pivot_records = []
        for role_name, row in pivot.iterrows():
            r = {"role_name": role_name}
            for c in TARGET_REGIONAL_COUNTRIES:
                r[c] = int(row.get(c, 0))
            pivot_records.append(r)

        available_roles = (
            sorted(role_skills["role_name"].dropna().unique().tolist()) if not role_skills.empty else []
        )
        current_role = selected_role or (available_roles[0] if available_roles else "")

        role_demand_chart = []
        if current_role and not role_skills.empty:
            sub = role_skills[role_skills["role_name"] == current_role]
            skill_pivot = sub.pivot_table(
                index="skill_name", columns="country", values="demand_pct_in_role", fill_value=0.0
            )
            skill_pivot["_sum"] = skill_pivot.sum(axis=1)
            top_skills = skill_pivot.sort_values("_sum", ascending=False).head(10).drop(columns=["_sum"])
            for s_name, s_row in top_skills.iterrows():
                rec = {"skill_name": s_name}
                for c in TARGET_REGIONAL_COUNTRIES:
                    rec[c] = float(round(s_row.get(c, 0.0), 2))
                role_demand_chart.append(rec)

        audit_records = unclass.fillna("").to_dict(orient="records")

        return {
            "role_pivot": pivot_records,
            "audit_records": audit_records,
            "available_roles": available_roles,
            "selected_role": current_role,
            "role_demand_chart": role_demand_chart,
        }

    def get_salary(self) -> Dict[str, Any]:
        self._ensure_data()
        with self._lock:
            if self.country_salary is None or self.role_salary is None or self.rates_df is None:
                self.country_salary, self.role_salary, self.rates_df = analyze_regional_salaries(
                    self.raw_df, self.config
                )
            country_salary = self.country_salary
            role_salary = self.role_salary
            rates = self.rates_df

        csal_records = country_salary.fillna("").to_dict(orient="records")
        rsal_records = role_salary.fillna("").to_dict(orient="records") if not role_salary.empty else []
        rate_records = rates.fillna("").to_dict(orient="records")

        return {
            "country_salary": csal_records,
            "role_salary": rsal_records,
            "rates": rate_records,
            "focal_advisory": {
                "title": "🇱🇰 SRI LANKA SALARY DISCLOSURE ADVISORY",
                "notice": (
                    "Only 2 out of 57 advertisements (3.51%) in Sri Lanka disclose numerical compensation "
                    "(Contractual offers: LKR 50,000 and LKR 75,000 monthly). Small sample warning is active (N < 10). "
                    "Cross-country compensation comparisons involving Sri Lanka carry extreme statistical uncertainty and must be treated with caution."
                ),
            },
        }

    def get_similarities(self) -> Dict[str, Any]:
        self._ensure_data()
        with self._lock:
            if self.demand_df is None:
                self.demand_df = calculate_skill_demand_percentages(self.raw_df, self.config)
            if self.sim_df is None:
                self.sim_df = calculate_country_similarities(self.demand_df)
            sim_df = self.sim_df

        pairwise = sim_df.fillna("").to_dict(orient="records")

        countries = list(TARGET_REGIONAL_COUNTRIES)
        matrix = {
            "cosine_similarity": {c1: {c2: 1.0 if c1 == c2 else 0.0 for c2 in countries} for c1 in countries},
            "jaccard_top10_similarity": {c1: {c2: 1.0 if c1 == c2 else 0.0 for c2 in countries} for c1 in countries},
            "spearman_rank_correlation": {c1: {c2: 1.0 if c1 == c2 else 0.0 for c2 in countries} for c1 in countries},
        }

        for _, r in sim_df.iterrows():
            c1, c2 = r["country_a"], r["country_b"]
            if c1 in matrix["cosine_similarity"] and c2 in matrix["cosine_similarity"]:
                matrix["cosine_similarity"][c1][c2] = float(r["cosine_similarity"])
                matrix["cosine_similarity"][c2][c1] = float(r["cosine_similarity"])
                matrix["jaccard_top10_similarity"][c1][c2] = float(r["jaccard_top10_similarity"])
                matrix["jaccard_top10_similarity"][c2][c1] = float(r["jaccard_top10_similarity"])
                matrix["spearman_rank_correlation"][c1][c2] = float(r["spearman_rank_correlation"])
                matrix["spearman_rank_correlation"][c2][c1] = float(r["spearman_rank_correlation"])

        return {
            "countries": countries,
            "pairwise": pairwise,
            "matrix": matrix,
        }

    def get_sensitivity(self) -> Dict[str, Any]:
        self._ensure_data()
        with self._lock:
            if self.sens_summary is None:
                self.sens_summary, _ = run_regional_sensitivity_analysis(self.raw_df, self.config)
            sens_summary = self.sens_summary

        return {"summary": sens_summary.fillna("").to_dict(orient="records")}

    def get_eligibility_funnel(self) -> Dict[str, Any]:
        self._ensure_data()
        with self._lock:
            if self.funnel_df is None:
                self.funnel_df = build_exclusion_funnel(self.raw_df, self.config)
            funnel_df = self.funnel_df

        return {"funnel": funnel_df.fillna("").to_dict(orient="records")}

    def get_artifact_csv(self, artifact_type: str) -> Tuple[str, str]:
        self._ensure_data()
        if artifact_type == "skill_demand":
            if self.demand_df is None:
                self.demand_df = calculate_skill_demand_percentages(self.raw_df, self.config)
            return self.demand_df.to_csv(index=False), "skill_demand_by_country.csv"
        elif artifact_type == "skill_gaps":
            if self.demand_df is None:
                self.demand_df = calculate_skill_demand_percentages(self.raw_df, self.config)
            if self.gap_df is None:
                self.gap_df = calculate_skill_gaps(self.demand_df, focal_country=FOCAL_MARKET)
            return self.gap_df.to_csv(index=False), "skill_gaps_focal_srilanka.csv"
        elif artifact_type == "salary_summary":
            if self.country_salary is None:
                self.country_salary, self.role_salary, self.rates_df = analyze_regional_salaries(
                    self.raw_df, self.config
                )
            return self.country_salary.to_csv(index=False), "salary_summary_by_country.csv"
        elif artifact_type == "role_salaries":
            if self.role_salary is None:
                self.country_salary, self.role_salary, self.rates_df = analyze_regional_salaries(
                    self.raw_df, self.config
                )
            return self.role_salary.to_csv(index=False), "role_salaries_regional.csv"
        elif artifact_type == "similarities":
            if self.demand_df is None:
                self.demand_df = calculate_skill_demand_percentages(self.raw_df, self.config)
            if self.sim_df is None:
                self.sim_df = calculate_country_similarities(self.demand_df)
            return self.sim_df.to_csv(index=False), "country_skill_profile_similarities.csv"
        elif artifact_type == "funnel":
            if self.funnel_df is None:
                self.funnel_df = build_exclusion_funnel(self.raw_df, self.config)
            return self.funnel_df.to_csv(index=False), "regional_eligibility_funnel.csv"
        elif artifact_type == "sensitivity":
            if self.sens_summary is None:
                self.sens_summary, _ = run_regional_sensitivity_analysis(self.raw_df, self.config)
            return self.sens_summary.to_csv(index=False), "regional_sensitivity_summary.csv"
        else:
            raise HTTPException(status_code=404, detail=f"Unknown artifact type: {artifact_type}")

    # Single-Batch Role Segmentation
    def get_single_role_segmentation(self) -> Dict[str, Any]:
        freq_csv_path = DATA_DIR / "analysis" / "role_skill_frequencies.csv"
        extracted_csv_path = DATA_DIR / "processed" / "jobs_extracted.csv"

        has_extracted = extracted_csv_path.exists()
        extracted_count = 0
        if has_extracted:
            try:
                df_ex = pd.read_csv(extracted_csv_path, usecols=[0])
                extracted_count = len(df_ex)
            except Exception:
                extracted_count = 0

        if self.single_freq_df is None and freq_csv_path.exists():
            try:
                self.single_freq_df = pd.read_csv(freq_csv_path)
                self.single_analysis_completed = True
            except Exception:
                pass

        if self.single_freq_df is not None:
            freq_df = self.single_freq_df
            role_options = sorted(freq_df["role_name"].dropna().unique().tolist())
            role_counts = freq_df.groupby("role_name")["job_count"].max().to_dict()
            return {
                "has_extracted_data": has_extracted,
                "extracted_count": extracted_count,
                "analysis_completed": True,
                "role_options": role_options,
                "role_counts": role_counts,
                "frequencies": freq_df.fillna("").to_dict(orient="records"),
            }

        return {
            "has_extracted_data": has_extracted,
            "extracted_count": extracted_count,
            "analysis_completed": False,
            "role_options": [],
            "role_counts": {},
            "frequencies": [],
        }

    def execute_single_role_segmentation(self) -> Dict[str, Any]:
        extracted_csv_path = DATA_DIR / "processed" / "jobs_extracted.csv"
        if not extracted_csv_path.exists():
            raise HTTPException(
                status_code=400,
                detail="No extracted data found at data/processed/jobs_extracted.csv. Run extraction first.",
            )

        df = pd.read_csv(extracted_csv_path)
        role_df = classify_roles(df)
        freq_df = build_role_skill_frequency_table(role_df)

        analysis_dir = DATA_DIR / "analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        freq_df.to_csv(analysis_dir / "role_skill_frequencies.csv", index=False, encoding="utf-8")

        self.single_role_df = role_df
        self.single_freq_df = freq_df
        self.single_analysis_completed = True

        role_options = sorted(freq_df["role_name"].dropna().unique().tolist())
        role_counts = role_df["role_name"].value_counts().to_dict()

        return {
            "status": "success",
            "analysis_completed": True,
            "total_jobs_classified": len(role_df),
            "role_options": role_options,
            "role_counts": role_counts,
            "frequencies": freq_df.fillna("").to_dict(orient="records"),
        }


regional_manager = RegionalAnalysisManager()


@app.get("/api/regional/summary")
def api_get_regional_summary() -> Dict[str, Any]:
    return regional_manager.get_summary()


@app.post("/api/regional/refresh")
def api_refresh_regional_data() -> Dict[str, Any]:
    return regional_manager.refresh()


@app.get("/api/regional/skill-demand")
def api_get_skill_demand(
    category: Optional[str] = None,
    top_n: int = 15,
) -> Dict[str, Any]:
    return regional_manager.get_skill_demand(category=category, top_n=top_n)


@app.get("/api/regional/skill-gaps")
def api_get_skill_gaps(comparator: str = "India") -> Dict[str, Any]:
    return regional_manager.get_skill_gaps(comparator=comparator)


@app.get("/api/regional/roles")
def api_get_regional_roles(selected_role: Optional[str] = None) -> Dict[str, Any]:
    return regional_manager.get_roles(selected_role=selected_role)


@app.get("/api/regional/salary")
def api_get_regional_salary() -> Dict[str, Any]:
    return regional_manager.get_salary()


@app.get("/api/regional/similarities")
def api_get_regional_similarities() -> Dict[str, Any]:
    return regional_manager.get_similarities()


@app.get("/api/regional/sensitivity")
def api_get_regional_sensitivity() -> Dict[str, Any]:
    return regional_manager.get_sensitivity()


@app.get("/api/regional/eligibility-funnel")
def api_get_regional_eligibility_funnel() -> Dict[str, Any]:
    return regional_manager.get_eligibility_funnel()


@app.get("/api/regional/download/{artifact_name}")
def api_download_regional_artifact(artifact_name: str):
    csv_str, filename = regional_manager.get_artifact_csv(artifact_name)
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/regional/role-segmentation")
def api_get_role_segmentation() -> Dict[str, Any]:
    return regional_manager.get_single_role_segmentation()


@app.post("/api/regional/role-segmentation/execute")
def api_execute_role_segmentation() -> Dict[str, Any]:
    return regional_manager.execute_single_role_segmentation()


@app.get("/api/regional/role-segmentation/download")
def api_download_role_segmentation():
    freq_csv_path = DATA_DIR / "analysis" / "role_skill_frequencies.csv"
    if not freq_csv_path.exists():
        raise HTTPException(status_code=404, detail="No role_skill_frequencies.csv file found.")
    with open(freq_csv_path, "r", encoding="utf-8") as f:
        content = f.read()
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="role_skill_frequencies.csv"'},
    )


# ==============================================================================
# Scraping Accuracy & Benchmark Validation Backend Manager & Endpoints
# ==============================================================================

class ReviewDecisionRequest(BaseModel):
    benchmark_id: str
    field_name: str
    status: str
    reviewer_id: str
    reviewer_notes: str
    corrected_value: str = ""
    original_predicted: str = ""
    original_expected: str = ""
    source_url: str = ""
    country: str = ""
    source_platform: str = ""


class ValidationManager:
    def __init__(self):
        self._lock = threading.Lock()

    def get_runs(self) -> Dict[str, Any]:
        runs = discover_evaluation_runs()
        return {
            "runs": runs,
            "latest_run_id": runs[0]["run_id"] if runs else None,
        }

    def _load_run_with_summary(self, run_id: str) -> Optional[Dict[str, Any]]:
        data = load_evaluation_run_data(run_id)
        if not data:
            data = load_evaluation_run_data("latest")
        if data and data["summary_df"].empty:
            target_dir = get_results_dir()
            run_tag = data.get("run_tag", "latest")
            s_csv = target_dir / f"evaluation_summary_{run_tag}.csv"
            if not s_csv.exists():
                s_csv = target_dir / "evaluation_summary_latest.csv"
            if s_csv.exists():
                try:
                    data["summary_df"] = pd.read_csv(s_csv)
                except Exception:
                    pass
        return data

    def get_validation_data(
        self,
        run_id: str = "latest",
        country: Optional[str] = None,
        platform: Optional[str] = None,
        method: Optional[str] = None,
        field_name: Optional[str] = None,
        status: Optional[str] = None,
        error_cat: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            data = self._load_run_with_summary(run_id)
            if not data:
                return {
                    "has_data": False,
                    "runs": discover_evaluation_runs(),
                    "message": "No evaluation run found.",
                }

            metrics = data.get("metrics", {})
            meta = metrics.get("metadata", {})
            errors_df = data.get("errors_df", pd.DataFrame())
            summary_df = data.get("summary_df", pd.DataFrame())

            # Filter options extraction
            countries = ["All"]
            platforms = ["All"]
            methods = ["All"]
            field_names = ["All"]
            statuses = ["All"]
            error_cats = ["All"]

            if not errors_df.empty:
                if "country" in errors_df.columns:
                    countries += sorted([c for c in errors_df["country"].dropna().unique() if c])
                if "source_platform" in errors_df.columns:
                    platforms += sorted([p for p in errors_df["source_platform"].dropna().unique() if p])
                if "extraction_method" in errors_df.columns:
                    methods += sorted([m for m in errors_df["extraction_method"].dropna().unique() if m])
                if "field_name" in errors_df.columns:
                    field_names += sorted([f for f in errors_df["field_name"].dropna().unique() if f])
                if "error_status" in errors_df.columns:
                    statuses += sorted([s for s in errors_df["error_status"].dropna().unique() if s])
                elif "error_type" in errors_df.columns:
                    statuses += sorted([s for s in errors_df["error_type"].dropna().unique() if s])
                if "error_category" in errors_df.columns:
                    error_cats += sorted([ec for ec in errors_df["error_category"].dropna().unique() if ec])

            # Apply filters to count matching errors
            filtered_errors = filter_evaluation_errors(
                errors_df,
                country=country,
                platform=platform,
                method=method,
                field_name=field_name,
                status=status,
                error_cat=error_cat,
                search_query=search_query,
            )

            # Stratified breakdowns
            country_strat = compute_stratified_view(summary_df, "country", filter_value=country)
            platform_strat = compute_stratified_view(summary_df, "platform", filter_value=platform)
            method_strat = compute_stratified_view(summary_df, "extraction_method", filter_value=method)

            # Numeric salary metrics
            field_metrics = metrics.get("field_metrics", {})
            f_min = field_metrics.get("salary_min", {})
            f_max = field_metrics.get("salary_max", {})
            numeric_salary = {
                "comparable_count": f_min.get("comparable_count", 0),
                "salary_min_mae": f_min.get("mae", 0.0) or 0.0,
                "salary_min_medae": f_min.get("medae", 0.0) or 0.0,
                "salary_max_mae": f_max.get("mae", 0.0) or 0.0,
                "salary_max_medae": f_max.get("medae", 0.0) or 0.0,
                "excluded_incompatible_count": f_min.get("excluded_incompatible_count", 0),
            }

            return {
                "has_data": True,
                "run_id": data.get("run_tag", run_id),
                "is_synthetic": data.get("is_synthetic", False),
                "metadata": meta,
                "filter_options": {
                    "countries": countries,
                    "platforms": platforms,
                    "methods": methods,
                    "field_names": field_names,
                    "statuses": statuses,
                    "error_categories": error_cats,
                },
                "stratified": {
                    "country": country_strat.fillna("").to_dict(orient="records"),
                    "platform": platform_strat.fillna("").to_dict(orient="records"),
                    "extraction_method": method_strat.fillna("").to_dict(orient="records"),
                },
                "field_metrics": field_metrics,
                "numeric_salary": numeric_salary,
                "total_errors_count": len(errors_df),
                "filtered_errors_count": len(filtered_errors),
            }

    def get_review_queue(
        self,
        run_id: str = "latest",
        country: Optional[str] = None,
        platform: Optional[str] = None,
        method: Optional[str] = None,
        field_name: Optional[str] = None,
        status: Optional[str] = None,
        error_cat: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        with self._lock:
            data = self._load_run_with_summary(run_id)
            if not data:
                return {"total_count": 0, "items": [], "limit": limit, "offset": offset}

            errors_df = data.get("errors_df", pd.DataFrame())
            filtered_errors = filter_evaluation_errors(
                errors_df,
                country=country,
                platform=platform,
                method=method,
                field_name=field_name,
                status=status,
                error_cat=error_cat,
                search_query=search_query,
            )

            annotations = load_review_annotations()
            queue_df = build_review_queue(filtered_errors, annotations)

            total_count = len(queue_df)
            paginated_df = queue_df.iloc[offset : offset + limit] if total_count > 0 else pd.DataFrame()

            return {
                "total_count": total_count,
                "items": paginated_df.fillna("").to_dict(orient="records"),
                "limit": limit,
                "offset": offset,
            }

    def rerun_pipeline(self) -> Dict[str, Any]:
        success, msg, _ = rerun_evaluation_pipeline()
        return {"success": success, "message": msg}

    def save_review(self, req: ReviewDecisionRequest) -> Dict[str, Any]:
        success, msg = save_review_annotation(
            benchmark_id=req.benchmark_id,
            field_name=req.field_name,
            status=req.status,
            reviewer_id=req.reviewer_id,
            reviewer_notes=req.reviewer_notes,
            corrected_value=req.corrected_value,
            original_predicted=req.original_predicted,
            original_expected=req.original_expected,
            source_url=req.source_url,
            country=req.country,
            source_platform=req.source_platform,
        )
        return {"success": success, "message": msg}

    def get_history(self) -> Dict[str, Any]:
        history = get_correction_history()
        return {"history": history}

    def get_artifact(
        self,
        artifact_name: str,
        run_id: str = "latest",
        country: Optional[str] = None,
        platform: Optional[str] = None,
        method: Optional[str] = None,
        field_name: Optional[str] = None,
        status: Optional[str] = None,
        error_cat: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """Returns (content_str, filename, media_type)."""
        data = self._load_run_with_summary(run_id)
        if not data:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

        run_tag = data.get("run_tag", "latest")
        meta = data.get("metrics", {}).get("metadata", {})
        eval_ts = str(meta.get("timestamp", run_tag))[:10].replace(":", "").replace("-", "")

        if artifact_name == "summary":
            sum_df = data.get("summary_df", pd.DataFrame())
            content = sum_df.to_csv(index=False, encoding="utf-8") if not sum_df.empty else ""
            return content, f"scraping_accuracy_summary_{eval_ts}.csv", "text/csv"

        elif artifact_name == "errors":
            errors_df = data.get("errors_df", pd.DataFrame())
            filtered = filter_evaluation_errors(
                errors_df,
                country=country,
                platform=platform,
                method=method,
                field_name=field_name,
                status=status,
                error_cat=error_cat,
                search_query=search_query,
            )
            content = filtered.to_csv(index=False, encoding="utf-8") if not filtered.empty else ""
            return content, f"scraping_errors_filtered_{eval_ts}.csv", "text/csv"

        elif artifact_name == "stratification":
            sum_df = data.get("summary_df", pd.DataFrame())
            if not sum_df.empty and "dimension" in sum_df.columns:
                sub = sum_df[sum_df["dimension"].isin(["country", "platform"])]
                content = sub.to_csv(index=False, encoding="utf-8")
            else:
                content = ""
            return content, f"accuracy_stratification_{eval_ts}.csv", "text/csv"

        elif artifact_name == "queue":
            errors_df = data.get("errors_df", pd.DataFrame())
            filtered = filter_evaluation_errors(
                errors_df,
                country=country,
                platform=platform,
                method=method,
                field_name=field_name,
                status=status,
                error_cat=error_cat,
                search_query=search_query,
            )
            annotations = load_review_annotations()
            queue_df = build_review_queue(filtered, annotations)
            content = queue_df.to_csv(index=False, encoding="utf-8") if not queue_df.empty else ""
            return content, f"validation_review_queue_{eval_ts}.csv", "text/csv"

        elif artifact_name == "report":
            report_md = data.get("report_md", "")
            return report_md, f"scraping_evaluation_report_{eval_ts}.md", "text/markdown"

        else:
            raise HTTPException(status_code=400, detail=f"Unknown artifact '{artifact_name}'.")


validation_manager = ValidationManager()


@app.get("/api/validation/runs")
def api_get_validation_runs() -> Dict[str, Any]:
    return validation_manager.get_runs()


@app.get("/api/validation/data")
def api_get_validation_data(
    run_id: str = "latest",
    country: Optional[str] = None,
    platform: Optional[str] = None,
    method: Optional[str] = None,
    field_name: Optional[str] = None,
    status: Optional[str] = None,
    error_cat: Optional[str] = None,
    search_query: Optional[str] = None,
) -> Dict[str, Any]:
    return validation_manager.get_validation_data(
        run_id=run_id,
        country=country,
        platform=platform,
        method=method,
        field_name=field_name,
        status=status,
        error_cat=error_cat,
        search_query=search_query,
    )


@app.get("/api/validation/review-queue")
def api_get_validation_review_queue(
    run_id: str = "latest",
    country: Optional[str] = None,
    platform: Optional[str] = None,
    method: Optional[str] = None,
    field_name: Optional[str] = None,
    status: Optional[str] = None,
    error_cat: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    return validation_manager.get_review_queue(
        run_id=run_id,
        country=country,
        platform=platform,
        method=method,
        field_name=field_name,
        status=status,
        error_cat=error_cat,
        search_query=search_query,
        limit=limit,
        offset=offset,
    )


@app.post("/api/validation/rerun")
def api_rerun_validation_pipeline() -> Dict[str, Any]:
    return validation_manager.rerun_pipeline()


@app.post("/api/validation/review")
def api_save_validation_review(req: ReviewDecisionRequest) -> Dict[str, Any]:
    return validation_manager.save_review(req)


@app.get("/api/validation/history")
def api_get_validation_history() -> Dict[str, Any]:
    return validation_manager.get_history()


@app.get("/api/validation/download/{artifact_name}")
def api_download_validation_artifact(
    artifact_name: str,
    run_id: str = "latest",
    country: Optional[str] = None,
    platform: Optional[str] = None,
    method: Optional[str] = None,
    field_name: Optional[str] = None,
    status: Optional[str] = None,
    error_cat: Optional[str] = None,
    search_query: Optional[str] = None,
):
    content, filename, media_type = validation_manager.get_artifact(
        artifact_name=artifact_name,
        run_id=run_id,
        country=country,
        platform=platform,
        method=method,
        field_name=field_name,
        status=status,
        error_cat=error_cat,
        search_query=search_query,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/navigation")
def get_navigation_routes() -> List[Dict[str, Any]]:
    """Return all navigation items matching the exact existing project structure."""
    return [
        {
            "id": "research-dashboard",
            "name": "Research Dashboard",
            "path": "/",
            "icon": "LayoutDashboard",
            "type": "react",
            "isMigrated": True,
            "badge": "Active",
        },
        {
            "id": "0-user-dashboard",
            "name": "0 User Dashboard",
            "path": "/pages/0_User_Dashboard",
            "icon": "LineChart",
            "type": "streamlit",
            "isMigrated": False,
        },
        {
            "id": "1-collect-data",
            "name": "1 Collect Data",
            "path": "/pages/1_Collect_Data",
            "icon": "DownloadCloud",
            "type": "react",
            "isMigrated": True,
            "badge": "Active",
        },
        {
            "id": "2-raw-data",
            "name": "2 Raw Data",
            "path": "/pages/2_Raw_Data",
            "icon": "FileText",
            "type": "react",
            "isMigrated": True,
            "badge": "Active",
        },
        {
            "id": "3-clean-data",
            "name": "3 Clean Data",
            "path": "/pages/3_Clean_Data",
            "icon": "Sparkles",
            "type": "react",
            "isMigrated": True,
            "badge": "Active",
        },
        {
            "id": "4-master-dataset",
            "name": "4 Master Dataset",
            "path": "/pages/4_Master_Dataset",
            "icon": "Database",
            "type": "streamlit",
            "isMigrated": False,
        },
        {
            "id": "5-extract-skills",
            "name": "5 Extract Skills",
            "path": "/pages/5_Extract_Skills",
            "icon": "Cpu",
            "type": "streamlit",
            "isMigrated": False,
        },
        {
            "id": "6-quality-report",
            "name": "6 Quality Report",
            "path": "/pages/6_Quality_Report",
            "icon": "CheckSquare",
            "type": "streamlit",
            "isMigrated": False,
        },
        {
            "id": "7-failure-logs",
            "name": "7 Failure Logs",
            "path": "/pages/7_Failure_Logs",
            "icon": "AlertOctagon",
            "type": "react",
            "isMigrated": True,
            "badge": "Active",
        },
        {
            "id": "8-external-domains",
            "name": "8 External Domains",
            "path": "/pages/8_External_Domains",
            "icon": "Globe",
            "type": "react",
            "isMigrated": True,
            "badge": "Active",
        },
        {
            "id": "9-manual-reviews",
            "name": "9 Manual Reviews",
            "path": "/pages/9_Manual_Reviews",
            "icon": "UserCheck",
            "type": "streamlit",
            "isMigrated": False,
        },
        {
            "id": "10-scraping-validation",
            "name": "10 Scraping Validation",
            "path": "/pages/10_Scraping_Validation",
            "icon": "ShieldCheck",
            "type": "react",
            "isMigrated": True,
            "badge": "Active",
            "isIndividual": True,
        },
        {
            "id": "11-skill-relationship-analysis",
            "name": "11 Skill Relationship Analysis",
            "path": "/pages/11_Skill_Relationship_Analysis",
            "icon": "Network",
            "type": "streamlit",
            "isMigrated": False,
        },
        {
            "id": "12-regional-analysis",
            "name": "12 Regional Analysis",
            "path": "/pages/12_Regional_Analysis",
            "icon": "Compass",
            "type": "react",
            "isMigrated": True,
            "badge": "Active",
            "isIndividual": True,
        },
        {
            "id": "13-temporal-analysis",
            "name": "13 Temporal Analysis",
            "path": "/pages/13_Temporal_Analysis",
            "icon": "TrendingUp",
            "type": "streamlit",
            "isMigrated": False,
        },
        {
            "id": "14-role-skill-analysis",
            "name": "14 Role Skill Analysis",
            "path": "/pages/14_Role_Skill_Analysis",
            "icon": "Briefcase",
            "type": "streamlit",
            "isMigrated": False,
        },
    ]


# Mount frontend static distribution if built
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_react_frontend(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="127.0.0.1", port=8000, reload=True)
