# Comprehensive Implementation Audit Report: Individual Research Component & Supervisor Feedback

**Project ID:** J26-SE-355  
**Project Title:** Quantitative Analysis Framework for Technical Skill Identification for IT Sector Jobs  
**Individual Research Component:** Comparative Regional Market Analysis (Sri Lanka, India, Singapore, Malaysia)  
**Student Name:** E. M. G. R. Ekanayaka  
**Student ID:** IT23213944  
**Date of Assessment:** October 2026  
**Git Branch:** `feature/regional-market-data-validation`  
**Current Head Commit:** [`8310eab`](file:///Users/gavidurushela/Research/tool/J26_SE_355/INDIVIDUAL_COMPONENT_FILE_DOCUMENTATION.md)  
**Audit Status:** COMPLETE — Evidence-Based Static, Empirical, and Methodological Audit  

---

## 1. Executive Summary

This audit report delivers an evidence-based evaluation of the individual research component **Comparative Regional Market Analysis** within Project `J26-SE-355`, directly responding to supervisor feedback:

> *"Think about the accuracy of foreign websites when scraping data. The Indian job market can have a bigger impact. Need to think about delivering accurate results for the user. How to validate the scraped data."*

The audit evaluated the source code, configuration registries, empirical datasets, ground-truth benchmarks, statistical outputs, Streamlit user interface, and automated test suite.

### Key Audit Findings Summary

1. **Architecture & Engineering Rigor (PASS):**  
   The individual research component has established a multi-country pipeline including regional normalization ([`salary_normalizer.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/cleaning/salary_normalizer.py), [`location_normalizer.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/cleaning/location_normalizer.py)), a centralized source registry with SSRF protection ([`source_registry.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/source_registry.py)), an evaluation engine ([`comparator.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/comparator.py), [`metrics.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/metrics.py)), a quantitative analytics engine ([`regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py)), two dedicated Streamlit tabs (Tab 10 & Tab 11), and a 224-test offline test suite passing in under 5 seconds.

2. **The Indian IT Market Representation & Bias (PARTIAL — HIGH METHODOLOGICAL RISK):**  
   While dedicated adapters for India ([`shine.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/shine.py), [`timesjobs.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/timesjobs.py)) successfully parse titles and companies (95.8% agreement) and handle Lakhs INR compensation, the Indian sample size is small ($N=22$ eligible advertisements) and drawn almost exclusively from Shine.com. More critically, **only 10 technical skills were extracted across all 22 Indian postings** (mean: 1.16 skills/ad vs. 7.44 in Singapore and 4.49 in Sri Lanka). 45 canonical skills (including Git, JavaScript, React, SQL, HTML) exhibit **0.0% demand** in India purely due to scraper extraction limitations.

3. **Spurious Statistical Significance in Skill Gaps (FAIL — CRITICAL SCIENTIFIC DEFECT):**  
   Because Indian postings yielded 0 mentions for common skills, two-proportion $z$-tests in [`regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py#L720-L750) calculate $z = 4.138$ ($p = 0.0000$) for Teamwork, $z = 3.733$ ($p = 0.0002$) for Git, and $z = 3.469$ ($p = 0.0005$) for JavaScript. The dashboard labels these differences as **"Statistically Meaningful"**! **This is an extraction failure masquerading as an empirical labour-market finding**, violating scientific validity and failing the supervisor's instruction to prevent users from mistaking unreliable data for real market differences.

4. **Independent Benchmark Ground-Truth Status (PARTIAL — AUDIT GAP):**  
   A 120-advertisement ground-truth dataset exists ([`data/evaluation/benchmark_dataset.csv`](file:///Users/gavidurushela/Research/tool/J26_SE_355/data/evaluation/benchmark_dataset.csv)). However, **109 out of 120 records have `status_skills` set to `not_reviewed`** (including 24/27 in India and 45/48 in Sri Lanka). Only 21 records have verified ground-truth skills. Consequently, **skill extraction accuracy cannot currently be benchmarked against verified ground truth for the focal market or India**.

5. **Denominator Distortion in Skill Demand (PARTIAL — METHODOLOGICAL INCONSISTENCY):**  
   The proposal specifies that the denominator for skill demand must be the total eligible IT advertisements in that country. In the implementation, [`filter_records_with_provenance()`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py#L500) filters out advertisements with zero extracted skills (`require_at_least_n_skills = 1`), reducing denominators from 28 to 22 in India, 57 to 45 in Sri Lanka, and 20 to 15 in Malaysia. This artificially inflates skill demand percentages in countries with higher extraction failure rates.

6. **Salary Disclosure Scarcity in Focal Market (Sri Lanka):**  
   In Sri Lanka, only **2 out of 57 advertisements** (3.51%) disclose salary information. While the salary module correctly keeps nominal currencies separate and flags small samples, drawing cross-country compensation conclusions for Sri Lanka on a sample of $N=2$ is statistically fragile.

---

## 2. Repository and Implementation Overview

### 2.1 Workspace Structure
The project is hosted in repository `J26_SE_355` on branch `feature/regional-market-data-validation`. The working tree contains clean code with user tracking manifests unstaged.

### 2.2 System Architecture
```mermaid
flowchart TD
    subgraph INGESTION["1. Foreign Ingestion & Governance"]
        URL[Target Vacancy / Search URLs] --> VAL[src/security/url_validator.py]
        SREG[config/source_registry.json] --> SMAN[src/scraping/source_registry.py]
        VAL & SMAN --> CL[Safe HTTP Client]
    end

    subgraph ADAPTERS["2. Site-Specific Adapters"]
        CL --> SHINE[src/scraping/extractors/shine.py (India)]
        CL --> TJ[src/scraping/extractors/timesjobs.py (India)]
        CL --> MCF[src/scraping/extractors/mycareersfuture.py (Singapore)]
        CL --> TOP[src/scraping/extractors/topjobs.py (Sri Lanka)]
        CL --> JLD[src/scraping/extractors/jsonld.py]
        CL --> GEN[src/scraping/extractors/generic_html.py]
        SHINE & TJ & MCF & TOP & JLD & GEN --> RAW[(data/raw/all_pilot_crawled_predictions.csv)]
    end

    subgraph CLEANING["3. Regional Schema & Normalization"]
        RAW --> DEDUP[src/cleaning/clean_jobs.py]
        DEDUP --> SAL[src/cleaning/salary_normalizer.py]
        DEDUP --> LOC[src/cleaning/location_normalizer.py]
        DEDUP --> ITC[src/cleaning/it_classifier.py]
        SAL & LOC & ITC --> PROC[(data/processed/jobs_clean_internal.csv)]
    end

    subgraph EVALUATION["4. Quality Benchmark Engine"]
        BM[(data/evaluation/benchmark_dataset.csv)] --> COMP[src/evaluation/comparator.py]
        RAW --> COMP
        COMP --> MET[src/evaluation/metrics.py]
        MET --> REP[src/evaluation/reporter.py]
        REP --> RES[(data/evaluation/results/)]
    end

    subgraph ANALYTICS["5. Regional Analytics (Individual Component)"]
        PROC & BM --> RENG[src/analytics/regional_analysis.py]
        RENG --> DEM[calculate_skill_demand_percentages]
        RENG --> GAPS[calculate_skill_gaps via math.erfc]
        RENG --> ROLES[compare_regional_roles]
        RENG --> SALA[analyze_regional_salaries]
        RENG --> SIM[calculate_country_similarities]
        RENG --> SENS[run_regional_sensitivity_analysis]
        DEM & GAPS & ROLES & SALA & SIM & SENS --> ART[(data/analysis/regional/)]
    end

    subgraph PRESENTATION["6. Streamlit User Interface"]
        ART --> T10[Tab 10: Comparative Regional Analysis]
        RES --> T11[Tab 11: Scraping Accuracy & Validation]
    end
```

---

## 3. Verified File Inventory

Every file listed below was inspected directly in the filesystem; line counts, exact paths, ownership, and statuses are verified.

| No. | Repository-Relative Path | Subsystem | Ownership | Lines | Implementation Status | Test Coverage |
| :---: | :--- | :--- | :--- | :---: | :---: | :--- |
| 1 | [`src/analytics/regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py) | Analytics Engine | Individual Component | 1,346 | `PASS` | `test_regional_analysis.py`, `test_regression_and_reproducibility.py` |
| 2 | [`src/analytics/regional_dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_dashboard_view.py) | Streamlit UI (Tab 10) | Individual Component | 440 | `PASS` | `test_regression_and_reproducibility.py` |
| 3 | [`src/cleaning/salary_normalizer.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/cleaning/salary_normalizer.py) | Normalization | Individual Component | 560 | `PASS` | `test_regional_market_schema.py`, `test_regression_and_reproducibility.py` |
| 4 | [`src/cleaning/location_normalizer.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/cleaning/location_normalizer.py) | Normalization | Individual Component | 341 | `PASS` | `test_regional_market_schema.py`, `test_regression_and_reproducibility.py` |
| 5 | [`src/cleaning/clean_jobs.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/cleaning/clean_jobs.py) | Cleaning / Dedup | Shared / Extended | 692 | `PASS` | `test_cleaning.py`, `test_regression_and_reproducibility.py` |
| 6 | [`src/cleaning/validate_jobs.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/cleaning/validate_jobs.py) | Quality Rules | Shared Infrastructure | 260 | `PASS` | `test_cleaning.py` |
| 7 | [`src/cleaning/it_classifier.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/cleaning/it_classifier.py) | IT Heuristic Filter | Shared / Extended | 277 | `PASS` | `test_it_classifier.py` |
| 8 | [`src/scraping/source_registry.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/source_registry.py) | Web Governance | Individual Component | 277 | `PASS` | `test_foreign_portal_adapters.py`, `test_regression_and_reproducibility.py` |
| 9 | [`src/scraping/models.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/models.py) | Data Schemas | Shared / Extended | 185 | `PASS` | `test_extractors.py`, `test_regression_and_reproducibility.py` |
| 10 | [`src/scraping/extractor_registry.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractor_registry.py) | Extraction Router | Shared / Extended | 154 | `PASS` | `test_foreign_portal_adapters.py` |
| 11 | [`src/scraping/extractors/shine.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/shine.py) | India Site Adapter | Individual Component | 333 | `PASS` | `test_foreign_portal_adapters.py`, `test_regression_and_reproducibility.py` |
| 12 | [`src/scraping/extractors/timesjobs.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/timesjobs.py) | India Site Adapter | Individual Component | 196 | `PASS` | `test_foreign_portal_adapters.py`, `test_regression_and_reproducibility.py` |
| 13 | [`src/scraping/extractors/mycareersfuture.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/mycareersfuture.py) | Singapore Adapter | Individual Component | 206 | `PASS` | `test_foreign_portal_adapters.py`, `test_regression_and_reproducibility.py` |
| 14 | [`src/scraping/extractors/topjobs.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/topjobs.py) | Sri Lanka Adapter | Shared Infrastructure | 267 | `PASS` | `test_extractors.py` |
| 15 | [`src/scraping/extractors/jsonld.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/jsonld.py) | Schema.org Extractor | Shared / Extended | 558 | `PASS` | `test_extractors.py`, `test_regression_and_reproducibility.py` |
| 16 | [`src/scraping/extractors/generic_html.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/generic_html.py) | Fallback Extractor | Shared / Extended | 449 | `PASS` | `test_extractors.py`, `test_regression_and_reproducibility.py` |
| 17 | [`src/security/url_validator.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/security/url_validator.py) | SSRF Security | Shared / Extended | 202 | `PASS` | `test_url_validator.py`, `test_regression_and_reproducibility.py` |
| 18 | [`src/evaluation/schema.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/schema.py) | Benchmark Data Model | Individual Component | 361 | `PASS` | `test_benchmark_evaluation.py` |
| 19 | [`src/evaluation/comparator.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/comparator.py) | Field Comparator | Individual Component | 911 | `PASS` | `test_benchmark_evaluation.py`, `test_regression_and_reproducibility.py` |
| 20 | [`src/evaluation/metrics.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/metrics.py) | Quality Statistics | Individual Component | 525 | `PASS` | `test_benchmark_evaluation.py`, `test_regression_and_reproducibility.py` |
| 21 | [`src/evaluation/reporter.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/reporter.py) | Quality Reporter | Individual Component | 472 | `PASS` | `test_benchmark_evaluation.py`, `test_regression_and_reproducibility.py` |
| 22 | [`src/evaluation/dashboard_data.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/dashboard_data.py) | Benchmark UI Store | Individual Component | 504 | `PASS` | `test_validation_dashboard.py`, `test_regression_and_reproducibility.py` |
| 23 | [`src/evaluation/dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/dashboard_view.py) | Streamlit UI (Tab 11) | Individual Component | 614 | `PASS` | `test_validation_dashboard.py` |
| 24 | [`src/evaluation/evaluate_scraping.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/evaluate_scraping.py) | Evaluation CLI | Individual Component | 224 | `PASS` | `test_benchmark_evaluation.py` |
| 25 | [`src/evaluation/build_benchmark.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/build_benchmark.py) | Benchmark Builder | Individual Component | 321 | `PASS` | `test_benchmark_evaluation.py` |
| 26 | [`src/roles/classifier.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/roles/classifier.py) | Role Classifier | Shared Infrastructure | 229 | `PASS` | `test_role_classifier.py` |
| 27 | [`src/roles/taxonomy.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/roles/taxonomy.py) | Role Taxonomy | Shared Infrastructure | 164 | `PASS` | `test_role_classifier.py` |
| 28 | [`src/extraction/lexical/extractor.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/extraction/lexical/extractor.py) | Skill Extractor | Shared Infrastructure | 338 | `PASS` | `test_extractors.py` |
| 29 | [`src/extraction/taxonomy/loader.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/extraction/taxonomy/loader.py) | Skill Taxonomy Loader | Shared Infrastructure | 160 | `PASS` | `test_extractors.py` |
| 30 | [`app.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/app.py) | Main App (Tabs 1–11) | Shared / Extended | 1,471 | `PASS` | Manual execution verified |
| 31 | [`theme.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/theme.py) | Visual System & CSS | Shared Infrastructure | 557 | `PASS` | Manual execution verified |
| 32 | [`config/source_registry.json`](file:///Users/gavidurushela/Research/tool/J26_SE_355/config/source_registry.json) | Source Portal Registry | Individual Component | 374 | `PASS` | `test_foreign_portal_adapters.py` |
| 33 | [`config/role_taxonomy.json`](file:///Users/gavidurushela/Research/tool/J26_SE_355/config/role_taxonomy.json) | Standard IT Roles (12) | Shared Infrastructure | 196 | `PASS` | `test_role_classifier.py` |
| 34 | [`config/skill_taxonomy.json`](file:///Users/gavidurushela/Research/tool/J26_SE_355/config/skill_taxonomy.json) | Skill Dictionary (55) | Shared Infrastructure | 480 | `PASS` | `test_extractors.py` |
| 35 | [`config/approved_domains.txt`](file:///Users/gavidurushela/Research/tool/J26_SE_355/config/approved_domains.txt) | Permitted Domains | Shared Infrastructure | 27 | `PASS` | `test_url_validator.py` |
| 36 | [`data/evaluation/benchmark_dataset.csv`](file:///Users/gavidurushela/Research/tool/J26_SE_355/data/evaluation/benchmark_dataset.csv) | Ground Truth (N=120) | Individual Component | 121 | `PARTIAL` | `test_benchmark_evaluation.py` |
| 37 | [`data/raw/all_pilot_crawled_predictions.csv`](file:///Users/gavidurushela/Research/tool/J26_SE_355/data/raw/all_pilot_crawled_predictions.csv) | Cross-Market Crawl | Individual Component | 107 | `PARTIAL` | `test_regional_analysis.py` |
| 38 | [`tests/test_regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/tests/test_regional_analysis.py) | Unit Tests (Analytics) | Individual Component | 588 | `PASS` | Ran via unittest (13 tests) |
| 39 | [`tests/test_regression_and_reproducibility.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/tests/test_regression_and_reproducibility.py) | Regression Tests | Individual Component | 1,046 | `PASS` | Ran via unittest (36 tests) |
| 40 | [`tests/test_foreign_portal_adapters.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/tests/test_foreign_portal_adapters.py) | Unit Tests (Scraping) | Individual Component | 303 | `PASS` | Ran via unittest (12 tests) |
| 41 | [`tests/test_benchmark_evaluation.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/tests/test_benchmark_evaluation.py) | Unit Tests (Benchmark) | Individual Component | 670 | `PASS` | Ran via unittest (27 tests) |

---

## 4. Proposal-to-Implementation Traceability Matrix

| Research Requirement (from Proposal) | Target Subsystem | Implementation File(s) | Status | Evidence / Identified Problems |
| :--- | :--- | :--- | :---: | :--- |
| **RQ1: Advertisement-level skill demand %** | Regional Analytics | [`src/analytics/regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py#L613) | `PARTIAL` | Deduplicated per ad. However, denominator drops ads with zero extracted skills (`require_at_least_n_skills=1`), violating proposal. |
| **RQ2: Regional IT role distribution** | Roles & Taxonomy | [`src/analytics/regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py#L760) | `PASS` | Evaluates 12 canonical roles, audits unclassified share (7.1% IN, 17.5% LK), and segments skills by role. |
| **RQ3: Disclosed salary distributions** | Salary Normalizer | [`src/cleaning/salary_normalizer.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/cleaning/salary_normalizer.py) | `PASS` | Handles LKR, INR, SGD, MYR, monthly equivalents. Sri Lanka disclosure is only 3.5% ($N=2$), flagged as small sample. |
| **RQ4: Statistical skill gaps (pp difference)** | Quantitative Engine | [`src/analytics/regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py#L683) | `FAIL` | Implements two-proportion $z$-test via `math.erfc`. However, falsely reports extractor zero-counts in India as "Statistically Meaningful" gaps! |
| **National profile similarity measures** | Statistical Analytics | [`src/analytics/regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py#L986) | `PASS` | Cosine similarity, Top-10 Jaccard overlap, Spearman rank correlation computed natively without scipy. |
| **5-Regime systematic sensitivity analysis** | Sensitivity Engine | [`src/analytics/regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py#L1057) | `PASS` | Tests Baseline, Approved Portals, Benchmark Verified, Unambiguous Roles, and Salary-Disclosed subsample. |
| **Decoupled task eligibility rules** | Provenance Filtering | [`src/analytics/regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py#L414) | `PASS` | Explicitly separates general counts, skill demand, role shares, geographic eligibility, and salary filters. |
| **Interactive Research Dashboard** | Streamlit UI | [`src/analytics/regional_dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_dashboard_view.py) | `PASS` | 6 interactive sub-tabs in Tab 10 rendering KPI cards, custom tables, charts, and CSV artifact downloads. |

---

## 5. Supervisor-Comment-to-Implementation Traceability Matrix

| Supervisor Directive | Required Implementation | Existing Implementation | Status | Findings and Gaps |
| :--- | :--- | :--- | :---: | :--- |
| **1. Foreign website scraping accuracy** | Dedicated site adapters for foreign portals; validation against source evidence | [`shine.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/shine.py), [`timesjobs.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/timesjobs.py), [`mycareersfuture.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/mycareersfuture.py) | `PARTIAL` | High accuracy on title/employer (95.8%). Severe extraction failure on work mode (0.0%), high date hallucination (81.1%), and zero Malaysia predictions. |
| **2. Indian market impact and representation** | Adequate Indian sample, regional cities, LPA salary handling, role terminology | [`shine.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/shine.py), [`source_registry.json`](file:///Users/gavidurushela/Research/tool/J26_SE_355/config/source_registry.json) | `PARTIAL` | LPA salary parser works well. However, only 22 eligible Indian ads exist; only 10 skills extracted; major Indian portal (`naukri.com`) is perimeter-blocked. |
| **3. Accurate extraction of job fields** | Multi-field extraction and field-level error characterization | [`comparator.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/comparator.py), [`metrics.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/metrics.py) | `PASS` | Field comparator decouples raw vs. normalized agreement; Wilson CIs; MAE/MedAE on numeric salaries. |
| **4. Validation against source pages / reference dataset** | Curated ground-truth dataset with independent review labels | [`benchmark_dataset.csv`](file:///Users/gavidurushela/Research/tool/J26_SE_355/data/evaluation/benchmark_dataset.csv) (N=120) | `PARTIAL` | Benchmark dataset exists, but `status_skills` is `not_reviewed` for 109/120 records (including 24/27 in India and 45/48 in Sri Lanka). |
| **5. Detection of duplicates, missing fields, stale ads** | Deduplication engine, quality rules, stale listing checks | [`clean_jobs.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/cleaning/clean_jobs.py), [`validate_jobs.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/cleaning/validate_jobs.py) | `PASS` | 3-step deduplication (URL hash, syndicated match, fingerprint). Stale listings identified via closing date comparison. |
| **6. Transparent communication of data limitations** | Disclaimers, sample size warnings, small-sample flags ($N < 10$) | Tab 10 UI, Tab 11 UI, [`regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py) | `PARTIAL` | Small sample flags ($N < 10$) present. However, $z$-test labels extractor zero-counts in India as "Statistically Meaningful" without data-quality disclaimer! |
| **7. Defensible, reproducible regional results** | Automated regression suite, SHA-256 reproducibility manifests | [`test_regression_and_reproducibility.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/tests/test_regression_and_reproducibility.py), [`reporter.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/reporter.py) | `PASS` | 224 automated tests pass 100% offline. `export_reproducibility_record()` records commit hash and input data SHA-256 checksums. |

---

## 6. Foreign-Website Scraping Accuracy Audit

### 6.1 Supported Portals vs. Missing Adapters

| Portal Hostname | Country | Extraction Strategy | Adapter Status | Validation Status | Real Crawl Records (N) | Known Deficiencies |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `www.shine.com` | India | Site Adapter + JSON-LD | [`shine.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/shine.py) | `validated` | 23 | Fails to extract inline skills in body text; misses work mode badge. |
| `timesjobs.com` | India | Site Adapter | [`timesjobs.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/timesjobs.py) | `pilot_tested` | 0 | Tested on fixture; zero live/crawled records in pilot prediction dataset. |
| `www.naukri.com` | India | Blocked / None | None | `access_restricted` | 2 (manual/error) | Cloudflare / Akamai Bot Manager blocks automated requests with HTTP 403. |
| `mycareersfuture.gov.sg`| Singapore | Site Adapter + JSON-LD | [`mycareersfuture.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/mycareersfuture.py)| `validated` | 22 | Excellent title, salary, description extraction; work mode extraction fails. |
| `my.jobstreet.com` | Malaysia | Blocked / None | None | `access_restricted` | 0 | Cloudflare Turnstile challenge returns HTTP 403. No crawler records. |
| `my.hiredly.com` | Malaysia | Generic HTML Fallback | [`generic_html.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/generic_html.py)| `pilot_tested` | 0 | Zero crawled records in pilot predictions. |
| `itpro.lk` | Sri Lanka | JSON-LD | [`jsonld.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/jsonld.py) | `validated` | 47 | High structured extraction quality; work mode often missing in schema. |
| `topjobs.lk` | Sri Lanka | Site Adapter | [`topjobs.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/topjobs.py) | `validated` | 3 | HTML table structure parsed; flyer image advertisements require OCR. |

### 6.2 Empirical Field Agreement Rates (from Ground-Truth Benchmark, N=120)

```text
Field               Exact Agreement    Normalized Agreement    Coverage    Correctness (Precision)
job_title                 77.7%               77.7%              77.7%              100.0%
employer / company        76.8%               77.7%              77.7%              100.0%
country                    0.0%               66.1%              66.1%              100.0%
location                  65.2%               65.2%              66.1%               98.7%
work_mode                  8.0%                8.0%              12.5%               64.3%
posting_date              20.5%               77.7%              77.7%              100.0%
closing_date               0.0%                0.0%               7.1%                0.0% (81.1% Hallucination)
job_description            0.0%                1.8%              77.7%                2.3%
salary_disclosed          77.7%               77.7%              77.7%              100.0%
salary_min / max          77.7%               30.4%              30.4%              100.0%
skills                     0.0%                0.0%               4.8%                0.0% (109/120 Not Reviewed)
```

---

## 7. Indian Job-Market Coverage and Bias Assessment

### 7.1 Empirical Dataset Representation by Country

| Country | Benchmark Ads | Pilot Crawled Ads | Skill-Eligible Ads ($N_c$) | Salary-Disclosed Ads | Disclosed Salary Rate | Mean Skills / Ad | Median Desc Length |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **India** | 27 | 25 | **22** | 12 | 42.86% | **1.16** | 851 chars |
| **Malaysia** | 20 | 0 | **15** | 13 | 65.00% | **1.00** | 95 chars (snippet) |
| **Singapore** | 25 | 22 | **24** | 24 | 96.00% | **7.44** | 2,862 chars |
| **Sri Lanka** | 48 | 42 | **45** | 2 | 3.51% | **4.49** | 1,638 chars |

### 7.2 The Indian Skill Demand Artifact
In [`data/analysis/regional/skill_demand_by_country.csv`](file:///Users/gavidurushela/Research/tool/J26_SE_355/data/analysis/regional/skill_demand_by_country.csv), only 10 technical skills appear with non-zero counts in India:
1. Communication (31.82%, 7 ads)
2. Leadership (27.27%, 6 ads)
3. Python (22.73%, 5 ads)
4. Problem Solving (22.73%, 5 ads)
5. Software Testing (13.64%, 3 ads)
6. Cybersecurity (13.64%, 3 ads)
7. Java (9.09%, 2 ads)
8. C++ (9.09%, 2 ads)
9. Amazon Web Services (9.09%, 2 ads)
10. PostgreSQL (4.55%, 1 ad)

**All other 45 canonical skills in the taxonomy (Git, JavaScript, React, SQL, HTML, CSS, Docker, Linux, Node.js, etc.) have 0.0% demand in India.**

### 7.3 Source & Role Bias
- **Portal Monoculture:** India is represented almost entirely by Shine.com. Naukri (India's market leader with >70% tech traffic) is absent due to bot-wall blocks.
- **Role Concentration:** 57.1% of Indian postings are categorized as "General IT Role", while specialized engineering roles are underrepresented.
- **Sample Inadequacy:** $N=22$ eligible advertisements cannot be generalized to the multi-million Indian IT labour market without severe selection bias.

---

## 8. Independent Benchmark & Validation Assessment

### 8.1 Ground-Truth Benchmark Structure
- **Dataset Path:** [`data/evaluation/benchmark_dataset.csv`](file:///Users/gavidurushela/Research/tool/J26_SE_355/data/evaluation/benchmark_dataset.csv)
- **Total Records:** 120 advertisements (Sri Lanka: 48, India: 27, Singapore: 25, Malaysia: 20).
- **Curated Fields:** Title, company, location, country, work mode, dates, description snippet, salary bounds/currency/period, skills.

### 8.2 The Critical Benchmark Gap: `status_skills`

| Country | Total Benchmark Ads | `status_skills = 'verified'` | `status_skills = 'not_reviewed'` | `status_skills = 'unavailable'` | Verified Coverage |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **India** | 27 | **0** | **24** | 3 | **0.0%** |
| **Sri Lanka** | 48 | **0** | **45** | 3 | **0.0%** |
| **Singapore** | 25 | **2** | **22** | 1 | **8.0%** |
| **Malaysia** | 20 | **19** | **1** | 0 | **95.0%** |
| **Total** | **120** | **21** | **109** | **7** | **17.5%** |

> [!CAUTION]
> Because 109 out of 120 benchmark records have `status_skills` set to `not_reviewed`, technical skill extraction accuracy in the focal market (Sri Lanka) and primary comparator (India) is **unverified against ground truth**. The evaluation engine correctly reports 0.0% macro F1-score for skills because reference labels have not been reviewed.

---

## 9. Salary Normalization Assessment

### 9.1 Multi-Currency Parsing & Indian LPA Handling
The salary normalizer ([`src/cleaning/salary_normalizer.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/cleaning/salary_normalizer.py)) implements robust regex parsing for:
- Lakhs Per Annum (`LPA`, `Lacs`): Correctly maps `5 - 10 Lakhs PA` to `min: 500,000`, `max: 1,000,000 INR`.
- Pay-Period Standardization: Standardizes hourly ($160\text{h/mo}$), daily ($20\text{d/mo}$), monthly ($1.0$), and annual ($/12.0$).
- Reversed Ranges: Flagged as `unparseable` (e.g. `8000 - 5000 SGD`).
- Undisclosed Salaries: Correctly treated as undisclosed, never coerced to zero.

### 9.2 Numeric Accuracy
On comparable evaluated pairs in the benchmark ($N=34$), the Mean Absolute Error (MAE) and Median Absolute Error (MedAE) are **0.00**, confirming that when salary fields are extracted, the mathematical conversion is exact.

### 9.3 Regional Salary Transparency Paradox

```text
Country       Total Eligible IT Ads    Disclosed Salary Count    Disclosure Rate %    Sample Sufficiency
Singapore              25                       24                    96.00%          Robust (N=24)
Malaysia               20                       13                    65.00%          Adequate (N=13)
India                  28                       12                    42.86%          Marginal (N=12)
Sri Lanka              57                        2                     3.51%          Severely Deficient (N=2)
```

In Sri Lanka, only 2 postings disclose salary. Any cross-national salary comparison involving Sri Lanka is descriptive only and cannot support inferential claims.

---

## 10. Regional Calculation & Statistical Validity Assessment

### 10.1 Denominator Inconsistency
- **Proposal Intended Formula:**
  $$\text{Demand \%}_{s,c} = \left(\frac{\text{Eligible IT Ads in Country } c \text{ mentioning Skill } s}{\text{Total Eligible IT Ads in Country } c}\right) \times 100$$
- **Actual Implementation Formula:**
  $$\text{Demand \%}_{s,c} = \left(\frac{\text{Ads in Country } c \text{ mentioning Skill } s}{\text{Eligible Ads in Country } c \text{ with } \ge 1 \text{ Extracted Skill}}\right) \times 100$$

By dropping zero-skill advertisements, the denominator drops from 28 to 22 in India, 57 to 45 in Sri Lanka, and 20 to 15 in Malaysia. This inflates skill percentages and distorts comparisons against markets where full descriptions yield high skill coverage (Singapore: 24/25 retained).

### 10.2 Spurious Statistical Significance in Skill Gaps

In [`data/analysis/regional/skill_gaps_focal_srilanka.csv`](file:///Users/gavidurushela/Research/tool/J26_SE_355/data/analysis/regional/skill_gaps_focal_srilanka.csv):

| Skill Name | Focal Demand (LK, N=45) | Comparator Demand (IN, N=22) | Gap (pp) | $z$-statistic | $p$-value | Statistically Significant | Evidence Status Displayed in UI |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Teamwork** | 51.11% | 0.00% | +51.11 pp | 4.138 | 0.0000 | `True` | **"Statistically Meaningful"** |
| **Git** | 44.44% | 0.00% | +44.44 pp | 3.733 | 0.0002 | `True` | **"Statistically Meaningful"** |
| **JavaScript**| 40.00% | 0.00% | +40.00 pp | 3.469 | 0.0005 | `True` | **"Statistically Meaningful"** |

**Scientific Assessment:**  
Claiming that Sri Lanka has a "statistically meaningful" advantage over India in Git ($p=0.0002$) and JavaScript ($p=0.0005$) when India's 0.0% is caused by scraper under-extraction is **scientifically invalid**. The $z$-test assumption of independent, identically distributed representative sampling is violated.

---

## 11. UI Transparency Assessment

### 11.1 Strengths
- **Decoupled Metric Cards:** Clearly presents Focal Market Ads, Comparator Ads, Skill-Eligible Vacancies, and Salary Disclosure Rate.
- **Sensitivity Analysis Sub-View:** Tab 10 Sub-Tab 5 provides complete 5-regime comparison.
- **Audit Funnel:** Tab 10 Sub-Tab 6 shows exact attrition at each filtering stage.
- **Benchmark KPIs:** Tab 11 presents exact vs. normalized agreement and Wilson score 95% CIs.

### 11.2 Critical Deficiencies
- **Misleading Significance Badges:** Tab 10 Sub-Tab 1 displays green "Statistically Meaningful" badges on spurious gaps.
- **Description Length Asymmetry Hidden:** The UI does not warn users that Malaysia's data is based on 95-character snippets while Singapore's is based on 2,960-character full descriptions.
- **Salary Comparison Visual Misdirection:** Displaying a box plot comparing Singapore ($N=24$) and Sri Lanka ($N=2$) without an explicit "Extreme Data Scarcity" banner invites misinterpretation.

---

## 12. Automated Test Results

The automated test suite was executed locally in the repository environment:

```bash
python3 -m unittest discover tests
```

### Verified Test Outcome
- **Total Tests Discovered:** **224**
- **Total Tests Passed:** **224**
- **Total Tests Failed:** **0**
- **Total Tests Skipped:** **0**
- **Total Execution Time:** **4.540s**

### Module Breakdown
- `test_regression_and_reproducibility.py`: 36 tests (Tasks 1–6 regression, edge cases, reproducibility manifests) — `PASS`
- `test_benchmark_evaluation.py`: 27 tests (Wilson CIs, multi-label F1, MAE/MedAE, compatibility guards) — `PASS`
- `test_regional_analysis.py`: 13 tests (denominators, z-tests, sensitivity regimes, role shares) — `PASS`
- `test_foreign_portal_adapters.py`: 12 tests (Shine, TimesJobs, MCF, offline HTML fixtures) — `PASS`
- `test_regional_market_schema.py`: 18 tests (LPA salary, pay periods, location gazetteer) — `PASS`
- `test_validation_dashboard.py`: 17 tests (Streamlit data engine, review queue, annotation store) — `PASS`
- Base Subsystems (`test_cleaning`, `test_extractors`, `test_it_classifier`, `test_url_validator`, etc.): 101 tests — `PASS`

---

## 13. Prioritised Corrective-Action Plan

| Priority | Module / File | Current Observed Problem | Proposed Correction | Research Requirement |
| :---: | :--- | :--- | :--- | :--- |
| **P1 (Critical)** | [`src/analytics/regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py#L740) | Spurious statistical significance on extractor zero-counts | Add data-quality guard: if comparator count is 0 and $N < 30$, set `evidence_status = "Data Collection Artifact (Unverified)"` instead of `"Statistically Meaningful"`. | RQ1, RQ4 |
| **P2 (Critical)** | [`data/evaluation/benchmark_dataset.csv`](file:///Users/gavidurushela/Research/tool/J26_SE_355/data/evaluation/benchmark_dataset.csv) | `status_skills` is `not_reviewed` for 109/120 benchmark records | Review and verify canonical skill labels for India ($N=27$) and Sri Lanka ($N=48$) to enable valid ground-truth evaluation. | Validation |
| **P3 (High)** | [`src/analytics/regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py#L630) | Denominator drops zero-skill ads, inflating demand % | Use Total Eligible IT Ads ($N_c$) as denominator, not ads with $\ge 1$ skill. | Proposal RQ1 |
| **P4 (High)** | [`src/scraping/extractors/shine.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/shine.py#L240) | Shine extractor extracts only 1.16 skills/ad (misses inline skills) | Enhance text extraction to parse technical skills from both description body and skill chips. | Foreign Scraping |
| **P5 (High)** | [`data/raw/all_pilot_crawled_predictions.csv`](file:///Users/gavidurushela/Research/tool/J26_SE_355/data/raw/all_pilot_crawled_predictions.csv) | Zero Malaysia crawl predictions; Malaysia uses 95-char snippets | Ingest full-text crawl records for Malaysia or explicitly flag Malaysia as snippet-only pilot. | RQ1, RQ4 |
| **P6 (Medium)** | [`src/analytics/regional_dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_dashboard_view.py#L220) | Sri Lanka salary box plot displayed on $N=2$ | Suppress box plot when $N < 5$; display "Insufficient Data ($N=2$)" warning card instead. | RQ3, UI |
| **P7 (Medium)** | [`src/scraping/extractors/shine.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/scraping/extractors/shine.py#L210) | Work mode agreement is 0.0% across foreign portals | Add regex patterns for modern work mode badges (`Remote`, `Hybrid`, `Work from home`). | Schema Normalization |
| **P8 (Low)** | [`src/evaluation/comparator.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/evaluation/comparator.py#L420) | Date hallucination rate is 81.1% on closing dates | Do not populate closing date with placeholder/scrape date when absent in HTML. | Benchmark Quality |

---

## 14. Implemented Changes vs. Pending Decisions

### Implemented & Tested in Repository
- Zero-dependency statistical math in [`src/analytics/regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py#L730) (two-proportion $z$-test via `math.erfc`, Spearman correlation via pandas ranks).
- Decoupled provenance filtering in [`regional_dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_dashboard_view.py).
- Full 224-test regression and reproducibility suite.

### Pending Supervisor Approval / Additional Data
- Completing manual review of 109 unreviewed benchmark skill annotations in `benchmark_dataset.csv`.
- Crawling full descriptions for Malaysian vacancies to eliminate snippet length asymmetry.
- Establishing formal API access or researcher partnership for perimeter-restricted portals (`naukri.com`, `my.jobstreet.com`).

---

## 15. Unresolved Limitations & Supervisor Decisions

1. **Inclusion of India in Assessment:** The proposal originally centered on Sri Lanka, Singapore, and Malaysia. India was added as a high-impact comparator. The supervisor must formally confirm whether India's scope is accepted as an extension given the data collection limitations on Naukri.
2. **Acceptable Ground-Truth Sample Size:** The current benchmark has 120 records. For statistical validity across 4 countries and 12 roles, a benchmark of 250–300 verified records is recommended.
3. **Macroeconomic PPP Deflators:** Disclosed salaries are nominal. Panel feedback should confirm whether nominal local currency comparison with static USD reference is acceptable, or whether World Bank PPP conversion factors are mandatory.

---

## 16. Final Readiness Assessment

| Evaluation Dimension | Verdict | Scientific Justification |
| :--- | :---: | :--- |
| **Software Engineering & Code Quality** | `PASS` | Clean, modular architecture, comprehensive documentation, 224 automated tests passing in ~4.5s. |
| **Foreign Portal Governance & Security** | `PASS` | Ethical source registry, SSRF protection, offline HTML fixtures, polite rate limiting. |
| **Salary Parsing & Normalization** | `PASS` | Lakhs INR, currency tokens, pay periods correctly standardized; MAE = 0.00 on benchmark pairs. |
| **Indian Market Representativeness** | `PARTIAL` | Only 22 eligible ads; single portal (`shine.com`); mean skills per ad is only 1.16; major portal blocked. |
| **Ground-Truth Benchmark Coverage** | `PARTIAL` | 120 ads curated, but 109/120 records have unreviewed skills; focal market and India skills unverified. |
| **Regional Comparative Trustworthiness** | `FAIL` | Spurious statistical significance ($p < 0.001$) reported on extractor zero-counts in India. |
| **OVERALL READINESS FOR SUBMISSION** | **PROVISIONAL / NOT READY** | **Requires P1 and P2 corrections before findings can be defended before an academic assessment panel.** |
