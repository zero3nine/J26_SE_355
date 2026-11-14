# Implementation Suggestions

This is a code-informed backlog from the documentation review on **2026-11-14**, not a record of completed fixes. Research intent follows the supplied TAF and temporal proposal. References identify the owning code; archived reports were not used to establish these findings.

## Implementation update: public dashboard

The independent SkillScope interface and read-only publication boundary are now implemented in `public_dashboard/`, with local publication controls in `pages/0_User_Dashboard.py` and CLI tooling in `tools/publish_dashboard.py`. Deployment files isolate the public app and sanitized SQLite snapshot. The publisher requires a matched, explicitly completed cohort from one extraction run for empirical data; demo generation is reproducible across process hash seeds and keeps the master data untouched.

Items 1-5 below are **partly addressed in the new public path**: shared denominators, full calendar grids, matched methods, read-only access, contextual exports, and atomic snapshots now have dedicated regressions. The observations about the original research modules remain valid; those implementations were not rewritten. Public trend summaries and offline baseline outlooks are documented separately from the original research models. Importing richer, reviewed component outputs, stable extraction-completion logging, threshold validation, and hosted-environment verification remain open.

The numbered sections retain the original review evidence and recommendations. Refer to About and the README for current launch/deployment behavior.

## 1. Define the publication boundary before the user dashboard

**Observed:** `pages/0_User_Dashboard.py` reads job-level tables, calls database initialization, classifies roles, and invokes temporal calculations. It lives beside administrative pages in the same Streamlit app. `schema.sql` stores regional summaries and evaluation runs, but has no common publication model for all four analysis branches.

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

**Observed:** `http_client.py` automatically retries certificate failures with `verify=False`. OCR in `service.py` downloads image URLs through a separate Requests path; browser rendering also has its own request path. Source-registry permission/validation labels are manually embedded claims. An alternate scraper remains in `scrape_jobs.py`.

**Suggested change:** Fix certificate configuration and fail clearly instead of silently disabling TLS verification. Review URL/redirect/subresource validation consistently across HTTP, browser, and image paths, including size/time limits. Record verified source-access decisions and collection coverage. Consolidate collection implementations after identifying callers; do not bypass portal restrictions to increase coverage.

**Acceptance:** Offline tests exercise redirects and image/subresource boundaries, and collection logs identify failures rather than weakening transport checks silently.

## 9. Improve reproducibility and maintainability incrementally

- **Dependencies:** Declare directly used NetworkX and Pillow dependencies, choose a supported Python version, and produce a reproducible dependency strategy. The existing environment passed `pip check`; that does not verify a clean installation. XLS is accepted by the importer but its `xlrd` engine is not declared; prefer CSV/XLSX or support it explicitly.
- **Database lifecycle:** Replace growing initialization-time ALTER logic with versioned migrations. Separate immutable research snapshots/publications from the mutable working database, and document backups and dataset provenance.
- **Source quality:** Remove shadowed duplicate `load_jobs()` declarations in `run_analysis.py`, wildcard shared imports, dynamic module reloads, duplicated role/regional page logic, and host-specific executable fallbacks in small, behavior-preserving changes.
- **Verification:** Add offline regressions for the issues above and CI for core suites. Keep live-source/model-download checks separate. Some legacy app tests depend on DNS; passing them locally does not guarantee an offline test run.
- **Documentation:** Maintain [About.md](About.md) for the overall implementation and [Temporal_Analysis_Component.md](Temporal_Analysis_Component.md) for this component. Update claims with code changes and recorded evidence; retain [archive/](archive/) as historical material.

## Review evidence and suggested order

This pass read the proposal scope/diagrams and the application, collection, cleaning, extraction, database, and analytical paths. It ran the five existing temporal tests (all passed, with timedelta deprecation warnings), `pip check` (passed), a temporary-database initialization/import check, a Streamlit HTTP health check, and exception-free app-entry execution in Streamlit's test harness. It also reproduced the temporal threshold defect in memory. It did not run the whole test suite, verify live portal policies, benchmark real model accuracy, or establish production readiness.

Next, validate a real matched extraction cohort and integrate richer reviewed research outputs where needed. Correct result-affecting issues in the original research paths before treating their reports as publishable findings. Then address configuration, evidence, and maintainability in small changes. The original documentation review made no implementation changes; the subsequent dashboard implementation is summarized in the update above.

## Dashboard verification record — 2026-11-14

- Sixteen dedicated public tests passed: cohort denominators, zero-result handling, sparse/missing periods, canonical export from a read-only master, invalid inputs, privacy boundary, CSV safety/provenance, offline forecast scope, atomic publication validation, cross-process fixture reproducibility, and a production runtime isolated from admin/ML packages.
- Six Playwright browser checks passed at desktop and phone widths: all views, shared filters, skill search/drill-down, empty/reset states, scoped downloads, URL restoration, forecast eligibility, and mobile navigation. No JavaScript errors or document-level horizontal overflow were observed. Screenshots are under ignored `tmp/dashboard-qa/`.
- The public tests plus the three pytest-based research files passed: 47 tests total. The local publication page also ran without exceptions in Streamlit's test harness; `pip check` and Compose configuration validation passed.
- The full unittest run reached 325 tests but was not green: the unchanged OCR suite imports removed `_is_boilerplate` from `run_extraction.py`; a DNS-dependent URL-validator assertion also failed in that run, then all six validator tests passed standalone. Redirected Windows output required `-X utf8` to avoid older CLI Unicode-print errors. `requirements-dev.txt` now declares the previously missing pytest runner. These results are not a claim that all research tests pass.
- Docker deployment files are prepared and configuration-validated, but the image could not be build/run-tested because the Docker daemon was stopped. No hosted service was provisioned. The synthetic snapshot is generated locally and the tracked master database is unchanged.

## Development workflow setup — 2026-11-14

Project-local [commit](../.agents/skills/commit/SKILL.md) and [change](../.agents/skills/change/SKILL.md) skills now follow the [development workflow](development-workflow.md), including observable Done when conditions, scoped security decisions, team boundaries, and next-step recommendations. This adds development guidance only; it does not resolve the implementation backlog above.

Both skills passed the bundled skill validator, 16 local documentation links resolved, and all six `src/test_app.py` checks passed. The full unittest discovery ran 327 tests with one error: `test_ocr_pipeline` still imports missing `_is_boilerplate` from `src/extraction/run_extraction.py`. Git blob hashes confirmed both involved files were identical to HEAD during this documentation-only change. The earlier DNS assertion did not fail in this run; its historical sensitivity is not thereby resolved. No public browser or Docker checks were run for this workflow setup. The OCR test/import contract remains a testing follow-up; collection security findings above remain open pending code verification and remediation.
