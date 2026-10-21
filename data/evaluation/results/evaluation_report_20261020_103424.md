# Information Extraction Benchmark Evaluation Report
**Project:** IT Job Market Intelligence Tool (J26_SE_355)  
**Evaluation Timestamp (UTC):** `2026-10-20T10:34:24Z`  
**Benchmark Dataset:** `/Users/gavidurushela/Research/tool/J26_SE_355/data/evaluation/benchmark_dataset.csv`  
**Predictions Source:** `/Users/gavidurushela/Research/tool/J26_SE_355/data/raw/all_pilot_crawled_predictions.csv`  
**Record Alignment Strategy:** `auto`  

---

## 1. Executive Summary & Core Extraction Metrics

| Metric | Value | Description |
| :--- | :--- | :--- |
| **Benchmark Records** | `120` | Total independently verified ground truth advertisements |
| **Predictions Loaded** | `106` | Total raw or cleaned scraping output records |
| **Matched Evaluations** | `120` | Records aligned for independent field-by-field evaluation |
| **Unmatched Benchmark Records** | `29` | Verified advertisements absent from prediction file |
| **Extra Predictions** | `17` | Prediction records not present in the benchmark dataset |
| **Exact Match Advertisements** | `6` / `120` (`5.00%`) | Advertisements where all verified fields were extracted correctly |
| **Macro Precision** | `56.75%` | Unweighted average precision across verified extraction fields |
| **Macro Recall** | `36.45%` | Unweighted average extraction recall across verified fields |
| **Macro F1-Score** | `42.70%` | Harmonic mean of macro precision and recall |

## 2. Field-by-Field Quality & Verification Matrix

> [!NOTE]
> Reference statuses strictly distinguish verified, unavailable, and ambiguous source data.
> Missing source information is never interpreted as a confirmed value.

| Field | Verified (N) | Correct (TP) | Incorrect | Missing (FN) | Precision | Recall | F1 | Unavail (N) | Correct Absent (TN) | Over-Extracted (FP) | Hallucination Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `job_title` | 112 | 87 | 0 | 25 | 100.0% | 77.7% | 87.4% | 8 | 6 | 2 | 25.0% |
| `company` | 112 | 86 | 1 | 25 | 98.9% | 76.8% | 86.4% | 8 | 6 | 2 | 25.0% |
| `location_raw` | 112 | 73 | 1 | 38 | 98.7% | 65.2% | 78.5% | 8 | 8 | 0 | 0.0% |
| `country_normalized` | 112 | 0 | 74 | 38 | 0.0% | 0.0% | 0.0% | 8 | 8 | 0 | 0.0% |
| `city_normalized` | 112 | 0 | 0 | 112 | 0.0% | 0.0% | 0.0% | 8 | 8 | 0 | 0.0% |
| `work_mode` | 112 | 9 | 5 | 98 | 64.3% | 8.0% | 14.3% | 8 | 8 | 0 | 0.0% |
| `posted_date` | 112 | 87 | 0 | 25 | 100.0% | 77.7% | 87.4% | 8 | 8 | 0 | 0.0% |
| `closing_date` | 14 | 0 | 1 | 13 | 0.0% | 0.0% | 0.0% | 106 | 20 | 86 | 81.1% |
| `description` | 112 | 85 | 2 | 25 | 97.7% | 75.9% | 85.4% | 8 | 6 | 2 | 25.0% |
| `salary` | 112 | 22 | 12 | 25 | 64.7% | 19.6% | 30.1% | 8 | 8 | 0 | 0.0% |
| `skills` | 21 | 0 | 1 | 20 | 0.0% | 0.0% | 0.0% | 7 | 7 | 0 | 0.0% |

## 3. Regional Stratification Analysis

| Country | Sample (N) | Exact Match Ads | Exact Match % | Title F1 | Company F1 | Salary Disclosed F1 | Work Mode F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **India** | 27 | 1 | 3.7% | 97.9% | 93.6% | 0.0% | 0.0% |
| **Malaysia** | 20 | 1 | 5.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **Singapore** | 25 | 1 | 4.0% | 97.9% | 97.9% | 93.6% | 0.0% |
| **Sri Lanka** | 48 | 3 | 6.2% | 95.3% | 95.3% | 0.0% | 31.0% |

