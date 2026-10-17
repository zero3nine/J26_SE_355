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
| Raw Input Records | raw | 137 | 137 | 0 | 100.0 | None (Entry point) |
| Geographic Filtering | geographic | 137 | 130 | 7 | 94.89 | non_target_country: 2, classified_non_it: 5 |
| General IT Quality | general | 137 | 130 | 7 | 94.89 | non_target_country: 2, classified_non_it: 5 |
| Skill-Demand Analysis | skill | 137 | 106 | 31 | 77.37 | non_target_country: 2, classified_non_it: 5, zero_extracted_skills: 24 |
| Role Comparisons | role | 137 | 130 | 7 | 94.89 | non_target_country: 2, classified_non_it: 5 |
| Salary Analysis | salary | 137 | 51 | 86 | 37.23 | non_target_country: 2, classified_non_it: 5, salary_undisclosed: 79 |


## 3. Cross-Market Canonical Skill Demand (%)
Formula: $\text{Demand } \% = \frac{n_{s, c}}{N_c} \times 100$, where $n_{s, c}$ is unique ads containing canonical skill $s$.

| country | skill_name | category | eligible_ads_denominator | mention_count | demand_pct | ci_lower_95 | ci_upper_95 | small_sample_flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| India | Communication | Professional Skills | 22 | 7 | 31.82 | 16.36 | 52.68 | False |
| India | Leadership | Professional Skills | 22 | 6 | 27.27 | 13.15 | 48.15 | False |
| India | Python | Programming Languages | 22 | 5 | 22.73 | 10.12 | 43.44 | False |
| India | Problem Solving | Professional Skills | 22 | 5 | 22.73 | 10.12 | 43.44 | False |
| India | Software Testing | Testing & QA | 22 | 3 | 13.64 | 4.75 | 33.33 | False |
| India | Cybersecurity | Security | 22 | 3 | 13.64 | 4.75 | 33.33 | False |
| India | Java | Programming Languages | 22 | 2 | 9.09 | 2.53 | 27.81 | False |
| India | C++ | Programming Languages | 22 | 2 | 9.09 | 2.53 | 27.81 | False |
| India | Amazon Web Services | Cloud & Infrastructure | 22 | 2 | 9.09 | 2.53 | 27.81 | False |
| India | PostgreSQL | Databases | 22 | 1 | 4.55 | 0.81 | 21.8 | False |
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
| Singapore | Communication | Professional Skills | 24 | 17 | 70.83 | 50.83 | 85.09 | False |
| Singapore | JavaScript | Programming Languages | 24 | 14 | 58.33 | 38.83 | 75.53 | False |
| Singapore | Problem Solving | Professional Skills | 24 | 14 | 58.33 | 38.83 | 75.53 | False |
| Singapore | Python | Programming Languages | 24 | 11 | 45.83 | 27.89 | 64.93 | False |
| Singapore | Teamwork | Professional Skills | 24 | 11 | 45.83 | 27.89 | 64.93 | False |
| Singapore | C# | Programming Languages | 24 | 9 | 37.5 | 21.16 | 57.29 | False |
| Singapore | C++ | Programming Languages | 24 | 9 | 37.5 | 21.16 | 57.29 | False |
| Singapore | CI/CD | DevOps & CI/CD | 24 | 8 | 33.33 | 17.97 | 53.29 | False |
| Singapore | Java | Programming Languages | 24 | 6 | 25.0 | 12.0 | 44.9 | False |
| Singapore | Test Automation | Testing & QA | 24 | 6 | 25.0 | 12.0 | 44.9 | False |
| Sri Lanka | Problem Solving | Professional Skills | 45 | 28 | 62.22 | 47.63 | 74.89 | False |
| Sri Lanka | Communication | Professional Skills | 45 | 27 | 60.0 | 45.45 | 72.98 | False |
| Sri Lanka | Teamwork | Professional Skills | 45 | 23 | 51.11 | 37.0 | 65.04 | False |
| Sri Lanka | Git | DevOps & CI/CD | 45 | 20 | 44.44 | 30.94 | 58.82 | False |
| Sri Lanka | JavaScript | Programming Languages | 45 | 18 | 40.0 | 27.02 | 54.55 | False |
| Sri Lanka | PHP | Programming Languages | 45 | 10 | 22.22 | 12.54 | 36.27 | False |
| Sri Lanka | Leadership | Professional Skills | 45 | 10 | 22.22 | 12.54 | 36.27 | False |
| Sri Lanka | CSS | Web & API | 45 | 9 | 20.0 | 10.9 | 33.82 | False |
| Sri Lanka | MySQL | Databases | 45 | 8 | 17.78 | 9.29 | 31.33 | False |
| Sri Lanka | Software Testing | Testing & QA | 45 | 8 | 17.78 | 9.29 | 31.33 | False |


