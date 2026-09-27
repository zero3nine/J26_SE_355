"""
Dashboard Visualization Layer for Skill Relationship & Technology Stack Analysis
Research Component: IT4010 - Skill Relationship & Technology Stack Analysis

Vertically Ordered Research Workflow:
Section 1: Analysis Overview
Section 2: Skill Normalization and Extraction Quality
Section 3: Skill Relationship Analysis (Frequency -> Heatmap -> Network Graph -> Jaccard -> PMI -> Composite Strength)
Section 4: Technology Stack and Ecosystem Discovery (Multi-Skill Stacks, Association Rules, Evidence Drilldown)
Section 5: Detailed Results and Methodology (Expandable Matrices, Complete Tables, Configurations, Math Reference)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import altair as alt
import networkx as nx
import pandas as pd
import streamlit as st

from src.extraction.normalization import get_skill_category
from theme import render_custom_table


# -----------------------------------------------------------------------------
# Section 1: Analysis Overview
# -----------------------------------------------------------------------------

def render_section_1_overview(report: dict, mode: str, analytics_dir: Path):
    """
    Renders Section 1: Compact KPI cards for jobs analyzed, canonical skills,
    skill relationships, and discovered stacks, plus active mode and dataset status.
    """
    st.markdown("""
    <div style="border-bottom: 2px solid #1E293B; padding-bottom: 8px; margin-bottom: 16px;">
        <h3 style="color: #38BDF8; font-weight: 700; margin: 0; font-size: 20px;">
            1. Analysis Overview
        </h3>
        <p style="color: #94A3B8; font-size: 13px; margin: 4px 0 0 0;">
            High-level quantitative summary of analyzed job advertisements, canonical skill entities, and discovered patterns.
        </p>
    </div>
    """, unsafe_allow_html=True)

    jobs_analyzed = report.get("jobs_with_selected_skills", 0)
    total_csv_rows = report.get("total_rows_in_csv", jobs_analyzed)
    unique_skills = report.get("unique_skills", 0)
    skill_pairs = report.get("skill_pairs", 0)
    coverage_pct = report.get("extraction_coverage_pct", round((jobs_analyzed / total_csv_rows * 100), 1) if total_csv_rows > 0 else 0.0)

    # Count stacks if table exists
    stacks_count = 0
    path_stacks = analytics_dir / "technology_stacks.csv"
    if path_stacks.exists():
        try:
            df_st = pd.read_csv(path_stacks)
            stacks_count = len(df_st)
        except Exception:
            stacks_count = 0

    mode_display = {
        "lexical_skills": "Lexical Skill Extraction (Taxonomy Matching)",
        "semantic_skills": "Semantic Skill Extraction (Embedding Similarity)",
        "combined": "Combined Extraction (Lexical ∪ Semantic)",
    }.get(mode, mode.replace("_", " ").title())

    # Extraction mode and dataset status banner
    st.markdown(f"""
    <div style="background: #111827; border: 1px solid #1F2937; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
        <div>
            <span style="color: #9CA3AF; font-size: 13px;">Extraction Mode:</span>
            <span style="color: #38BDF8; font-weight: 600; font-size: 13px; margin-left: 8px;">{mode_display}</span>
            <span style="color: #64748B; margin: 0 8px;">|</span>
            <span style="color: #9CA3AF; font-size: 13px;">Dataset Status:</span>
            <span style="color: #10B981; font-weight: 600; font-size: 13px; margin-left: 8px;">{jobs_analyzed} of {total_csv_rows} postings analyzed ({coverage_pct}% coverage)</span>
        </div>
        <div>
            <span style="background: rgba(56, 189, 248, 0.15); color: #38BDF8; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.3);">
                Canonical Taxonomy v0.1.0
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 4 Compact KPI Cards
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 18px;">
        <div class="kpi-card clean">
            <div class="kpi-label">Job Ads Analysed</div>
            <div class="kpi-value">{jobs_analyzed}</div>
            <div class="kpi-trend">
                <span class="trend-up">Valid technical records</span>
            </div>
        </div>
        <div class="kpi-card scraped">
            <div class="kpi-label">Unique Canonical Skills</div>
            <div class="kpi-value">{unique_skills}</div>
            <div class="kpi-trend">
                <span class="trend-up">Normalized entities</span>
            </div>
        </div>
        <div class="kpi-card partial">
            <div class="kpi-label">Observed Skill Relationships</div>
            <div class="kpi-value">{skill_pairs}</div>
            <div class="kpi-trend">
                <span class="trend-neutral">Co-occurring pairs</span>
            </div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Discovered Stack Patterns</div>
            <div class="kpi-value">{stacks_count}</div>
            <div class="kpi-trend">
                <span class="trend-up" style="color: #A78BFA;">Multi-skill ecosystems</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if jobs_analyzed < 5:
        st.warning(
            f"⚠️ **Small Sample Size Warning (N = {jobs_analyzed}):** A single advertisement (or very small sample) "
            "is insufficient for generalizable research conclusions. With N = 1, all co-occurring technical skills in the posting "
            "trivially yield Jaccard = 1.00, Support = 1.00, and Confidence = 1.00, while PMI evaluates to 0.00 (log₂(1.0/1.0)). "
            "Accumulate a larger batch of job advertisements (e.g. 15–20+ postings) to compute statistically robust relationships, "
            "uncover distinct technology stacks, and avoid degenerate correlation metrics."
        )
    elif jobs_analyzed < 10:
        st.info(
            f"ℹ️ **Sample Size Advisory:** Currently evaluating an empirical sample of **{jobs_analyzed}** valid "
            "IT job advertisements. Relationships and multi-skill combinations reflect observed patterns within this dataset. "
            "As additional job flyers are processed through OCR and web extraction, statistical sample size will continue to scale."
        )


