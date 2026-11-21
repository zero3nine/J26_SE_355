# Known issues and implementation notes

The [implementation roadmap](roadmap.md) orders this backlog into small changes with acceptance checks. The dated review and validation records below preserve the evidence available at the time.

## Current issues

The **2026-11-21** refactor added read-only regional loading, batch recovery, import membership and rollback, atomic extraction saves, matched research scopes, and collection safeguards. The dated notes below retain the earlier review history. These are the remaining issues.

| Area | Evidence and impact | Next check or change |
| --- | --- | --- |
| Historical traceability | The [batch picker](../src/scraping/batches.py) checks that cleaned records belong to the raw scope. New clean artifacts include a manifest for the raw data and both exports. Older append operations may only have the incoming CSV. Older [import membership](../src/database/schema.sql) can be recovered where a job version recorded its import. | Confirm older scopes from original records when they are needed for research. |
| Posting identity | The [importer](../src/database/repository.py) matches normalized source URLs. Portal aliases and potential reposts can still split or duplicate an observation. | Review source-specific identities and collisions before consolidating historical rows. |
| Collection coverage | Configured single-vacancy listings are handled. Unclassified pages with one link still need source-specific fixture evidence. Registry labels, permissions, source access, and field coverage require live verification. | Test approved sources one at a time, record evidence, and keep restricted sources out of active collection. [Registry](../config/source_registry.json) |
| Browser egress | [Browser rendering](../src/scraping/browser_fetch.py) requires opt-in and sandboxed Chromium. Initial and final destinations are checked. Redirect and subresource egress, and a browser-wide response budget, require runtime controls. OCR image downloads use bounded, verified HTTP requests. | Verify the deployment's browser egress and sandbox before expanding live collection. |
| Extraction and eligibility | [Matched runs](../src/database/extraction_cohort.py) verify inputs and completion. New combined runs store text evidence and the pinned default model revision. Regional geography, temporal dates, and other measure-specific requirements can yield different denominators from the same run. | Review how posting identity, IT classification, and source evidence affect each empirical measure. |
| Forecast validation | The [temporal comparison](Temporal_Analysis_Component.md) uses a common eligible calendar. Forecasts use contiguous history and report a back-test for each displayed horizon. | Assess thresholds, coverage, benchmark performance, and suppression on a reviewed dated cohort. |
| Benchmark and release | The [pilot benchmark](../data/evaluation/SAMPLING_METHODOLOGY.md) has 120 records and 118 distinct source URLs. The default Linux images passed isolated startup checks. Clean Windows and optional admin image configurations, the hosted smoke test, and a reviewed empirical public cohort remain open. | Review repeated labels and coverage, then verify the sanitized publication independently of the admin runtime. |

### Refactor verification on 2026-11-21

The Linux Python 3.14 test environment used the declared research requirements and a CPU-only PyTorch build. An isolated checkout without the tracked master database passed 389 unittest checks and 71 selected pytest checks, including semantic extraction with the cached model. The 7 admin and 10 public browser checks used local Chromium and synthetic fixtures. An additional offline smoke check started Chromium with its sandbox enabled. Streamlit smoke checks reopened a saved batch across fresh sessions, cleaned it, published it to a temporary master, and verified separate relationship reports for two extraction runs.

### Collection and persistence fixes on 2026-11-22

Offline regression fixtures verify that rendered job details survive zero link discoveries, sparse imports preserve salary evidence, conflicting CSV job IDs and URLs roll back extraction saves, and raw and cleaned batch scopes agree at recovery. Replace a salary with new raw text or structured amounts. A disclosure flag alone preserves existing salary evidence. To record an explicit withdrawal, use the revised source text, such as “Salary not disclosed.”

On Linux with Docker 29.9.2 and Compose 5.6.1, both Compose files validated and the default images built from a temporary source copy with cached dependencies. In network-isolated containers, the lean admin responded to its health check and initialized a temporary master database. Gunicorn served the public API against a read-only synthetic snapshot. The API rejected POST and the mount refused writes. The default admin Compose configuration still needs an environment-level browser egress policy for live collection.

### Integrated review fixes on 2026-11-22

The isolated copy passed 488 pytest checks and 33 subtests, 415 unittest checks, six app checks, and all 17 local Chromium checks across the admin and public dashboards. An offline import-to-publication smoke test ran the pinned model, stored evidence for both methods, exported a reviewed fixture subset, and rejected a mixed synthetic subset while retaining the previous snapshot.

