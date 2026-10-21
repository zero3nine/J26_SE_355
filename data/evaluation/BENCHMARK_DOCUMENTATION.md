# Information Extraction Benchmark Dataset Documentation
**Project:** IT Job Market Intelligence Tool (J26_SE_355)  
**Branch:** `feature/regional-market-data-validation`  
**Location:** `data/evaluation/`  
**Canonical Datasets:** `data/evaluation/benchmark_dataset.csv`, `data/evaluation/benchmark_dataset.json`  

---

## 1. Purpose and Research Rationale

Schema validation (e.g., verifying that a scraped CSV contains required column headers or non-null fields) only confirms syntactic conformity. It cannot determine whether an extraction engine correctly identified the true job title, extracted the actual employer, accurately parsed salary bounds, or fabricated values on pages where those attributes do not exist.

This benchmark dataset establishes an independently audited, field-by-field reference standard derived directly from primary web page evidence. It measures the true factual extraction accuracy, precision, recall, and hallucination rates of the scraping architecture across regional IT labor markets (Sri Lanka, India, Singapore, and Malaysia).

---

## 2. Benchmark Dataset Schema Specification

The benchmark adheres to the standardized regional labor-market schema established in Task 1, linking each ground-truth record to granular field annotations and verification statuses:

| Column | Type | Allowed Values / Format | Description |
| :--- | :--- | :--- | :--- |
| `benchmark_id` | String | `BM-[CC]-[PLATFORM]-[NUM]` | Stable, unique identifier for the benchmark advertisement. |
| `source_url` | String | Valid HTTP/HTTPS URI | Canonical source URL of the job advertisement. |
| `source_platform` | String | Hostname (e.g. `itpro.lk`, `www.shine.com`) | Originating web portal platform. |
| `country` | String | `Sri Lanka`, `India`, `Singapore`, `Malaysia` | Country jurisdiction under observation. |
| `collection_context` | String | e.g. `batch_20261019_211946`, `portal_api_v2` | Crawl batch, extraction context, or API endpoint. |
| `extraction_method` | String | `jsonld`, `site_adapter`, `generic_html`, `browser_rendered`, `none` | Extraction method targeted for evaluation. |
| `expected_job_title_raw` | String | Clean text | Expected job title verbatim from page evidence. |
| `expected_company_raw` | String | Clean text | Expected employer or recruiting agency name. |
| `expected_location_raw` | String | Clean text | Verbatim geographic location string from page. |
| `expected_country_normalized` | String | `Sri Lanka`, `India`, `Singapore`, `Malaysia` | Standardized country name according to regional gazetteer. |
| `expected_city_normalized` | String | Standard city name | Normalized urban/administrative center. |
| `expected_work_mode` | String | `remote`, `hybrid`, `on_site`, `unspecified` | Verified work arrangement mode. |
| `expected_posted_date` | String | ISO `YYYY-MM-DD` or empty | Verifiable calendar date of publication. |
| `expected_closing_date` | String | ISO `YYYY-MM-DD` or empty | Verifiable deadline for applications. |
| `expected_description_snippet` | String | Verbatim text excerpt (100–200 chars) | Representative excerpt proving body text capture. |
| `expected_description_hash` | String | 16-char hex | SHA-256 hash of normalized body description text. |
| `expected_description_min_len` | Integer | $\ge 0$ | Minimum required character length for full body. |
| `expected_salary_disclosed` | Boolean | `True`, `False` | Whether compensation is explicitly stated in source. |
| `expected_salary_text_raw` | String | Verbatim string | Verbatim salary string as displayed in source. |
| `expected_salary_type` | String | `range`, `fixed`, `starting_from`, `up_to`, `undisclosed` | Structure of disclosed compensation. |
| `expected_salary_min` | Float | Numeric or empty | Lower compensation bound normalized to single pay period. |
| `expected_salary_max` | Float | Numeric or empty | Upper compensation bound normalized to single pay period. |
| `expected_salary_currency` | String | `LKR`, `INR`, `SGD`, `MYR`, `USD`, etc. | ISO 4217 currency code. |
| `expected_salary_period` | String | `hourly`, `daily`, `monthly`, `annual`, `unspecified` | Payment frequency period. |
| `expected_skills` | String | Comma-separated | Canonical skill labels explicitly required in source. |
| `status_job_title` | Enum | `verified`, `unavailable`, `ambiguous`, `not_reviewed` | Verification status of title. |
| `status_company` | Enum | `verified`, `unavailable`, `ambiguous`, `not_reviewed` | Verification status of company. |
| `status_location` | Enum | `verified`, `unavailable`, `ambiguous`, `not_reviewed` | Verification status of location. |
| `status_work_mode` | Enum | `verified`, `unavailable`, `ambiguous`, `not_reviewed` | Verification status of work mode. |
| `status_posted_date` | Enum | `verified`, `unavailable`, `ambiguous`, `not_reviewed` | Verification status of posting date. |
| `status_closing_date` | Enum | `verified`, `unavailable`, `ambiguous`, `not_reviewed` | Verification status of closing date. |
| `status_description` | Enum | `verified`, `unavailable`, `ambiguous`, `not_reviewed` | Verification status of description. |
| `status_salary` | Enum | `verified`, `unavailable`, `ambiguous`, `not_reviewed` | Verification status of salary information. |
| `status_skills` | Enum | `verified`, `unavailable`, `ambiguous`, `not_reviewed` | Verification status of canonical skills. |
| `verification_timestamp` | String | ISO 8601 UTC | Timestamp when audit was conducted. |
| `verified_by` | String | Reviewer ID | Auditor responsible for the verification. |
| `evidence_source` | String | `original_html_dom`, `portal_api_response`, `archived_page` | Form of primary evidence examined. |
| `reviewer_notes` | String | Text | Audit commentary, edge case notes, ambiguity reasons. |