# -----------------------------------------------------------------------------
# Section 2: Skill Normalization and Extraction Quality
# -----------------------------------------------------------------------------

def render_section_2_normalization_quality(report: dict, analytics_dir: Path):
    """
    Renders Section 2: Normalization quality audit, transparent mapping rules table,
    boundary preservation guarantees (Java != JS, C != C++, React != React Native),
    and extraction diagnostics (missing results, coverage, unresolved terms).
    """
    st.markdown("""
    <div style="border-bottom: 2px solid #1E293B; padding-bottom: 8px; margin-top: 24px; margin-bottom: 16px;">
        <h3 style="color: #38BDF8; font-weight: 700; margin: 0; font-size: 20px;">
            2. Skill Normalization and Extraction Quality
        </h3>
        <p style="color: #94A3B8; font-size: 13px; margin: 4px 0 0 0;">
            Verification of canonical skill mapping, transparent rule application, technology boundary preservation, and extraction diagnostics.
        </p>
    </div>
    """, unsafe_allow_html=True)

    norm_audit = report.get("normalization_audit", {})
    if not norm_audit:
        audit_file = analytics_dir / "normalization_audit.json"
        if audit_file.exists():
            try:
                with open(audit_file, "r", encoding="utf-8") as f:
                    norm_audit = json.load(f)
            except Exception:
                norm_audit = {}

    total_mentions = report.get("total_raw_mentions", norm_audit.get("total_terms", 0))
    mapped_count = norm_audit.get("mapped_count", report.get("unique_skills", 0))
    unmapped_count = norm_audit.get("unmapped_count", 0)
    canonical_skills_count = report.get("unique_skills", 0)
    coverage_pct = report.get("extraction_coverage_pct", 100.0)
    jobs_missing = report.get("jobs_missing_skills", 0)
    mapping_records = norm_audit.get("mapping_records", [])
    unmapped_terms = norm_audit.get("unmapped_terms", [])

    # Quality KPI Cards
    col_q1, col_q2, col_q3, col_q4 = st.columns(4)
    with col_q1:
        st.metric("Raw Skill Mentions", total_mentions)
    with col_q2:
        st.metric("Normalized Canonical Skills", canonical_skills_count)
    with col_q3:
        st.metric("Distinct Mapped Variants", mapped_count)
    with col_q4:
        st.metric("Extraction Coverage", f"{coverage_pct}%")

    # Technology Boundary Preservation Callout
    st.markdown("""
    <div style="background: rgba(56, 189, 248, 0.06); border-left: 3px solid #38BDF8; padding: 10px 14px; border-radius: 4px; margin: 14px 0; font-size: 13px; color: #CBD5E1;">
        <b style="color: #38BDF8;">Strict Technology Boundary Preservation:</b><br/>
        • <b>JavaScript & Web Ecosystem:</b> Aliases like <code>JS</code>, <code>Javascript</code>, <code>JAVASCRIPT</code>, <code>JavaScript</code>, and <code>es6</code> resolve to <b>JavaScript</b>.<br/>
        • <b>Language Boundaries:</b> <code>Java</code> is strictly separate from <code>JavaScript</code> and <code>Jakarta EE</code>.<br/>
        • <b>Compiled Languages:</b> <code>C</code> is strictly separate from <code>C++</code> and <code>C#</code>.<br/>
        • <b>Framework Boundaries:</b> <code>React</code> is strictly separate from <code>React Native</code>; <code>Node.js</code> is separate from <code>JavaScript</code>.<br/>
        • <b>Placeholders Excluded:</b> Non-technical placeholders such as <code>None</code>, <code>null</code>, <code>nan</code>, <code>N/A</code>, and empty strings are filtered out and never treated as skills.
    </div>
    """, unsafe_allow_html=True)

    # Transparent Mapping Table
    if mapping_records:
        st.markdown("<p style='color: #F8FAFC; font-size: 14px; font-weight: 600; margin-top: 14px; margin-bottom: 6px;'>Transparent Skill Normalization Audit Table</p>", unsafe_allow_html=True)
        sample_records = mapping_records[:15]
        map_headers = ["Original Extracted Term", "Canonical Technology", "Applied Normalization Rule"]
        map_rows = [[r.get("original_term", ""), r.get("canonical_skill", ""), r.get("rule", "Taxonomy Alias Lookup")] for r in sample_records]
        st.markdown(render_custom_table(map_headers, map_rows), unsafe_allow_html=True)
        if len(mapping_records) > 15:
            with st.expander(f"📋 View All {len(mapping_records)} Normalization Mapping Entries", expanded=False):
                full_map_rows = [[r.get("original_term", ""), r.get("canonical_skill", ""), r.get("rule", "Taxonomy Alias Lookup")] for r in mapping_records]
                st.markdown(render_custom_table(map_headers, full_map_rows), unsafe_allow_html=True)

    # Extraction Coverage & Missing Results Diagnostics
    with st.expander("🔍 Extraction Diagnostics: Missing Results & Unresolved Terms", expanded=False):
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown(f"""
            <div style="font-size: 13px; color: #CBD5E1; line-height: 1.6;">
                <b>Job Postings Coverage Analysis:</b><br/>
                • Total Raw Postings: <b>{report.get('total_rows_in_csv', 0)}</b><br/>
                • Postings with Valid Skills: <b>{report.get('jobs_with_selected_skills', 0)}</b> ({coverage_pct}%)<br/>
                • Postings Missing Technical Skills: <b>{jobs_missing}</b><br/>
                <i>Note: Postings missing skills typically consist of image flyers awaiting OCR or boilerplate notices ('Please refer full details') without text descriptions.</i>
            </div>
            """, unsafe_allow_html=True)
        with col_d2:
            st.markdown(f"""
            <div style="font-size: 13px; color: #CBD5E1; line-height: 1.6;">
                <b>Unresolved / Novel Variants ({len(unmapped_terms)}):</b><br/>
                {', '.join(unmapped_terms[:20]) if unmapped_terms else 'No unresolved terms detected in current extraction.'}
            </div>
            """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Section 3: Skill Relationship Analysis
# -----------------------------------------------------------------------------

def _generate_network_svg(
    df_edges: pd.DataFrame,
    focal_skill: str = "All Skills",
    weight_metric: str = "weight",
    min_count: int = 1,
    min_strength: float = 0.0,
) -> tuple[str, int, int]:
    """Constructs an interactive SVG network visualization with NetworkX spring layout."""
    if df_edges.empty:
        return "", 0, 0

    filtered = df_edges.copy()
    if "pair_count" in filtered.columns:
        filtered = filtered[filtered["pair_count"] >= min_count]
    elif "weight" in filtered.columns:
        filtered = filtered[filtered["weight"] >= min_count]

    if "relationship_strength" in filtered.columns:
        filtered = filtered[filtered["relationship_strength"] >= min_strength]

    if filtered.empty:
        return "", 0, 0

    if focal_skill and focal_skill != "All Skills":
        source_col = "source_skill" if "source_skill" in filtered.columns else "source"
        target_col = "target_skill" if "target_skill" in filtered.columns else "target"
        filtered = filtered[(filtered[source_col] == focal_skill) | (filtered[target_col] == focal_skill)]

    if filtered.empty:
        return "", 0, 0

    G = nx.Graph()
    for _, r in filtered.iterrows():
        u = str(r.get("source_skill", r.get("source", "")))
        v = str(r.get("target_skill", r.get("target", "")))
        w = float(r.get(weight_metric, r.get("weight", 1.0)))
        pair_cnt = int(r.get("pair_count", r.get("weight", 1)))
        jac = float(r.get("jaccard", 0.0))
        pmi = float(r.get("pmi", 0.0))
        rel_str = float(r.get("relationship_strength", 0.0))

        if u and v and u != v:
            G.add_edge(u, v, weight=w, pair_count=pair_cnt, jaccard=jac, pmi=pmi, strength=rel_str)

    isolated = [n for n in G.nodes() if G.degree(n) == 0]
    G.remove_nodes_from(isolated)

    if len(G.nodes) == 0:
        return "", 0, 0

    k_val = 1.9 / (len(G.nodes) ** 0.5 if len(G.nodes) > 1 else 1)
    pos = nx.spring_layout(G, seed=42, k=k_val, iterations=70)

    width, height = 860, 500
    cx_offset, cy_offset = width / 2, height / 2
    scale_x, scale_y = 360, 200

    degrees = dict(G.degree(weight="weight"))
    max_deg = max(degrees.values()) if degrees else 1

    cat_colors = {
        "Programming Languages": "#38BDF8",  # Sky
        "Frameworks & Libraries": "#818CF8",  # Indigo
        "Databases": "#34D399",              # Emerald
        "Cloud & Infrastructure": "#FBBF24",  # Amber
        "DevOps & CI/CD": "#F43F5E",          # Rose
        "Testing & QA": "#A78BFA",            # Purple
        "Data & AI": "#2DD4BF",               # Teal
        "General": "#94A3B8",
    }

    svg = [
        f'<div style="text-align: center; margin-bottom: 14px;">'
        f'<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="background: #0B1120; border-radius: 12px; border: 1px solid #1E293B; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">'
    ]

    svg.append(
        '<defs>'
        '<pattern id="sec3_grid" width="40" height="40" patternUnits="userSpaceOnUse">'
        '<path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1E293B" stroke-width="0.5" stroke-opacity="0.6" />'
        '</pattern>'
        '<linearGradient id="sec3_edge_grad" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#38BDF8" stop-opacity="0.85" />'
        '<stop offset="100%" stop-color="#818CF8" stop-opacity="0.55" />'
        '</linearGradient>'
        '</defs>'
        '<rect width="100%" height="100%" fill="url(#sec3_grid)" />'
    )

    # Edges
    for u, v, data in G.edges(data=True):
        x1 = int(pos[u][0] * scale_x + cx_offset)
        y1 = int(pos[u][1] * scale_y + cy_offset)
        x2 = int(pos[v][0] * scale_x + cx_offset)
        y2 = int(pos[v][1] * scale_y + cy_offset)
        raw_w = data.get("weight", 1.0)
        stroke_w = max(1.8, min(raw_w * 2.2, 7.5))

        pair_c = data.get("pair_count", 1)
        j_val = data.get("jaccard", 0.0)
        p_val = data.get("pmi", 0.0)
        s_val = data.get("strength", 0.0)

        tooltip = f"Edge: {u} ↔ {v}&#10;Pair Count: {pair_c}&#10;Jaccard: {j_val:.4f}&#10;PMI: {p_val:.4f} bits&#10;Strength: {s_val:.4f}"

        svg.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="url(#sec3_edge_grad)" stroke-width="{stroke_w}" stroke-linecap="round">'
            f'<title>{tooltip}</title>'
            f'</line>'
        )

    # Nodes
    for node in sorted(G.nodes()):
        x = int(pos[node][0] * scale_x + cx_offset)
        y = int(pos[node][1] * scale_y + cy_offset)
        deg = degrees.get(node, 1)
        r = 13 + int((deg / max_deg) * 13)
        cat = get_skill_category(node)
        color = cat_colors.get(cat, "#38BDF8")

        is_focal = (node == focal_skill)
        stroke_color = "#F59E0B" if is_focal else color
        stroke_width = 3.5 if is_focal else 2.5
        r_actual = r + 4 if is_focal else r

        node_tooltip = f"Canonical Skill: {node}&#10;Domain: {cat}&#10;Network Degree: {G.degree(node)}&#10;Weighted Volume: {deg:.1f}"

        svg.append(f'<circle cx="{x}" cy="{y}" r="{r_actual + 6}" fill="{stroke_color}" fill-opacity="{0.35 if is_focal else 0.16}" />')
        svg.append(
            f'<circle cx="{x}" cy="{y}" r="{r_actual}" fill="#0F172A" stroke="{stroke_color}" stroke-width="{stroke_width}">'
            f'<title>{node_tooltip}</title>'
            f'</circle>'
        )
        font_weight = "700" if is_focal else "600"
        font_fill = "#FEF08A" if is_focal else "#F1F5F9"
        svg.append(
            f'<text x="{x}" y="{y + r_actual + 14}" fill="{font_fill}" font-size="12" font-weight="{font_weight}" '
            f'text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, sans-serif">'
            f'<title>{node_tooltip}</title>'
            f'{node}</text>'
        )

    svg.append("</svg></div>")
    return "".join(svg), len(G.nodes), len(G.edges)