## 4. Skill Gaps: Sri Lanka vs. Regional Comparators
Formula: $\Delta_{s} = \text{Demand}_{\text{LK}}(s) - \text{Demand}_{\text{Comp}}(s)$ (Percentage Points, pp).

| comparator_country | skill_name | focal_demand_pct | comparator_demand_pct | gap_pp | gap_ci_lower_95 | gap_ci_upper_95 | p_value | evidence_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| India | Teamwork | 51.11 | 0.0 | 51.11 | 36.5 | 65.72 | 0.0 | Statistically Meaningful |
| India | Git | 44.44 | 0.0 | 44.44 | 29.92 | 58.96 | 0.0002 | Statistically Meaningful |
| India | JavaScript | 40.0 | 0.0 | 40.0 | 25.69 | 54.31 | 0.0005 | Statistically Meaningful |
| India | Problem Solving | 62.22 | 22.73 | 39.49 | 16.97 | 62.01 | 0.0024 | Statistically Meaningful |
| India | Communication | 60.0 | 31.82 | 28.18 | 4.02 | 52.34 | 0.0303 | Statistically Meaningful |
| India | Amazon Web Services | 8.89 | 9.09 | -0.2 | -14.81 | 14.41 | 0.9785 | Indeterminate / Expected Sampling Noise |
| India | Leadership | 22.22 | 27.27 | -5.05 | -27.27 | 17.17 | 0.6489 | Indeterminate / Expected Sampling Noise |
| India | C++ | 0.0 | 9.09 | -9.09 | -21.1 | 2.92 | 0.04 | Statistically Meaningful |
| India | Python | 11.11 | 22.73 | -11.62 | -31.39 | 8.15 | 0.21 | Indeterminate / Expected Sampling Noise |
| India | Cybersecurity | 0.0 | 13.64 | -13.64 | -27.98 | 0.7 | 0.0112 | Statistically Meaningful |
| Malaysia | Problem Solving | 62.22 | 0.0 | 62.22 | 48.05 | 76.39 | 0.0 | Statistically Meaningful |
| Malaysia | Communication | 60.0 | 0.0 | 60.0 | 45.69 | 74.31 | 0.0001 | Statistically Meaningful |
| Malaysia | Teamwork | 51.11 | 0.0 | 51.11 | 36.5 | 65.72 | 0.0004 | Statistically Meaningful |
| Malaysia | Git | 44.44 | 0.0 | 44.44 | 29.92 | 58.96 | 0.0016 | Statistically Meaningful |
| Malaysia | PHP | 22.22 | 0.0 | 22.22 | 10.07 | 34.37 | 0.0455 | Statistically Meaningful |
| Malaysia | Selenium | 4.44 | 6.67 | -2.23 | -16.22 | 11.76 | 0.7315 | Indeterminate / Expected Sampling Noise |
| Malaysia | Kubernetes | 2.22 | 6.67 | -4.45 | -17.79 | 8.89 | 0.4057 | Indeterminate / Expected Sampling Noise |
| Malaysia | C++ | 0.0 | 6.67 | -6.67 | -19.3 | 5.96 | 0.0805 | Indeterminate / Expected Sampling Noise |
| Malaysia | Cybersecurity | 0.0 | 6.67 | -6.67 | -19.3 | 5.96 | 0.0805 | Indeterminate / Expected Sampling Noise |
| Malaysia | Go | 0.0 | 13.33 | -13.33 | -30.53 | 3.87 | 0.0127 | Statistically Meaningful |
| Singapore | Git | 44.44 | 16.67 | 27.77 | 6.96 | 48.58 | 0.0211 | Statistically Meaningful |
| Singapore | PHP | 22.22 | 12.5 | 9.72 | -8.24 | 27.68 | 0.3254 | Indeterminate / Expected Sampling Noise |
| Singapore | Playwright | 8.89 | 0.0 | 8.89 | 0.57 | 17.21 | 0.1323 | Indeterminate / Expected Sampling Noise |
| Singapore | Leadership | 22.22 | 16.67 | 5.55 | -13.68 | 24.78 | 0.5851 | Indeterminate / Expected Sampling Noise |
| Singapore | Teamwork | 51.11 | 45.83 | 5.28 | -19.43 | 29.99 | 0.6761 | Indeterminate / Expected Sampling Noise |
| Singapore | CI/CD | 15.56 | 33.33 | -17.77 | -39.4 | 3.86 | 0.0883 | Indeterminate / Expected Sampling Noise |
| Singapore | JavaScript | 40.0 | 58.33 | -18.33 | -42.7 | 6.04 | 0.1459 | Indeterminate / Expected Sampling Noise |
| Singapore | Python | 11.11 | 45.83 | -34.72 | -56.67 | -12.77 | 0.0011 | Statistically Meaningful |
| Singapore | C# | 2.22 | 37.5 | -35.28 | -55.12 | -15.44 | 0.0001 | Statistically Meaningful |
| Singapore | C++ | 0.0 | 37.5 | -37.5 | -56.87 | -18.13 | 0.0 | Statistically Meaningful |