## Implementation update for the public dashboard

The independent SkillScope interface and read-only publication boundary are implemented in `public_dashboard/`, with local publication controls in `pages/0_User_Dashboard.py` and CLI tooling in `tools/publish_dashboard.py`. Empirical publication requires a reviewed subset of one recorded matched run, verifies its current inputs and completions, and rejects synthetic and unreviewed records. Demo generation is reproducible across process hash seeds.

The public path has regressions for shared denominators, full calendar grids, matched methods, read-only access, contextual exports, and atomic snapshots. Public trend summaries and offline baseline outlooks use their own documented calculations. Importing reviewed component outputs, validating thresholds against empirical evidence, and checking the hosted environment remain open.

The numbered sections retain the original review evidence and recommendations. Refer to About and the README for current launch/deployment behavior.

## 1. Define the publication boundary before the user dashboard

**Original observation:** The legacy `pages/0_User_Dashboard.py` read job-level tables, initialized the master database, classified roles, and invoked temporal calculations alongside administrative pages. That page now hosts publication controls and a link to SkillScope. Reviewed outputs from all four research branches still need a common publication contract where required.

**Suggested change:** Keep collection and research tools local. Add a deliberate publish operation that writes reviewed analysis datasets to a database. A separately runnable public app should read published results with read-only access, without importing collection tools or initializing schemas.

Start with a small publication contract: publication ID/status, generated time, observation window, included source/country/role scope, input snapshot/hash, extraction run(s), taxonomy/model/configuration versions, eligibility policy, counts/denominators, and warnings. Store result rows for skill demand, role-skill demand, relationships, regional comparisons, and temporal series/classifications. Store forecasts and validation separately when available. Publish a complete result set atomically; filter it at display time without silently changing its meaning.

**Acceptance:** An empty database produces a clear empty state; an approved publication renders without scraping or ML execution; unpublished runs remain invisible; every chart identifies its period, scope, method, and sample size. SQLite can remain an initial local implementation; choose hosted storage when deployment requirements are established.

## 2. Make extraction experiments comparable

**Observed:** `load_temporal_input()` reads every extraction run, `get_extracted_skills_dataset()` merges runs unless given a run ID, and the role page chooses the latest run with saved mentions. Re-extraction at a different threshold can therefore change some views through a union while others show one batch. A job with no saved mentions is indistinguishable from an unprocessed job in mention-based readers.

**Suggested change:** Record per-job extraction completion, including zero-skill results and failures. Define an explicit, immutable input cohort and matched lexical/semantic run configuration. Make all analysis readers honor it; avoid substituting 'latest run' when that run covers only part of the dataset. Preserve a stable canonical skill ID and a versioned display name across readers.

**Acceptance:** Repeating an experiment at a new threshold does not alter an existing publication. Method comparisons contain the same successfully processed jobs and explain exclusions.

## 3. Correct temporal sample and calendar handling

**Confirmed defect:** In `src/analytics/temporal_analysis.py`, `build_demand_series()` filters skill rows by `min_jobs`, but `expand_zero_demand_periods()` uses unfiltered denominators and fills missing counts with zero. A three-month probe with 5/1/5 eligible jobs and one mention each returned 20%/0%/20% at threshold five. The excluded middle month's real mention was replaced with zero.

**Suggested change:** Preserve eligibility/missingness states through aggregation; an excluded period must remain excluded. Construct one explicit calendar grid and distinguish zero mentions, insufficient jobs, no collection, and unprocessed extraction. Define leading/trailing zero rules deliberately. Fit trend slopes against elapsed time or require continuous periods; current code compresses gaps into sequential observations.

**Acceptance:** Tests cover excluded interior periods, genuine zero demand, no-source gaps, first/last mentions, and monthly/quarterly boundaries. Forecasting rejects unsupported gaps or uses a documented treatment.

## 4. Align eligibility and demand denominators

**Observed:** Temporal `load_eligible_jobs()` includes every non-empty dated master row without IT-status filtering. Regional `EligibilityConfig` excludes zero-skill records by default (`require_at_least_n_skills=1`). The relationship loader drops empty selected skill sets. The role loader defaults to jobs with mentions. Percentages across these paths therefore answer different questions. Master imports can also default missing classification to `it`; the shared cleaned schema does not preserve every internal eligibility field.

**Suggested change:** Define a shared curated IT population, preserve classification/review and duplicate provenance through persistence, and distinguish demand among eligible advertisements from conditional metrics among skill-bearing records. Method-dependent extraction failures should not silently change denominators.

