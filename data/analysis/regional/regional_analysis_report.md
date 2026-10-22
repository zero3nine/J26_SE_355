# Comparative Regional IT Labour-Market Analysis Report
**Project:** IT Job Market Intelligence Tool (`J26_SE_355`)  
**Research Contribution:** Comparative Regional Market Analysis  
**Focal Market:** `Sri Lanka` | **Comparators:** `India, Singapore, Malaysia`  
**Evaluation Baseline:** Task 2 Ground-Truth Benchmark & Task 3 Accuracy Verification  

## 1. Executive Summary & Research Methodology
This study provides empirical comparative evidence on IT skill demands, occupational role structures, and compensation disclosure across four regional economies: Sri Lanka (focal), India, Singapore, and Malaysia.

### Core Quantitative Principles Applied:
1. **Independent Eligibility Rules:** General job counts, skill-demand, role comparisons, and salary summaries have separate eligibility criteria.
2. **Salary Decoupling:** Skill-demand analysis **never** excludes an advertisement merely for omitting salary.
3. **Identical Denominators:** Demand percentages use the exact same eligible advertisement count per country.
4. **Uncertainty Quantification:** All proportions report Wilson Score 95% Confidence Intervals; samples with $N < 10$ are explicitly flagged.
5. **Audit-Ready Compensation:** Salaries are segregated by native currency; nominal conversions are never equated with purchasing power parity (PPP).

## 2. Multi-Stage Eligibility & Record Attrition Funnel
| stage | task | input_records | eligible_records | excluded_records | retention_rate_pct | primary_exclusions |
| --- | --- | --- | --- | --- | --- | --- |
| Raw Input Records | raw | 303 | 303 | 0 | 100.0 | None (Entry point) |
| Geographic Filtering | geographic | 303 | 303 | 0 | 100.0 | None |
| General IT Quality | general | 303 | 303 | 0 | 100.0 | None |
| Skill-Demand Analysis | skill | 303 | 141 | 162 | 46.53 | zero_extracted_skills: 162 |
| Role Comparisons | role | 303 | 303 | 0 | 100.0 | None |
| Salary Analysis | salary | 303 | 83 | 220 | 27.39 | salary_undisclosed: 220 |


## 3. Cross-Market Canonical Skill Demand (%)
Formula: $\text{Demand } \% = \frac{n_{s, c}}{N_c} \times 100$, where $n_{s, c}$ is unique ads containing canonical skill $s$.

