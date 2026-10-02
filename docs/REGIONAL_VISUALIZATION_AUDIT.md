# Regional Visualization Audit: Research Proposal Compliance Report

**Project ID:** J26-SE-355  
**Project Title:** Quantitative Analysis Framework for Technical Skill Identification for IT Sector Jobs  
**Individual Research Component:** Comparative Regional Market Analysis  
**Student Name:** E. M. G. R. Ekanayaka  
**Student ID:** IT23213944  
**Date of Audit:** October 2026  
**Git Branch:** `feature/regional-market-data-validation`  
**Current HEAD Commit:** `8310eab`  
**Audit Status:** COMPLETE — Evidence-Based Static, Empirical, Mathematical & UI Verification  

---

## 1. Current Branch and Working-Tree Status

- **Active Branch:** `feature/regional-market-data-validation`
- **Working Tree Integrity:** Working tree preserved in accordance with safety instructions. No branches were created, switched, or merged. User data collection manifests (`urls.txt`, `data/external_links_queue.json`, `data/raw/collection_manifest.json`, `config/approved_domains.txt`) and evaluation artifacts remain strictly intact.
- **Repository Cleanliness:** No commits, pushes, or external deployments were executed.

---

## 2. Research Proposal Requirements Reviewed

The research component evaluates IT job advertisement skill demand, salary/compensation, skill gaps, and market similarities across **Sri Lanka (Focal Market)**, **India**, **Singapore**, and **Malaysia**, under the individual research proposal:

- **Section 3.5: Salary Extraction and Normalization:** Monthly standardization, local currency isolation (LKR, INR, SGD, MYR), Indian format parsing (Lakhs/Crores), and non-inference of missing salary data.
- **Section 3.6: Regional Comparative Analysis:** Canonical skill demand percentages, cross-national grouped bar comparisons, 2D skill-demand heatmaps, two-proportion $z$-test skill gap divergence, and multidimensional skill-profile similarity.
- **Section 3.8: Evaluation Metrics:** Proportional skill demand, Wilson Score 95% confidence intervals, pooled two-sample $z$-statistics, Cosine similarity, Jaccard index (Top-10 skills), and Spearman rank correlation.
- **Section 3.9: Validation Strategy:** Benchmark dataset comparisons, multi-regime sensitivity analysis, task-specific eligibility filtering, and sample size audits.
- **Section 4.2: Individual Component Parts:** Pipeline architecture linking ingestion, cleaning, entity normalization, filtering, statistical inference, visualization, and reproducible export.
- **Section 5.2: Functional Requirements (FR-06 to FR-10):**
  - **FR-06:** Multi-country skill demand percentage comparison with clear denominators ($N_c$).
  - **FR-07:** Visual skill demand comparison and 2D intensity heatmap.
  - **FR-08:** Disclosed salary distribution comparison with local currency preservation.
  - **FR-09:** Cross-national skill-profile similarity matrix with multiple distance metrics.
  - **FR-10:** Exact-value data tables and reproducible CSV exports.
- **Section 5.3: Non-Functional Requirements:** Reproducibility, traceability, scientific honesty regarding missing/sparse data, and accessibility.

---

## 3. Visualization Audit Table

Each visualization requirement was audited against the codebase and empirical datasets prior to and following corrective enhancements:

| # | Visualization / Feature | Pre-Audit Status | Post-Enhancement Status | Implementation File Path | Key Functions / Components | Primary Empirical Data Source |
|---|-------------------------|------------------|-------------------------|--------------------------|----------------------------|-------------------------------|
| 1 | **Regional Skill-Demand Comparison Chart** | PARTIAL | **PASS** | [`src/analytics/regional_charts.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_charts.py), [`src/analytics/regional_dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_dashboard_view.py) | `build_skill_demand_bar_chart()`, `calculate_skill_demand_percentages()` | `data/analysis/regional/` (Harmonized multi-market dataset, $N=137$) |
| 2 | **Regional Skill-Demand Heatmap** | MISSING | **PASS** | [`src/analytics/regional_charts.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_charts.py), [`src/analytics/regional_dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_dashboard_view.py) | `build_skill_demand_heatmap()` | Aligned Canonical Skill Matrix (220 records, 55 skills × 4 countries) |
| 3 | **Salary & Compensation Comparison Chart** | MISSING | **PASS** | [`src/analytics/regional_charts.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_charts.py), [`src/analytics/regional_dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_dashboard_view.py) | `build_salary_interval_chart()`, `analyze_regional_salaries()` | Disclosed salary subsets (LKR: 2, INR: 12, SGD: 24, MYR: 13) |
| 4 | **Country-to-Country Similarity Matrix** | PARTIAL | **PASS** | [`src/analytics/regional_charts.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_charts.py), [`src/analytics/regional_dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_dashboard_view.py) | `build_country_similarity_matrix()`, `calculate_country_similarities()` | Aligned Canonical Skill Vectors ($D=55$ canonical skills) |
| 5 | **Exact-Value Analytical Tables** | PASS | **PASS** | [`src/analytics/regional_dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_dashboard_view.py) | `render_custom_table()`, `st.dataframe()` | Output DataFrames (`demand_df`, `gap_df`, `country_salary`, `sim_df`) |
| 6 | **Pipeline & Architecture Diagrams** | MISSING | **PASS** | [`src/analytics/regional_dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_dashboard_view.py) | Mermaid Flowchart in Top Expander | Documented system architecture |
| 7 | **Sample Size, Denominators & Observation Period** | PARTIAL | **PASS** | [`src/analytics/regional_dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_dashboard_view.py), [`src/analytics/regional_charts.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_charts.py) | In-UI Alert Banners, Chart Subtitles, Tooltips | Observation Period: August – October 2026; Denominators: LK=45, IN=22, SG=24, MY=15 |

