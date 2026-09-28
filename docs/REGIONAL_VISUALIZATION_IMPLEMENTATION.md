# Comparative Regional Analysis Visualizations: Implementation and User Guide

**Project ID:** J26-SE-355  
**Project Title:** Quantitative Analysis Framework for Technical Skill Identification for IT Sector Jobs  
**Individual Research Component:** Comparative Regional Market Analysis  
**Student Name:** E. M. G. R. Ekanayaka  
**Student ID:** IT23213944  
**Date:** October 2026  
**Git Branch:** `feature/regional-market-data-validation`  

---

## 1. Available Visualizations and Their UI Locations

All regional visualizations are situated inside **Tab 10: Comparative Regional Analysis** of the main Streamlit application (`app.py` via `src/analytics/regional_dashboard_view.py`).

| # | Visualization Component | UI Location / Tab | Chart Type | Library | Purpose |
|---|-------------------------|-------------------|------------|---------|---------|
| 1 | **Regional Pipeline Architecture Diagram** | Top Expander: *📐 Regional Analysis Pipeline & System Architecture* | Mermaid Flowchart | Streamlit Markdown / Mermaid | Visualizes the 6-stage analytical pipeline from ingestion to export. |
| 2 | **Regional Skill-Demand Grouped Bar Chart** | Sub-Tab 1: *1. Skill Demand & Gaps* (Mode: Grouped Bar Chart) | Grouped Bar Chart | Altair 6.0 (`mark_bar`) | Compares canonical skill demand % across Sri Lanka, India, Singapore, and Malaysia. |
| 3 | **Regional Skill-Demand 2D Heatmap** | Sub-Tab 1: *1. Skill Demand & Gaps* (Mode: Skill Demand Heatmap) | 2D Density Heatmap | Altair 6.0 (`mark_rect` + `mark_text`) | Visual matrix showing cross-country demand intensity with exact % cell labels. |
| 4 | **Disclosed Salary Range & Interval Plots** | Sub-Tab 3: *3. Salary & Compensation* | Horizontal Range / Interval Plot | Altair 6.0 (`mark_rule` + `mark_bar` + `mark_tick`) | Shows local currency min, max, IQR (25th–75th percentile), and median monthly compensation. |
| 5 | **4×4 Country-to-Country Similarity Matrix** | Sub-Tab 4: *4. Profile Similarities* | 4×4 Symmetric Matrix Heatmap | Altair 6.0 (`mark_rect` + `mark_text`) | Displays pairwise profile similarity scores with metric selector (Cosine, Jaccard, Spearman). |
| 6 | **Exact-Value Analytical Tables** | Sub-Tabs 1, 2, 3, 4, 5, 6 | Styled HTML & Interactive DataFrames | Custom Theme Tables + Streamlit DataFrames | Displays numerical values, confidence intervals, sample counts, and statistical statuses. |

---

## 2. Calculation Methodology

### 2.1 Regional Skill Demand Percentage
Each job posting is evaluated against the canonical skill taxonomy ($D=100+$ skills). To prevent frequency inflation, each advertisement is counted **at most once per canonical skill**:

$$\text{Demand}_c(s) = \left(\frac{k_{c,s}}{N_c}\right) \times 100$$

- $k_{c,s}$: Number of eligible advertisements in country $c$ mentioning canonical skill $s$.
- $N_c$: Total eligible IT advertisements in country $c$ for the skill-demand task stage.

### 2.2 Wilson Score 95% Confidence Intervals
Given small sample sizes in regional comparators, classical normal approximations ($\hat{p} \pm 1.96 \sqrt{\hat{p}(1-\hat{p})/n}$) fail near boundaries. The Wilson Score interval is applied:

$$\tilde{n} = N_c + 1.96^2 = N_c + 3.8416$$
$$\tilde{p} = \frac{k_{c,s} + 1.9208}{\tilde{n}}$$
$$\text{CI}_{95\%} = \tilde{p} \pm \frac{1.96}{\tilde{n}} \sqrt{N_c \hat{p}(1 - \hat{p}) + 0.9604}$$

### 2.3 Skill Gap Divergence and Artifact-Protected $z$-Test
The percentage point gap between Sri Lanka ($LK$) and comparator country $c$ is:

$$\text{Gap}_{LK - c}(s) = \text{Demand}_{LK}(s) - \text{Demand}_c(s)$$