| country | skill_name | category | eligible_ads_denominator | mention_count | demand_pct | ci_lower_95 | ci_upper_95 | small_sample_flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| India | Communication | Professional Skills | 21 | 7 | 33.33 | 17.19 | 54.63 | False |
| India | Leadership | Professional Skills | 21 | 6 | 28.57 | 13.81 | 49.96 | False |
| India | Problem Solving | Professional Skills | 21 | 5 | 23.81 | 10.63 | 45.09 | False |
| India | Python | Programming Languages | 21 | 4 | 19.05 | 7.67 | 40.0 | False |
| India | Software Testing | Testing & QA | 21 | 3 | 14.29 | 4.98 | 34.64 | False |
| India | Cybersecurity | Security | 21 | 3 | 14.29 | 4.98 | 34.64 | False |
| India | Java | Programming Languages | 21 | 2 | 9.52 | 2.65 | 28.91 | False |
| India | C++ | Programming Languages | 21 | 2 | 9.52 | 2.65 | 28.91 | False |
| India | Amazon Web Services | Cloud & Infrastructure | 21 | 2 | 9.52 | 2.65 | 28.91 | False |
| India | PostgreSQL | Databases | 21 | 1 | 4.76 | 0.85 | 22.67 | False |
| Malaysia | JavaScript | Programming Languages | 15 | 3 | 20.0 | 7.05 | 45.19 | False |
| Malaysia | Python | Programming Languages | 15 | 2 | 13.33 | 3.74 | 37.88 | False |
| Malaysia | Go | Programming Languages | 15 | 2 | 13.33 | 3.74 | 37.88 | False |
| Malaysia | Java | Programming Languages | 15 | 1 | 6.67 | 1.19 | 29.82 | False |
| Malaysia | TypeScript | Programming Languages | 15 | 1 | 6.67 | 1.19 | 29.82 | False |
| Malaysia | C++ | Programming Languages | 15 | 1 | 6.67 | 1.19 | 29.82 | False |
| Malaysia | PostgreSQL | Databases | 15 | 1 | 6.67 | 1.19 | 29.82 | False |
| Malaysia | Amazon Web Services | Cloud & Infrastructure | 15 | 1 | 6.67 | 1.19 | 29.82 | False |
| Malaysia | Kubernetes | Cloud & Infrastructure | 15 | 1 | 6.67 | 1.19 | 29.82 | False |
| Malaysia | Test Automation | Testing & QA | 15 | 1 | 6.67 | 1.19 | 29.82 | False |
| Singapore | Communication | Professional Skills | 43 | 27 | 62.79 | 47.86 | 75.62 | False |
| Singapore | Problem Solving | Professional Skills | 43 | 23 | 53.49 | 38.92 | 67.49 | False |
| Singapore | Python | Programming Languages | 43 | 20 | 46.51 | 32.51 | 61.08 | False |
| Singapore | JavaScript | Programming Languages | 43 | 20 | 46.51 | 32.51 | 61.08 | False |
| Singapore | CI/CD | DevOps & CI/CD | 43 | 19 | 44.19 | 30.43 | 58.89 | False |
| Singapore | Teamwork | Professional Skills | 43 | 16 | 37.21 | 24.38 | 52.14 | False |
| Singapore | Java | Programming Languages | 43 | 15 | 34.88 | 22.42 | 49.83 | False |
| Singapore | C++ | Programming Languages | 43 | 12 | 27.91 | 16.75 | 42.69 | False |
| Singapore | SQL | Databases | 43 | 12 | 27.91 | 16.75 | 42.69 | False |
| Singapore | Test Automation | Testing & QA | 43 | 12 | 27.91 | 16.75 | 42.69 | False |
| Sri Lanka | Problem Solving | Professional Skills | 62 | 36 | 58.06 | 45.67 | 69.52 | False |
| Sri Lanka | Communication | Professional Skills | 62 | 31 | 50.0 | 37.92 | 62.08 | False |
| Sri Lanka | Teamwork | Professional Skills | 62 | 25 | 40.32 | 29.02 | 52.75 | False |
| Sri Lanka | Git | DevOps & CI/CD | 62 | 23 | 37.1 | 26.16 | 49.54 | False |
| Sri Lanka | JavaScript | Programming Languages | 62 | 21 | 33.87 | 23.34 | 46.28 | False |
| Sri Lanka | Leadership | Professional Skills | 62 | 15 | 24.19 | 15.25 | 36.15 | False |
| Sri Lanka | CSS | Web & API | 62 | 12 | 19.35 | 11.43 | 30.85 | False |
| Sri Lanka | HTML | Web & API | 62 | 11 | 17.74 | 10.21 | 29.04 | False |
| Sri Lanka | PHP | Programming Languages | 62 | 10 | 16.13 | 9.0 | 27.21 | False |
| Sri Lanka | SQL | Databases | 62 | 10 | 16.13 | 9.0 | 27.21 | False |


## 4. Skill Gaps: Sri Lanka vs. Regional Comparators
Formula: $\Delta_{s} = \text{Demand}_{\text{LK}}(s) - \text{Demand}_{\text{Comp}}(s)$ (Percentage Points, pp).

