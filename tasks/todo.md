# TopJobs archive implementation checklist

The 28 November collection tried eight archived TopJobs detail URLs from two May 2024 listing replays. All eight returned HTTP 404. Collection continued through ITPro's public feed and indexed Wayback detail captures. See the [ITPro staging workflow](../docs/itpro-collection.md). The broader TopJobs feasibility tasks below remain open.

## Feasibility pilot

- [ ] **Replay a listing end to end.** Add the bounded archive CLI and extract vacancy numbers, links, and original date fields from a replayed listing. Verify deterministic output and coverage of CDX resumption, absent captures, historic table variants, safe redirects, and rate limits with offline fixtures.
- [ ] **Recover evidence for sampled vacancies.** Reuse the detail and OCR extractors on captured HTML and flyers and record usable, partial, and failed outcomes. Verify identity checks, soft 404s, missing flyers, original-date handling, and a restart that adds no duplicate records.
- [ ] **Run the capped four-quarter pilot.** Save a manifest and a quarterly coverage and failure report with distinct counts, usable date-and-text yield, and review notes. Verify that sampling and exclusion totals reconcile, then decide whether any period is suitable for backfill.

## Reviewed backfill, conditional on pilot yield

- [ ] **Reconcile the staged cohort with a temporary master.** Match vacancy references to existing TopJobs URLs, hold ambiguous matches for review, and run cleaning and import twice. Verify stable job and version counts, evidence traceability, and preservation of existing newer content.
- [ ] **Verify temporal eligibility and coverage.** Review text and opening dates, run matched skill extraction on the accepted subset, and check counts by original month. Verify that undated records and uncovered months are excluded as appropriate and eligible zero-skill ads stay in the denominator. Document supported periods before scaling or publishing.