def render_section_3_skill_relationship_analysis(analytics_dir: Path):
    """
    Renders Section 3: Ordered visualizations for Skill Relationship Analysis:
    1. Skill frequency distribution
    2. Skill co-occurrence heatmap
    3. Interactive skill relationship network graph
    4. Jaccard similarity results
    5. Pointwise Mutual Information results
    6. Composite relationship strength results
    """
    st.markdown("""
    <div style="border-bottom: 2px solid #1E293B; padding-bottom: 8px; margin-top: 24px; margin-bottom: 16px;">
        <h3 style="color: #38BDF8; font-weight: 700; margin: 0; font-size: 20px;">
            3. Skill Relationship Analysis
        </h3>
        <p style="color: #94A3B8; font-size: 13px; margin: 4px 0 0 0;">
            Sequential analysis pipeline: Individual Demand Baseline → Co-occurrence Matrix → Topological Network → Statistical Metrics.
        </p>
    </div>
    """, unsafe_allow_html=True)

    path_freq = analytics_dir / "skill_frequency.csv"
    path_matrix = analytics_dir / "cooccurrence_matrix.csv"
    path_pairs = analytics_dir / "skill_pairs.csv"
    path_edges = analytics_dir / "skill_network_edges.csv"
    path_jaccard = analytics_dir / "jaccard_similarity.csv"
    path_pmi = analytics_dir / "pmi_scores.csv"
    path_rel = analytics_dir / "skill_relationships.csv"

    # 1. Skill Frequency Distribution
    if path_freq.exists():
        df_freq = pd.read_csv(path_freq)
        if not df_freq.empty:
            st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 6px; margin-bottom: 8px;'>1. Skill Frequency Distribution</h4>", unsafe_allow_html=True)
            df_chart = df_freq.head(12).copy()
            df_chart["category"] = df_chart["skill"].apply(get_skill_category)

            chart = (
                alt.Chart(df_chart)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                .encode(
                    x=alt.X("job_count:Q", title="Job Postings Count"),
                    y=alt.Y("skill:N", sort="-x", title="Canonical Skill"),
                    color=alt.Color("category:N", scale=alt.Scale(scheme="category10"), legend=alt.Legend(title="Domain Category", orient="bottom")),
                    tooltip=[
                        alt.Tooltip("skill:N", title="Skill"),
                        alt.Tooltip("category:N", title="Category"),
                        alt.Tooltip("job_count:Q", title="Job Count"),
                        alt.Tooltip("frequency_pct:Q", title="Market Share (%)", format=".1f"),
                    ],
                )
                .properties(height=280)
            )
            st.altair_chart(chart, use_container_width=True)

    # 2. Skill Co-occurrence Heatmap
    if path_matrix.exists():
        df_matrix = pd.read_csv(path_matrix, index_col=0)
        if not df_matrix.empty and len(df_matrix.index) > 1:
            st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 18px; margin-bottom: 8px;'>2. Skill Co-occurrence Heatmap</h4>", unsafe_allow_html=True)
            st.markdown("<p style='color: #94A3B8; font-size: 12px; margin-top: -6px; margin-bottom: 10px;'>Symmetric co-occurrence matrix C(A, B). Diagonal represents individual counts; off-diagonals count shared postings (each skill counted at most once per ad).</p>", unsafe_allow_html=True)
            try:
                top_skills = df_matrix.sum(axis=1).sort_values(ascending=False).head(15).index.tolist()
                df_sub = df_matrix.loc[top_skills, top_skills]
                idx_name = df_sub.index.name or "index"
                df_long = df_sub.reset_index().melt(id_vars=idx_name, var_name="skill_b", value_name="count")
                df_long.rename(columns={idx_name: "skill_a"}, inplace=True)

                heatmap = (
                    alt.Chart(df_long)
                    .mark_rect()
                    .encode(
                        x=alt.X("skill_a:N", title="Canonical Skill A", sort=top_skills),
                        y=alt.Y("skill_b:N", title="Canonical Skill B", sort=top_skills),
                        color=alt.Color("count:Q", scale=alt.Scale(scheme="tealblues"), title="Co-occurrence"),
                        tooltip=[alt.Tooltip("skill_a:N"), alt.Tooltip("skill_b:N"), alt.Tooltip("count:Q", title="Co-occurrence Count")],
                    )
                )
                text_labels = (
                    alt.Chart(df_long)
                    .mark_text(baseline="middle", fontSize=11)
                    .encode(
                        x="skill_a:N",
                        y="skill_b:N",
                        text=alt.condition(alt.datum.count > 0, alt.Text("count:Q"), alt.value("")),
                        color=alt.condition(alt.datum.count > (df_long["count"].max() * 0.55), alt.value("white"), alt.value("#CBD5E1")),
                    )
                )
                st.altair_chart((heatmap + text_labels).properties(height=340), use_container_width=True)
            except Exception as e:
                st.warning(f"Heatmap visualization note: {e}")

    # 3. Interactive Skill Relationship Network Graph
    if path_edges.exists():
        df_edges = pd.read_csv(path_edges)
        if not df_edges.empty:
            st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 20px; margin-bottom: 8px;'>3. Interactive Skill Relationship Network Graph</h4>", unsafe_allow_html=True)
            all_skills = sorted(list(set(df_edges["source_skill"].dropna()).union(set(df_edges["target_skill"].dropna()))))

            col_c1, col_c2, col_c3, col_c4 = st.columns([2, 2, 2, 2])
            with col_c1:
                focal_skill = st.selectbox("Focal Skill (Ego Network):", options=["All Skills"] + all_skills, index=0, key="sec3_focal")
            with col_c2:
                max_pair = int(df_edges["pair_count"].max()) if "pair_count" in df_edges.columns else 1
                min_cooc = st.slider("Minimum Co-occurrence:", min_value=1, max_value=max(2, max_pair), value=1, key="sec3_cooc")
            with col_c3:
                min_strength = st.slider("Minimum Relationship Strength:", min_value=0.0, max_value=2.0, value=0.0, step=0.1, key="sec3_str")
            with col_c4:
                weight_metric = st.selectbox(
                    "Edge Weighting Metric:",
                    options=["weight", "jaccard", "relationship_strength", "pmi"],
                    format_func=lambda x: {"weight": "Pair Count", "jaccard": "Jaccard", "relationship_strength": "Composite Strength", "pmi": "PMI"}.get(x, x),
                    key="sec3_metric",
                )

            svg_html, node_count, edge_count = _generate_network_svg(
                df_edges, focal_skill=focal_skill, weight_metric=weight_metric, min_count=min_cooc, min_strength=min_strength
            )

            if svg_html:
                st.markdown(svg_html, unsafe_allow_html=True)
                st.caption(f"Topological Subgraph: **{node_count}** skills connected by **{edge_count}** edges. Node size reflects degree connectivity; edge width reflects relationship weight.")
            else:
                st.warning(f"No skill relationships meet the selected filter criteria (Focal Skill = '{focal_skill}', Min Co-occurrence = {min_cooc}, Min Strength = {min_strength:.1f}). Lower the thresholds to display lower-frequency connections.")

    # 4. Jaccard Similarity Results
    if path_jaccard.exists():
        df_jaccard = pd.read_csv(path_jaccard)
        if not df_jaccard.empty:
            st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 20px; margin-bottom: 6px;'>4. Jaccard Similarity Results</h4>", unsafe_allow_html=True)
            st.markdown("<p style='color: #94A3B8; font-size: 12px; margin-top: -4px; margin-bottom: 10px;'>Measures requirement set overlap: <b>J(A, B) = |J_A ∩ J_B| / |J_A ∪ J_B|</b> ∈ [0.0, 1.0].</p>", unsafe_allow_html=True)
            df_jac_view = df_jaccard.sort_values("jaccard", ascending=False).head(10)
            headers = ["Skill A", "Skill B", "Intersection |J_A ∩ J_B|", "Union |J_A ∪ J_B|", "Jaccard Score"]
            rows = [[str(r["skill_a"]), str(r["skill_b"]), str(r.get("intersection", "-")), str(r.get("union", "-")), f"{float(r['jaccard']):.4f}"] for _, r in df_jac_view.iterrows()]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

    # 5. Pointwise Mutual Information (PMI) Results
    if path_pmi.exists():
        df_pmi = pd.read_csv(path_pmi)
        if not df_pmi.empty:
            st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 20px; margin-bottom: 6px;'>5. Pointwise Mutual Information (PMI) Results</h4>", unsafe_allow_html=True)
            st.markdown("<p style='color: #94A3B8; font-size: 12px; margin-top: -4px; margin-bottom: 10px;'>Statistical log-odds dependency: <b>PMI(A, B) = log₂( P(A, B) / (P(A) × P(B)) )</b>. Bounded evaluation dampens rare pair spikes.</p>", unsafe_allow_html=True)
            df_pmi_view = df_pmi.sort_values("pmi", ascending=False).head(10)
            headers = ["Skill A", "Skill B", "Co-occurrence", "PMI Score (Bits)", "Statistical Affinity"]
            rows = []
            for _, r in df_pmi_view.iterrows():
                pmi_val = float(r["pmi"])
                aff = "Complementary" if pmi_val > 0.5 else ("Independent" if abs(pmi_val) <= 0.5 else "Substitutes")
                rows.append([str(r["skill_a"]), str(r["skill_b"]), str(r["cooccurrence"]), f"{pmi_val:.4f}", aff])
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

    # 6. Composite Relationship Strength Results
    if path_rel.exists():
        df_rel = pd.read_csv(path_rel)
        if not df_rel.empty and "relationship_strength" in df_rel.columns:
            st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 20px; margin-bottom: 6px;'>6. Composite Relationship Strength Results</h4>", unsafe_allow_html=True)
            st.markdown("<p style='color: #94A3B8; font-size: 12px; margin-top: -4px; margin-bottom: 10px;'>Scientifically justified composite metric: <b>Strength = Jaccard(A, B) × max(0, PMI(A, B))</b>, balancing empirical volume with statistical synergy.</p>", unsafe_allow_html=True)
            df_str_view = df_rel.sort_values("relationship_strength", ascending=False).head(10)
            headers = ["Skill A", "Skill B", "Pair Count", "Jaccard", "PMI (Bits)", "Composite Strength"]
            rows = [[str(r["skill_a"]), str(r["skill_b"]), str(r["pair_count"]), f"{float(r['jaccard']):.4f}", f"{float(r['pmi']):.4f}", f"{float(r['relationship_strength']):.4f}"] for _, r in df_str_view.iterrows()]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Section 4: Technology Stack and Ecosystem Discovery
