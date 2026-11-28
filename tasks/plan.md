# TopJobs historical backfill design

## Research objective

Recover historical Sri Lankan IT job advertisements with a verifiable original opening date and enough advert text to extract skills. The earlier archive check found 2,275 vacancy IDs in a TopJobs homepage capture from 4 January 2024. Both sampled detail URLs returned 404, and the detail index query timed out. Listing discovery and usable advert recovery therefore need separate measurements.

Start with a TopJobs-only feasibility pilot. A proposed starting sample is Q2 2020, Q2 2022, Q1 2024, and Q4 2025, with up to two distinct listing dates and 25 unique vacancies per quarter. Include the known 2024 capture as a diagnostic alongside the category seeds. Set a fixed sampling order, request budget, and per-vacancy attempt cap in the run configuration. Record missing periods and report the homepage diagnostic separately from the category sample. [TopJobs software and QA listings](https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=SDQ&jst=OPEN) · [TopJobs hardware and networking listings](https://topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=HNS&jst=OPEN)

## What to implement

### 1. Query the archive and discover listings

Add an opt-in CLI backed by a small Wayback client and archive-specific orchestration in `src/scraping/`. Query CDX by approved TopJobs URL variants and date windows. Save the original URL, indexed timestamp, status, MIME type, and digest. Keep bounded pagination and resume tokens. Reuse `parse_topjobs_listing_html` and the TopJobs link extractor where historical fixtures match. Add archive-specific parsing for demonstrated layout differences. Extract the vacancy number, detail URL candidates, title, employer, category, and explicit opening and closing dates. Resolve listing links against the original TopJobs URL and send the resulting approved targets through Wayback replay. [Wayback CDX API](https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server#readme)

### 2. Recover advert text and measure yield

For each sampled vacancy, look up archived detail URL candidates using the observed servlet parameters and verified scheme, host, and URL variants. Rank captures near the listing timestamp, then validate the replayed vacancy's identity and record its actual capture time. Reuse the TopJobs detail extractor for supported HTML and the existing OCR pipeline for captured flyers. Resolve flyer URLs from the archived detail page and retrieve them from the archive. Keep the listing description as evidence when it contains substantive requirements. Queue uncertain OCR or conflicting identities for review.

Write a resumable local manifest, staged records, and a coverage report. Save query parameters, attempted and actual replay URLs, timestamps, content digests, parser version, result status, date evidence, and text source. Separate access denials, rate limits, timeouts, missing captures, wrong-identity or soft-404 replays, missing flyers, unreadable text, and unverified dates. Measure distinct listing references, replayable details, usable HTML or OCR text, verifiable dates, and vacancies with both date and text by quarter and category. Include attempt counts and a manual check of sampled successes and failures. [Internet Archive APIs](https://archive.org/help/wayback_api.php)

### 3. Stage a reviewed cohort if the pilot supports it

Use the normalized TopJobs vacancy reference as the staged identity. Retain the original vacancy URL, archive URLs for each evidence item, and capture timestamps separately. Review collisions and potential reposts instead of merging by title and employer alone. The master currently matches trimmed source URLs, so identify existing TopJobs matches by vacancy reference first and reuse the stored URL where the match is unambiguous. Send ambiguous matches and conflicts between older archive content and a newer master record to review. Keep repeat captures in the evidence manifest and consolidate them into one candidate posting.

Feed reviewed rows through the existing historical import and cleaning flow. Preserve explicit opening dates, original date strings, and their evidence. For relative dates, require documented rules and corroboration before eligibility. Exclude capture-only, closing-date-only, conflicting, and missing dates from temporal analysis. Retain requirements text and evidence for reviewed ads with zero extracted skills. Prove the reviewed import is idempotent in a temporary master by importing it twice and checking job and version counts, including a case where a vacancy already exists under a different URL.

## Risks and controls

| Risk | Control |
| --- | --- |
| Capture gaps, missing assets, or a detail replay from a different time | Record attempted and actual timestamps for listing, detail, and flyer. Check identity and date coherence. Keep partial records for the coverage report. |
| Archive load and access restrictions | Use one request at a time initially, a configurable delay, bounded retries with backoff and `Retry-After`, and explicit page, byte, redirect, and time limits. Respect denials and archive exclusions. |
| Redirects or archived content pulling live or arbitrary URLs | Use verified HTTPS, validate both the archive transport and embedded original URL, and scope redirects to approved archive replay and original hosts. Parse HTML without executing scripts. Fetch only approved archived advert assets with bounded sizes. |
| Layout changes and OCR errors | Test with redacted fixtures covering date columns, JavaScript-linked IDs, soft 404s, flyers, and conflicting identities. Manually audit date parsing and OCR on sampled ads. |
| Open listings repeat across captures and coverage varies by occupation and period | Deduplicate by posting, report attrition for each sampled period, and treat gaps as missing observations. Use a source-specific cohort and report coverage before comparing months or splicing in other sources. |
| Category labels include unrelated roles or titles omit requirements | Review IT eligibility and whether the advert contains usable job content. Record exclusions and preserve eligible ads with zero skill mentions. |

## Decision after the pilot

Review usable date-and-text yield, manual audit agreement, request cost, and the distribution by original posting month. Expand only where observed coverage can support the intended unit of analysis. If usable months are sparse, report pooled or quarterly exploratory results where supported and look for a historical export for longitudinal work. The pilot is complete once the coverage and failure report supports a decision, including a result with zero usable ads.

Implementation order and verification are in the [task checklist](todo.md).
