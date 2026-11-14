# Temporal data quick start

The collector stores the posting date it can extract from each accessible advertisement (`posted_date_raw`) separately from the collection timestamp (`scraped_at`). When a submitted URL is a listing page, it now follows explicit same-site pagination links (such as “Next” or “Older”) and collects those pages' job links too. The normal request, time, and job limits bound this crawl. Raise `max_requests` and `max_time_seconds` when calling `run_collection_pipeline` if you want to traverse more pages.

In **Collect Data**, enable **Temporal collection: keep paging after the job target** to avoid stopping after the default target of valid IT jobs. The request and duration budgets remain in force. TopJobs listing-row opening dates are now copied into `posted_date_raw` when the detail page omits them. The temporal dataset builder also converts relative labels such as `2 months ago` using `scraped_at` as the reference, and records that conversion method.

The source registry includes Jobpal and DreamJobs as pending evaluation sources; their pages can be submitted to the collector, but their field accuracy and access rules still need review. Existing Sri Lankan sources include TopJobs, XpressJobs, and ITPro. DreamJobs exposes numbered listing pages, while Jobpal shows posted-age labels on its public listings; neither provides proof of a complete historical archive. [DreamJobs](https://www.dreamjobs.lk/), [Jobpal](https://jobpal.lk/)

This discovers older postings only when the portal still exposes them through public pagination. It cannot recover expired advertisements that the portal has removed; for those, provide historical URLs or an authorized archive/export. Keep the raw posting date and collection timestamp distinct in temporal analysis.

## Build temporal analysis files

Run from the repository root:

```bash
python -m src.analysis.build_temporal_dataset --input data/raw/batches --output data/analysis/temporal --frequency M
```

Use `--frequency Q` for quarterly periods if monthly samples are too sparse. The script writes:

- `temporal_jobs_with_quality_flags.csv` — all input rows, normalized dates and missing-date flags.
- `temporal_skill_demand.csv` — distinct jobs mentioning each skill per period, eligible dated job count, and normalized demand percentage.
- `temporal_data_quality_report.csv` — date coverage and selected columns.

The script prefers an available canonical/semantic skill column; otherwise it uses the raw skills column. Check the reported `skill_column_used` before interpreting results. If the existing CSV contains only raw skill text, run the project's normal skill extraction/cleaning step first and point the script at that analysis-ready CSV.

Unknown or unparsable dates are preserved in the quality file but excluded from temporal aggregation. Never substitute `scraped_at` for `posting_date` as a job publication date. Inspect skill delimiter formats and duplicates before reporting results.