## 5. Regional IT Role Distribution & Classification Quality
| country | total_it_jobs | unclassified_count | unclassified_pct | classification_quality |
| --- | --- | --- | --- | --- |
| India | 28 | 2 | 7.14 | High (>85% classified) |
| Malaysia | 20 | 2 | 10.0 | High (>85% classified) |
| Singapore | 25 | 1 | 4.0 | High (>85% classified) |
| Sri Lanka | 57 | 10 | 17.54 | Moderate (ambiguity present) |


### Key Comparable Role Frequencies:
| country | role_name | job_count | country_total_jobs | pct_of_country |
| --- | --- | --- | --- | --- |
| India | General IT Role | 16 | 28 | 57.14 |
| India | Software Engineer / Developer | 4 | 28 | 14.29 |
| India | IT Support / System Administrator | 2 | 28 | 7.14 |
| India | Network Engineer | 2 | 28 | 7.14 |
| India | Unclassified | 2 | 28 | 7.14 |
| Malaysia | Software Engineer / Developer | 6 | 20 | 30.0 |
| Malaysia | General IT Role | 5 | 20 | 25.0 |
| Malaysia | DevOps Engineer | 2 | 20 | 10.0 |
| Malaysia | Unclassified | 2 | 20 | 10.0 |
| Malaysia | Cybersecurity Engineer | 1 | 20 | 5.0 |
| Malaysia | Data Engineer | 1 | 20 | 5.0 |
| Malaysia | Database Administrator | 1 | 20 | 5.0 |
| Malaysia | ML / AI Engineer | 1 | 20 | 5.0 |
| Malaysia | Software Architect | 1 | 20 | 5.0 |
| Singapore | Software Engineer / Developer | 23 | 25 | 92.0 |
| Sri Lanka | General IT Role | 19 | 57 | 33.33 |
| Sri Lanka | Software Engineer / Developer | 17 | 57 | 29.82 |
| Sri Lanka | Unclassified | 10 | 57 | 17.54 |
| Sri Lanka | QA / Test Engineer | 9 | 57 | 15.79 |


## 6. Disclosed Compensation Coverage & Distributions
> **CRITICAL METHODOLOGICAL NOTICE:** Nominal salaries reflect local contractual commitments in native currencies. They MUST NOT be interpreted as establishing purchasing power parity (PPP), standard of living, or disposable income equivalence.

| country | currency | pay_period_standard | total_eligible_ads | disclosed_salary_count | disclosure_rate_pct | median_salary | iqr_salary | p25_salary | p75_salary | min_salary | max_salary | mean_salary | std_salary | small_sample_flag | parity_type | methodological_caveat |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| India | INR | monthly_equivalent | 28 | 12 | 42.86 | 27083.33 | 57291.66 | 22916.67 | 80208.33 | 14583.33 | 175000.0 | 56597.22 | 51880.92 | False | Nominal (Local Currency) | Nominal value only. Does NOT establish purchasing power or standard of living differences. |
| Malaysia | MYR | monthly_equivalent | 20 | 13 | 65.0 | 9750.0 | 4250.0 | 7750.0 | 12000.0 | 4250.0 | 18000.0 | 10096.15 | 3820.91 | False | Nominal (Local Currency) | Nominal value only. Does NOT establish purchasing power or standard of living differences. |
| Singapore | SGD | monthly_equivalent | 25 | 24 | 96.0 | 5750.0 | 4062.5 | 4750.0 | 8812.5 | 3400.0 | 19000.0 | 7585.42 | 4205.5 | False | Nominal (Local Currency) | Nominal value only. Does NOT establish purchasing power or standard of living differences. |
| Sri Lanka | LKR | monthly_equivalent | 57 | 2 | 3.51 | 62500.0 | 12500.0 | 56250.0 | 68750.0 | 50000.0 | 75000.0 | 62500.0 | 17677.67 | True | Nominal (Local Currency) | Nominal value only. Does NOT establish purchasing power or standard of living differences. |


