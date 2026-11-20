# Run J26-SE-355 Locally

This repository has two independent applications: the public SkillScope dashboard and the local Streamlit research/admin tools. This guide covers setup, publication, and deployment. For project scope and implementation, see [About](docs/About.md), [Temporal Analysis Component](docs/Temporal_Analysis_Component.md), and [implementation suggestions](docs/suggestions.md). Older documents are in `docs/archive/`.

For development, use the project [workflow and Done when agreement](docs/development-workflow.md): `Commit: <outcome>` runs the tests-first implementation workflow through a local commit; `Change: <adjustment>` makes a scoped edit while preserving unspecified functionality. Ask `What's the next step?` for one recommendation with acceptance conditions and outstanding security/testing issues. The repository skills are [commit](.agents/skills/commit/SKILL.md) and [change](.agents/skills/change/SKILL.md).

## Clone the repository

```bash
git clone https://github.com/zero3nine/J26_SE_355.git
cd J26_SE_355
```

## Public dashboard: quick start

From the repository root, run:

```bash
python -m tools.publish_dashboard --synthetic
python -m public_dashboard.app
```

Open [SkillScope at localhost:8080](http://localhost:8080). This path needs only Python's standard library, not the research requirements or an ML model download. It creates a separate demo database at `data/public/dashboard.sqlite3` with 4,896 synthetic advertisements, November 2023–October 2026, four markets, five career areas, and paired extraction methods. The master database is untouched. Stop the server with `Ctrl+C`.

The dashboard includes career/skill exploration, chronological demand, market comparisons, skill connections, extraction comparisons, scoped CSV downloads, and shareable filter URLs. All demo views and exports identify synthetic data. The optional `DASHBOARD_DB` environment variable or local `--database` argument selects another publication.

SkillScope uses a blue palette with light and dark appearances. Use **Dark mode** in the top bar to toggle it. The initial appearance follows your device setting; choosing a mode saves that preference in this browser. If browser storage is blocked, the toggle still works for the current page. Appearance does not change analysis filters, exports, or shared links. The local research/admin portal uses a matching light palette, blue sidebar, rounded cards, and consistent status colors across its modules; its Streamlit theme configuration remains independent of SkillScope.

### Publish reviewed research data

Keep the admin app local. Its **Public Dashboard** page can prepare synthetic data or publish a reviewed cohort from one extraction run. Set `PUBLIC_DASHBOARD_URL` in the admin environment if the public dashboard is hosted elsewhere.

The legacy master schema cannot distinguish successful zero-skill extraction from an unprocessed job. Prepare a reviewed cohort CSV explicitly confirming both methods completed in the selected run:

```csv
job_id,lexical_completed,semantic_completed
actual_master_job_id,true,true
another_successfully_processed_job,true,true
```

Include genuine zero-skill results; exclude failures, unprocessed records, non-IT records, and invalid dates. Resolve unmapped canonical skill mentions before publication; the exporter rejects them. Then publish locally:

```bash
python -m tools.publish_dashboard --master data/master_jobs.sqlite3 --run-id YOUR_RUN_ID --cohort reviewed_cohort.csv --title "Reviewed IT sample" --provenance "Sources, observation period, review protocol, and limitations"
```

Use only genuine identifiers from your run. The publisher reads the master in read-only mode, strips private text/URLs, canonicalizes saved skill labels, retains zero-skill jobs, records configuration, precomputes exploratory baseline forecasts where supported, and atomically replaces the separate snapshot. Refresh the public app to read the new publication. Never label an unreviewed or mixed synthetic cohort as empirical research.

### Deploy only the dashboard and publication

Generate a publication first. On a machine running Docker:

```bash
docker compose -f compose.dashboard.yaml up --build -d
```

This builds `Dockerfile.dashboard` and mounts **only** `data/public/` read-only. The image contains the independent dashboard package and its production server; it does not copy Streamlit pages, the master database, source adapters, publisher tools, or ML packages. The service runs as a non-root user on port 8080 with a health check at `/healthz`.

The Compose port binds to host loopback. For public hosting, place it behind your hosting platform's HTTPS ingress or a reverse proxy to `127.0.0.1:8080`. Preserve the read-only publication-directory mount. Transfer only the sanitized snapshot to the host and replace it atomically; do not deploy the master database. On Linux, the snapshot must be readable by container UID 10001 (the publisher creates it with mode 0644). Mount the directory rather than a single file so atomic replacement is visible to readers.

For a Linux host without Docker, install `requirements-dashboard.txt` and run `gunicorn public_dashboard.app:application --bind 127.0.0.1:8080 --workers 2 --threads 4`, with `DASHBOARD_DB` pointing to the published snapshot and HTTPS handled by the host. The standard-library preview server is for local development. See [Gunicorn deployment guidance](https://gunicorn.org/guides/docker/) for production hosting considerations.

### Public-app verification

```bash
python -m unittest discover -s tests -p "test_public_dashboard.py"
```

For desktop/mobile browser checks, install the research requirements and Chromium, then run:

```bash
python -m playwright install chromium
python tests/browser_public_dashboard.py
python tests/browser_admin_theme.py
```

The public browser suite creates its own temporary publication/server. The admin browser suite uses a temporary project copy and synthetic records to check every module at desktop/phone widths, sampled contrast, keyboard focus, search, CSV download, and collection-mode switching. Neither suite uses the working master database. Both save screenshots under ignored `tmp/dashboard-qa/`. The public application has no Internet-hosted scripts, fonts, chart libraries, or image dependencies.

## Local research/admin application

### Run the admin portal with Docker

With Docker Compose v2, run the following from the repository root on Linux. Use real directories for `data/` and `data/admin/` so the mount stays inside this checkout.

```bash
mkdir -p -m 750 data/admin
sudo env ADMIN_UID="$(id -u)" ADMIN_GID="$(id -g)" \
  docker compose -f compose.admin.yaml up --build -d
```

If you use Docker without `sudo`, omit `sudo` and keep `env`. The UID and GID let the non-root container user write to the project directory as your regular user. You can also set these values and optional settings in a project-local Compose `.env` file.

Open the [research/admin portal](http://127.0.0.1:8501). The container installs the research dependencies and Streamlit inside the image. Use `sudo docker compose -f compose.admin.yaml down` to stop it. The public dashboard can run independently at [127.0.0.1:8080](http://127.0.0.1:8080).

- **Data and permissions.** The admin's only host bind mount is this checkout's `data/admin/`, which Git ignores. SQLite, saved batches, reports, app logs, model downloads, submitted URLs, and approved-domain edits persist there. The image filesystem is read-only and `/tmp` is in memory. Docker manages image layers and container metadata in its own storage.
- **Existing data and publishing.** An empty `data/admin/` starts with an empty master database. To use existing research data, stop the writer and put a consistent copy under `data/admin/`. The admin's **Public Dashboard** page writes snapshots under `data/admin/public/`. Transfer only the reviewed or synthetic snapshot into the public service's `data/public/` directory using an atomic replacement.
- **OCR and browser fallback.** Tesseract is included for image OCR. Chromium is optional. Set `ADMIN_INSTALL_CHROMIUM=true` and rebuild to use Playwright with trusted test pages. The existing browser fallback launches Chromium with its sandbox disabled, so leave it off for live collection in the admin container. [Playwright Docker guidance](https://playwright.dev/python/docs/docker)

#### Docker smoke test

Run this in a checkout with a fresh `data/admin/` before adding real data, while the public dashboard serves a snapshot on port 8080. Apply the same Docker permission setup as above.

```bash
mkdir -p -m 750 data/admin
export ADMIN_UID="$(id -u)"
export ADMIN_GID="$(id -g)"
docker compose -f compose.admin.yaml run --build --rm -T admin python - <<'PY'
import os

import pandas as pd

from src.database.connection import DB_PATH
from src.database.repository import import_jobs_dataframe

assert os.getuid() > 0
assert not DB_PATH.exists(), "Use a fresh data/admin directory for the smoke test."
result = import_jobs_dataframe(pd.DataFrame([{
    "job_id": "synthetic-docker-1",
    "source_url": "https://example.com/synthetic-docker-1",
    "job_title_raw": "Synthetic Python Engineer",
    "job_description": "Synthetic Python engineering position for Docker verification.",
    "country": "Sri Lanka",
    "posting_date": "2026-01-15",
    "classification_status": "it",
    "source_platform": "Synthetic",
}]), source_name="Synthetic Docker smoke test")
assert result["inserted_jobs"] == 1, result
PY
docker compose -f compose.admin.yaml up --wait
```

Open [the admin portal](http://127.0.0.1:8501) and check **Master Dataset** for the synthetic job. Recreate the admin container, verify the row, and check both health endpoints:

```bash
docker compose -f compose.admin.yaml up --force-recreate --wait
docker compose -f compose.admin.yaml exec -T admin python - <<'PY'
from src.database.connection import database_connection

with database_connection() as connection:
    row = connection.execute(
        "SELECT job_title FROM jobs WHERE source_url = ?",
        ("https://example.com/synthetic-docker-1",),
    ).fetchone()
    assert row and row["job_title"] == "Synthetic Python Engineer", row
PY
curl -fsS http://127.0.0.1:8501/_stcore/health
curl -fsS http://127.0.0.1:8080/healthz
docker compose -f compose.admin.yaml down
```

### Run the admin portal with local Python

## 1. Prerequisites

Install Git and Python. The existing checkout was verified with **Python 3.14.7**; the repository does not yet declare a supported Python range or provide a dependency lock file. Use a virtual environment and allow enough disk space for the scientific/ML dependencies and model cache.

Internet access is needed to install packages, collect live advertisements, and download the Sentence Transformer model on first semantic extraction. No paid API key or separate database server is required. The application uses the local `data/master_jobs.sqlite3` file.

## 2. Install research dependencies


On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

On macOS/Linux, create the environment with your chosen Python interpreter and activate it with:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

If PowerShell blocks activation, use `.venv\Scripts\python.exe` in place of `python` in subsequent commands; activation is optional. Keep dependency installation and application launch on the same interpreter.

### Optional collection dependencies

- **JavaScript-rendered pages:** run `python -m playwright install chromium` before enabling **Playwright Browser Fallback**.
- **Advertisement images:** install the Tesseract OCR executable separately and put it on `PATH`. Confirm `tesseract --version` works before enabling **Run Advertisement Image OCR**. Installing `pytesseract` alone does not install that executable. Restart the app after changing `PATH`.
- If these tools are unavailable, leave browser fallback off and turn OCR off in **Collect Data**. OCR currently defaults to on. Text-based pages and historical CSV/XLSX imports can be used without OCR; image-only advertisements may then lack usable descriptions.

The collection HTTP client verifies TLS certificates on every request, including redirects and temporary-error retries. A certificate or TLS handshake failure returns `tls_error`, records the failing URL, and stops that URL before browser fallback, extraction, or OCR. No unverified retry is attempted. Correct the source certificate (including its hostname, validity, and chain) or the local trusted CA configuration before collecting that source again; do not disable verification. Other sources can continue within the existing crawl budgets.

Use CSV or XLSX for historical imports. The UI also offers XLS, but its additional Excel reader engine is not declared in `requirements.txt`.

## 3. Launch the application

From the repository root:

```bash
python -m streamlit run app.py --server.address 127.0.0.1
```

Open [localhost:8501](http://localhost:8501). Stop the server with `Ctrl+C`. If that port is occupied, append `--server.port 8502` and open the corresponding address.

This launches the local multipage research/admin app. The Public Dashboard page contains publication controls and links to the independent dashboard; it does not embed or serve the public web app.

Database-backed pages initialize missing tables automatically. To initialize them explicitly:

```bash
python -c "from src.database.connection import initialize_database; initialize_database()"
```

Initialization does not populate job/skill records or reset the existing database. The repository includes a database snapshot; do not assume its contents are a vetted research release. Back up the database before intentional imports, with the app stopped; preserve any remaining SQLite WAL/SHM sidecars with it.

## 4. Populate the analysis views

If the supplied database already contains jobs and saved skill mentions, open the analysis pages to inspect them. To add your own data:

1. In **Collect Data**, choose **Live Scraping** and submit a small set of permitted public job/listing URLs, or choose **Historical Data Import**, upload a CSV/XLSX file, and review the column mapping. Retain original posting dates and source URLs. Live collection depends on the source's access policy and page structure.
2. Inspect **Raw Data**, then run **Clean and Standardize Data** in **Clean Data**. Check quality reports and ambiguous/manual-review records before publication.
3. In **Master Dataset**, select the current cleaned data or upload a cleaned CSV and click **Publish jobs to master database**. Rows need a source URL (`source_url`, `job_url`, or `url`). An existing URL is matched rather than inserted as a separate advertisement. Check the reported failed/inserted/updated counts.
4. In **Extract Skills**, select **Master database** and the intended job scope. Choose or calibrate the semantic threshold, then click **Run Lexical + Semantic Extraction**. The first run may download `sentence-transformers/all-MiniLM-L6-v2`.
5. Click **Save lexical and semantic results**. Running extraction or downloading its CSV alone does not complete this persistence step. Uploaded-CSV extraction results cannot be saved through this page; publish the jobs first, then extract from the master database.
6. Open **Role Skill Analysis**, **Skill Relationship Analysis**, **Regional Analysis**, **Temporal Analysis**, or open the independent **SkillScope** dashboard after publishing its snapshot. Relationship analysis has its own **Run Skill Analysis** action. Temporal analysis requires usable posting dates and enough observations; a short collection will not enable every forecast.

Session state is temporary. Cleaned/extracted CSVs are written under `data/processed/`, but database-driven views need the explicit job and skill save steps. Use synthetic fixtures only in a disposable research copy, and keep them separate from empirical data.

## 5. Verify the environment

```bash
python -m unittest discover -s tests -p "test_*.py"
python -m unittest src/test_app.py
```

For a focused temporal check:

```bash
python -m unittest discover -s tests -p "test_temporal_analysis.py"
```

Install `requirements-dev.txt` after the research requirements for the pytest-based tests. On Windows, use `python -X utf8 -m unittest discover -s tests -p "test_*.py"` when redirecting output, because older research CLI messages contain Unicode. Some tests use DNS or optional ML/browser dependencies. A failure needs its actual traceback reviewed; it should not be dismissed as an installation issue automatically. Tests under source subdirectories are not all included by discovery limited to `tests/`.

The new public app has dedicated boundary/analytics tests and desktop/mobile browser checks. Current verification results and remaining legacy research-test issues are recorded in [suggestions.md](docs/suggestions.md). A clean Docker image build remains unverified because Docker Desktop was not running during implementation.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `ModuleNotFoundError` or `streamlit` not found | Install requirements and launch with the same virtual-environment Python. |
| Chromium executable missing | Run `python -m playwright install chromium`, or disable browser fallback. |
| Tesseract not found | Add the executable to `PATH`, restart, and verify `tesseract --version`; otherwise disable OCR. |
| Model download fails | Check network access/model-cache availability; semantic extraction needs the model locally. |
| Jobs appear but temporal/skill views are empty | Check posting dates, extraction scope, saved skill mentions, and minimum-period/sample controls. |
| Historical rows fail publication | Supply genuine source URLs and inspect import counts; do not invent source evidence. |
| Database cannot be opened or is locked | Ensure `data/` is writable and stop competing app/import processes before retrying. |

Current analytical limitations and result-affecting defects are recorded in [suggestions.md](docs/suggestions.md). Review them before interpreting outputs as research findings.