---

## 3. Field Verification Status Definitions

To eliminate single-flag bias, every field is classified under one of four distinct states:

1. **`verified`**: The field value has been directly verified against primary source page evidence. The expected value represents confirmed ground truth.
2. **`unavailable`**: The field is genuinely absent from the source advertisement (e.g., compensation is undisclosed, application deadline is unstated, or employer name is confidential).  
   *Core Rule:* Missing source information is NEVER interpreted as a confirmed zero or empty string. If the scraping system extracts a value for an `unavailable` field, it is penalized as an over-extraction (hallucination).
3. **`ambiguous`**: The source advertisement presents conflicting, unanchored, or indeterminate information (e.g., location given as "Singapore / Remote / APAC", or date stated as "Posted recently"). Ambiguous fields are logged in qualitative audits but excluded from strict precision/recall denominators.
4. **`not_reviewed`**: The field has not yet undergone independent human audit and is excluded from quantitative metrics.

---

## 4. Normalization and Matching Rules

Before comparing extracted predictions against benchmark labels, field-specific matching rules are applied:

- **Job Title**: Normalizes casing, strips surrounding punctuation, and collapses multiple whitespace. Exact normalized match or token Jaccard similarity $\ge 0.80$ is accepted.
- **Company Name**: Strips corporate legal suffixes (`Pvt Ltd`, `Pte Ltd`, `LLC`, `Inc`, `Sdn Bhd`, `Bhd`, `Co.`, `Hiring for Client`) before comparison.
- **Location Raw & Normalized**: Raw strings are compared modulo punctuation; normalized country and city are matched against the regional gazetteer (`Sri Lanka`, `India`, `Singapore`, `Malaysia`).
- **Work Mode**: Standardized against enum `{'remote', 'hybrid', 'on_site', 'unspecified'}`.
- **Dates**: Standardized into ISO `YYYY-MM-DD`. Timestamps with timezone offsets (e.g. `2026-10-19T19:43:20+05:30`) are normalized to date-only calendar values.
- **Description**: Verifies body text length exceeds `expected_description_min_len` and verifies containment of `expected_description_snippet`.
- **Salary Information**:
  - `expected_salary_disclosed` is checked as a boolean.
  - Quantitative min and max are compared within a 1.0 unit floating-point tolerance.
  - Currency must match ISO code (`SGD`, `LKR`, `INR`, `MYR`, `USD`).
  - Period must match standardized enum (`hourly`, `daily`, `monthly`, `annual`).

---

## 5. Strict Separation of Benchmark from Scraper & Operational Data

To prevent data contamination, information leakage, and benchmark gaming:

1. **Physical File Isolation**: Benchmark datasets reside exclusively in `data/evaluation/`. Raw scraping batches reside in `data/raw/batches/`, and operational clean data resides in `data/processed/`.
2. **Read-Only Ingestion**: The evaluation script loads benchmark records into immutable in-memory representations and never writes back to the benchmark file path.
3. **Prevention of Self-Evaluation**: The evaluation entry point checks input paths and raises an immediate fatal error (exit code 1) if `--predictions` is passed pointing to `--benchmark`.
4. **Separation from Threshold Tuning**: The extraction system's classification thresholds and regex patterns must only be tuned using separate validation splits (e.g., `data/evaluation/ground_truth.csv` for skills). The benchmark dataset is reserved strictly for evaluation.

