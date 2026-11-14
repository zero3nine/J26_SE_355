# Repository Guidelines

## Project Structure & Module Organization
This Python/Streamlit research prototype collects job advertisements, cleans records, extracts skills, and analyzes job markets. `app.py` is the entry point; `pages/` contains numbered dashboard pages, with shared UI code in `app_shared.py` and `theme.py`.

Keep pipeline logic in `src/`: `scraping/`, `cleaning/`, `extraction/`, `roles/`, `analytics/`, and `analysis/`. Persistence belongs in `database/`, URL safeguards in `security/`, and benchmark tooling in `evaluation/`. `config/` holds taxonomies and domain policies. Tests live in `tests/`, offline HTML fixtures in `tests/fixtures/`, synthetic datasets in `test_data/`, and research documentation in `docs/`. `data/` contains datasets and the master SQLite database.

## Build, Test, and Development Commands
Run commands from the repository root using an isolated environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The final command starts the local dashboard. No separate build step is configured.

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m unittest src/test_app.py
python -m unittest discover -s tests -p "test_cleaning.py"
```

These run the main suite, app checks, and a focused test file, respectively.

## Coding Style & Naming Conventions
Use four-space indentation, `snake_case` for functions and modules, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants. Follow neighboring code's type hints and docstrings. Preserve numbered page filenames such as `13_Temporal_Analysis.py`. Keep reusable transformations outside Streamlit page code. No repository-wide formatter or linter configuration is currently provided.

## Testing Guidelines
Use `unittest`, naming files and methods `test_*.py` and `test_*`. Add regression tests for changed parsing, normalization, classification, or analytics behavior. Prefer offline fixtures, mocked network calls, and temporary databases. Run affected tests and the main suite before review; no enforced coverage percentage is configured.

## Commit & Pull Request Guidelines
Recent history commonly uses `feat:`, `fix:`, `docs:`, `chore:`, and `refactor:`, sometimes scoped, for example `fix(database): restore summary fields`. Use concise, specific subjects. PRs should describe the change, link relevant issues, report validation commands and results, and include screenshots for dashboard changes.

## Data & Crawling Safety
Preserve URL validation and crawling delays. Review portal terms before collection. Avoid incidental changes to tracked databases or research datasets; explain intentional data updates and their provenance. Keep generated logs, reports, and analytics outputs consistent with `.gitignore`.
