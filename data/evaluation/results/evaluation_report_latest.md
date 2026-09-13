# Information Extraction Quality & Benchmark Evaluation Report
**Project:** IT Job Market Intelligence Tool (J26_SE_355)  
**Evaluation Timestamp (UTC):** `2026-10-20T11:19:48Z`  
**Benchmark Dataset:** `/Users/gavidurushela/Research/tool/J26_SE_355/data/evaluation/benchmark_dataset.csv`  
**Predictions Source:** `/Users/gavidurushela/Research/tool/J26_SE_355/data/raw/all_pilot_crawled_predictions.csv`  
**Record Alignment Strategy:** `auto`  
**Unit of Analysis:** Individual Job Advertisement (with intra-record field clustering)  

---

## 1. Executive Summary & Core Quality Scorecard

> [!IMPORTANT]
> **Coverage vs. Correctness Distinction:**
> - **Extraction Coverage (Completeness):** Proportion of eligible reference values captured by the scraper.
> - **Extraction Correctness (Precision):** Proportion of captured predictions that are factually accurate.
> A system that extracts very few values cannot appear reliable merely because its few predictions happen to be accurate.

| Evaluation Dimension | Metric Value | 95% Confidence Interval | Scientific Interpretation |
| :--- | :---: | :---: | :--- |
| **Benchmark Corpus** | `120` ads | N/A | Total independently verified reference advertisements |
| **Predictions Ingested** | `106` ads | N/A | Total candidate scraper output records |
| **Aligned Evaluations** | `120` ads | N/A | Successfully joined record pairs |
| **Unmatched Benchmark Ads** | `29` ads | N/A | Benchmark vacancies missing from prediction file |
| **Extra Predictions** | `17` ads | N/A | Scraper predictions without benchmark ground truth |
| **Exact Match Advertisements** | `4` / `120` (`3.33%`) | [1.3%, 8.3%] | Advertisements where **all** verified fields are extracted correctly and absent fields omitted |
| **Macro Extraction Coverage** | `56.53%` | N/A | Average field completeness across eligible reference attributes |
| **Macro Extraction Correctness** | `73.96%` | N/A | Average conditional accuracy when an attribute was captured |
| **Macro Recall (Unconditional)** | `45.10%` | N/A | Overall capture rate of ground-truth reference values |
| **Macro F1-Score** | `54.90%` | N/A | Harmonic mean of macro precision and recall |

## 2. Field-by-Field Agreement and Quality Matrix

| Evaluated Field | Eligible (N) | Matched Preds | Correct (TP) | Incorrect | Missing (FN) | Exact Agree % | Norm Agree % | 95% Wilson CI | Coverage % | Correctness % | Unavail (N) | Hallucination % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `job_title` | 112 | 87 | 87 | 0 | 25 | 77.7% | 77.7% | [69.1%, 84.4%] | 77.7% | 100.0% | 8 | 25.0% |
| `employer` | 112 | 87 | 87 | 0 | 25 | 76.8% | 77.7% | [69.1%, 84.4%] | 77.7% | 100.0% | 8 | 25.0% |
| `country` | 112 | 74 | 74 | 0 | 38 | 0.0% | 66.1% | [56.9%, 74.2%] | 66.1% | 100.0% | 8 | 0.0% |
| `location` | 112 | 74 | 73 | 1 | 38 | 65.2% | 65.2% | [56.0%, 73.4%] | 66.1% | 98.7% | 8 | 0.0% |
| `work_mode` | 112 | 14 | 9 | 5 | 98 | 8.0% | 8.0% | [4.3%, 14.6%] | 12.5% | 64.3% | 8 | 0.0% |
| `posting_date` | 112 | 87 | 87 | 0 | 25 | 20.5% | 77.7% | [69.1%, 84.4%] | 77.7% | 100.0% | 8 | 0.0% |
| `closing_date` | 14 | 1 | 0 | 1 | 13 | 0.0% | 0.0% | [0.0%, 21.5%] | 7.1% | 0.0% | 106 | 81.1% |
| `job_description` | 112 | 87 | 2 | 85 | 25 | 0.0% | 1.8% | [0.5%, 6.3%] | 77.7% | 2.3% | 8 | 25.0% |
| `salary_disclosed` | 112 | 87 | 87 | 0 | 25 | 77.7% | 77.7% | [69.1%, 84.4%] | 77.7% | 100.0% | 8 | 0.0% |
| `salary_min` | 112 | 34 | 34 | 0 | 25 | 77.7% | 30.4% | [22.6%, 39.4%] | 30.4% | 100.0% | 8 | 0.0% |
| `salary_max` | 112 | 34 | 34 | 0 | 25 | 77.7% | 30.4% | [22.6%, 39.4%] | 30.4% | 100.0% | 8 | 0.0% |
| `currency` | 100 | 34 | 34 | 0 | 66 | 34.0% | 34.0% | [25.5%, 43.7%] | 34.0% | 100.0% | 20 | 0.0% |
| `pay_period` | 59 | 34 | 34 | 0 | 25 | 37.3% | 57.6% | [44.9%, 69.4%] | 57.6% | 100.0% | 61 | 93.4% |
| `skills` | 21 | 1 | 0 | 1 | 20 | 0.0% | 0.0% | [0.0%, 15.5%] | 4.8% | 0.0% | 7 | 0.0% |

