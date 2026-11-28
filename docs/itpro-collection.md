# Staging ITPro advertisements for research

The ITPro public widget includes vacancy IDs, titles, employers, advert text, and a `created_on` timestamp. Historical Wayback captures can contain the publisher's structured `datePosted` and the advert text. Use the normalized ITPro vacancy ID to compare records across URL slug changes. Keep archive timestamps as capture evidence.

## Recent feed

Save one snapshot of the [documented public widget](https://itpro.lk/widgets/) and run the staging module with the snapshot date. The following example requests up to 850 current entries from the last 90 days. The portal's [retention policy](https://itpro.lk/recruiter-faq/) limits which ads are visible, so the result represents the ads available when the feed was collected.

```bash
curl --fail --max-time 30 --max-filesize 5000000 \
  'https://itpro.lk/api/?action=getJobs&type=0&category=0&count=850&random=0&days_behind=90&response=json' \
  -o itpro-widget-response.txt
python -m src.scraping.itpro_feed itpro-widget-response.txt itpro-recent.csv --as-of 2026-11-28
```

The staging module reads the response as data, keeps the original vacancy URL, removes direct recruiter contact details from advert text, and reports exclusion counts and coverage by posting month. The role screen uses technical categories and title signals. The project's cleaning step still classifies ambiguous roles for review.

## Archived ads

Use [Wayback CDX](https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server#readme) to discover indexed job detail URLs and timestamps. Narrow vacancy URL prefixes work better than a site-wide detail query for this source. Query within explicit dates and replay indexed detail captures with a bounded request count, a delay between requests, and no live redirects. Keep a JSONL log next to the downloaded content. Each entry needs an HTTP `status`, an `archive_url` recording the actual replay URL for successful requests, and a relative `file` with the downloaded HTML.

```bash
python -m tools.stage_itpro_archive itpro-wayback.csv captures/attempts.jsonl
```

The staging tool checks the ITPro vacancy path and uses the publisher's structured original posting date. Captures must contain the advert text. The output keeps the archive URL, capture time, content SHA-256, and date source alongside each vacancy. It uses the earliest usable capture per vacancy ID supplied to the run.

## Public tracker snapshots

The [Sri Lanka Software Jobs tracker](https://github.com/Senadeera-NK/sri-lanka-software-jobs) versioned its `jobs.json` snapshots. Use a full local clone and pin the tracker revision.

```bash
python -m tools.stage_itpro_tracker /path/to/tracker itpro-tracker.csv \
  --revision e5fcb4240ed8179c105af30b29f8532f55fc0d27
```

The tracker scraper uses ITPro's `mysql_date`, but its date parser can substitute the current time if parsing fails. Staging requires the same complete posting timestamp on at least two distinct observation dates, rejects conflicting timestamps, and saves both snapshot commits. Cross-check overlapping vacancy IDs against original publisher and archived dates before including tracker rows. Tracker coverage also depends on its title and category filters. Keep the discovery cohort available for sensitivity analysis.

## Import and comparison

Review the staging output through the existing historical CSV import and cleaning flow. Compare the resulting vacancy IDs against the master before import so URL aliases cannot duplicate postings or replace newer adverts with archived versions. Retain the staged evidence alongside the cleaned cohort. Mark ambiguous roles for review and record months where the archive had little or no usable coverage.

Keep archived and recent ITPro cohorts identifiable in analysis. Both are affected by availability and archive selection, particularly in months with few surviving ads. The [Mendeley LinkedIn Sri Lanka reference](https://doi.org/10.17632/ptvzzmr86p.1) has historical dates and publisher-provided skill tags. Its raw advert descriptions are unavailable, so it supports a separate descriptive comparison of the supplied tags.
