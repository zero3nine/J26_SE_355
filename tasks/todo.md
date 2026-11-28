# TopJobs archive implementation checklist

The 28 November collection tried eight archived TopJobs detail URLs from two May 2024 listing replays. All eight returned HTTP 404. Collection continued through ITPro's public feed and indexed Wayback detail captures. See the [ITPro staging workflow](../docs/itpro-collection.md). The broader TopJobs feasibility tasks below remain open.

## Temporal backfill results

The follow-up added 1,006 dated, full-text Sri Lankan job candidates after cleaning and deduplication. The additions include 298 ITPro Wayback adverts, 403 ITPro tracker adverts, and 305 XpressJobs publisher adverts. The combined collection has 1,558 candidates and 23 consecutive completed calendar months with at least 10 candidates each, from December 2024 through October 2026. The rule-based classifier marked 966 candidates as IT and 592 as ambiguous. The IT subset has 10 consecutive months with at least 10 ads each, from January through October 2026. Earlier periods remain uneven.

The local cohort, monthly coverage, and provenance records are in `data/raw/historical_imports/2026-11-28-temporal-backfill/`. A repeat import on a temporary master skipped all 1,558 rows and added zero job versions. The tracked master still has 356 jobs. See the [ITPro tracker instructions](../docs/itpro-collection.md#public-tracker-snapshots) and [XpressJobs staging instructions](../docs/xpress-historical-collection.md).

## Feasibility pilot

- [ ] **Replay a listing end to end.** Add the bounded archive CLI and extract vacancy numbers, links, and original date fields from a replayed listing. Verify deterministic output and coverage of CDX resumption, absent captures, historic table variants, safe redirects, and rate limits with offline fixtures.
- [ ] **Recover evidence for sampled vacancies.** Reuse the detail and OCR extractors on captured HTML and flyers and record usable, partial, and failed outcomes. Verify identity checks, soft 404s, missing flyers, original-date handling, and a restart that adds no duplicate records.
- [ ] **Run the capped four-quarter pilot.** Save a manifest and a quarterly coverage and failure report with distinct counts, usable date-and-text yield, and review notes. Verify that sampling and exclusion totals reconcile, then decide whether any period is suitable for backfill.

## Reviewed backfill, conditional on pilot yield

- [ ] **Reconcile the staged cohort with a temporary master.** Match vacancy references to existing TopJobs URLs, hold ambiguous matches for review, and run cleaning and import twice. Verify stable job and version counts, evidence traceability, and preservation of existing newer content.
- [ ] **Verify temporal eligibility and coverage.** Review text and opening dates, run matched skill extraction on the accepted subset, and check counts by original month. Verify that undated records and uncovered months are excluded as appropriate and eligible zero-skill ads stay in the denominator. Document supported periods before scaling or publishing.