# -----------------------------------------------------------------------------

def render_section_4_technology_stacks(analytics_dir: Path):
    """
    Renders Section 4: Multi-skill combinations, directional market association rules,
    interactive evidence drilldown, and explicit distinction between co-occurrence and causation.
    """
    st.markdown("""
    <div style="border-bottom: 2px solid #1E293B; padding-bottom: 8px; margin-top: 24px; margin-bottom: 16px;">
        <h3 style="color: #38BDF8; font-weight: 700; margin: 0; font-size: 20px;">
            4. Technology Stack and Ecosystem Discovery
        </h3>
        <p style="color: #94A3B8; font-size: 13px; margin: 4px 0 0 0;">
            Identification of multi-skill technology combinations (2 to 4 skills) and directional association rules supported by job advertisement evidence.
        </p>
    </div>
    """, unsafe_allow_html=True)

    path_stacks = analytics_dir / "technology_stacks.csv"
    path_rules = analytics_dir / "association_rules.csv"

    # Multi-skill Stacks
    if path_stacks.exists():
        df_stacks = pd.read_csv(path_stacks)
        if not df_stacks.empty:
            st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 6px; margin-bottom: 8px;'>Discovered Multi-Skill Technology Stacks</h4>", unsafe_allow_html=True)

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                min_stack_size = st.selectbox("Minimum Stack Size:", options=[2, 3, 4], index=0, key="sec4_min_stack")
            with col_s2:
                filter_recurring = st.checkbox("Show Only Recurring Stacks (≥ 2 Job Postings)", value=False, key="sec4_filter_rec")

            df_filt_stacks = df_stacks[df_stacks["stack_size"] >= min_stack_size].copy()
            if filter_recurring:
                df_filt_stacks = df_filt_stacks[df_filt_stacks["job_count"] >= 2]

            df_filt_stacks = df_filt_stacks.sort_values(["stack_size", "job_count"], ascending=[False, False]).head(15)

            headers = ["Technology Stack Combination", "Size", "Job Count", "Support Ratio", "Empirical Classification"]
            rows = []
            for _, r in df_filt_stacks.iterrows():
                cnt = int(r["job_count"])
                status = "Recurring Ecosystem (≥ 2 jobs)" if cnt >= 2 else "Single Ad Requirement (1 job)"
                rows.append([
                    str(r["stack"]).replace("'", "").replace("[", "").replace("]", ""),
                    str(r["stack_size"]),
                    str(cnt),
                    f"{float(r['support']):.4f}",
                    status,
                ])
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

            # Evidence Drilldown
            if "supporting_jobs" in df_stacks.columns:
                st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 18px; margin-bottom: 8px;'>🔍 Empirical Evidence Drilldown: Supporting Job Records</h4>", unsafe_allow_html=True)
                stack_list = df_stacks["stack"].tolist()
                selected_stack = st.selectbox("Select Technology Stack to Inspect Grounding Job Postings:", options=stack_list, key="sec4_stack_evidence")

                selected_row = df_stacks[df_stacks["stack"] == selected_stack].iloc[0]
                supp_raw = selected_row.get("supporting_jobs", "[]")
                try:
                    records = json.loads(supp_raw) if isinstance(supp_raw, str) else []
                except Exception:
                    records = []

                if records:
                    st.markdown(f"<p style='color: #38BDF8; font-size: 13px;'>Found <b>{len(records)}</b> supporting job advertisement(s) containing stack: <b>{selected_stack}</b></p>", unsafe_allow_html=True)
                    supp_headers = ["Job Title", "Company", "Location", "Job ID"]
                    supp_rows = [[r.get("title", "N/A"), r.get("company", "N/A"), r.get("location", "N/A"), r.get("job_id", "N/A")] for r in records]
                    st.markdown(render_custom_table(supp_headers, supp_rows), unsafe_allow_html=True)
                else:
                    st.caption(f"Stack {selected_stack} is supported by {selected_row['job_count']} job(s). Metadata recorded in jobs_extracted.csv.")

    # Directional Association Rules
    if path_rules.exists():
        df_rules = pd.read_csv(path_rules)
        if not df_rules.empty:
            st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 20px; margin-bottom: 8px;'>Directional Market Association Rules</h4>", unsafe_allow_html=True)
            st.markdown("<p style='color: #94A3B8; font-size: 12px; margin-top: -6px; margin-bottom: 10px;'>Asymmetric dependencies: Antecedent (If) → Consequent (Then). Support = P(A ∩ B); Confidence = P(B|A); Lift > 1.0 confirms positive synergy.</p>", unsafe_allow_html=True)
            df_rules_view = df_rules.sort_values(["lift", "confidence"], ascending=[False, False]).head(12)
            headers = ["Antecedent (If)", "Consequent (Then)", "Pair Count", "Support", "Confidence", "Lift"]
            rows = [[str(r["antecedent"]), str(r["consequent"]), str(r.get("pair_count", "-")), f"{float(r['support']):.4f}", f"{float(r['confidence']):.4f}", f"{float(r['lift']):.4f}"] for _, r in df_rules_view.iterrows()]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

    # Causation & Dependency Disclaimer
    st.markdown("""
    <div style="background: #0F172A; border-left: 3px solid #F59E0B; padding: 10px 14px; border-radius: 4px; margin-top: 16px; font-size: 12px; color: #94A3B8; line-height: 1.5;">
        <b style="color: #F59E0B;">Methodological Distinction (Co-occurrence vs. Causation):</b><br/>
        Observed co-occurrence and association rules indicate that employers frequently request these skills together in recruiting advertisements. 
        They reflect market co-demand and complementary ecosystems, but do <b>not</b> prove a technical prerequisite, hard dependency, or causation.
    </div>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Section 5: Detailed Results and Methodology
# -----------------------------------------------------------------------------

def render_section_5_detailed_results_methodology(analytics_dir: Path):
    """
    Renders Section 5: Expandable detailed sections for complete pairwise matrices,
    full metrics inventories, configuration values, and plain-language mathematical guides.
    """
    st.markdown("""
    <div style="border-bottom: 2px solid #1E293B; padding-bottom: 8px; margin-top: 24px; margin-bottom: 16px;">
        <h3 style="color: #38BDF8; font-weight: 700; margin: 0; font-size: 20px;">
            5. Detailed Results and Methodology
        </h3>
        <p style="color: #94A3B8; font-size: 13px; margin: 4px 0 0 0;">
            Expandable repository of complete symmetric matrices, comprehensive pairwise tables, hyperparameter configurations, and formula definitions.
        </p>
    </div>
    """, unsafe_allow_html=True)

    path_matrix = analytics_dir / "cooccurrence_matrix.csv"
    path_rel = analytics_dir / "skill_relationships.csv"
    path_edges = analytics_dir / "skill_network_edges.csv"

    # 1. Full Co-occurrence Matrix Table
    if path_matrix.exists():
        df_matrix = pd.read_csv(path_matrix, index_col=0)
        with st.expander("📋 Full Symmetric Co-occurrence Matrix Table", expanded=False):
            st.dataframe(df_matrix, use_container_width=True)

    # 2. Complete Pairwise Metrics Inventory
    if path_rel.exists():
        df_rel = pd.read_csv(path_rel)
        with st.expander(f"📋 Complete Pairwise Metrics Inventory ({len(df_rel)} Valid Skill Pairs)", expanded=False):
            headers = ["Skill A", "Skill B", "Co-occurrence Count", "Jaccard Similarity", "PMI Score (Bits)", "Composite Strength"]
            rows = [[str(r["skill_a"]), str(r["skill_b"]), str(r["pair_count"]), f"{float(r['jaccard']):.4f}", f"{float(r['pmi']):.4f}", f"{float(r['relationship_strength']):.4f}"] for _, r in df_rel.iterrows()]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

    # 3. Pipeline Configuration & Hyperparameters
    with st.expander("⚙️ Pipeline Configuration & Model Hyperparameters", expanded=False):
        config_headers = ["Parameter", "Active Value", "Description / Scientific Purpose"]
        config_rows = [
            ["Taxonomy Version", "v0.1.0 (IT Skills Taxonomy)", "Curated hierarchical skill dictionary with verified technology aliases"],
            ["Intra-Job Deduplication", "Enabled (Strict Set)", "Guarantees each job contributes at most once per canonical skill pair"],
            ["Technology Boundary Isolation", "Active (Java!=JS, C!=C++, React!=React Native)", "Prevents false merges between distinct technological frameworks"],
            ["Minimum Rule Support", "Adaptive (min(0.05, 1.0/N))", "Dynamically scales with sample size to capture low-frequency pilot associations"],
            ["Maximum Stack Size", "4 Skills", "Upper combinatorial bound for frequent multi-skill itemset mining"],
            ["Network Layout Algorithm", "NetworkX Spring Layout (Fruchterman-Reingold)", "Force-directed physics simulation positioning topologically related nodes nearby"],
        ]
        st.markdown(render_custom_table(config_headers, config_rows), unsafe_allow_html=True)

    # 4. Comprehensive Mathematical Reference & Formulas
    with st.expander("📐 Mathematical Reference & Statistical Definitions", expanded=False):
        st.markdown("""
        <div style="font-size: 13px; color: #CBD5E1; line-height: 1.7;">
            <b>1. Skill Co-occurrence C(A, B):</b><br/>
            The exact number of unique job advertisements containing both Skill A and Skill B. Each advertisement contributes at most once.<br/><br/>
            
            <b>2. Jaccard Similarity J(A, B):</b><br/>
            <code>J(A, B) = |J_A ∩ J_B| / |J_A ∪ J_B|</code><br/>
            A normalized metric ranging from 0.0 (no shared postings) to 1.0 (identical distribution of postings).<br/><br/>
            
            <b>3. Pointwise Mutual Information PMI(A, B):</b><br/>
            <code>PMI(A, B) = log₂( P(A, B) / (P(A) × P(B)) )</code><br/>
            Quantifies the probability of co-occurrence relative to statistical independence. PMI > 0 reflects complementary synergy; PMI < 0 reflects substitution.<br/><br/>
            
            <b>4. Composite Relationship Strength:</b><br/>
            <code>Strength(A, B) = Jaccard(A, B) × max(0, PMI(A, B))</code><br/>
            A composite metric combining empirical volume (Jaccard) with statistical affinity (PMI) to prevent rare one-off pairs from dominating.<br/><br/>
            
            <b>5. Directional Association Rules (A → B):</b><br/>
            • <b>Support:</b> <code>P(A ∩ B) = Count(A, B) / Total Jobs</code><br/>
            • <b>Confidence:</b> <code>P(B | A) = Count(A, B) / Count(A)</code><br/>
            • <b>Lift:</b> <code>Confidence(A → B) / P(B)</code> (Lift > 1.0 indicates that requiring Skill A increases the likelihood of requiring Skill B).
        </div>
        """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Master Orchestrator: Unified Analytics Dashboard
# -----------------------------------------------------------------------------

def render_all_analytics(report: dict, mode: str, output_dir: Path):
    """
    Master layout orchestrator assembling the 5 structured sections:
    1. Analysis Overview
    2. Skill Normalization and Extraction Quality
    3. Skill Relationship Analysis (Frequency -> Heatmap -> Network Graph -> Jaccard -> PMI -> Strength)
    4. Technology Stack and Ecosystem Discovery
    5. Detailed Results and Methodology
    """
    analytics_dir = output_dir / mode

    # Section 1: Overview
    render_section_1_overview(report, mode, analytics_dir)

    # Section 2: Normalization Quality & Diagnostics
    render_section_2_normalization_quality(report, analytics_dir)

    # Section 3: Skill Relationship Analysis
    render_section_3_skill_relationship_analysis(analytics_dir)

    # Section 4: Technology Stack and Ecosystem Discovery
    render_section_4_technology_stacks(analytics_dir)

    # Section 5: Detailed Results and Methodology
    render_section_5_detailed_results_methodology(analytics_dir)