## 3. Numeric Salary Error Analysis

> [!NOTE]
> **Currency and Pay-Period Compatibility Policy:**
> Monetary bounds are only compared when currency and pay period match. Incompatible pairs are excluded from numeric error metrics and tracked separately.

| Metric | Salary Minimum | Salary Maximum |
| :--- | :---: | :---: |
| **Comparable Evaluated Pairs** | `34` | `34` |
| **Mean Absolute Error (MAE)** | `0.00` | `0.00` |
| **Median Absolute Error (MedAE)** | `0.00` | `0.00` |
| **Excluded Incompatible Pairs** | `0` | `0` |
| **Excluded Unavailable References** | `8` | `8` |

## 4. Canonical Skill Extraction Evaluation (Multi-Label)

- **Evaluated Advertisements with Verified Skills:** 21
- **Micro-Averaged Precision:** 0.00% | **Recall:** 0.00% | **F1:** 0.00%
- **Macro-Averaged Precision:** 0.00% | **Recall:** 0.00% | **F1:** 0.00%

### Top Per-Label Skill Performance

| Canonical Skill Label | Support (N) | Precision | Recall | F1-Score |
| :--- | :---: | :---: | :---: | :---: |
| `cloud architecture` | 1 | 0.0% | 0.0% | 0.0% |
| `kubernetes` | 1 | 0.0% | 0.0% | 0.0% |
| `python` | 1 | 0.0% | 0.0% | 0.0% |

## 5. Regional Stratification Analysis

| Country | Sample (N) | Exact Match Ads | Exact Match % | 95% Wilson CI | Title Agreement | Employer Agreement | Work Mode Agreement | Statistical Caveat |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **India** | 27 | 0 | 0.0% | [0.0%, 12.5%] | 95.8% | 95.8% | 0.0% | Adequate pilot sample |
| **Malaysia** | 20 | 1 | 5.0% | [0.9%, 23.6%] | 0.0% | 0.0% | 0.0% | Adequate pilot sample |
| **Singapore** | 25 | 1 | 4.0% | [0.7%, 19.5%] | 95.8% | 95.8% | 0.0% | Adequate pilot sample |
| **Sri Lanka** | 48 | 2 | 4.2% | [1.1%, 14.0%] | 91.1% | 91.1% | 20.0% | Adequate pilot sample |

## 6. Extraction Architecture and Platform Analysis

| Extraction Method | Evaluated (N) | Exact Match Ads | Exact Match % | 95% Wilson CI | Method Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `browser_rendered` | 3 | 0 | 0.0% | [0.0%, 56.1%] | Headless browser DOM hydration for SPAs |
| `generic_html` | 5 | 0 | 0.0% | [0.0%, 43.5%] | Heuristic fallback across HTML selectors |
| `jsonld` | 79 | 0 | 0.0% | [0.0%, 4.6%] | Schema.org structured metadata |
| `none` | 8 | 4 | 50.0% | [21.5%, 78.5%] | Negative controls (error / search pages) |
| `site_adapter` | 25 | 0 | 0.0% | [0.0%, 13.3%] | Tailored REST API / portal adapter |

