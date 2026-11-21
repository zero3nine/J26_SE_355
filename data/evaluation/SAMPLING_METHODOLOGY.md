# Sampling Procedure and Stratification Methodology
**Project:** IT Job Market Intelligence Tool (J26_SE_355)  
**Evaluation Dataset:** [benchmark_dataset.csv](benchmark_dataset.csv) (120 records)

---

## 1. Overview and Sampling Objectives

The primary objective of this pilot benchmark dataset is to provide an independently verified reference corpus to evaluate the information extraction fidelity of the scraping system. The benchmark is designed to rigorously stress-test:
1. Structured data parsing (Schema.org `JobPosting` JSON-LD).
2. Site-specific adapters (dedicated DOM / REST API extractors).
3. Generic HTML fallback heuristics.
4. Client-side hydrated SPA rendering.
5. Incomplete, ambiguous, and non-job edge cases.

---

## 2. Target Geographic Scope and Sample Counts

The pilot benchmark covers four target economies in South and Southeast Asia. It contains **120 records across 118 distinct source URLs**, including eight records labeled as negative controls. The table counts records by their assigned benchmark country.

| Country | Sample Count (N) | Percentage (%) | Primary Hubs Covered |
| :--- | :---: | :---: | :--- |
| **Sri Lanka** | 48 | 40.0% | Colombo, Western Province, Kandy, Wattala |
| **India** | 27 | 22.5% | Bangalore, Delhi NCR, Mumbai, Hyderabad, Chennai, Coimbatore |
| **Singapore** | 25 | 20.8% | Central, Downtown Core, Jurong, One-North |
| **Malaysia** | 20 | 16.7% | Kuala Lumpur, Cyberjaya, Penang, Petaling Jaya, Johor Bahru |
| **Total** | **120** | **100.0%** | — |

Keep benchmark IDs unique. Review repeated URLs and their evidence before using the benchmark to count distinct vacancies.

---

## 3. Portal Diversity and Extraction Architecture Coverage

The sample includes 13 source hostnames, counting subdomains separately. The architecture column describes the original sampling context. For current implementation status and fixture coverage, see the [collection issues](../../docs/suggestions.md#current-issues).

| Platform Hostname | Country | Sample (N) | Primary Extraction Architecture |
| :--- | :--- | :---: | :--- |
| `itpro.lk` | Sri Lanka | 42 | Schema.org JSON-LD |
| `topjobs.lk` | Sri Lanka | 2 | Site Adapter (HTML table DOM) |
| `xpress.jobs` | Sri Lanka | 2 | JSON-LD / HTML |
| `ikman.lk` | Sri Lanka | 1 | Microdata / JSON-LD |
| `rooster.jobs` | Sri Lanka | 1 | Generic HTML Search (Negative Control) |
| `www.shine.com` | India | 23 | JSON-LD & Heuristic HTML |
| `recruiter.shine.com` | India | 1 | Landing Page (Negative Control) |
| `resume.shine.com` | India | 1 | Ancillary Service (Negative Control) |
| `www.naukri.com` | India | 2 | Browser-Rendered HTML / Filtered Query |
| `www.mycareersfuture.gov.sg` | Singapore | 25 | REST API Adapter / Browser SPA |
| `my.jobstreet.com` | Malaysia | 12 | Schema.org JSON-LD |
| `my.hiredly.com` | Malaysia | 5 | JSON-LD / Structured HTML |
| `www.techinasia.com` | Malaysia | 3 | Headless Browser Hydration |

### Extraction Method Distribution
- **`jsonld`** (79 records, 65.8%): Schema.org structured metadata.
- **`site_adapter`** (25 records, 20.8%): Specialized site logic (MyCareersFuture REST API and TopJobs legacy parser).
- **`generic_html`** (5 records, 4.2%): Unstructured heuristic extraction.
- **`browser_rendered`** (3 records, 2.5%): Playwright-rendered single-page applications.
- **`none`** (8 records, 6.7%): Intentionally sampled non-job pages, search aggregators, and error pages to test negative rejection.

---

## 4. Ordinary Cases vs. Challenging Edge Cases

The sampling design deliberately includes both straightforward listings and complex edge cases:

### A. Missing & Undisclosed Salaries
In Sri Lanka and India, many IT advertisements omit explicit salary ranges. These records test whether the extractor correctly marks compensation as undisclosed without inventing placeholder values or coercing missing figures to zero.
- *Benchmark behavior:* `expected_salary_disclosed: False`, `status_salary: verified`.

### B. Transparent Monthly & Annual Salary Ranges
- **Singapore (`mycareersfuture.gov.sg`):** Mandatory disclosed monthly salary ranges in SGD (e.g., `$4,000 - $6,000 monthly`).
- **India (`shine.com`):** Annual CTC compensation in INR or Lakhs Per Annum (e.g., `50000 - 300000 INR per YEAR`, `18-24 Lacs P.A.`).
- **Malaysia (`jobstreet.com.my`):** Monthly salary ranges in Malaysian Ringgit (e.g., `RM 9,000 - RM 15,000 per month`).

### C. Multi-Location and Ambiguous Geographies
- Multi-city listings: e.g., `Bangalore, Karnataka, IN; Coimbatore, Tamil Nadu, IN` (DIRAA HR Services).
- Sub-regional urban clusters: e.g., `Wattala / Wellawatte` (Fashionxpo.lk).
- Federal Territories and special administrative zones: e.g., `Cyberjaya, Selangor` vs. `Kuala Lumpur`.

### D. Unusual Date Formats & Timezones
- ISO 8601 with explicit timezone offsets: `2026-10-19T19:43:20+05:30` (Sri Lanka standard time).
- Plain date formats: `2026-10-20` (Singapore MCF).
- Relative dates and ambiguous postings: Marked as `ambiguous` to test whether the system avoids fabricating historical dates.

### E. Negative Controls and Non-Job Pages
- Session expired and server error pages (`topjobs.lk/applicant/errorPage.do`).
- Commercial landing pages (`recruiter.shine.com`, `resume.shine.com`).
- Filtered search listings (`naukri.com/high-salary-jobs`, `rooster.jobs/?query=...`).
- Category listings (`itpro.lk/jobs/quality-assurance/fulltime/`).

---

## 5. Sampling Limitations and Representativeness Warning

> [!CAUTION]
> This stratified convenience sample measures extraction agreement on the selected records. Market-wide vacancy counts, wages, and cross-country economic comparisons require a separate sampling design.