**Acceptance:** The same cohort produces the same eligible-job totals across branches where the estimand is shared. Conditional metrics explicitly label their population. Synthetic data remains identifiable and outside empirical publications.

## 5. Repair temporal method-sensitivity summaries

**Observed:** `representation_comparison()` averages positive-mention rows, while the page's zero-expanded series use method-specific endpoints. Trend agreement inner-joins skills, omitting method-only skills. The displayed mean-demand ranking is therefore not a controlled comparison over a shared skill-period grid.

**Suggested change:** Compare matched runs on one eligible job cohort and calendar grid, including defensible zeros. Report shared-skill and union-skill coverage, rank correlation, top-k overlap, trend direction/label agreement, and emerging-candidate overlap with explicit denominators.

**Acceptance:** Synthetic examples with an omitted month, a method-only skill, and a genuine zero have manually verified expected results.

## 6. Validate screening and forecasting claims

**Observed:** Trend thresholds are heuristics; directional labels are assigned before the volatility rule. The proposal's source-stability and threshold-sensitivity safeguards are not automated. Forecast generation uses a 150-tree forest, evaluation a 100-tree forest; one-step back-tests accompany forecasts of up to three periods. Count gates do not establish regular coverage or sufficient statistical evidence.

**Suggested change:** Review labeling precedence and tune thresholds with recorded sensitivity analysis. Share model construction between evaluation and final fitting. Evaluate each published horizon, report target counts and source coverage, and suppress unsupported forecasts. Add uncertainty estimates only with a defensible procedure. Keep Gradient Boosting and sequence models conditional on data and baseline evidence.

**Acceptance:** Published classifications include evidence and uncertainty; model claims refer to the evaluated configuration and horizon. A baseline may remain the preferred model.

## 7. Preserve real extraction evidence and configuration

**Observed:** `store_extracted_skills()` assigns confidence `1.0` to both methods and stores provenance labels in `original_span`. Semantic scores exist in the extractor but are discarded when `run_extraction()` reduces results to skill-ID lists. Threshold defaults differ (`0.58` in the API/extractor; `0.45` in the combined CLI/page). Run metadata includes generic or hard-coded model/version values. Canonical definitions are duplicated between the taxonomy JSON and `normalization.py`.

**Suggested change:** Carry maximum similarity, candidate text/offsets, input-text provenance, exact model revision, taxonomy hash, and actual threshold into structured persisted results. Treat cosine similarity as a model score, not calibrated confidence. Centralize taxonomy and extraction configuration. The text builder labels some inputs as title fallback while still concatenating the available description; make that behavior and label agree.

**Acceptance:** A reported skill can be traced to the actual input, method, configuration, and supporting text. Metadata never implies validation that did not occur.

## 8. Make collection behavior and permissions explicit

**Updated 2026-11-14:** `http_client.py` now keeps TLS verification enabled and returns a terminal `tls_error` on certificate/handshake failure; the service records the failure and skips browser fallback for that URL. Correct the source certificate or local trust configuration before resuming collection.

**Remaining observed paths:** OCR in `service.py` downloads image URLs through a separate Requests path; browser rendering also has its own request path. Source-registry permission/validation labels are manually embedded claims. An alternate scraper remains in `scrape_jobs.py`.

**Suggested change:** Review URL/redirect/subresource validation consistently across HTTP, browser, and image paths, including size/time limits. Record verified source-access decisions and collection coverage. Consolidate collection implementations after identifying callers; do not bypass portal restrictions to increase coverage.

**Acceptance:** Offline tests exercise redirects and image/subresource boundaries, and collection logs identify failures rather than weakening transport checks silently.

## 9. Improve reproducibility and maintainability incrementally

- **Dependencies:** Declare directly used NetworkX and Pillow dependencies, choose a supported Python version, and produce a reproducible dependency strategy. The existing environment passed `pip check`; that does not verify a clean installation. XLS is accepted by the importer but its `xlrd` engine is not declared; prefer CSV/XLSX or support it explicitly.
- **Database lifecycle:** Replace growing initialization-time ALTER logic with versioned migrations. Separate immutable research snapshots/publications from the mutable working database, and document backups and dataset provenance.
- **Source quality:** Remove shadowed duplicate `load_jobs()` declarations in `run_analysis.py`, wildcard shared imports, dynamic module reloads, duplicated role/regional page logic, and host-specific executable fallbacks in small, behavior-preserving changes.
- **Verification:** Add offline regressions for the issues above and CI for core suites. Keep live-source/model-download checks separate. Some legacy app tests depend on DNS; passing them locally does not guarantee an offline test run.
- **Documentation:** Maintain [About.md](About.md) for the overall implementation and [Temporal_Analysis_Component.md](Temporal_Analysis_Component.md) for this component. Update claims with code changes and recorded evidence; retain [archive/](archive/) as historical material.