| comparator_country | skill_name | focal_demand_pct | comparator_demand_pct | gap_pp | gap_ci_lower_95 | gap_ci_upper_95 | p_value | evidence_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| India | Teamwork | 40.32 | 0.0 | 40.32 | 28.11 | 52.53 | 0.0005 | Data Collection Artifact (Unverified) |
| India | Git | 37.1 | 0.0 | 37.1 | 25.08 | 49.12 | 0.001 | Data Collection Artifact (Unverified) |
| India | Problem Solving | 58.06 | 23.81 | 34.25 | 12.28 | 56.22 | 0.0067 | Statistically Meaningful |
| India | JavaScript | 33.87 | 0.0 | 33.87 | 22.09 | 45.65 | 0.002 | Data Collection Artifact (Unverified) |
| India | CSS | 19.35 | 0.0 | 19.35 | 9.52 | 29.18 | 0.0293 | Data Collection Artifact (Unverified) |
| India | Amazon Web Services | 8.06 | 9.52 | -1.46 | -15.72 | 12.8 | 0.8352 | Indeterminate / Expected Sampling Noise |
| India | Leadership | 24.19 | 28.57 | -4.38 | -26.45 | 17.69 | 0.6899 | Indeterminate / Expected Sampling Noise |
| India | Python | 11.29 | 19.05 | -7.76 | -26.31 | 10.79 | 0.3647 | Indeterminate / Expected Sampling Noise |
| India | C++ | 1.61 | 9.52 | -7.91 | -20.85 | 5.03 | 0.0933 | Indeterminate / Expected Sampling Noise |
| India | Cybersecurity | 4.84 | 14.29 | -9.45 | -25.34 | 6.44 | 0.1484 | Indeterminate / Expected Sampling Noise |
| Malaysia | Problem Solving | 58.06 | 0.0 | 58.06 | 45.78 | 70.34 | 0.0001 | Data Collection Artifact (Unverified) |
| Malaysia | Communication | 50.0 | 0.0 | 50.0 | 37.55 | 62.45 | 0.0004 | Data Collection Artifact (Unverified) |
| Malaysia | Teamwork | 40.32 | 0.0 | 40.32 | 28.11 | 52.53 | 0.0028 | Data Collection Artifact (Unverified) |
| Malaysia | Git | 37.1 | 0.0 | 37.1 | 25.08 | 49.12 | 0.0048 | Data Collection Artifact (Unverified) |
| Malaysia | HTML | 17.74 | 0.0 | 17.74 | 8.23 | 27.25 | 0.0781 | Indeterminate / Expected Sampling Noise |
| Malaysia | Python | 11.29 | 13.33 | -2.04 | -20.96 | 16.88 | 0.8254 | Indeterminate / Expected Sampling Noise |
| Malaysia | Kubernetes | 3.23 | 6.67 | -3.44 | -16.81 | 9.93 | 0.5367 | Indeterminate / Expected Sampling Noise |
| Malaysia | Selenium | 3.23 | 6.67 | -3.44 | -16.81 | 9.93 | 0.5367 | Indeterminate / Expected Sampling Noise |
| Malaysia | C++ | 1.61 | 6.67 | -5.06 | -18.07 | 7.95 | 0.2689 | Indeterminate / Expected Sampling Noise |
| Malaysia | Go | 0.0 | 13.33 | -13.33 | -30.53 | 3.87 | 0.0036 | Statistically Meaningful |
| Singapore | Git | 37.1 | 20.93 | 16.17 | -0.93 | 33.27 | 0.0767 | Indeterminate / Expected Sampling Noise |
| Singapore | Data Analysis | 11.29 | 2.33 | 8.96 | -0.12 | 18.04 | 0.0888 | Indeterminate / Expected Sampling Noise |
| Singapore | Playwright | 8.06 | 0.0 | 8.06 | 1.28 | 14.84 | 0.0565 | Indeterminate / Expected Sampling Noise |
| Singapore | PHP | 16.13 | 9.3 | 6.83 | -5.79 | 19.45 | 0.3113 | Indeterminate / Expected Sampling Noise |
| Singapore | REST API | 8.06 | 2.33 | 5.73 | -2.41 | 13.87 | 0.2135 | Indeterminate / Expected Sampling Noise |
| Singapore | Java | 12.9 | 34.88 | -21.98 | -38.49 | -5.47 | 0.0074 | Statistically Meaningful |
| Singapore | C# | 3.23 | 25.58 | -22.35 | -36.11 | -8.59 | 0.0006 | Statistically Meaningful |
| Singapore | C++ | 1.61 | 27.91 | -26.3 | -40.07 | -12.53 | 0.0001 | Statistically Meaningful |
| Singapore | CI/CD | 12.9 | 44.19 | -31.29 | -48.32 | -14.26 | 0.0003 | Statistically Meaningful |
| Singapore | Python | 11.29 | 46.51 | -35.22 | -52.08 | -18.36 | 0.0 | Statistically Meaningful |