---

## 4. Exact Implementation Paths and Functions

### 4.1 Analytics Engine (`src/analytics/`):
- **[`src/analytics/regional_analysis.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_analysis.py):**
  - `load_regional_market_data()`: Harmonizes multi-market raw data into an ISO-standard schema.
  - `filter_records_with_provenance()`: Enforces task-specific eligibility filtering (general, skill, salary) with reason tracking.
  - `calculate_skill_demand_percentages()`: Calculates country-level demand percentages with Wilson Score 95% confidence intervals and anti-inflation unique skill counting per posting.
  - `calculate_skill_gaps()`: Computes two-proportion pooled $z$-tests, confidence intervals for percentage point divergence, and flags zero-mention extraction artifacts.
  - `analyze_regional_salaries()`: Computes parametric and non-parametric compensation statistics (median, IQR, min, max) preserving nominal local currencies.
  - `calculate_country_similarities()`: Computes multidimensional vector Cosine similarity, Top-10 Jaccard overlap, and Spearman rank order correlation across national profiles.
  - `run_regional_sensitivity_analysis()`: Executes 5-regime sensitivity testing.
  - `build_exclusion_funnel()`: Generates attrition funnels across task stages.

### 4.2 Visualization Builders (`src/analytics/`):
- **[`src/analytics/regional_charts.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_charts.py):**
  - `build_skill_demand_bar_chart()`: Altair grouped bar chart with focal country sorting, interactive tooltips, and country colors.
  - `build_skill_demand_heatmap()`: Altair 2D intensity heatmap with full rectangular grid guarantees and text value overlays.
  - `build_salary_interval_chart()`: Altair horizontal interval/range plots with independent currency axes, IQR bars, and median ticks.
  - `build_country_similarity_matrix()`: Altair 4×4 symmetric similarity heatmap with metric selector, diagonal = 1.0000, and text overlays.

### 4.3 User Interface (`src/analytics/regional_dashboard_view.py`):
- **[`src/analytics/regional_dashboard_view.py`](file:///Users/gavidurushela/Research/tool/J26_SE_355/src/analytics/regional_dashboard_view.py):**
  - Renders the Comparative Regional IT Labour-Market Analysis view within Streamlit (Tab 10 in main navigation).
  - Integrates the Pipeline Architecture expander, Executive KPI summary cards, and 6 dedicated analytical sub-tabs.

---

## 5. Actual Data Sources and Mathematical Formulas

### 5.1 Data Sources and Empirical Volume
- **Total Ingested Postings:** 137 records
  - 🇱🇰 Sri Lanka (Focal Market): 59 records (itpro.lk, topjobs.lk)
  - 🇮🇳 India: 31 records (shine.com, timesjobs.com)
  - 🇸🇬 Singapore: 25 records (jobstreet.com.sg, nodeflair.com)
  - 🇲🇾 Malaysia: 20 records (jobstreet.com.my, hiredly.com)
  - Unknown/Excluded: 2 records
- **Skill-Eligible Denominators ($N_c$):**
  - Sri Lanka: $N_{LK} = 45$ eligible vacancies
  - India: $N_{IN} = 22$ eligible vacancies
  - Singapore: $N_{SG} = 24$ eligible vacancies
  - Malaysia: $N_{MY} = 15$ eligible vacancies
- **Observation Window:** August 2026 – October 2026

### 5.2 Mathematical Formulas

#### A. Canonical Skill Demand Percentage
$$\text{Demand}_c(s) = \left(\frac{k_{c,s}}{N_c}\right) \times 100$$
Where:
- $k_{c,s}$ = Number of eligible IT advertisements in country $c$ mentioning canonical skill $s$ at least once.
- $N_c$ = Total eligible IT advertisements in country $c$ for the skill-demand task.

#### B. Wilson Score 95% Confidence Interval
$$\hat{p} = \frac{k_{c,s}}{N_c}, \quad \tilde{n} = N_c + z^2, \quad \tilde{p} = \frac{k_{c,s} + \frac{1}{2}z^2}{\tilde{n}}$$
$$\text{CI}_{95\%} = \tilde{p} \pm \frac{z}{\tilde{n}} \sqrt{N_c \hat{p}(1 - \hat{p}) + \frac{z^2}{4}}, \quad \text{where } z = 1.96$$

#### C. Skill Gap Divergence and Two-Proportion $z$-Test
$$\text{Gap}_{LK - c}(s) = \left(\hat{p}_{LK,s} - \hat{p}_{c,s}\right) \times 100 \quad \text{(percentage points)}$$
$$p_{\text{pooled}} = \frac{k_{LK,s} + k_{c,s}}{N_{LK} + N_c}, \quad \text{SE}_{\text{pool}} = \sqrt{p_{\text{pooled}}(1 - p_{\text{pooled}})\left(\frac{1}{N_{LK}} + \frac{1}{N_c}\right)}$$
$$z = \frac{\hat{p}_{LK,s} - \hat{p}_{c,s}}{\text{SE}_{\text{pool}}}, \quad p = \text{erfc}\left(\frac{|z|}{\sqrt{2}}\right)$$

#### D. Multidimensional Profile Similarities
1. **Cosine Similarity:**
   $$\text{Cosine}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|} = \frac{\sum_{i=1}^D u_i v_i}{\sqrt{\sum_{i=1}^D u_i^2} \sqrt{\sum_{i=1}^D v_i^2}}$$
