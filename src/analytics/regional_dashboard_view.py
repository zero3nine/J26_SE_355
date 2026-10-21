"""
Streamlit View Component for Comparative Regional IT Labor-Market Analysis.
Project: IT Job Market Intelligence Tool (J26_SE_355).
Research Component: Comparative Regional Market Analysis.

Focal Market: Sri Lanka (LK)
Comparators: India (IN), Singapore (SG), Malaysia (MY)
"""

from __future__ import annotations

import pathlib
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from src.analytics.regional_analysis import (
    COMPARATOR_MARKETS,
    DEFAULT_OUTPUT_DIR,
    FOCAL_MARKET,
    TARGET_REGIONAL_COUNTRIES,
    EligibilityConfig,
    analyze_regional_salaries,
    build_exclusion_funnel,
    calculate_country_similarities,
    calculate_skill_demand_percentages,
    calculate_skill_gaps,
    compare_regional_roles,
    filter_records_with_provenance,
    load_regional_market_data,
    run_regional_sensitivity_analysis,
)
import altair as alt

from src.analytics.regional_charts import (
    build_country_similarity_matrix,
    build_salary_interval_chart,
    build_skill_demand_bar_chart,
    build_skill_demand_heatmap,
)
from theme import make_status_pill, render_custom_table


def render_regional_analysis_view(current_dir: pathlib.Path):
    """Renders the comprehensive Comparative Regional IT Labor-Market Analysis dashboard view."""
    st.subheader("Comparative Regional IT Labour-Market Analysis")
    st.markdown(
        "<div style='font-size:13px; color:#94A3B8; margin-top:-8px; margin-bottom:20px;'>"
        "Empirical quantitative comparison of technical skill demand, role distributions, "
        "and compensation disclosure across <b>Sri Lanka (Focal Market)</b>, <b>India</b>, "
        "<b>Singapore</b>, and <b>Malaysia</b>."
        "</div>",
        unsafe_allow_html=True,
    )

    # 1. Load Harmonized Data or check disk cache
    data_dir = current_dir / "data" / "analysis" / "regional"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Check if analysis has been run in session state or on disk
    if "regional_analysis_data" not in st.session_state:
        with st.spinner("Loading and harmonizing multi-market datasets..."):
            try:
                df = load_regional_market_data()
                st.session_state.regional_raw_df = df
                st.session_state.regional_config = EligibilityConfig()
                st.session_state.regional_analysis_data = True
            except Exception as e:
                st.error(f"Failed to load regional market data: {e}")
                return

    df = st.session_state.regional_raw_df
    config = st.session_state.regional_config

    # Top Control Bar
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            st.markdown(
                "**Markets Under Study:** "
                "<span style='background:#1E293B; color:#38BDF8; padding:3px 8px; border-radius:12px; font-size:12px;'>🇱🇰 Sri Lanka (Focal)</span> "
                "<span style='background:#1E293B; color:#F59E0B; padding:3px 8px; border-radius:12px; font-size:12px;'>🇮🇳 India</span> "
                "<span style='background:#1E293B; color:#10B981; padding:3px 8px; border-radius:12px; font-size:12px;'>🇸🇬 Singapore</span> "
                "<span style='background:#1E293B; color:#A78BFA; padding:3px 8px; border-radius:12px; font-size:12px;'>🇲🇾 Malaysia</span>",
                unsafe_allow_html=True,
            )
        with c2:
            st.caption(f"Harmonized Records: **{len(df)}**")
        with c3:
            if st.button("🔄 Refresh Regional Analysis"):
                with st.spinner("Re-evaluating pipeline..."):
                    df = load_regional_market_data()
                    st.session_state.regional_raw_df = df
                    st.success("Pipeline refreshed!")

    # System Architecture & Analytical Pipeline Expander
    with st.expander("📐 Regional Analysis Pipeline & System Architecture", expanded=False):
        st.markdown(
            """
            <div style="font-size:13px; color:#CBD5E1; margin-bottom:12px;">
            The Comparative Regional Labor-Market Analysis component implements a multi-stage quantitative pipeline
            designed for cross-national robustness, strict entity normalization, and transparent data-quality auditing.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
```mermaid
flowchart TD
    subgraph S1["Stage 1: Multi-Country Ingestion"]
        LK["Sri Lanka (itpro.lk, topjobs.lk)"]
        IN["India (shine.com, timesjobs.com)"]
        SG["Singapore (jobstreet.com.sg, nodeflair.com)"]
        MY["Malaysia (jobstreet.com.my, hiredly.com)"]
    end

    subgraph S2["Stage 2: Harmonization & Pre-Processing"]
        NORM["HTML Stripping & Content Deduplication"]
        SSRF["SSRF-Protected Domain Registry"]
        CLASS["IT vs. Non-IT Role Classifier"]
    end

    subgraph S3["Stage 3: Normalization & Canonical Mapping"]
        SKILL["Canonical Skill Taxonomy (100+ standard skills)"]
        SAL["Salary Normalizer (Regex, Currencies, Period Standardizer)"]
        LOC["ISO-3166 Country & Region Normalizer"]
    end

    subgraph S4["Stage 4: Task-Specific Eligibility Filtering"]
        E_GEN["General Eligibility (Valid IT Job, ISO Country)"]
        E_SKL["Skill Eligibility (At least 1 extracted skill)"]
        E_SAL["Salary Eligibility (Disclosed & parsable period)"]
    end

    subgraph S5["Stage 5: Quantitative Statistical Engine"]
        DEM["Demand % = (k / N) × 100 with Wilson 95% CIs"]
        GAP["Two-Proportion z-Tests & Zero-Count Artifact Detector"]
        DIST["Isolated Local Currency Distributions (Median, IQR, Range)"]
        SIM["4×4 Profile Similarities (Cosine, Jaccard, Spearman)"]
    end

    subgraph S6["Stage 6: Interactive Visualizations & Audited Deliverables"]
        CHART["Interactive Grouped Bar Chart & 2D Demand Heatmap"]
        INT_SAL["Local Currency Range & Interval Charts"]
        MAT["4×4 Symmetric Similarity Matrix Heatmap"]
        EXP["Reproducible CSV Exports & Funnel Audit"]
    end

    S1 --> S2 --> S3 --> S4 --> S5 --> S6
```
            """
        )
        st.markdown(
            """
            **Pipeline Architecture Components (Proposal Sections 3.5, 3.6, 3.8, 4.2):**
            - **1. Multi-Country Ingestion:** Standardized scraping adapters with rate-limiting and anti-blocking measures.
            - **2. Harmonization & Validation:** Text cleaning, title/description integrity verification, and IT role scoping.
            - **3. Normalization:** Canonical skill taxonomy matching (ESCO/custom), monthly nominal salary normalization (preserving LKR, INR, SGD, MYR), and ISO-3166-1 country resolution.
            - **4. Task-Specific Eligibility Filtering:** Independent inclusion criteria prevent salary disclosure scarcity (3.5% in LK) from distorting skill demand samples.
            - **5. Statistical Inference:** Empirical skill demand rates with Wilson score 95% confidence intervals, two-proportion $z$-tests with crawler extraction artifact flags, and multidimensional profile similarity.
            - **6. Verification & Reporting:** Complete transparency through exact-value tables, confidence intervals, sample sizes, and reproducible CSV exports.
            """
        )

    # 2. Executive KPI Cards
    eligible_general, _, _ = filter_records_with_provenance(df, config, task="general")
    eligible_skill, _, _ = filter_records_with_provenance(df, config, task="skill")
    eligible_salary, _, _ = filter_records_with_provenance(df, config, task="salary")

    lk_count = len(eligible_general[eligible_general["country"] == FOCAL_MARKET])
    comp_count = len(eligible_general[eligible_general["country"] != FOCAL_MARKET])
    overall_salary_cov = round(len(eligible_salary) / len(eligible_general) * 100.0, 1) if len(eligible_general) > 0 else 0.0

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
        <div class="kpi-card clean">
            <div class="kpi-label">Focal Market (Sri Lanka)</div>
            <div class="kpi-value">{lk_count}</div>
            <div class="kpi-trend"><span class="trend-up">Baseline ads</span></div>
        </div>
        <div class="kpi-card scraped">
            <div class="kpi-label">Regional Comparators</div>
            <div class="kpi-value">{comp_count}</div>
            <div class="kpi-trend"><span class="trend-up">IN, SG, MY ads</span></div>
        </div>
        <div class="kpi-card partial">
            <div class="kpi-label">Skill-Eligible Vacancies</div>
            <div class="kpi-value">{len(eligible_skill)}</div>
            <div class="kpi-trend"><span class="trend-neutral">Extracted competencies</span></div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Salary Disclosure Rate</div>
            <div class="kpi-value">{overall_salary_cov}%</div>
            <div class="kpi-trend"><span class="trend-up" style="color: #A78BFA;">{len(eligible_salary)} disclosed</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sub-tabs for deep quantitative exploration
    view_tab1, view_tab2, view_tab3, view_tab4, view_tab5, view_tab6 = st.tabs([
        "1. Skill Demand & Gaps",
        "2. Role Distribution",
        "3. Salary & Compensation",
        "4. Profile Similarities",
        "5. Sensitivity Analysis",
        "6. Eligibility Funnel & Audit",
    ])

    # --------------------------------------------------------------------------
    # Tab 1: Skill Demand & Gaps
    # --------------------------------------------------------------------------
    with view_tab1:
        st.subheader("Canonical Skill Demand (% of National Vacancies)")
        st.markdown(
            """
            <div style="background:#1E293B; border-left:4px solid #38BDF8; padding:10px 14px; border-radius:4px; font-size:12px; color:#E2E8F0; margin-bottom:16px;">
                <b>Observation Window:</b> August 2026 – October 2026 &nbsp;|&nbsp;
                <b>Sample Denominators (N):</b> 🇱🇰 Sri Lanka (N=45) &bull; 🇮🇳 India (N=22) &bull; 🇸🇬 Singapore (N=24) &bull; 🇲🇾 Malaysia (N=15) &nbsp;|&nbsp;
                <b>Formula:</b> <code>Demand % = (Eligible Ads Mentioning Skill / Total Country Eligible Ads) × 100</code> with Wilson 95% CIs.
            </div>
            """,
            unsafe_allow_html=True,
        )

        demand_df = calculate_skill_demand_percentages(df, config)

        if demand_df.empty:
            st.info("No skill demand records meet current eligibility criteria.")
        else:
            col_filt1, col_filt2, col_filt3 = st.columns([2, 1, 1])
            with col_filt1:
                sel_mode = st.radio(
                    "Visualization Mode",
                    ["📊 Grouped Bar Chart", "🔥 Skill Demand Heatmap", "📋 Dual View (Chart + Heatmap)"],
                    horizontal=True,
                )
            with col_filt2:
                categories = ["All Categories"] + sorted(demand_df["category"].unique())
                sel_cat = st.selectbox("Filter Category", categories)
            with col_filt3:
                top_k = st.slider("Top Skills to Display", 5, 35, 15, 5)

            # Render Visualizations using Altair
            if sel_mode == "📊 Grouped Bar Chart":
                chart = build_skill_demand_bar_chart(demand_df, focal_country=FOCAL_MARKET, top_n=top_k, selected_category=sel_cat)
                st.altair_chart(chart, use_container_width=True)
            elif sel_mode == "🔥 Skill Demand Heatmap":
                heat = build_skill_demand_heatmap(demand_df, focal_country=FOCAL_MARKET, top_n=top_k, selected_category=sel_cat)
                st.altair_chart(heat, use_container_width=True)
            else:
                chart = build_skill_demand_bar_chart(demand_df, focal_country=FOCAL_MARKET, top_n=top_k, selected_category=sel_cat)
                st.altair_chart(chart, use_container_width=True)
                heat = build_skill_demand_heatmap(demand_df, focal_country=FOCAL_MARKET, top_n=top_k, selected_category=sel_cat)
                st.altair_chart(heat, use_container_width=True)

            # Skill Gaps Table: Sri Lanka vs. Selected Comparator
            st.subheader("Skill Gap Divergence (Sri Lanka vs. Comparators)")
            sel_comp = st.radio("Select Comparator Country for Gap Analysis", list(COMPARATOR_MARKETS), horizontal=True)

            gap_df = calculate_skill_gaps(demand_df, focal_country=FOCAL_MARKET)
            comp_gaps = gap_df[gap_df["comparator_country"] == sel_comp]

            if not comp_gaps.empty:
                headers = [
                    "Canonical Skill",
                    "Category",
                    f"Sri Lanka %",
                    f"{sel_comp} %",
                    "Gap (pp)",
                    "95% CI (pp)",
                    "p-value",
                    "Evidence Status",
                ]
                rows = []
                for _, r in comp_gaps.head(25).iterrows():
                    is_sig = r["statistically_significant"]
                    is_art = r.get("zero_comparator_artifact", False)
                    if is_art:
                        status_pill = make_status_pill("Artifact (0-count)", "scraped")
                    elif is_sig and not r["small_sample_warning"]:
                        status_pill = make_status_pill("Significant", "clean")
                    elif r["small_sample_warning"]:
                        status_pill = make_status_pill("Indeterminate", "partial")
                    else:
                        status_pill = make_status_pill("Sampling Noise", "scraped")

                    rows.append([
                        str(r["skill_name"]),
                        str(r["category"]),
                        f"{r['focal_demand_pct']}%",
                        f"{r['comparator_demand_pct']}%",
                        f"{'+' if r['gap_pp'] > 0 else ''}{r['gap_pp']} pp",
                        f"[{r['gap_ci_lower_95']}, {r['gap_ci_upper_95']}]",
                        f"{r['p_value']:.4f}",
                        status_pill,
                    ])
                st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

            # Expandable Detailed Exact-Value Analytical Table
            with st.expander("📊 Complete Exact-Value Skill Demand Data Table & Export"):
                st.dataframe(
                    demand_df[[
                        "country", "skill_name", "category", "mention_count",
                        "eligible_ads_denominator", "demand_pct", "ci_lower_95", "ci_upper_95"
                    ]].rename(columns={
                        "country": "Country",
                        "skill_name": "Canonical Skill",
                        "category": "Category",
                        "mention_count": "Mentions (k)",
                        "eligible_ads_denominator": "Sample Size (N)",
                        "demand_pct": "Demand %",
                        "ci_lower_95": "95% CI Lower",
                        "ci_upper_95": "95% CI Upper",
                    }),
                    use_container_width=True,
                    height=300,
                )
                csv_demand_all = demand_df.to_csv(index=False)
                st.download_button(
                    "📥 Export All Skill Demand Records (CSV)",
                    csv_demand_all,
                    "canonical_skill_demand_regional_all.csv",
                    "text/csv",
                )

    # --------------------------------------------------------------------------
    # Tab 2: Role Distribution
    # --------------------------------------------------------------------------
    with view_tab2:
        st.subheader("IT Occupational Role Distributions Across Markets")
        st.markdown(
            "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>"
            "Job postings are classified into canonical IT roles using multi-keyword title and description matching. "
            "Ambiguous postings are explicitly audited as <code>Unclassified</code> rather than silently forced."
            "</p>",
            unsafe_allow_html=True,
        )

        role_counts, role_skills, unclass_summary = compare_regional_roles(df, config)

        col_r1, col_r2 = st.columns([3, 2])
        with col_r1:
            st.markdown("##### Role Frequency by Country")
            role_pivot = role_counts.pivot_table(index="role_name", columns="country", values="job_count", fill_value=0).astype(int)
            st.dataframe(role_pivot, height=350, use_container_width=True)

        with col_r2:
            st.markdown("##### Classification Quality Audit")
            u_headers = ["Country", "Total IT Jobs", "Unclassified", "Unclassified %", "Status"]
            u_rows = []
            for _, r in unclass_summary.iterrows():
                pill = make_status_pill(r["classification_quality"], "clean" if r["unclassified_pct"] < 15.0 else "partial")
                u_rows.append([
                    str(r["country"]),
                    str(r["total_it_jobs"]),
                    str(r["unclassified_count"]),
                    f"{r['unclassified_pct']}%",
                    pill,
                ])
            st.markdown(render_custom_table(u_headers, u_rows), unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Role-Segmented Skill Demand")
        all_roles = sorted(role_skills["role_name"].unique()) if not role_skills.empty else []
        if all_roles:
            selected_role = st.selectbox("Inspect Technical Skill Demand for Role", all_roles)
            role_demand_sub = role_skills[role_skills["role_name"] == selected_role]
            role_skill_pivot = role_demand_sub.pivot_table(index="skill_name", columns="country", values="demand_pct_in_role", fill_value=0.0)
            st.bar_chart(role_skill_pivot.head(10), height=350)

    # --------------------------------------------------------------------------
    # Tab 3: Salary & Compensation
    # --------------------------------------------------------------------------
    with view_tab3:
        st.subheader("Disclosed Compensation Distributions (Native Currencies)")
        st.markdown(
            """
            <div style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid #EF4444; padding: 12px 16px; border-radius: 4px; margin-bottom: 16px;">
                <b style="color: #F87171;">CRITICAL METHODOLOGICAL NOTICE:</b><br>
                <span style="font-size: 13px; color: #FCA5A5;">
                Nominal salaries reflect contractual cash offers in local currencies (LKR, INR, SGD, MYR) normalized to monthly equivalents.
                Nominal values <b>DO NOT</b> establish purchasing power parity (PPP), local taxation differences, or living standards.
                Undisclosed salaries are strictly excluded from denominators rather than converted to zero.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        country_salary, role_salary, rates_df = analyze_regional_salaries(df, config)

        # Focal Market (Sri Lanka) sample size warning banner
        st.markdown(
            """
            <div style="background: rgba(245, 158, 11, 0.15); border-left: 4px solid #F59E0B; padding: 10px 14px; border-radius: 4px; margin-bottom: 20px;">
                <b style="color: #F59E0B;">🇱🇰 SRI LANKA SALARY DISCLOSURE ADVISORY:</b><br>
                <span style="font-size: 12.5px; color: #FDE68A;">
                Only <b>2 out of 57 advertisements (3.51%)</b> in Sri Lanka disclose numerical compensation
                (Contractual offers: LKR 50,000 and LKR 75,000 monthly). Small sample warning is active (N &lt; 10).
                Cross-country compensation comparisons involving Sri Lanka carry extreme statistical uncertainty and must be treated with caution.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Disclosed Salary Interval & Range Visualization
        st.markdown("##### National Disclosed Salary Range Plots (Isolated Local Currencies)")
        st.caption("Whiskers: Min to Max Range | Filled Bar: Interquartile Range (IQR, 25th–75th Percentile) | White Marker: Median Monthly Equivalent.")
        salary_chart = build_salary_interval_chart(country_salary)
        st.altair_chart(salary_chart, use_container_width=True)

        st.markdown("##### National Salary Coverage & Distribution Summary")
        sal_headers = [
            "Country",
            "Currency",
            "Disclosed / Total",
            "Coverage %",
            "Median (Monthly)",
            "IQR (Monthly)",
            "Min - Max",
            "Sample Status",
        ]
        sal_rows = []
        for _, r in country_salary.iterrows():
            flag_pill = make_status_pill("Small Sample (N<10)", "partial") if r["small_sample_flag"] else make_status_pill("Stable", "clean")
            sal_rows.append([
                str(r["country"]),
                str(r["currency"]),
                f"{r['disclosed_salary_count']} / {r['total_eligible_ads']}",
                f"{r['disclosure_rate_pct']}%",
                f"{r['currency']} {r['median_salary']:,.2f}",
                f"{r['currency']} {r['iqr_salary']:,.2f}",
                f"{r['min_salary']:,.0f} - {r['max_salary']:,.0f}",
                flag_pill,
            ])
        st.markdown(render_custom_table(sal_headers, sal_rows), unsafe_allow_html=True)

        if not role_salary.empty:
            st.markdown("---")
            st.markdown("##### Monthly Salary Ranges by Comparable Role")
            st.dataframe(role_salary, height=250, use_container_width=True)
            csv_role_sal = role_salary.to_csv(index=False)
            st.download_button(
                "📥 Export Role Salaries (CSV)",
                csv_role_sal,
                "role_salaries_regional.csv",
                "text/csv",
            )

        st.markdown("---")
        with st.expander("ℹ️ Indicative Reference Exchange Rates (As of October 2026)"):
            st.caption("Rates provided solely for transparent audit conversion. Strictly prohibited from inferring economic living standards.")
            st.table(rates_df)

    # --------------------------------------------------------------------------
    # Tab 4: Profile Similarities
    # --------------------------------------------------------------------------
    with view_tab4:
        st.subheader("Cross-National Skill Demand Profile Similarities")
        st.markdown(
            "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>"
            "Computes multidimensional similarity between country-level canonical skill vectors.<br>"
            "<b>Cosine:</b> Proportional alignment of technical priorities. "
            "<b>Jaccard:</b> Overlap among top-10 in-demand skills. "
            "<b>Spearman:</b> Monotonic rank correlation."
            "</p>",
            unsafe_allow_html=True,
        )

        sim_df = calculate_country_similarities(demand_df)
        if not sim_df.empty:
            metric_options = {
                "Cosine Similarity (Proportional Vector Alignment)": "cosine_similarity",
                "Jaccard Overlap (Top-10 In-Demand Skills)": "jaccard_top10_similarity",
                "Spearman Rank Correlation (Monotonic Skill Order)": "spearman_rank_correlation",
            }
            sel_sim_label = st.radio(
                "Select Multidimensional Similarity Measure for 4×4 Matrix Heatmap",
                list(metric_options.keys()),
                horizontal=True,
            )
            sel_sim_key = metric_options[sel_sim_label]

            # Render 4x4 Symmetric Similarity Heatmap
            sim_matrix_chart = build_country_similarity_matrix(sim_df, metric_choice=sel_sim_key)
            st.altair_chart(sim_matrix_chart, use_container_width=True)

            st.markdown("##### Pairwise Exact-Value Similarity Indices")
            sim_headers = [
                "Market Pair",
                "Sample Sizes",
                "Cosine Similarity",
                "Jaccard (Top 10)",
                "Spearman Rank Corr.",
                "Reliability",
            ]
            sim_rows = []
            for _, r in sim_df.iterrows():
                rel_pill = make_status_pill("High Uncertainty (N<10)", "partial") if r["sparse_sample_flag"] else make_status_pill("Adequate Sample", "clean")
                sim_rows.append([
                    f"{r['country_a']} ↔ {r['country_b']}",
                    f"{r['sample_size_a']} vs {r['sample_size_b']}",
                    f"<b>{r['cosine_similarity']:.4f}</b>",
                    f"{r['jaccard_top10_similarity']:.4f}",
                    f"{r['spearman_rank_correlation']:.4f}",
                    rel_pill,
                ])
            st.markdown(render_custom_table(sim_headers, sim_rows), unsafe_allow_html=True)

            csv_sim = sim_df.to_csv(index=False)
            st.download_button(
                "📥 Export Pairwise Similarities (CSV)",
                csv_sim,
                "country_skill_profile_similarities.csv",
                "text/csv",
            )

    # --------------------------------------------------------------------------
    # Tab 5: Sensitivity Analysis
    # --------------------------------------------------------------------------
    with view_tab5:
        st.subheader("Systematic Sensitivity & Validation Regimes")
        st.markdown(
            "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>"
            "Evaluates whether core analytical conclusions materially shift under 5 alternative filtering regimes."
            "</p>",
            unsafe_allow_html=True,
        )

        sens_summary, _ = run_regional_sensitivity_analysis(df, config)
        sens_headers = [
            "Scenario",
            "Eligible Ads",
            "Markets",
            "Mean MAD Shift (pp)",
            "Max Shift (pp)",
            "Stability Assessment",
        ]
        sens_rows = []
        for _, r in sens_summary.iterrows():
            stab_pill = make_status_pill(r["stability_assessment"], "clean" if "Robust" in r["stability_assessment"] or "Baseline" in r["stability_assessment"] else "partial")
            sens_rows.append([
                str(r["scenario_name"]),
                str(r["total_eligible_ads"]),
                str(r["countries_evaluated"]),
                f"{r['mean_abs_demand_shift_pp']} pp" if pd.notna(r["mean_abs_demand_shift_pp"]) else "N/A",
                f"{r['max_demand_shift_pp']} pp" if pd.notna(r["max_demand_shift_pp"]) else "N/A",
                stab_pill,
            ])
        st.markdown(render_custom_table(sens_headers, sens_rows), unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # Tab 6: Eligibility Funnel & Audit
    # --------------------------------------------------------------------------
    with view_tab6:
        st.subheader("Documented Task Eligibility & Record Attrition Funnel")
        st.markdown(
            "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>"
            "Tracks record eligibility and explicit exclusion reasons stage-by-stage across all analytical tasks."
            "</p>",
            unsafe_allow_html=True,
        )

        funnel_df = build_exclusion_funnel(df, config)
        f_headers = [
            "Analytical Task Stage",
            "Input Ads",
            "Eligible Ads",
            "Excluded Ads",
            "Retention %",
            "Primary Exclusion Reasons",
        ]
        f_rows = []
        for _, r in funnel_df.iterrows():
            f_rows.append([
                str(r["stage"]),
                str(r["input_records"]),
                str(r["eligible_records"]),
                str(r["excluded_records"]),
                f"{r['retention_rate_pct']}%",
                str(r["primary_exclusions"]),
            ])
        st.markdown(render_custom_table(f_headers, f_rows), unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Download Reproducible Research Artifacts")
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            csv_demand = demand_df.to_csv(index=False)
            st.download_button(
                "📥 Skill Demand CSV",
                csv_demand,
                "skill_demand_by_country.csv",
                "text/csv",
            )
        with col_d2:
            csv_gap = gap_df.to_csv(index=False)
            st.download_button(
                "📥 Skill Gaps CSV",
                csv_gap,
                "skill_gaps_focal_srilanka.csv",
                "text/csv",
            )
        with col_d3:
            csv_sal = country_salary.to_csv(index=False)
            st.download_button(
                "📥 Salary Summary CSV",
                csv_sal,
                "salary_summary_by_country.csv",
                "text/csv",
            )

        col_d4, col_d5, col_d6 = st.columns(3)
        with col_d4:
            csv_sim = sim_df.to_csv(index=False)
            st.download_button(
                "📥 Profile Similarities CSV",
                csv_sim,
                "country_skill_profile_similarities.csv",
                "text/csv",
            )
        with col_d5:
            csv_funnel = funnel_df.to_csv(index=False)
            st.download_button(
                "📥 Eligibility Funnel CSV",
                csv_funnel,
                "regional_eligibility_funnel.csv",
                "text/csv",
            )
        with col_d6:
            csv_sens = sens_summary.to_csv(index=False)
            st.download_button(
                "📥 Sensitivity Analysis CSV",
                csv_sens,
                "regional_sensitivity_summary.csv",
                "text/csv",
            )