## 5. Regional IT Role Distribution & Classification Quality
| country | total_it_jobs | unclassified_count | unclassified_pct | classification_quality |
| --- | --- | --- | --- | --- |
| India | 31 | 2 | 6.45 | High (>85% classified) |
| Malaysia | 20 | 2 | 10.0 | High (>85% classified) |
| Singapore | 47 | 21 | 44.68 | Moderate (ambiguity present) |
| Sri Lanka | 205 | 104 | 50.73 | Moderate (ambiguity present) |


### Key Comparable Role Frequencies:
| country | role_name | job_count | country_total_jobs | pct_of_country |
| --- | --- | --- | --- | --- |
| India | General IT Role | 19 | 31 | 61.29 |
| India | Software Engineer / Developer | 4 | 31 | 12.9 |
| India | IT Support / System Administrator | 2 | 31 | 6.45 |
| India | Network Engineer | 2 | 31 | 6.45 |
| India | Unclassified | 2 | 31 | 6.45 |
| Malaysia | Software Engineer / Developer | 6 | 20 | 30.0 |
| Malaysia | General IT Role | 5 | 20 | 25.0 |
| Malaysia | DevOps Engineer | 2 | 20 | 10.0 |
| Malaysia | Unclassified | 2 | 20 | 10.0 |
| Malaysia | Cybersecurity Engineer | 1 | 20 | 5.0 |
| Malaysia | Data Engineer | 1 | 20 | 5.0 |
| Malaysia | Database Administrator | 1 | 20 | 5.0 |
| Malaysia | ML / AI Engineer | 1 | 20 | 5.0 |
| Malaysia | Software Architect | 1 | 20 | 5.0 |
| Singapore | Software Engineer / Developer | 25 | 47 | 53.19 |
| Singapore | Unclassified IT | 20 | 47 | 42.55 |
| Sri Lanka | Unclassified | 68 | 205 | 33.17 |
| Sri Lanka | General IT Role | 54 | 205 | 26.34 |
| Sri Lanka | Unclassified IT | 36 | 205 | 17.56 |
| Sri Lanka | Software Engineer / Developer | 17 | 205 | 8.29 |


## 6. Disclosed Compensation Coverage & Distributions
> **CRITICAL METHODOLOGICAL NOTICE:** Nominal salaries reflect local contractual commitments in native currencies. They MUST NOT be interpreted as establishing purchasing power parity (PPP), standard of living, or disposable income equivalence.

| country | currency | pay_period_standard | total_eligible_ads | disclosed_salary_count | disclosure_rate_pct | median_salary | iqr_salary | p25_salary | p75_salary | min_salary | max_salary | mean_salary | std_salary | small_sample_flag | parity_type | methodological_caveat |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| India | INR | monthly_equivalent | 31 | 11 | 35.48 | 27083.33 | 65624.99 | 23958.33 | 89583.33 | 14583.33 | 175000.0 | 60416.67 | 52613.96 | False | Nominal (Local Currency) | Nominal value only. Does NOT establish purchasing power or standard of living differences. |
| Malaysia | MYR | monthly_equivalent | 20 | 13 | 65.0 | 9750.0 | 4250.0 | 7750.0 | 12000.0 | 4250.0 | 18000.0 | 10096.15 | 3820.91 | False | Nominal (Local Currency) | Nominal value only. Does NOT establish purchasing power or standard of living differences. |
| Singapore | SGD | monthly_equivalent | 47 | 46 | 97.87 | 7250.0 | 5237.5 | 5000.0 | 10237.5 | 2500.0 | 23375.0 | 8713.57 | 5359.67 | False | Nominal (Local Currency) | Nominal value only. Does NOT establish purchasing power or standard of living differences. |
| Sri Lanka | LKR | monthly_equivalent | 205 | 13 | 6.34 | 65000.0 | 20000.0 | 55000.0 | 75000.0 | 37500.0 | 110000.0 | 68653.85 | 21055.86 | False | Nominal (Local Currency) | Nominal value only. Does NOT establish purchasing power or standard of living differences. |