2. **Jaccard Similarity (Top-10 Skills):**
   $$J(A, B) = \frac{|T_{10}(A) \cap T_{10}(B)|}{|T_{10}(A) \cup T_{10}(B)|}$$
3. **Spearman Rank Correlation:**
   $$\rho = \frac{\text{Cov}(\text{Rank}(\mathbf{u}), \text{Rank}(\mathbf{v}))}{\sigma_{\text{Rank}(\mathbf{u})} \sigma_{\text{Rank}(\mathbf{v})}}$$

---

## 6. Audit of Pre-Existing Defects and Missing Features

Prior to this intervention, the following defects and omissions existed in the codebase:

1. **Missing 2D Skill Demand Heatmap (CRITICAL PROPOSAL GAP):**  
   The UI offered only an unsorted default Streamlit bar chart (`st.bar_chart(pivot_demand.head(15))`). No 2D intensity heatmap existed in the application.
2. **Missing Salary Visual Chart (CRITICAL PROPOSAL GAP):**  
   The Salary & Compensation sub-tab displayed only an HTML summary table. There was no visual interval, range, or distribution chart comparing compensation across markets.
3. **Missing 4×4 Country Similarity Matrix Heatmap (CRITICAL PROPOSAL GAP):**  
   Profile similarities were presented as a flat 6-row pairwise table. The 4×4 symmetric matrix heatmap required by Proposal Section 3.6 was not rendered.
4. **Spurious Statistical Significance from Crawler Artifacts (METHODOLOGICAL DEFECT):**  
   Because Indian job cards on Shine.com frequently lacked full descriptive bodies, 45 canonical skills (e.g., Git, JavaScript, Teamwork, CSS, HTML) had 0 extracted mentions in India ($k_{IN} = 0$). In `calculate_skill_gaps()`, two-proportion $z$-tests generated $z = 4.138$ ($p = 0.0000$) for Teamwork, $z = 3.733$ ($p = 0.0002$) for Git, and $z = 3.469$ ($p = 0.0005$) for JavaScript. The dashboard labeled these crawler under-extraction artifacts as **"Statistically Meaningful"**!
5. **Missing Architecture Diagram in Dashboard:**  
   The 6-stage analytical pipeline connecting data collection, normalization, filtering, statistical inference, and validation was absent from the live dashboard.
6. **Incomplete Analytical Table Exports:**  
   Detailed skill-demand tables with exact confidence intervals and pairwise similarity matrices lacked dedicated download actions.

---

## 7. Changes Implemented

1. **Created Visualization Module (`src/analytics/regional_charts.py`):**
   - Implemented `build_skill_demand_bar_chart()` with custom country color mapping, focal country sorting, interactive tooltips, and explicit denominators.
   - Implemented `build_skill_demand_heatmap()` with complete rectangular grid guarantees, text value overlays, and unobserved data handling.
   - Implemented `build_salary_interval_chart()` with independent currency scales, min-to-max range rules, IQR bars, median tick marks, and small-sample alerts.
   - Implemented `build_country_similarity_matrix()` with 4×4 symmetric cell construction, metric selection, and exact decimal text overlays.

