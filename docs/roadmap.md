# Implementation roadmap

The pipeline can reopen saved batches, replay imports with recorded membership, and save both extraction methods as one matched run. Regional Analysis reads the master database without importing records. The research views offer explicit extraction-run selection. See the [issue register](suggestions.md#current-issues) for the remaining limitations.

### Coverage in the bundled snapshot

The read-only audit of the bundled master excluded the 1,416 exact synthetic fixture URL matches. The remaining 356 postings still need provenance and eligibility review. Parseable posting dates use UTC calendar months and include date-only and ISO timestamp values. The 105 rows without a usable date are excluded from the monthly counts.

| Market | Postings | With a usable date | Jun 2026 | Jul | Aug | Sep | Oct |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Sri Lanka | 242 | 148 | 0 | 0 | 9 | 37 | 102 |
| India | 31 | 23 | 0 | 0 | 6 | 7 | 10 |
| Singapore | 47 | 46 | 1 | 1 | 4 | 5 | 35 |
| Malaysia | 20 | 19 | 0 | 0 | 0 | 0 | 19 |
| Unknown or unspecified | 16 | 15 | 0 | 0 | 0 | 0 | 15 |
| **Total** | **356** | **251** | **1** | **1** | **19** | **49** | **181** |

All 356 rows have a non-empty description, and none has text in the separate `requirements` field. Description length and skill-bearing requirements within descriptions still need source-specific review. TopJobs hostnames account for 125 of Sri Lanka's 242 rows, Shine hostnames for 27 of India's 31, and MyCareersFuture for all 47 Singapore rows. The data supports exploratory descriptions of those samples and source mixes. It is too sparse for market-wide or longitudinal demand claims. Neither the [tracked pilot CSV](../data/raw/all_pilot_crawled_predictions.csv) nor the [temporal preparation export](../data/analysis/temporal/temporal_jobs_with_quality_flags.csv) extends the usable date range before June 2026. An authorized historical export with original dates and preserved requirements text is still needed.

| Order | Work | Done when |
| --- | --- | --- |
| 1 | **Finish collection environment verification.** The default Linux images and offline sandbox smoke checks passed. Verify intended deployment egress, clean Windows setup, and optional admin image variants, then pilot permitted portals individually. | Approved offline and live checks have dated results for listing and detail coverage, required OCR/browser setup, and field completeness. Restricted sources stay excluded. |
| 2 | **Review posting identity and sample eligibility.** Inspect repeated URLs, portal aliases, possible reposts, and benchmark labels. Define which advertisements qualify for each shared measure. | Reviewed identity rules distinguish repeat observations from distinct postings. A hand-calculated sample gives the expected counts, and documented exclusions explain differences between measures. |
| 3 | **Assess extraction and temporal evidence on reviewed data.** New runs preserve model and text evidence and the forecast view back-tests each displayed horizon. Evaluate extraction accuracy, trend thresholds, and forecast performance against reviewed advertisements. | Reviewers can trace published results to model, taxonomy, inputs, and horizon-specific checks. Threshold and coverage decisions have documented empirical support. |
| 4 | **Publish one reviewed empirical sample.** Prepare the cohort and verify the public runtime with only the sanitized snapshot. | Another teammate can reproduce the publication. The hosted dashboard and exports identify the cohort, methods, and limitations, and the snapshot is served read-only. |