## Original review evidence

This pass read the proposal scope/diagrams and the application, collection, cleaning, extraction, database, and analytical paths. It ran the five existing temporal tests (all passed, with timedelta deprecation warnings), `pip check` (passed), a temporary-database initialization/import check, a Streamlit HTTP health check, and exception-free app-entry execution in Streamlit's test harness. It also reproduced the temporal threshold defect in memory. It did not run the whole test suite, verify live portal policies, benchmark real model accuracy, or establish production readiness.

The original review proposed validating a matched extraction cohort and correcting the research results before publication. The [roadmap](roadmap.md) incorporates the batch recovery and re-import gaps found in the latest review.

## Dashboard verification record — 2026-11-14

- Sixteen dedicated public tests passed: cohort denominators, zero-result handling, sparse/missing periods, canonical export from a read-only master, invalid inputs, privacy boundary, CSV safety/provenance, offline forecast scope, atomic publication validation, cross-process fixture reproducibility, and a production runtime isolated from admin/ML packages.
- Six Playwright browser checks passed at desktop and phone widths: all views, shared filters, skill search/drill-down, empty/reset states, scoped downloads, URL restoration, forecast eligibility, and mobile navigation. No JavaScript errors or document-level horizontal overflow were observed. Screenshots are under ignored `tmp/dashboard-qa/`.
- The public tests plus the three pytest-based research files passed: 47 tests total. The local publication page also ran without exceptions in Streamlit's test harness; `pip check` and Compose configuration validation passed.
- The full unittest run reached 325 tests but was not green: the unchanged OCR suite imports removed `_is_boilerplate` from `run_extraction.py`; a DNS-dependent URL-validator assertion also failed in that run, then all six validator tests passed standalone. Redirected Windows output required `-X utf8` to avoid older CLI Unicode-print errors. `requirements-dev.txt` now declares the previously missing pytest runner. These results are not a claim that all research tests pass.
- Docker deployment files are prepared and configuration-validated, but the image could not be build/run-tested because the Docker daemon was stopped. No hosted service was provisioned. The synthetic snapshot is generated locally and the tracked master database is unchanged.

## Development workflow setup — 2026-11-14

Project-local [commit](../.agents/skills/commit/SKILL.md) and [change](../.agents/skills/change/SKILL.md) skills now follow the [development workflow](development-workflow.md), including observable Done when conditions, scoped security decisions, team boundaries, and next-step recommendations. This adds development guidance only; it does not resolve the implementation backlog above.

Both skills passed the bundled skill validator, 16 local documentation links resolved, and all six `src/test_app.py` checks passed. The full unittest discovery ran 327 tests with one error: `test_ocr_pipeline` still imports missing `_is_boilerplate` from `src/extraction/run_extraction.py`. Git blob hashes confirmed both involved files were identical to HEAD during this documentation-only change. The earlier DNS assertion did not fail in this run; its historical sensitivity is not thereby resolved. No public browser or Docker checks were run for this workflow setup. The OCR test/import contract remains a testing follow-up; collection security findings above remain open pending code verification and remediation.

## Public dashboard theme update — 2026-11-14

SkillScope now uses a Google-inspired blue palette and an accessible Dark mode toggle. Shared semantic colors cover surfaces, controls, charts, and status labels in both appearances. The initial mode follows the device setting until the user chooses; a validated light/dark preference is stored locally when possible, with a working page-local fallback if storage is blocked. Filters, analytical definitions, exports, and shared URLs are unchanged. The research/admin theme is outside this update.

The new theme regression failed before implementation. After implementation, all ten Playwright checks passed (the six existing checks plus four theme checks): persistence, keyboard toggling without analytical requests/state changes, system preference changes, invalid/blocked storage, scoped download, both appearances across all six views, sampled text contrast of at least 4.5:1, and desktop/mobile layout. Light/dark screenshots are saved under ignored `tmp/dashboard-qa/`; desktop overviews and the dark mobile connections view were visually reviewed. All 16 public unittest checks and six app checks passed. Full discovery again ran 327 tests with only the existing OCR import error; both involved files still matched HEAD. Patch hygiene passed. No Docker or hosted checks were run.