## 7. Pairwise Country Skill Profile Similarity Matrix
Metrics: Cosine Similarity across all canonical skills, Jaccard on Top-10 skills, and Spearman Rank Correlation.

| country_a | country_b | sample_size_a | sample_size_b | cosine_similarity | jaccard_top10_similarity | spearman_rank_correlation | sparse_sample_flag | metric_limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Singapore | Sri Lanka | 43 | 62 | 0.8625 | 0.3333 | 0.8405 | False | Measures proportional skill priority alignment. Does NOT establish labor mobility, economic equivalence, or wage parity. |
| India | Singapore | 21 | 43 | 0.6556 | 0.3333 | 0.481 | False | Measures proportional skill priority alignment. Does NOT establish labor mobility, economic equivalence, or wage parity. |
| India | Sri Lanka | 21 | 62 | 0.6337 | 0.25 | 0.389 | False | Measures proportional skill priority alignment. Does NOT establish labor mobility, economic equivalence, or wage parity. |
| Malaysia | Singapore | 15 | 43 | 0.5367 | 0.1765 | 0.3952 | False | Measures proportional skill priority alignment. Does NOT establish labor mobility, economic equivalence, or wage parity. |
| Malaysia | Sri Lanka | 15 | 62 | 0.3797 | 0.1765 | 0.3094 | False | Measures proportional skill priority alignment. Does NOT establish labor mobility, economic equivalence, or wage parity. |
| India | Malaysia | 21 | 15 | 0.3497 | 0.25 | 0.4385 | False | Measures proportional skill priority alignment. Does NOT establish labor mobility, economic equivalence, or wage parity. |


## 8. Robustness & Sensitivity Analysis
Evaluation of parameter stability across 5 validation regimes:

| scenario_key | scenario_name | total_eligible_ads | countries_evaluated | mean_abs_demand_shift_pp | max_demand_shift_pp | lk_top5_skills | stability_assessment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1_baseline | Baseline Full Dataset | 141 | 4 | 0.0 | 0.0 | Problem Solving (58.06%), Communication (50.0%), Teamwork (40.32%), Git (37.1%), JavaScript (33.87%) | Baseline Anchor (0.0 pp) |
| 2_verified_sources_only | Approved Portals Only | 104 | 4 | 1.11 | 18.49 | Problem Solving (60.42%), Communication (56.25%), Teamwork (50.0%), Git (45.83%), JavaScript (39.58%) | Robust (<3.0 pp shift) |
| 3_benchmark_verified_only | Ground-Truth Benchmark Only | 96 | 4 | 1.22 | 18.49 | Problem Solving (62.5%), Communication (57.5%), Teamwork (55.0%), Git (47.5%), JavaScript (42.5%) | Robust (<3.0 pp shift) |
| 4_unambiguous_roles_only | Unambiguous Roles Only | 141 | 4 | 0.0 | 0.0 | Problem Solving (58.06%), Communication (50.0%), Teamwork (40.32%), Git (37.1%), JavaScript (33.87%) | Robust (<3.0 pp shift) |
| 5_salary_disclosed_subsample | Salary-Disclosed Subsample (Bias Test) | 67 | 4 | 2.28 | 40.32 | Problem Solving (75.0%), Communication (25.0%), Analytical Thinking (0.0%), Teamwork (0.0%), CSS (0.0%) | Robust (<3.0 pp shift) |


## 9. Limitations & Research Caveats
- **Sample Size Asymmetry:** Pilot web crawling collected larger volumes in Sri Lanka and India compared to Singapore and Malaysia. Rank differences in sparse samples ($N < 10$) carry wide confidence intervals.
- **Salary Disclosure Self-Selection:** Less than 45% of Indian and Sri Lankan vacancies disclose compensation, whereas Singapore mandates or frequently provides salary bands. Disclosed salaries represent a non-random subset.
- **Occupational Granularity:** Classification assigns jobs based on title and description keywords. Sub-specializations and seniority tiers (e.g. Associate vs Lead) are grouped within broad canonical roles.