2. **Corrected Spurious Significance in Engine (`src/analytics/regional_analysis.py`):**
   - Added artifact detection logic:
     ```python
     is_zero_comparator_artifact = (k2 == 0) and (n2 < 30) and is_sig
     is_zero_focal_artifact = (k1 == 0) and (n1 < 30) and is_sig
     is_artifact = is_zero_comparator_artifact or is_zero_focal_artifact
     if is_artifact:
         evidence_status = "Data Collection Artifact (Unverified)"
     elif is_sig and not is_unstable:
         evidence_status = "Statistically Meaningful"
     else:
         evidence_status = "Indeterminate / Expected Sampling Noise"
     ```
   - Added `zero_comparator_artifact` boolean to `calculate_skill_gaps()` output schema.

3. **Enhanced User Interface (`src/analytics/regional_dashboard_view.py`):**
   - Added top-level expandable architecture section with Mermaid flowchart and component mapping.
   - Enhanced Sub-Tab 1 with visualization mode switcher (`Grouped Bar Chart`, `Skill Demand Heatmap`, `Dual View`), Top-N slider, category selector, scraper artifact status pills, and expandable exact-value table.
   - Enhanced Sub-Tab 3 with Sri Lanka salary disclosure warning callout, Altair salary range interval chart, and role salary export.
   - Enhanced Sub-Tab 4 with similarity metric selector (`Cosine`, `Jaccard`, `Spearman`), Altair 4×4 symmetric matrix heatmap, and pairwise export.
   - Enhanced Sub-Tab 6 with download buttons for all 6 reproducible CSV artifacts.

4. **Created Automated Test Suite (`tests/test_regional_visualizations.py`):**
   - Implemented 5 unit tests validating chart marks, encoding dimensions, tooltips, grid completeness, currency isolation, matrix symmetry, and artifact detection.

---

## 8. Tests Executed and Results

The entire test suite was executed offline without network access:

```bash
python3 -m unittest discover tests
```

**Results:**
- **Tests Discovered:** 229 tests (including 5 new visualization tests in `tests/test_regional_visualizations.py` and 13 engine tests in `tests/test_regional_analysis.py`).
- **Passing:** 229 tests (100% pass rate).
- **Failures:** 0.
- **Errors:** 0.
- **Execution Duration:** 2.357 seconds.

---

## 9. Remaining Limitations and Data-Quality Warnings

In adherence to research safety rules, the following empirical limitations are transparently documented:

1. **Indian Job Market Extraction Limitation:**
   Indian records ($N=22$ eligible) originate predominantly from Shine.com. Due to job card brevity, mean extracted skills per posting is 1.16 (compared to 7.44 in Singapore and 4.49 in Sri Lanka). 45 canonical skills show 0.0% demand in India purely as a crawler artifact. These are now explicitly flagged in the UI as `Artifact (0-count)`.
2. **Sri Lanka Salary Scarcity:**
   Only 2 out of 57 advertisements (3.51%) in Sri Lanka disclose numerical compensation (LKR 50,000 and LKR 75,000 monthly). Cross-national salary comparisons involving Sri Lanka carry extreme statistical uncertainty.
3. **Nominal Currency Isolation:**
   Local currencies (LKR, INR, SGD, MYR) are strictly isolated. Purchasing power parity (PPP) and taxation differences are not modeled.

---

## 10. Final Proposal-Compliance Assessment

| Proposal Section | Functional Requirement | Compliance Status | Evidence / Verification |
|------------------|------------------------|-------------------|-------------------------|
| Section 3.6 | FR-06: Regional Skill Demand % | **COMPLIANT (PASS)** | Implemented with Wilson 95% CIs and denominators ($N_c$) |
| Section 3.6 | FR-07: Grouped Bar Chart & 2D Heatmap | **COMPLIANT (PASS)** | Altair grouped bar chart & 2D interactive heatmap with exact % overlay |
| Section 3.5 | FR-08: Salary Comparison Chart | **COMPLIANT (PASS)** | Altair horizontal interval/range plot with local currency isolation |
| Section 3.6 | FR-09: Country Similarity Matrix | **COMPLIANT (PASS)** | 4×4 symmetric matrix heatmap (Cosine, Jaccard, Spearman) |
| Section 3.8 | FR-10: Analytical Tables & Exports | **COMPLIANT (PASS)** | Exact-value tables with Wilson CIs and reproducible CSV downloads |
| Section 4.2 | Pipeline Architecture Diagram | **COMPLIANT (PASS)** | Interactive Mermaid pipeline diagram in dashboard expander |
| Section 3.9 | Scientific Honesty & Validation | **COMPLIANT (PASS)** | Zero-count artifact detection, Sri Lanka sample alerts, 5-regime sensitivity |

**Conclusion:** The Comparative Regional Market Analysis visualizations are fully implemented, connected to empirical analytical data, mathematically correct, and visible in the Streamlit user interface.
