# Run J26-SE-355 Locally

This guide takes you from cloning the repository to running the research application and populating its analysis views. For project scope and implementation, see [About](docs/About.md), [Temporal Analysis Component](docs/Temporal_Analysis_Component.md), and [implementation suggestions](docs/suggestions.md). Older documents are in `docs/archive/`.

## 1. Prerequisites

Install Git and Python. The existing checkout was verified with **Python 3.14.7**; the repository does not yet declare a supported Python range or provide a dependency lock file. Use a virtual environment and allow enough disk space for the scientific/ML dependencies and model cache.

Internet access is needed to install packages, collect live advertisements, and download the Sentence Transformer model on first semantic extraction. No paid API key or separate database server is required. The application uses the local `data/master_jobs.sqlite3` file.

## 2. Clone and install

```bash
git clone https://github.com/zero3nine/J26_SE_355.git
cd J26_SE_355
```

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

Use CSV or XLSX for historical imports. The UI also offers XLS, but its additional Excel reader engine is not declared in `requirements.txt`.

## 3. Launch the application

From the repository root:

```bash
python -m streamlit run app.py --server.address 127.0.0.1
```

Open [localhost:8501](http://localhost:8501). Stop the server with `Ctrl+C`. If that port is occupied, append `--server.port 8502` and open the corresponding address.

This launches the current multipage research app, including its administrative tools and existing User Dashboard page. An independently deployed public dashboard has not yet been implemented.

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
6. Open **Role Skill Analysis**, **Skill Relationship Analysis**, **Regional Analysis**, **Temporal Analysis**, or **User Dashboard**. Relationship analysis has its own **Run Skill Analysis** action. Temporal analysis requires usable posting dates and enough observations; a short collection will not enable every forecast.

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

Some tests use DNS or optional ML/browser dependencies. A failure needs its actual traceback reviewed; it should not be dismissed as an installation issue automatically. Tests under source subdirectories are not all included by discovery limited to `tests/`.

The documentation pass verified the existing environment with `pip check`, the five temporal tests, a temporary-database import, a Streamlit health check, and exception-free app-entry execution in Streamlit's test harness. A fresh dependency installation and complete test run were not performed.

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