---

## 6. How to Run the Evaluation CLI

### Basic Command
Run the evaluation CLI against any raw batch CSV or clean operational CSV:
```bash
python -m src.evaluation.evaluate_scraping \
    --benchmark data/evaluation/benchmark_dataset.csv \
    --predictions data/raw/batches/jobs_raw_batch_20261019_211946.csv \
    --output-dir data/evaluation/results/
```

### Options and Arguments
- `--benchmark`, `-b`: Path to benchmark dataset CSV or JSON (default: `data/evaluation/benchmark_dataset.csv`).
- `--predictions`, `-p`: Path to extraction predictions file (required).
- `--output-dir`, `-o`: Output folder for reports (default: `data/evaluation/results/`).
- `--match-key`, `-m`: Alignment strategy: `auto`, `source_url`, or `job_id` (default: `auto`).
- `--quiet`, `-q`: Suppress terminal output (useful for automated CI/CD runs).

### Exit Codes
- `0`: Evaluation executed successfully and matching records were evaluated.
- `1`: Invalid arguments, schema validation failure, missing files, or attempted benchmark overwriting.
- `2`: Execution completed, but zero prediction records matched the benchmark dataset (signaling alignment or URL mismatch issues).

---

## 7. How to Add a Verified Advertisement

1. **Source Evidence Collection**:
   - Access the target job advertisement on the public web.
   - Save the raw HTML DOM snapshot or REST API response under `data/evaluation/evidence/snapshots/` using the sanitized filename pattern: `evidence_[COUNTRY]_[PLATFORM]_[ID].html`.
2. **Record Creation**:
   - Generate a stable benchmark ID: `BM-[COUNTRY_CODE]-[PLATFORM]-[NUM]` (e.g., `BM-SG-MCF-026`).
   - Extract the verbatim values directly from the snapshot evidence.
3. **Field Status Assignment**:
   - For every field present on the page, set status to `verified` and record the expected value.
   - For any field absent from the page (e.g. undisclosed salary), set status to `unavailable` and leave the expected value empty (`expected_salary_disclosed: False`).
   - For ambiguous fields, set status to `ambiguous` and record the explanation in `reviewer_notes`.
4. **Validation Check**:
   - Re-run benchmark validation:
     ```bash
     python -c "from src.evaluation.schema import load_benchmark_dataset; load_benchmark_dataset('data/evaluation/benchmark_dataset.csv'); print('Valid!')"
     ```

---

## 8. Metric Definitions and Mathematical Formulation

### 1. Field Precision, Recall, and F1
For any evaluated field with reference status `verified`:
$$\text{Precision} = \frac{TP}{TP + FP_{\text{incorrect}}}$$
$$\text{Recall} = \frac{TP}{TP + FN_{\text{missing}}} = \frac{\text{Correct}}{\text{Total Verified Records}}$$
$$F_1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

### 2. Hallucination Rate on Unavailable Fields
When a field is `unavailable` in the source advertisement:
$$\text{Hallucination Rate} = \frac{FP_{\text{over-extracted}}}{Total\ Unavailable\ Records}$$
Where $FP_{\text{over-extracted}}$ denotes instances where the scraper invented or extracted an unauthorized value for an absent attribute.

### 3. Exact Match Rate
An advertisement is counted as an exact match only if all verified fields are correctly extracted and all unavailable fields are correctly omitted:
$$\text{Exact Match Rate} = \frac{\text{Fully Correct Advertisements}}{\text{Total Matched Advertisements}}$$

---

## 9. Epistemic Scope and What the Benchmark Cannot Establish

1. **Non-Representativeness of National Labor Markets**: This pilot benchmark of 120 verified advertisements provides high-fidelity point-in-time ground truth for evaluating scraper information extraction accuracy. It does not establish statistical representativeness of entire national economies.
2. **Portal Bias**: Sampling reflects the distribution of accessible portals during the collection period and should not be interpreted as the structural distribution of all IT employment in a given nation.
3. **Temporal Ephemerality**: Job listings are dynamic. Benchmark verification reflects the state of the listing at `verification_timestamp`. If a listing is updated or withdrawn by the employer after this date, the preserved evidence snapshot serves as the ground truth.