Theme security review found no new major issue: no new dependencies, remote assets, analytical query inputs, or relaxed security headers were needed. The new startup script is served from the existing static allowlist under the unchanged Content Security Policy. The unrelated OCR testing follow-up and earlier collection-security backlog remain open.

## Collection TLS failure handling — 2026-11-14

The collection HTTP client no longer retries `SSLError` with verification disabled. Every request keeps `verify=True`; certificate/handshake failures return `tls_error`, an actionable certificate/trust-configuration message, and the failing URL (including redirect targets). The service writes the failure to the batch/failure log and skips browser fallback, extraction, and OCR for that URL. Other queued URLs retain the existing collection behavior. No URL policy, crawling delay, response limit, dependency, or research dataset changed.

Before implementation, offline regressions demonstrated the second HTTP attempt and browser fallback after TLS failure. After implementation, all nine new offline tests passed: terminal failures with either user agent, redirect-target TLS failure, verified redirect success, initial/redirect URL rejection, polite delay, response-size cap, temporary-status retries, verified user-agent fallback, and temporary-directory collection failure logging. The existing multi-portal (8), foreign-adapter (16), and enhancement (4) checks also passed, as did all six app checks.

Validation commands: `python -X utf8 -m unittest discover -s tests -p "test_http_client.py"`, the same discovery command for `test_multi_portal_scraping.py`, `test_foreign_portal_adapters.py`, and `test_enhancements.py`, plus `python -X utf8 -m unittest src/test_app.py`. Full discovery (`python -X utf8 -m unittest discover -s tests -p "test_*.py"`) ran 336 tests: 335 passed and the existing OCR import error remained. Standalone OCR discovery reproduced the missing `_is_boilerplate` import; both `tests/test_ocr_pipeline.py` and `src/extraction/run_extraction.py` had identical working-tree and HEAD Git blob hashes. This unrelated baseline failure remains a follow-up. Patch hygiene passed.

The changed transport/caller paths were reviewed for verification bypass and preservation of URL/redirect checks, timeouts, delays, and bounded responses. Separate browser/image/subresource paths and source-permission verification in section 8 remain open; this narrow fix does not establish their safety. No live collection or public browser/deployment checks were run for this transport-only change.

## Admin portal appearance update — 2026-11-14

All research/admin modules now use SkillScope's light palette, blue navigation, rounded cards, and readable status colors. Native widgets use `.streamlit/config.toml`; shared components and page-specific HTML use the same palette. Publication and temporal pages receive the shared CSS. Regional and relationship chart colors were adjusted for light surfaces. The raw-record metadata card's HTML whitespace was normalized so closing markup is not displayed as a code block. No controls, calculation logic, analytical thresholds, queries, export contents, or research datasets changed. No new dependencies or external resources were added; the shared theme uses system fonts.

`python -X utf8 tests/browser_admin_theme.py` passed all five checks using a temporary project, synthetic master records, and synthetic session/review records: all 15 modules plus home at desktop and phone widths, populated component preview, sampled component-text contrast of at least 4.5:1, keyboard focus, unchanged raw search/CSV export, and collection-mode switching. No JavaScript errors or document-level horizontal overflow were observed. Screenshots are under ignored `tmp/dashboard-qa/admin/`; home, collection (desktop/mobile), raw data, manual review, populated regional summary, and component-preview screenshots were visually inspected. The temporary preview page and seeded data are only part of the QA setup, not the application.

All six app checks passed. Full unittest discovery ran 336 tests: 335 passed and the existing OCR `_is_boilerplate` import error remained. Both involved files (`tests/test_ocr_pipeline.py` and `src/extraction/run_extraction.py`) still had working-tree blob hashes identical to HEAD. A syntax-tree comparison also confirmed that existing control flow/calculations were unchanged by the palette replacements and CSS loading; the additional raw-card wrapper only normalizes HTML whitespace. Patch hygiene passed. The independent public runtime was unchanged; no deployment or live-collection checks were run.

The changed styling introduces no script, query, permission, or transport changes. Existing collection-security follow-ups in section 8 remain open. Initial browser QA with an empty temporary master also exposed an existing regional empty-data `KeyError: 'country'` at `regional_dashboard_view.py`'s general-eligibility summary; final regional appearance checks used populated synthetic records. Its filtering/summary logic is unchanged. A separate functional fix should handle the empty-data state; it was deliberately left outside this UI-only update.
