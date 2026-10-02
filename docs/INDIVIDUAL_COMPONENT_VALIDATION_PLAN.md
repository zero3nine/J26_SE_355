# Individual Research Component: Practical Validation Protocol & Benchmark Plan

**Project ID:** J26-SE-355  
**Component:** Quantitative Analysis Framework for Technical Skill Identification for IT Sector Jobs: Comparative Regional Market Analysis  
**Student Name:** E. M. G. R. Ekanayaka  
**Student ID:** IT23213944  
**Date of Plan:** October 2026  
**Document Status:** Operational Quality Benchmark & Validation Protocol  

---

## 1. Executive Protocol Purpose

This document establishes the practical, operational validation plan to address supervisor feedback:

> *"Think about the accuracy of foreign websites when scraping data. The Indian job market can have a bigger impact. Need to think about delivering accurate results for the user. How to validate the scraped data."*

The protocol guarantees that data scraped from foreign job portals (India, Singapore, Malaysia) and the focal domestic market (Sri Lanka) is audited against independently reviewed reference evidence before being consumed by comparative statistical models.

---

## 2. Distinction of Quality Dimensions

To prevent misleading aggregation, five distinct quality dimensions are evaluated independently:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Extraction Accuracy    │ Extracted fields match the original source page │
├───────────────────────────┼─────────────────────────────────────────────────┤
│ 2. Record Validity        │ Data conforms to schema constraints and types   │
├───────────────────────────┼─────────────────────────────────────────────────┤
│ 3. Job Authenticity       │ Advertisement originates from a verified entity │
├───────────────────────────┼─────────────────────────────────────────────────┤
│ 4. Current Availability   │ Vacancy remains open and active at audit time   │
├───────────────────────────┼─────────────────────────────────────────────────┤
│ 5. Analytical Reliability │ Dataset meets sample size & power requirements  │
└─────────────────────────────────────────────────────────────────────────────┘
```

A record that fails Availability (e.g. expired vacancy) is **not** an extraction error. Similarly, an unstated salary is **not** an invalid record.

---

## 3. Stratified Sampling Procedure

To ensure representative coverage without portal or role bias, benchmark samples must be drawn according to a stratified protocol:

### 3.1 Stratification Matrix Targets

```text
Market Hub        Focal / Comparator    Target Sample    Primary Source Portals               Target Role Quota
Sri Lanka (LK)    Focal Baseline             80          topjobs.lk, itpro.lk, xpress.jobs    Dev: 40%, QA: 15%, Infra: 20%, Other: 25%
India (IN)        Primary Comparator         80          shine.com, timesjobs.com             Dev: 40%, QA: 15%, Infra: 20%, Other: 25%
Singapore (SG)    Advanced ASEAN Hub         50          mycareersfuture.gov.sg               Dev: 40%, QA: 15%, Infra: 20%, Other: 25%
Malaysia (MY)     Emerging ASEAN Hub         50          my.hiredly.com, techinasia.com       Dev: 40%, QA: 15%, Infra: 20%, Other: 25%
Total Target                                260          Multi-portal representation
```

### 3.2 Random Selection Sampling Protocol
1. **Deduplication:** Group candidate URLs by canonical domain and path; eliminate exact duplicates.
2. **Quota Partitioning:** Sort candidate postings into 12 canonical occupational roles using [`src/roles/classifier.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/roles/classifier.py).
3. **Random Draw:** Sample uniformly within each (Country, Role) stratum using a fixed random seed (`seed = 42`) for audit reproducibility.
4. **Snapshot Capture:** For each sampled vacancy, capture and store the raw HTML snapshot into [`data/evaluation/evidence/snapshots/`](file:///Users/gavidurushela/Research/tool/J26_SE_355/data/evaluation/evidence/) alongside its SHA-256 hash.

---

## 4. Ground-Truth Benchmark Data Schema

Reference datasets must conform to the 38-column specification defined in [`src/evaluation/schema.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/schema.py):

| Column Name | Data Type | Permitted Values / Description |
| :--- | :---: | :--- |
| `benchmark_id` | `string` | Unique identifier (e.g. `BM-IN-SHINE-001`, `BM-LK-TOP-012`). |
| `source_url` | `string` | Full canonical URL of original advertisement. |
| `source_platform` | `string` | Hostname (e.g. `www.shine.com`, `itpro.lk`). |
| `country` | `string` | Target market (`Sri Lanka`, `India`, `Singapore`, `Malaysia`). |
| `collection_context` | `string` | Crawl context (`production_pilot`, `offline_fixture`). |
| `extraction_method` | `string` | Extractor evaluated (`site_adapter`, `jsonld`, `generic_html`). |
| `expected_job_title_raw` | `string` | Verbatim job title from page. |
| `expected_company_raw` | `string` | Verbatim employer / organization name. |
| `expected_location_raw` | `string` | Verbatim location string from advertisement. |
| `expected_country_normalized` | `string` | Standard country name (`Sri Lanka`, `India`, `Singapore`, `Malaysia`). |
| `expected_city_normalized` | `string` | Standard city or state name (e.g. `Bengaluru`, `Colombo`, `Singapore`). |
| `expected_work_mode` | `string` | `remote`, `hybrid`, `on_site`, `unspecified`. |
| `expected_posted_date` | `string` | ISO 8601 date (`YYYY-MM-DD`) or empty if unstated. |
| `expected_closing_date` | `string` | ISO 8601 date (`YYYY-MM-DD`) or empty if unstated. |
| `expected_description_snippet`| `string` | First 250 characters of clean plain text description. |
| `expected_description_hash` | `string` | SHA-256 hash of normalized full description body. |
| `expected_description_min_len`| `integer`| Minimum acceptable description character length. |
| `expected_salary_disclosed` | `boolean` | `True` if compensation disclosed; `False` if unstated. |
| `expected_salary_text_raw` | `string` | Verbatim compensation string (e.g. `5 - 10 Lakhs PA`). |
| `expected_salary_type` | `string` | `range`, `single_value`, `undisclosed`, `unparseable`. |
| `expected_salary_min` | `float` | Minimum numeric compensation (in local currency). |
| `expected_salary_max` | `float` | Maximum numeric compensation (in local currency). |
| `expected_salary_currency` | `string` | Standard currency token (`LKR`, `INR`, `SGD`, `MYR`, `USD`). |
| `expected_salary_period` | `string` | `hourly`, `daily`, `monthly`, `annual`, `unspecified`. |
| `expected_skills` | `JSON list` | Verified list of canonical skill IDs (e.g. `["python", "docker"]`). |
| `status_job_title` | `string` | `verified`, `unavailable`, `ambiguous`, `not_reviewed`. |
| `status_company` | `string` | `verified`, `unavailable`, `ambiguous`, `not_reviewed`. |
| `status_location` | `string` | `verified`, `unavailable`, `ambiguous`, `not_reviewed`. |
| `status_work_mode` | `string` | `verified`, `unavailable`, `ambiguous`, `not_reviewed`. |
| `status_posted_date` | `string` | `verified`, `unavailable`, `ambiguous`, `not_reviewed`. |
| `status_closing_date` | `string` | `verified`, `unavailable`, `ambiguous`, `not_reviewed`. |
| `status_description` | `string` | `verified`, `unavailable`, `ambiguous`, `not_reviewed`. |
| `status_salary` | `string` | `verified`, `unavailable`, `ambiguous`, `not_reviewed`. |
| `status_skills` | `string` | `verified`, `unavailable`, `ambiguous`, `not_reviewed`. |
| `verification_timestamp` | `string` | ISO 8601 UTC datetime of verification. |
| `verified_by` | `string` | Researcher or adjudicator identifier. |
| `evidence_source` | `string` | File path or URL to evidence snapshot. |
| `reviewer_notes` | `string` | Qualitative notes detailing layout edge cases or ambiguity. |

---

## 5. Field-Level Comparison & Normalization Rules

Implemented in [`src/evaluation/comparator.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/comparator.py):

### 5.1 Text Fields (Job Title, Employer)
- **Exact Agreement:** Case-sensitive string equality after stripping leading/trailing whitespace.
- **Normalized Agreement:** Lowercased, punctuation stripped, corporate suffixes removed (`Pvt Ltd`, `LLC`, `Inc`, `Corp`, `Sdn Bhd`).
- **Acceptance Rule:** If normalized agreement $\ge 85.0\%$ and exact agreement $\ge 75.0\%$, the field passes.

### 5.2 Geographic Fields (Country, Location)
- **Country:** Evaluated against canonical country mapping ([`src/analytics/regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py#L143)). 2-letter ISO codes (`LK`, `IN`, `SG`, `MY`) must map to canonical names.
- **Location:** City and state names mapped using gazetteer regex rules. Compound locations (`Bengaluru / Hyderabad`) must retain primary hub without throwing unparseable errors.

### 5.3 Work Mode (Remote, Hybrid, On-Site)
- **Rule B Enforcement:** If location or text is empty, the expected status is `unspecified`. A scraper must **never** infer remote work from missing location strings.
- **Agreement:** Strict categorical match across `remote`, `hybrid`, `on_site`, `unspecified`.

### 5.4 Dates (Posted Date, Closing Date)
- **Normalization:** Converted to ISO `YYYY-MM-DD`.
- **Hallucination Guard:** If ground-truth closing date is `unavailable`, extracting any date value is flagged as a `hallucinated_date` error.

### 5.5 Numeric Compensation (Salary Bounds)
- **Compatibility Guard:** Predictions are only compared when normalized currency and pay period match reference labels.
- **Error Metric:** Mean Absolute Error (MAE) and Median Absolute Error (MedAE):
  $$\text{MAE} = \frac{1}{M} \sum_{i=1}^{M} |\hat{y}_i - y_i|$$
- **Lakhs Conversion:** `1 Lakh = 100,000 INR`. Verified against numeric amounts.

### 5.6 Technical Skills (Multi-Label Set Comparison)
- Evaluated as a multi-label set of canonical skill IDs.
- For each advertisement $i$, compare reference set $R_i$ with predicted set $P_i$:
  $$\text{Precision} = \frac{|R_i \cap P_i|}{|P_i|}, \quad \text{Recall} = \frac{|R_i \cap P_i|}{|R_i|}, \quad F_1 = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
- Report both Micro-averaged (overall skill pool) and Macro-averaged (per-skill average) metrics.

---

## 6. Statistical Metric Formulations

### 6.1 Wilson Score 95% Confidence Interval for Proportions
For observed successes $k$ in sample size $n$ ($p = k/n$):
$$\text{CI}_{95\%} = \frac{p + \frac{z^2}{2n} \pm z \sqrt{\frac{p(1-p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}} \quad (z = 1.96)$$
Wilson score intervals are robust for small sample sizes ($n < 30$) and extreme proportions near $0\%$ or $100\%$.

### 6.2 Extraction Coverage vs. Extraction Correctness
- **Extraction Coverage (Completeness):**
  $$\text{Coverage} = \frac{\text{Eligible References with Non-Empty Prediction}}{\text{Total Eligible References}}$$
- **Extraction Correctness (Precision):**
  $$\text{Correctness} = \frac{\text{Correct Predictions}}{\text{Total Non-Empty Predictions}}$$

---

## 7. Human-in-the-Loop Review & Adjudication Workflow

Integrated in Streamlit Tab 11 ([`src/evaluation/dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/dashboard_view.py)):

```text
[Candidate Prediction] ──► [Comparator (comparator.py)]
                                  │
                   ┌──────────────┴──────────────┐
                   ▼                             ▼
           [Exact Match]                 [Discrepancy / Ambiguous]
           (Auto-Accepted)                       │
                                                 ▼
                                     [Manual Review Queue (Tab 11)]
                                                 │
                               ┌─────────────────┴─────────────────┐
                               ▼                                   ▼
                      [Accept Prediction]                 [Reject / Override]
                               │                                   │
                               └─────────────────┬─────────────────┘
                                                 ▼
                               [correction_history.jsonl (Audit Log)]
```

### 7.1 Review Adjudication Rules
1. **Never Overwrite Benchmark Labels Directly:** Manual reviews record decisions in [`data/evaluation/correction_history.jsonl`](file:///Users/gavidurushela/Research/tool/J26_SE_355/data/evaluation/). The primary benchmark dataset remains immutable.
2. **Mandatory Justification Notes:** Any override of reference or prediction must include a text justification citing page evidence.
3. **Dual-Reviewer Rule on Boundary Cases:** Disagreements regarding role classification or currency ambiguity require two independent reviewer approvals.

---

## 8. Quality Gates & Acceptance Criteria

Before comparative regional analytics can be published or defended before an academic panel, the dataset must satisfy these minimum quality gates:

| Quality Gate | Minimum Threshold | Current Observed Status | Publication Readiness |
| :--- | :---: | :---: | :---: |
| **Job Title Agreement** | $\ge 90.0\%$ | 77.7% (Exact), 77.7% (Norm) | `PROVISIONAL` |
| **Employer Agreement** | $\ge 85.0\%$ | 76.8% (Exact), 77.7% (Norm) | `PROVISIONAL` |
| **Location / Country Agreement** | $\ge 90.0\%$ | 65.2% (Loc), 66.1% (Country) | `PROVISIONAL` |
| **Salary Parsing MAE** | $\le 5.0\text{ local units}$ | 0.00 MAE | **PASS** |
| **Skill Extraction F1-Score** | $\ge 75.0\%$ | **0.00% (Unreviewed)** | `FAIL (BLOCKING)` |
| **Closing Date Hallucination** | $\le 5.0\%$ | **81.1%** | `FAIL (BLOCKING)` |
| **Indian Sample Representation** | $\ge 100\text{ eligible ads}$ | **22 eligible ads** | `FAIL (BLOCKING)` |
| **Focal Market Salary Disclosure** | $\ge 25\text{ disclosed ads}$ | **2 disclosed ads** | `FAIL (BLOCKING)` |
| **Zero-Count Significance Guard**| Active | **Absent (Spurious gaps shown)**| `FAIL (BLOCKING)` |

---

## 9. Repeatable Test & Execution Commands

### 9.1 Run Automated Regression Suite
```bash
# Execute entire test suite (224 tests) offline
python3 -m unittest discover tests

# Execute benchmark evaluation test suite
python3 -m unittest tests/test_benchmark_evaluation.py

# Execute foreign portal adapter tests
python3 -m unittest tests/test_foreign_portal_adapters.py

# Execute regional analytics test suite
python3 -m unittest tests/test_regional_analysis.py
```

### 9.2 Execute Evaluation Against Benchmark Dataset
```bash
# Run CLI evaluation generating latest error and metric artifacts
python3 -m src.evaluation.evaluate_scraping \
  --benchmark data/evaluation/benchmark_dataset.csv \
  --predictions data/raw/all_pilot_crawled_predictions.csv \
  --match-key auto \
  --output-dir data/evaluation/results
```

### 9.3 Launch Streamlit Research & Validation Interface
```bash
# Launch interactive dashboard with Tab 10 (Regional Analysis) & Tab 11 (Validation)
python3 -m streamlit run app.py
```
