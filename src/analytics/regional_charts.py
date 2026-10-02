"""
Altair Visualization Generator for Comparative Regional IT Labor-Market Analysis.
Project: IT Job Market Intelligence Tool (J26_SE_355).
Research Component: Comparative Regional Market Analysis.

Visualizations:
1. Regional Skill-Demand Grouped Bar Chart (Demand % with Wilson 95% CIs and Sample Sizes).
2. Regional Skill-Demand Interactive Heatmap (Skills vs. Countries with Exact % Overlay).
3. Disclosed Salary Interval & Distribution Range Charts (Preserving Native Currencies).
4. 4x4 Country-to-Country Skill Profile Similarity Matrix (Cosine, Jaccard, Spearman).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import altair as alt
import numpy as np
import pandas as pd


# Consistent Research Palette for Target Regional Markets
COUNTRY_COLORS = {
    "Sri Lanka": "#38BDF8",  # Sky Blue (Focal Market)
    "India": "#F59E0B",      # Amber (Major Regional Comparator)
    "Singapore": "#10B981",  # Emerald (High-Wage Regional Hub)
    "Malaysia": "#A78BFA",   # Purple (Emerging Tech Hub)
}

TARGET_COUNTRIES_ORDER = ["Sri Lanka", "India", "Singapore", "Malaysia"]


def get_market_color_scale() -> alt.Scale:
    """Returns an Altair categorical scale mapped to canonical country research colors."""
    return alt.Scale(
        domain=list(COUNTRY_COLORS.keys()),
        range=list(COUNTRY_COLORS.values()),
    )


# ==============================================================================
# 1. Regional Skill-Demand Grouped Bar Chart
# ==============================================================================

def build_skill_demand_bar_chart(
    demand_df: pd.DataFrame,
    focal_country: str = "Sri Lanka",
    top_n: int = 15,
    selected_category: str = "All Categories",
) -> alt.Chart:
    """Builds an interactive grouped bar chart comparing canonical skill demand percentages.
    
    Features:
    - Primary metric: Demand % = (Ads mentioning skill / Total eligible ads) * 100.
    - Bars grouped by canonical skill, sorted by focal market demand descending.
    - Explicit hover tooltips displaying Country, Skill, Demand %, Mention Count (k),
      Eligible Sample Size (N), and 95% Wilson Confidence Interval.
    - Native country color coding.
    """
    if demand_df.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No data available"]})).mark_text().encode(text="msg:N")

    df = demand_df.copy()
    if selected_category != "All Categories":
        df = df[df["category"] == selected_category]

    if df.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No skills match the selected filter"]})).mark_text().encode(text="msg:N")

    # Determine top N skills based on focal country demand
    focal_skills = (
        df[df["country"] == focal_country]
        .sort_values("demand_pct", ascending=False)["skill_name"]
        .head(top_n)
        .tolist()
    )
    if not focal_skills:
        # Fallback to overall top skills if focal country has no data for this subset
        focal_skills = (
            df.groupby("skill_name")["demand_pct"]
            .max()
            .sort_values(ascending=False)
            .head(top_n)
            .index.tolist()
        )

    plot_df = df[df["skill_name"].isin(focal_skills)].copy()
    plot_df["ci_label"] = plot_df.apply(
        lambda r: f"[{r['ci_lower_95']}%, {r['ci_upper_95']}%]", axis=1
    )

    color_scale = get_market_color_scale()

    chart = (
        alt.Chart(plot_df)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X(
                "skill_name:N",
                title="Canonical Technical Skill (Sorted by Sri Lanka Demand)",
                sort=focal_skills,
                axis=alt.Axis(labelAngle=-45, labelFontSize=11, titleFontSize=12, titlePadding=10),
            ),
            y=alt.Y(
                "demand_pct:Q",
                title="Skill Demand (% of Eligible Ads in Country)",
                scale=alt.Scale(domain=[0, min(100, max(plot_df["demand_pct"].max() * 1.15, 20))]),
                axis=alt.Axis(format=".1f", titleFontSize=12),
            ),
            color=alt.Color(
                "country:N",
                scale=color_scale,
                legend=alt.Legend(title="Labor Market", orient="top", direction="horizontal", titleFontSize=11),
            ),
            xOffset=alt.XOffset("country:N", sort=TARGET_COUNTRIES_ORDER),
            tooltip=[
                alt.Tooltip("skill_name:N", title="Canonical Skill"),
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("country:N", title="Market"),
                alt.Tooltip("demand_pct:Q", title="Demand Rate", format=".2f"),
                alt.Tooltip("mention_count:Q", title="Mentions (k)"),
                alt.Tooltip("eligible_ads_denominator:Q", title="Eligible Vacancies (N)"),
                alt.Tooltip("ci_label:N", title="Wilson 95% CI"),
            ],
        )
        .properties(
            title=alt.TitleParams(
                text=f"Top {len(focal_skills)} Canonical Skills by Demand Across Regional IT Markets",
                subtitle="Observation Period: August – October 2026 | Unit: % of National Eligible Vacancies",
                fontSize=14,
                subtitleFontSize=11,
                subtitleColor="#94A3B8",
            ),
            height=380,
        )
    )

    return chart


# ==============================================================================
# 2. Regional Skill-Demand Interactive Heatmap
# ==============================================================================

def build_skill_demand_heatmap(
    demand_df: pd.DataFrame,
    focal_country: str = "Sri Lanka",
    top_n: int = 20,
    selected_category: str = "All Categories",
) -> alt.Chart:
    """Builds an interactive 2D heatmap matrix (Skills vs. Countries).
    
    Design:
    - Rows: Canonical technical skills, sorted by focal country demand descending.
    - Columns: Approved regional countries in standard research order.
    - Cell Color: Continuous gradient representing demand percentage.
    - Cell Overlay: Clear text showing exact percentage (e.g., '35.6%').
    - Empty/Unobserved combinations explicitly formatted as '0.0%' (or flagged).
    """
    if demand_df.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No data available"]})).mark_text().encode(text="msg:N")

    df = demand_df.copy()
    if selected_category != "All Categories":
        df = df[df["category"] == selected_category]

    if df.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No skills match the selected filter"]})).mark_text().encode(text="msg:N")

    # Top skills by focal market
    focal_skills = (
        df[df["country"] == focal_country]
        .sort_values("demand_pct", ascending=False)["skill_name"]
        .head(top_n)
        .tolist()
    )
    if not focal_skills:
        focal_skills = (
            df.groupby("skill_name")["demand_pct"]
            .max()
            .sort_values(ascending=False)
            .head(top_n)
            .index.tolist()
        )

    # Build complete grid to guarantee no missing cell holes
    denominators = df.groupby("country")["eligible_ads_denominator"].first().to_dict()
    grid_rows = []

    for skill in focal_skills:
        skill_subset = df[df["skill_name"] == skill]
        cat = skill_subset["category"].iloc[0] if not skill_subset.empty else "Technical"

        for country in TARGET_COUNTRIES_ORDER:
            match = skill_subset[skill_subset["country"] == country]
            n_val = denominators.get(country, 0)

            if not match.empty:
                r = match.iloc[0]
                pct = float(r["demand_pct"])
                k_val = int(r["mention_count"])
                ci_str = f"[{r['ci_lower_95']}%, {r['ci_upper_95']}%]"
                unobserved = False
            else:
                pct = 0.0
                k_val = 0
                ci_str = "0.0% (Unobserved / Zero Count)"
                unobserved = True

            grid_rows.append({
                "skill_name": skill,
                "category": cat,
                "country": country,
                "demand_pct": pct,
                "demand_label": f"{pct:.1f}%",
                "mention_count": k_val,
                "denominator": n_val,
                "ci_label": ci_str,
                "is_unobserved": unobserved,
                "observation_note": "Unobserved or Zero Mention" if unobserved else "Validated Sample",
            })

    grid_df = pd.DataFrame(grid_rows)

    base = alt.Chart(grid_df).encode(
        x=alt.X(
            "country:N",
            title="Labor Market",
            sort=TARGET_COUNTRIES_ORDER,
            axis=alt.Axis(orient="top", labelFontSize=12, labelFontWeight="bold", titleFontSize=12),
        ),
        y=alt.Y(
            "skill_name:N",
            title="Canonical Technical Skill",
            sort=focal_skills,
            axis=alt.Axis(labelFontSize=11, titleFontSize=12),
        ),
    )

    rect = base.mark_rect(stroke="#1E293B", strokeWidth=1).encode(
        color=alt.Color(
            "demand_pct:Q",
            scale=alt.Scale(scheme="blues", domain=[0, max(grid_df["demand_pct"].max(), 25)]),
            legend=alt.Legend(title="Demand %", orient="right", format=".1f"),
        ),
        tooltip=[
            alt.Tooltip("skill_name:N", title="Canonical Skill"),
            alt.Tooltip("category:N", title="Category"),
            alt.Tooltip("country:N", title="Market"),
            alt.Tooltip("demand_pct:Q", title="Demand %", format=".2f"),
            alt.Tooltip("mention_count:Q", title="Mentions (k)"),
            alt.Tooltip("denominator:Q", title="Eligible Ads (N)"),
            alt.Tooltip("ci_label:N", title="95% Wilson CI"),
            alt.Tooltip("observation_note:N", title="Status"),
        ],
    )

    text = base.mark_text(baseline="middle", fontSize=11).encode(
        text="demand_label:N",
        color=alt.condition(alt.datum.demand_pct > 25, alt.value("white"), alt.value("#94A3B8")),
    )

    chart = (rect + text).properties(
        title=alt.TitleParams(
            text="Canonical Skill Demand Intensity Heatmap",
            subtitle="Cross-market demand matrix (% of eligible national vacancies). Sorted by Sri Lanka demand.",
            fontSize=14,
            subtitleFontSize=11,
            subtitleColor="#94A3B8",
        ),
        height=max(320, len(focal_skills) * 24),
    )

    return chart


# ==============================================================================
# 3. Disclosed Salary Interval & Range Plots
# ==============================================================================

def build_salary_interval_chart(
    country_salary_df: pd.DataFrame,
) -> alt.Chart:
    """Builds horizontal interval plots for disclosed monthly salaries in native currencies.
    
    Safety:
    - Independent axes per country: LKR, INR, SGD, MYR are NEVER placed on a shared numeric axis.
    - Displays: Min-to-Max range rule, 25th-to-75th percentile (IQR) bar, and Median tick mark.
    - Explicit disclosure counts (N) and warnings for small sample sizes.
    """
    if country_salary_df.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No disclosed salary data available"]})).mark_text().encode(text="msg:N")

    charts = []
    color_scale = get_market_color_scale()

    for country in TARGET_COUNTRIES_ORDER:
        match = country_salary_df[country_salary_df["country"] == country]
        if match.empty:
            continue
        row = match.iloc[0]
        c_df = pd.DataFrame([row])

        # Subtitle badge text
        n_disclosed = int(row["disclosed_salary_count"])
        coverage = float(row["disclosure_rate_pct"])
        curr = str(row["currency"])
        warning_note = " ⚠️ Small Sample (N<10)" if row["small_sample_flag"] else ""

        title_text = f"{country} ({curr}) — Disclosed N={n_disclosed} ({coverage}% coverage){warning_note}"

        base = alt.Chart(c_df)

        # Range rule: min to max
        rule = base.mark_rule(size=3, color="#64748B").encode(
            x=alt.X(
                "min_salary:Q",
                title=f"Monthly Disclosed Salary ({curr})",
                scale=alt.Scale(domain=[row["min_salary"] * 0.9, row["max_salary"] * 1.1]),
                axis=alt.Axis(format=",.0f"),
            ),
            x2="max_salary:Q",
            tooltip=[
                alt.Tooltip("country:N", title="Market"),
                alt.Tooltip("currency:N", title="Currency"),
                alt.Tooltip("min_salary:Q", title="Min (Monthly)", format=",.0f"),
                alt.Tooltip("p25_salary:Q", title="25th Percentile", format=",.0f"),
                alt.Tooltip("median_salary:Q", title="Median (Monthly)", format=",.0f"),
                alt.Tooltip("p75_salary:Q", title="75th Percentile", format=",.0f"),
                alt.Tooltip("max_salary:Q", title="Max (Monthly)", format=",.0f"),
                alt.Tooltip("disclosed_salary_count:Q", title="Disclosed Ads (N)"),
            ],
        )

        # IQR Bar: p25 to p75
        bar = base.mark_bar(size=18, opacity=0.85).encode(
            x="p25_salary:Q",
            x2="p75_salary:Q",
            color=alt.Color("country:N", scale=color_scale, legend=None),
        )

        # Median Tick Mark
        tick = base.mark_tick(size=24, thickness=3, color="#FFFFFF").encode(
            x="median_salary:Q",
        )

        sub_chart = (rule + bar + tick).properties(
            title=alt.TitleParams(
                text=title_text,
                fontSize=12,
                fontWeight="bold",
                color="#F8FAFC" if not row["small_sample_flag"] else "#F59E0B",
            ),
            height=70,
        )
        charts.append(sub_chart)

    if not charts:
        return alt.Chart(pd.DataFrame({"msg": ["No salary charts available"]})).mark_text().encode(text="msg:N")

    # Stack charts vertically with independent axes
    combined = alt.vconcat(*charts).properties(
        title=alt.TitleParams(
            text="Disclosed Monthly Salary Ranges by Regional Labor Market",
            subtitle="Whiskers: Min to Max | Filled Bar: IQR (25th–75th Percentile) | White Tick: Median. Local Currencies Isolated.",
            fontSize=14,
            subtitleFontSize=11,
            subtitleColor="#94A3B8",
        )
    )

    return combined


# ==============================================================================
# 4. 4x4 Country-to-Country Skill Profile Similarity Matrix
# ==============================================================================

def build_country_similarity_matrix(
    sim_df: pd.DataFrame,
    metric_choice: str = "cosine_similarity",
) -> alt.Chart:
    """Builds a symmetric 4x4 country-to-country skill-demand similarity heatmap.
    
    Supported Metrics:
    - 'cosine_similarity': Vector angle alignment (0.0 to 1.0).
    - 'jaccard_top10_similarity': Top-10 skill set overlap (0.0 to 1.0).
    - 'spearman_rank_correlation': Monotonic rank order correlation (-1.0 to 1.0).
    """
    metric_titles = {
        "cosine_similarity": ("Cosine Similarity", "Proportional Canonical Vector Alignment (0 to 1)"),
        "jaccard_top10_similarity": ("Jaccard Similarity (Top 10)", "Intersection-over-Union of Top-10 In-Demand Skills"),
        "spearman_rank_correlation": ("Spearman Rank Correlation", "Monotonic Concordance of Skill Demand Order (-1 to +1)"),
    }
    short_title, metric_desc = metric_titles.get(metric_choice, ("Similarity Metric", ""))

    matrix_rows = []

    for c1 in TARGET_COUNTRIES_ORDER:
        for c2 in TARGET_COUNTRIES_ORDER:
            if c1 == c2:
                # Diagonal: perfect self-similarity
                score = 1.0000
                matrix_rows.append({
                    "country_a": c1,
                    "country_b": c2,
                    "score": score,
                    "score_label": "1.0000",
                    "sample_info": "Same Market (Diagonal = 1.0)",
                    "reliability": "Perfect Self-Alignment",
                    "metric_name": short_title,
                })
            else:
                # Find matching row in pairwise dataframe
                match = sim_df[
                    ((sim_df["country_a"] == c1) & (sim_df["country_b"] == c2)) |
                    ((sim_df["country_a"] == c2) & (sim_df["country_b"] == c1))
                ]
                if not match.empty:
                    r = match.iloc[0]
                    score = float(r[metric_choice])
                    sparse = bool(r["sparse_sample_flag"])
                    matrix_rows.append({
                        "country_a": c1,
                        "country_b": c2,
                        "score": score,
                        "score_label": f"{score:.4f}",
                        "sample_info": f"{r['sample_size_a']} vs {r['sample_size_b']} ads",
                        "reliability": "High Uncertainty (N<10)" if sparse else "Adequate Sample",
                        "metric_name": short_title,
                    })
                else:
                    matrix_rows.append({
                        "country_a": c1,
                        "country_b": c2,
                        "score": 0.0,
                        "score_label": "N/A",
                        "sample_info": "Unobserved",
                        "reliability": "Unverified",
                        "metric_name": short_title,
                    })

    mat_df = pd.DataFrame(matrix_rows)

    domain_range = [0, 1] if metric_choice != "spearman_rank_correlation" else [-0.5, 1.0]

    base = alt.Chart(mat_df).encode(
        x=alt.X(
            "country_b:N",
            title="Comparator Market",
            sort=TARGET_COUNTRIES_ORDER,
            axis=alt.Axis(orient="top", labelFontSize=12, labelFontWeight="bold", titleFontSize=12),
        ),
        y=alt.Y(
            "country_a:N",
            title="Reference Market",
            sort=TARGET_COUNTRIES_ORDER,
            axis=alt.Axis(labelFontSize=12, labelFontWeight="bold", titleFontSize=12),
        ),
    )

    rect = base.mark_rect(stroke="#1E293B", strokeWidth=2).encode(
        color=alt.Color(
            "score:Q",
            scale=alt.Scale(domain=domain_range, scheme="tealblues"),
            legend=alt.Legend(title=short_title, orient="right", format=".2f"),
        ),
        tooltip=[
            alt.Tooltip("country_a:N", title="Market A"),
            alt.Tooltip("country_b:N", title="Market B"),
            alt.Tooltip("metric_name:N", title="Metric"),
            alt.Tooltip("score:Q", title="Score", format=".4f"),
            alt.Tooltip("sample_info:N", title="Sample Denominators"),
            alt.Tooltip("reliability:N", title="Reliability Status"),
        ],
    )

    text = base.mark_text(baseline="middle", fontSize=13, fontWeight="bold").encode(
        text="score_label:N",
        color=alt.condition(alt.datum.score > 0.65, alt.value("white"), alt.value("#0F172A")),
    )

    chart = (rect + text).properties(
        title=alt.TitleParams(
            text=f"Country Skill-Profile Similarity Matrix ({short_title})",
            subtitle=f"{metric_desc}. Full 4×4 symmetric pairwise comparison matrix.",
            fontSize=14,
            subtitleFontSize=11,
            subtitleColor="#94A3B8",
        ),
        width=480,
        height=380,
    )

    return chart