A two-proportion pooled $z$-test computes statistical divergence:

$$p_{\text{pool}} = \frac{k_{LK,s} + k_{c,s}}{N_{LK} + N_c}, \quad \text{SE}_{\text{pool}} = \sqrt{p_{\text{pool}}(1 - p_{\text{pool}})\left(\frac{1}{N_{LK}} + \frac{1}{N_c}\right)}$$
$$z = \frac{\hat{p}_{LK,s} - \hat{p}_{c,s}}{\text{SE}_{\text{pool}}}, \quad p = \text{erfc}\left(\frac{|z|}{\sqrt{2}}\right)$$

**Scraper Artifact Protection:**  
If a comparator has zero mentions ($k_c = 0$) and small sample size ($N_c < 30$), the gap is flagged as `zero_comparator_artifact = True` and labeled `Artifact (0-count)` rather than claiming genuine statistical significance.

### 2.4 Salary Normalization
Contractual salary text is extracted and normalized to monthly equivalents:
- **Annual:** $\text{Salary} / 12$
- **Hourly:** $\text{Salary} \times 160$
- **Weekly:** $\text{Salary} \times 4.333$
- **Indian Formats:** Parsed via regex for Lakhs ($10^5$) and Crores ($10^7$).
- **Currencies Isolated:** LKR, INR, SGD, and MYR are never aggregated onto a common axis without explicit notation. Undisclosed salaries are never converted to zero.

### 2.5 Country Similarity Metrics
Country skill demand vectors $\mathbf{u}, \mathbf{v} \in \mathbb{R}^{55}$ are compared using:
1. **Cosine Similarity:** Measures proportional vector alignment:
   $$\text{Cosine}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$$
2. **Jaccard Similarity (Top 10):** Overlap between top 10 most demanded skills:
   $$J(A, B) = \frac{|T_{10}(A) \cap T_{10}(B)|}{|T_{10}(A) \cup T_{10}(B)|}$$
3. **Spearman Rank Correlation:** Monotonic concordance of skill demand rankings:
   $$\rho = \text{Corr}(\text{Rank}(\mathbf{u}), \text{Rank}(\mathbf{v}))$$

---

## 3. Data Sources and Denominators

The empirical dataset consists of **137 harmonized IT job advertisements** collected from foreign and local portals:

| Labor Market | Primary Portals | Ingested Ads | Task: General ($N$) | Task: Skill ($N$) | Task: Salary ($N$) | Salary Disclosure % |
|--------------|-----------------|--------------|----------------------|-------------------|--------------------|---------------------|
| 🇱🇰 **Sri Lanka (Focal)** | itpro.lk, topjobs.lk | 59 | 57 | **45** | 2 | 3.51% |
| 🇮🇳 **India** | shine.com, timesjobs.com | 31 | 28 | **22** | 12 | 42.86% |
| 🇸🇬 **Singapore** | jobstreet.com.sg, nodeflair.com | 25 | 25 | **24** | 24 | 96.00% |
| 🇲🇾 **Malaysia** | jobstreet.com.my, hiredly.com | 20 | 20 | **15** | 13 | 65.00% |
| **Total** | Multi-Portal Harmonized | **137** | **130** | **106** | **51** | **39.23%** |

*Observation Period:* August 2026 – October 2026.

---

## 4. How to Interpret the Visualizations

### 4.1 Grouped Bar Chart (Sub-Tab 1)
- **X-Axis:** Canonical skills, ordered by Sri Lanka demand descending.
- **Y-Axis:** Demand percentage ($0\%$ to $100\%$).
- **Color Legend:**
  - 🇱🇰 Sri Lanka: Sky Blue (`#38BDF8`)
  - 🇮🇳 India: Amber (`#F59E0B`)
  - 🇸🇬 Singapore: Emerald (`#10B981`)
  - 🇲🇾 Malaysia: Purple (`#A78BFA`)
- **Hover Tooltip:** Shows canonical skill, category, country, demand %, mentions ($k$), sample size ($N$), and Wilson 95% confidence interval $[LB\%, UB\%]$.