## 4. Extraction Method and Portal Breakdown

### Extraction Architecture Comparison

| Extraction Method | Evaluated Records (N) | Exact Match Records | Exact Match Rate | Method Description |
| :--- | :---: | :---: | :---: | :--- |
| `browser_rendered` | 3 | 0 | 0.0% | Headless browser DOM hydration for SPAs |
| `generic_html` | 5 | 0 | 0.0% | Heuristic fallback across unstructured HTML |
| `jsonld` | 79 | 0 | 0.0% | Schema.org JobPosting structured metadata |
| `none` | 8 | 6 | 75.0% | Failed or unextracted pages |
| `site_adapter` | 25 | 0 | 0.0% | Portal-tailored DOM / REST API extraction |

### Source Platform Breakdown

| Platform Hostname | Sample (N) | Exact Match Rate | Primary Country |
| :--- | :---: | :---: | :--- |
| `ikman.lk` | 1 | 0.0% | Sri Lanka |
| `itpro.lk` | 42 | 2.4% | Sri Lanka |
| `my.hiredly.com` | 5 | 0.0% | Malaysia |
| `my.jobstreet.com` | 12 | 0.0% | Malaysia |
| `recruiter.shine.com` | 1 | 0.0% | India |
| `resume.shine.com` | 1 | 0.0% | India |
| `rooster.jobs` | 1 | 100.0% | Sri Lanka |
| `topjobs.lk` | 2 | 50.0% | Sri Lanka |
| `www.mycareersfuture.gov.sg` | 25 | 4.0% | Singapore |
| `www.naukri.com` | 2 | 50.0% | India |
| `www.shine.com` | 23 | 0.0% | India |
| `www.techinasia.com` | 3 | 33.3% | Malaysia |
| `xpress.jobs` | 2 | 0.0% | Sri Lanka |

## 5. Qualitative Error Taxonomy & Failure Case Analysis

- **Value Discrepancies (Incorrect extractions):** 97
- **Omissions (Missing predictions for verified fields):** 444
- **Over-extractions (Hallucinations on unavailable fields):** 92

#### Sample Value Discrepancies

| Benchmark ID | Field | Expected Ground Truth | System Prediction | Discrepancy Reason |
| :--- | :--- | :--- | :--- | :--- |
| `BM-LK-ITPRO-001` | `country_normalized` | `Sri Lanka` | `LK` | Mismatch: expected 'Sri Lanka' != predicted 'LK' |
| `BM-LK-ITPRO-002` | `country_normalized` | `Sri Lanka` | `LK` | Mismatch: expected 'Sri Lanka' != predicted 'LK' |
| `BM-LK-ITPRO-003` | `country_normalized` | `Sri Lanka` | `LK` | Mismatch: expected 'Sri Lanka' != predicted 'LK' |
| `BM-LK-ITPRO-004` | `country_normalized` | `Sri Lanka` | `LK` | Mismatch: expected 'Sri Lanka' != predicted 'LK' |
| `BM-LK-ITPRO-005` | `work_mode` | `hybrid` | `remote` | Mismatch: expected 'hybrid' != predicted 'remote' |
| `BM-LK-ITPRO-006` | `country_normalized` | `Sri Lanka` | `LK` | Mismatch: expected 'Sri Lanka' != predicted 'LK' |

## 6. Source Ambiguities & Methodological Limitations

1. **Convenience Sample Scope:** This pilot benchmark of independently audited job advertisements provides rigorous point validation for extraction heuristics. It does not establish statistical representativeness of entire national labor markets.
2. **Separation from Operational Pipelines:** Reference benchmark labels are strictly stored in `data/evaluation/` and must never be fed into scraping queues or used for dynamic threshold calibration.
3. **Irreducible Ambiguity:** Source pages with indeterminate locations (e.g., 'Remote / APAC') or unanchored relative dates ('Recently added') are flagged as `ambiguous` and excluded from strict accuracy denominators.