## 7. Pairwise Country Skill Profile Similarity Matrix
Metrics: Cosine Similarity across all canonical skills, Jaccard on Top-10 skills, and Spearman Rank Correlation.

| country_a | country_b | sample_size_a | sample_size_b | cosine_similarity | jaccard_top10_similarity | spearman_rank_correlation | sparse_sample_flag | metric_limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Singapore | Sri Lanka | 24 | 45 | 0.8561 | 0.25 | 0.6598 | False | Measures proportional skill priority alignment. Does NOT establish labor mobility, economic equivalence, or wage parity. |
| India | Singapore | 22 | 24 | 0.652 | 0.3333 | 0.4555 | False | Measures proportional skill priority alignment. Does NOT establish labor mobility, economic equivalence, or wage parity. |
| India | Sri Lanka | 22 | 45 | 0.5961 | 0.25 | 0.2863 | False | Measures proportional skill priority alignment. Does NOT establish labor mobility, economic equivalence, or wage parity. |
| Malaysia | Singapore | 15 | 24 | 0.5221 | 0.1765 | 0.2386 | False | Measures proportional skill priority alignment. Does NOT establish labor mobility, economic equivalence, or wage parity. |
| India | Malaysia | 22 | 15 | 0.3685 | 0.25 | 0.3861 | False | Measures proportional skill priority alignment. Does NOT establish labor mobility, economic equivalence, or wage parity. |
| Malaysia | Sri Lanka | 15 | 45 | 0.3551 | 0.1111 | 0.1459 | False | Measures proportional skill priority alignment. Does NOT establish labor mobility, economic equivalence, or wage parity. |


## 8. Robustness & Sensitivity Analysis
Evaluation of parameter stability across 5 validation regimes:

| scenario_key | scenario_name | total_eligible_ads | countries_evaluated | mean_abs_demand_shift_pp | max_demand_shift_pp | lk_top5_skills | stability_assessment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1_baseline | Baseline Full Dataset | 106 | 4 | 0.0 | 0.0 | Problem Solving (62.22%), Communication (60.0%), Teamwork (51.11%), Git (44.44%), JavaScript (40.0%) | Baseline Anchor (0.0 pp) |
| 2_verified_sources_only | Approved Portals Only | 90 | 3 | 0.11 | 4.55 | Problem Solving (62.22%), Communication (60.0%), Teamwork (51.11%), Git (44.44%), JavaScript (40.0%) | Robust (<3.0 pp shift) |
| 3_benchmark_verified_only | Ground-Truth Benchmark Only | 101 | 4 | 0.24 | 3.89 | Problem Solving (62.5%), Communication (57.5%), Teamwork (55.0%), Git (47.5%), JavaScript (42.5%) | Robust (<3.0 pp shift) |
| 4_unambiguous_roles_only | Unambiguous Roles Only | 106 | 4 | 0.0 | 0.0 | Problem Solving (62.22%), Communication (60.0%), Teamwork (51.11%), Git (44.44%), JavaScript (40.0%) | Robust (<3.0 pp shift) |
| 5_salary_disclosed_subsample | Salary-Disclosed Subsample (Bias Test) | 45 | 3 | 1.02 | 14.4 |  | Robust (<3.0 pp shift) |


## 9. Limitations & Research Caveats
- **Sample Size Asymmetry:** Pilot web crawling collected larger volumes in Sri Lanka and India compared to Singapore and Malaysia. Rank differences in sparse samples ($N < 10$) carry wide confidence intervals.
- **Salary Disclosure Self-Selection:** Less than 45% of Indian and Sri Lankan vacancies disclose compensation, whereas Singapore mandates or frequently provides salary bands. Disclosed salaries represent a non-random subset.
- **Occupational Granularity:** Classification assigns jobs based on title and description keywords. Sub-specializations and seniority tiers (e.g. Associate vs Lead) are grouped within broad canonical roles.