### 4.2 2D Skill Demand Heatmap (Sub-Tab 1)
- **Rows:** Canonical skills sorted by focal market demand.
- **Columns:** The 4 target countries in standard research order.
- **Color Intensity:** Deep blue gradient proportional to demand rate.
- **Cell Labels:** Exact demand percentages (e.g., `51.1%`, `0.0%`).
- **Interpretation:** Quickly reveals cross-border competency clusters (e.g., Python high across all markets; Java dominant in India/Malaysia).

### 4.3 Salary Interval & Range Plot (Sub-Tab 3)
- **Whiskers (Rule):** Extend from Minimum to Maximum disclosed monthly salary in that country's currency.
- **Solid Bar:** Interquartile Range (IQR, 25th percentile to 75th percentile).
- **White Marker:** Median monthly compensation.
- **Interpretation:** Conveys the central tendency and contractual salary dispersion while preserving native currencies (LKR, INR, SGD, MYR).

### 4.4 4×4 Country Similarity Matrix Heatmap (Sub-Tab 4)
- **Rows & Columns:** The 4 labor markets.
- **Diagonal Cells:** Exactly `1.0000` (perfect self-similarity).
- **Off-Diagonal Cells:** Symmetric pairwise scores ($M_{ij} = M_{ji}$).
- **Metric Selector:** Allows toggling between Cosine Similarity, Jaccard Index (Top 10), and Spearman Rank Correlation.

---

## 5. How to Use Filters and Exports

### 5.1 Interactive Filters
- **Visualization Mode Switcher:** Toggle between *📊 Grouped Bar Chart*, *🔥 Skill Demand Heatmap*, and *📋 Dual View (Chart + Heatmap)* in Sub-Tab 1.
- **Skill Category Filter:** Filter skills by Programming Languages, Cloud & DevOps, Databases, Frameworks, or Soft Skills.
- **Top-N Slider:** Adjust the number of skills rendered (5 to 35 skills).
- **Comparator Radio:** Select India, Singapore, or Malaysia to compute bilateral skill gaps relative to Sri Lanka.
- **Similarity Metric Selector:** Toggle the 4×4 heatmap between Cosine, Jaccard, and Spearman measures.

### 5.2 Reproducible Data Exports
Dedicated CSV download buttons are available across the dashboard:
1. `📥 Export All Skill Demand Records (CSV)`: In Sub-Tab 1 expander (`canonical_skill_demand_regional_all.csv`).
2. `📥 Export Role Salaries (CSV)`: In Sub-Tab 3 (`role_salaries_regional.csv`).
3. `📥 Export Pairwise Similarities (CSV)`: In Sub-Tab 4 (`country_skill_profile_similarities.csv`).
4. `📥 Skill Demand CSV`, `📥 Skill Gaps CSV`, `📥 Salary Summary CSV`, `📥 Profile Similarities CSV`, `📥 Eligibility Funnel CSV`, `📥 Sensitivity Analysis CSV`: In Sub-Tab 6.

---

## 6. How to Run the Application and Automated Tests

### 6.1 Running the Streamlit Application
From the repository root:
```bash
python3 -m streamlit run app.py
```
Navigate to `http://localhost:8501`, log in if prompted, and click **🌐 Comparative Regional Analysis** (Tab 10) in the left sidebar.

### 6.2 Running Automated Tests
Run the entire offline test suite:
```bash
python3 -m unittest discover tests
```

To run specifically the regional analysis and visualization tests:
```bash
python3 -m unittest tests/test_regional_analysis.py tests/test_regional_visualizations.py
```

Expected result:
```
Ran 18 tests in 0.450s
OK
```

---

## 7. Known Limitations and Data-Quality Warnings

1. **Crawler Extraction Asymmetry in India (Shine.com):**  
   Due to abbreviated job card summaries on Shine.com, several canonical skills (Git, JavaScript, HTML, CSS) were not captured in the Indian sample ($N=22$). The system explicitly detects this zero-count condition and flags it as a `Data Collection Artifact (Unverified)` rather than reporting false statistical significance.
2. **Sri Lanka Compensation Scarcity:**  
   Sri Lanka has a salary disclosure rate of only $3.51\%$ ($N=2$ disclosed advertisements). Compensation charts display an active `Small Sample (N<10)` warning.
3. **Purchasing Power Parity (PPP):**  
   Nominal contractual salaries are presented in local currencies. Nominal figures reflect local currency cash offers and do not establish purchasing power parity or living standards.
