# Repository Guidelines

## Project Structure & Module Organization
This project collects job advertisements, extracts skills, and analyzes IT markets. `app.py` starts the local Streamlit research tools; `pages/` contains numbered pages. Shared UI code lives in `app_shared.py` and `theme.py`. The independent public app lives in `public_dashboard/`; `tools/publish_dashboard.py` prepares its separate read-only publication.

Keep pipeline logic in `src/`: `scraping/`, `cleaning/`, `extraction/`, `roles/`, `analytics/`, and `analysis/`. Persistence belongs in `database/`, URL safeguards in `security/`, and benchmark tooling in `evaluation/`. `config/` holds taxonomies and domain policies. Tests live in `tests/`, offline HTML fixtures in `tests/fixtures/`, synthetic datasets in `test_data/`, and research documentation in `docs/`. `data/` contains datasets and the master SQLite database.

## Build, Test, and Development Commands
Run commands from the repository root using an isolated environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
python -m tools.publish_dashboard --synthetic
python -m public_dashboard.app
```

These launch the research tools, generate a separate synthetic publication, and serve the public dashboard. Production public deployment uses `Dockerfile.dashboard`; no frontend build is needed.

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m unittest src/test_app.py
python -m unittest discover -s tests -p "test_cleaning.py"
```

These run the main suite, app checks, and a focused test file, respectively.

## Coding Style & Naming Conventions
Use four-space indentation, `snake_case` for functions and modules, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants. Follow neighboring code's type hints and docstrings. Preserve numbered page filenames such as `13_Temporal_Analysis.py`. Keep reusable transformations outside Streamlit page code. No repository-wide formatter or linter configuration is currently provided.

## Testing Guidelines
Use `test_*.py` files and `test_*` methods. Research tests use unittest and pytest (`requirements-dev.txt`). Public tests run with `python -m unittest discover -s tests -p "test_public_dashboard.py"`; explicit Playwright checks use `python tests/browser_public_dashboard.py`. Prefer offline fixtures, mocked network calls, and temporary databases. Run affected tests and the main suite before review; no coverage percentage is enforced.

## Commit & Pull Request Guidelines
Recent history commonly uses `feat:`, `fix:`, `docs:`, `chore:`, and `refactor:`, sometimes scoped, for example `fix(database): restore summary fields`. Use concise, specific subjects. PRs should describe the change, link relevant issues, report validation commands and results, and include screenshots for dashboard changes.

## Data & Crawling Safety
Preserve URL validation and crawling delays. Avoid incidental changes to tracked research data. Never ship the master database or admin/ML dependencies with the public app. Publish reviewed matched cohorts; retain zero-skill jobs and synthetic provenance. Generated snapshots under `data/public/` are ignored.