## 7. Error Taxonomy & Qualitative Diagnostics

### Most Frequent Error Categories

| Error Category | Frequency (N) | Description |
| :--- | :---: | :--- |
| `unmatched_record_missing` | 458 | Primary classification of extraction discrepancy |
| `incorrect_text_value` | 177 | Primary classification of extraction discrepancy |
| `missing_prediction` | 153 | Primary classification of extraction discrepancy |
| `hallucinated_date` | 86 | Primary classification of extraction discrepancy |
| `hallucination_on_unavailable_field` | 67 | Primary classification of extraction discrepancy |
| `date_mismatch` | 1 | Primary classification of extraction discrepancy |

### Diagnostic Sample of Extraction Failures

| Benchmark ID | Field | Expected Ground Truth | Predicted Value | Error Details |
| :--- | :--- | :--- | :--- | :--- |
| `BM-LK-ITPRO-001` | `work_mode` | `hybrid` | `` | Expected verified 'hybrid', but prediction was empty. |
| `BM-LK-ITPRO-001` | `closing_date` | `` | `2027-01-17T23:59:59+05:30` | Date unavailable in source but prediction extracted: '2027-01-17T23:59:59+05:30' |
| `BM-LK-ITPRO-001` | `job_description` | `<p>Contribute to designing, develop` | `<p>Contribute to designing, develop` | Mismatch: expected 'p contribute to designing developing testing and maintaining high quality software solutions under the guidance of experienced engineers p p at bitsliz' != predicted 'p contribute to designing developing testing and maintaining high quality software solutions under the guidance of experienced engineers p p at bitslize you ll build products spanning al powered business solutions enterprise platforms workflow automation analytics and mobile applications while working with organizations across diverse industries to solve real business challenges and drive digital transformation p p requirements p ul li knowledge of frontend and or backend development li li familiarity with software design concepts and system integrations li li understanding of databases and rest apis li li currently based in sri lanka and available for local interviews and onboarding li li ability to work from home hybrid setup li ul' |
| `BM-LK-ITPRO-001` | `description` | `<p>Contribute to designing, develop` | `<p>Contribute to designing, develop` | Mismatch: expected 'p contribute to designing developing testing and maintaining high quality software solutions under the guidance of experienced engineers p p at bitsliz' != predicted 'p contribute to designing developing testing and maintaining high quality software solutions under the guidance of experienced engineers p p at bitslize you ll build products spanning al powered business solutions enterprise platforms workflow automation analytics and mobile applications while working with organizations across diverse industries to solve real business challenges and drive digital transformation p p requirements p ul li knowledge of frontend and or backend development li li familiarity with software design concepts and system integrations li li understanding of databases and rest apis li li currently based in sri lanka and available for local interviews and onboarding li li ability to work from home hybrid setup li ul' |
| `BM-LK-ITPRO-001` | `currency` | `LKR` | `` | Expected verified 'LKR', but prediction was empty. |
| `BM-LK-ITPRO-001` | `pay_period` | `` | `` | Field unavailable in source but prediction extracted: '' |
| `BM-LK-ITPRO-002` | `work_mode` | `on_site` | `` | Expected verified 'on_site', but prediction was empty. |
| `BM-LK-ITPRO-002` | `closing_date` | `` | `2027-01-17T23:59:59+05:30` | Date unavailable in source but prediction extracted: '2027-01-17T23:59:59+05:30' |

## 8. Methodological Scope & Statistical Caveats

1. **Unit of Analysis:** The unit of analysis is the individual job vacancy advertisement. Attribute evaluations within an advertisement are correlated and must not be treated as independent Bernoulli trials.
2. **Convenience Sample Limitations:** This benchmark evaluates extraction engine correctness against authentic web sources. It does not establish the true macroeconomic distribution of job openings or wages across South and Southeast Asia.
3. **Source Drift & Ephemerality:** In the event of source web page expiration, the locally preserved evidence snapshot serves as the definitive reference standard.
