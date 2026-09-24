"""
Dashboard Visualization Layer for Skill Relationship & Technology Stack Analysis
Quantitative Analysis Framework for Technical Skill Identification

Renders:
1. Analysis Overview KPIs & Extraction Mode Badge
2. Skill Frequency Chart (Canonical Names & Categories)
3. Relationship Ranking Chart (Metric Toggle: Co-occurrence, Jaccard, PMI, Strength)
4. Skill Co-occurrence Heatmap (Altair mark_rect + mark_text numeric overlay)
5. Jaccard Similarity & Mathematical Documentation
6. Pointwise Mutual Information (PMI) & Ecosystem Affinity
7. Composite Relationship Strength Table
8. Interactive Skill Network Graph (NetworkX Spring Layout, SVG with glow, tooltips, sliders)
9. Directional Association Rules (Support, Confidence, Lift)
10. Technology Stack Patterns & Supporting Job Record Evidence Drilldown
"""

import json
from pathlib import Path
from typing import Optional

import altair as alt
import networkx as nx
import pandas as pd
import streamlit as st

from src.extraction.normalization import get_skill_category
from theme import render_custom_table


# -----------------------------------------------------------------------------
# 1. Overview KPIs & Metadata
# -----------------------------------------------------------------------------

def render_analysis_overview(report: dict, mode: str, analytics_dir: Path):
    """Render high-level analysis KPIs, provenance label, and data quality warnings."""
    jobs_analyzed = report.get("jobs_with_selected_skills", 0)
    unique_skills = report.get("unique_skills", 0)
    skill_pairs = report.get("skill_pairs", 0)
    has_rules = report.get("association_rules_generated", False)
    has_stacks = report.get("technology_stacks_generated", False)

    mode_display = {
        "lexical_skills": "Lexical Skill Extraction (Keyword Taxonomy)",
        "semantic_skills": "Semantic Skill Extraction (Embedding Similarity)",
        "combined": "Combined Extraction (Lexical ∪ Semantic)",
    }.get(mode, mode.replace("_", " ").title())

    st.markdown(f"""
    <div style="background: #111827; border: 1px solid #1F2937; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
        <div>
            <span style="color: #9CA3AF; font-size: 13px;">Active Extraction Mode:</span>
            <span style="color: #38BDF8; font-weight: 600; font-size: 13px; margin-left: 8px;">{mode_display}</span>
        </div>
        <div>
            <span style="background: rgba(56, 189, 248, 0.15); color: #38BDF8; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.3);">
                Canonical Taxonomy v0.1.0
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
        <div class="kpi-card clean">
            <div class="kpi-label">Jobs Analysed</div>
            <div class="kpi-value">{jobs_analyzed}</div>
            <div class="kpi-trend">
                <span class="trend-up">With validated skills</span>
            </div>
        </div>
        <div class="kpi-card scraped">
            <div class="kpi-label">Unique Skills</div>
            <div class="kpi-value">{unique_skills}</div>
            <div class="kpi-trend">
                <span class="trend-up">Canonical technologies</span>
            </div>
        </div>
        <div class="kpi-card partial">
            <div class="kpi-label">Skill Pairs</div>
            <div class="kpi-value">{skill_pairs}</div>
            <div class="kpi-trend">
                <span class="trend-neutral">Co-occurring pairs</span>
            </div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Tech Patterns</div>
            <div class="kpi-value">{"Identified" if has_stacks else "Pending"}</div>
            <div class="kpi-trend">
                <span class="trend-up" style="color: #A78BFA;">Multi-skill stacks</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if jobs_analyzed < 5:
        st.info(
            f"ℹ️ **Research Integrity Notice:** Currently evaluating a pilot set of {jobs_analyzed} job advertisements. "
            "Pairwise co-occurrence and PMI scores reflect observed signals in this sample. As additional job flyers "
            "are processed through the OCR and extraction pipeline, statistical stability will increase."
        )


# -----------------------------------------------------------------------------
# 2. Skill Frequency Chart & Table (Phase 2.D)
# -----------------------------------------------------------------------------

def render_top_skills(analytics_dir: Path):
    path = analytics_dir / "skill_frequency.csv"
    if not path.exists():
        return

    df = pd.read_csv(path)
    if df.empty:
        return

    st.subheader("📊 Skill Frequency Distribution")
    st.markdown(
        "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>"
        "Most frequently requested canonical technologies across analyzed IT job postings."
        "</p>",
        unsafe_allow_html=True,
    )

    df_chart = df.head(15).copy()
    df_chart["category"] = df_chart["skill"].apply(get_skill_category)

    chart = (
        alt.Chart(df_chart)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            x=alt.X("job_count:Q", title="Job Postings Count"),
            y=alt.Y("skill:N", sort="-x", title="Canonical Skill"),
            color=alt.Color(
                "category:N",
                scale=alt.Scale(scheme="category10"),
                legend=alt.Legend(title="Technology Domain", orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("skill:N", title="Canonical Skill"),
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("job_count:Q", title="Job Count"),
                alt.Tooltip("frequency_pct:Q", title="Market Share (%)", format=".1f"),
            ],
        )
        .properties(height=340)
    )
    st.altair_chart(chart, use_container_width=True)

    with st.expander("📋 View Normalized Skill Frequency Table", expanded=False):
        df_display = df.copy()
        df_display["category"] = df_display["skill"].apply(get_skill_category)
        headers = ["Canonical Skill", "Domain Category", "Job Count", "Market Percentage"]
        rows = [
            [
                str(r["skill"]),
                str(r["category"]),
                str(r["job_count"]),
                f"{r['frequency_pct']:.1f}%",
            ]
            for _, r in df_display.iterrows()
        ]
        st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 3. Relationship Ranking Chart & Skill Pairs (Phase 2.C)
# -----------------------------------------------------------------------------

def render_skill_pairs(analytics_dir: Path):
    path_pairs = analytics_dir / "skill_pairs.csv"
    path_rel = analytics_dir / "skill_relationships.csv"

    if not path_pairs.exists():
        return

    df_pairs = pd.read_csv(path_pairs)
    if df_pairs.empty:
        return

    st.subheader("📈 Skill Relationship Ranking")
    st.markdown(
        "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:12px;'>"
        "Ranking of observed skill relationships by selected quantitative metric."
        "</p>",
        unsafe_allow_html=True,
    )

    # Merge relationship strength if available
    df_data = df_pairs.copy()
    if path_rel.exists():
        df_rel = pd.read_csv(path_rel)
        if not df_rel.empty:
            df_data = df_rel.copy()

    metric_choice = st.selectbox(
        "Rank Skill Relationships By:",
        options=[
            "Composite Relationship Strength",
            "Pair Co-occurrence Count",
            "Jaccard Similarity",
            "Pointwise Mutual Information (PMI)",
        ],
        index=0 if "relationship_strength" in df_data.columns else 1,
        key="rel_ranking_metric",
    )

    metric_col_map = {
        "Composite Relationship Strength": "relationship_strength",
        "Pair Co-occurrence Count": "pair_count",
        "Jaccard Similarity": "jaccard",
        "Pointwise Mutual Information (PMI)": "pmi",
    }
    target_col = metric_col_map[metric_choice]

    if target_col not in df_data.columns:
        target_col = "pair_count"

    df_sorted = df_data.sort_values(target_col, ascending=False).head(15).copy()
    df_sorted["pair_label"] = df_sorted["skill_a"].astype(str) + " + " + df_sorted["skill_b"].astype(str)

    chart = (
        alt.Chart(df_sorted)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5, color="#818CF8")
        .encode(
            x=alt.X(f"{target_col}:Q", title=metric_choice),
            y=alt.Y("pair_label:N", sort="-x", title="Skill Pair"),
            tooltip=[
                alt.Tooltip("pair_label:N", title="Skill Pair"),
                alt.Tooltip(f"{target_col}:Q", title=metric_choice, format=".4f" if target_col != "pair_count" else "d"),
                alt.Tooltip("pair_count:Q", title="Co-occurrence Count"),
            ],
        )
        .properties(height=340)
    )
    st.altair_chart(chart, use_container_width=True)

    with st.expander("📋 View Detailed Skill Pairs Table", expanded=False):
        headers = ["Skill A", "Skill B", "Co-occurrence Count"]
        rows = [[str(r["skill_a"]), str(r["skill_b"]), str(r["pair_count"])] for _, r in df_sorted.iterrows()]
        st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 4. Skill Co-occurrence Heatmap (Phase 2.B)
# -----------------------------------------------------------------------------

def render_cooccurrence(analytics_dir: Path):
    path = analytics_dir / "cooccurrence_matrix.csv"
    if not path.exists():
        return

    df = pd.read_csv(path, index_col=0)
    if df.empty:
        return

    st.subheader("🔥 Skill Co-occurrence Heatmap")
    st.markdown(
        "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:14px;'>"
        "Symmetric co-occurrence matrix C(A, B). Diagonal C(A, A) represents individual skill frequency. "
        "Each job advert contributes at most once per canonical skill pair."
        "</p>",
        unsafe_allow_html=True,
    )

    try:
        index_col = df.index.name or "index"
        df_long = df.reset_index().melt(id_vars=index_col, var_name="skill_b", value_name="count")
        df_long.rename(columns={index_col: "skill_a"}, inplace=True)

        heatmap = (
            alt.Chart(df_long)
            .mark_rect()
            .encode(
                x=alt.X("skill_a:N", title="Canonical Skill A", sort=sorted(df.index.tolist())),
                y=alt.Y("skill_b:N", title="Canonical Skill B", sort=sorted(df.index.tolist())),
                color=alt.Color(
                    "count:Q",
                    scale=alt.Scale(scheme="tealblues"),
                    title="Co-occurrence",
                ),
                tooltip=[
                    alt.Tooltip("skill_a:N", title="Skill A"),
                    alt.Tooltip("skill_b:N", title="Skill B"),
                    alt.Tooltip("count:Q", title="Co-occurrence Count"),
                ],
            )
        )

        # Overlay numeric labels directly on cells
        text_labels = (
            alt.Chart(df_long)
            .mark_text(baseline="middle")
            .encode(
                x="skill_a:N",
                y="skill_b:N",
                text=alt.condition(alt.datum.count > 0, alt.Text("count:Q"), alt.value("")),
                color=alt.condition(
                    alt.datum.count > (df_long["count"].max() * 0.6),
                    alt.value("white"),
                    alt.value("#CBD5E1"),
                ),
            )
        )

        composite_chart = (heatmap + text_labels).properties(height=380)
        st.altair_chart(composite_chart, use_container_width=True)
    except Exception as e:
        st.warning(f"Heatmap visualization note: {e}")

    with st.expander("📋 View Raw Co-occurrence Matrix Table", expanded=False):
        st.dataframe(df, use_container_width=True)


# -----------------------------------------------------------------------------
# 5. Jaccard Similarity (Phase 3 & 4)
# -----------------------------------------------------------------------------

def render_jaccard(analytics_dir: Path):
    path = analytics_dir / "jaccard_similarity.csv"
    if not path.exists():
        return

    df = pd.read_csv(path)
    if df.empty:
        return

    st.subheader("📐 Jaccard Similarity")
    st.markdown(
        "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:14px;'>"
        "Measures normalized skill overlap: <b>J(A, B) = |J_A ∩ J_B| / |J_A ∪ J_B|</b>. "
        "Range: [0.0, 1.0], where 1.0 indicates perfect co-occurrence equivalence."
        "</p>",
        unsafe_allow_html=True,
    )

    df_display = df.sort_values("jaccard", ascending=False).head(30)
    headers = ["Skill A", "Skill B", "Intersection |J_A ∩ J_B|", "Union |J_A ∪ J_B|", "Jaccard Score"]
    rows = [
        [
            str(r["skill_a"]),
            str(r["skill_b"]),
            str(r.get("intersection", "-")),
            str(r.get("union", "-")),
            f"{float(r['jaccard']):.4f}",
        ]
        for _, r in df_display.iterrows()
    ]
    st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 6. Pointwise Mutual Information (PMI) (Phase 3 & 4)
# -----------------------------------------------------------------------------

def render_pmi(analytics_dir: Path):
    path = analytics_dir / "pmi_scores.csv"
    if not path.exists():
        return

    df = pd.read_csv(path)
    if df.empty:
        return

    st.subheader("💡 Pointwise Mutual Information (PMI)")
    st.markdown(
        "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:14px;'>"
        "Quantifies statistical dependence: <b>PMI(A, B) = log₂( P(A, B) / (P(A) × P(B)) )</b>. "
        "PMI > 0 indicates complementary technology ecosystem affinity; PMI < 0 indicates technology substitution."
        "</p>",
        unsafe_allow_html=True,
    )

    df_display = df.sort_values("pmi", ascending=False).head(30)
    headers = ["Skill A", "Skill B", "Co-occurrence", "PMI Score (Bits)", "Interpretation"]
    rows = []
    for _, r in df_display.iterrows():
        pmi_val = float(r["pmi"])
        interpretation = "Complementary" if pmi_val > 0.5 else ("Independent" if abs(pmi_val) <= 0.5 else "Substitutes")
        rows.append([
            str(r["skill_a"]),
            str(r["skill_b"]),
            str(r["cooccurrence"]),
            f"{pmi_val:.4f}",
            interpretation,
        ])
    st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 7. Composite Relationship Strength (Phase 3 & 4)
# -----------------------------------------------------------------------------

def render_relationship_strength(analytics_dir: Path):
    path = analytics_dir / "skill_relationships.csv"
    if not path.exists():
        return

    df = pd.read_csv(path)
    if df.empty:
        return

    st.subheader("⚡ Composite Relationship Strength")
    st.markdown(
        "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:14px;'>"
        "Scientifically validated composite metric: <b>Strength(A, B) = Jaccard(A, B) × max(0, PMI(A, B))</b>. "
        "Balances empirical co-occurrence frequency against statistical independence."
        "</p>",
        unsafe_allow_html=True,
    )

    df_display = df.sort_values("relationship_strength", ascending=False).head(30)
    headers = ["Skill A", "Skill B", "Pair Count", "Jaccard", "PMI", "Relationship Strength"]
    rows = [
        [
            str(r["skill_a"]),
            str(r["skill_b"]),
            str(r["pair_count"]),
            f"{float(r['jaccard']):.4f}",
            f"{float(r['pmi']):.4f}",
            f"{float(r['relationship_strength']):.4f}",
        ]
        for _, r in df_display.iterrows()
    ]
    st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 8. Interactive Skill Network Graph (Phase 2.A)
# -----------------------------------------------------------------------------

def _generate_network_svg(
    df_edges: pd.DataFrame,
    weight_metric: str = "weight",
    min_count: int = 1,
    min_strength: float = 0.0,
) -> tuple[str, int, int]:
    """
    Constructs an interactive SVG network visualization with NetworkX spring layout.
    Filters edges by min_count and min_strength, sizes nodes by degree, and embeds tooltips.
    """
    if df_edges.empty:
        return "", 0, 0

    # Filter edges
    filtered = df_edges.copy()
    if "pair_count" in filtered.columns:
        filtered = filtered[filtered["pair_count"] >= min_count]
    elif "weight" in filtered.columns:
        filtered = filtered[filtered["weight"] >= min_count]

    if "relationship_strength" in filtered.columns:
        filtered = filtered[filtered["relationship_strength"] >= min_strength]

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

    if len(G.nodes) == 0:
        return "", 0, 0

    # Compute NetworkX force layout
    k_val = 1.8 / (len(G.nodes) ** 0.5 if len(G.nodes) > 1 else 1)
    pos = nx.spring_layout(G, seed=42, k=k_val, iterations=60)

    # Canvas dimensions
    width, height = 820, 500
    cx_offset, cy_offset = width / 2, height / 2
    scale_x, scale_y = 340, 200

    degrees = dict(G.degree(weight="weight"))
    max_deg = max(degrees.values()) if degrees else 1

    # Domain category colors
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
        f'<div style="text-align: center; margin-bottom: 16px;">'
        f'<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="background: #0B1120; border-radius: 12px; border: 1px solid #1E293B; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">'
    ]

    # Grid pattern and linear gradients
    svg.append(
        '<defs>'
        '<pattern id="net_grid" width="40" height="40" patternUnits="userSpaceOnUse">'
        '<path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1E293B" stroke-width="0.5" stroke-opacity="0.6" />'
        '</pattern>'
        '<linearGradient id="edge_grad" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#38BDF8" stop-opacity="0.8" />'
        '<stop offset="100%" stop-color="#818CF8" stop-opacity="0.5" />'
        '</linearGradient>'
        '</defs>'
        '<rect width="100%" height="100%" fill="url(#net_grid)" />'
    )

    # 1. Draw Edges with tooltips
    for u, v, data in G.edges(data=True):
        x1 = int(pos[u][0] * scale_x + cx_offset)
        y1 = int(pos[u][1] * scale_y + cy_offset)
        x2 = int(pos[v][0] * scale_x + cx_offset)
        y2 = int(pos[v][1] * scale_y + cy_offset)
        raw_w = data.get("weight", 1.0)
        stroke_w = max(1.8, min(raw_w * 2.0, 7.5))

        pair_c = data.get("pair_count", 1)
        j_val = data.get("jaccard", 0.0)
        p_val = data.get("pmi", 0.0)
        s_val = data.get("strength", 0.0)

        tooltip = f"Edge: {u} ↔ {v}&#10;Pair Count: {pair_c}&#10;Jaccard: {j_val:.4f}&#10;PMI: {p_val:.4f}&#10;Rel. Strength: {s_val:.4f}"

        svg.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="url(#edge_grad)" stroke-width="{stroke_w}" stroke-linecap="round">'
            f'<title>{tooltip}</title>'
            f'</line>'
        )

    # 2. Draw Nodes with glow halos and category styling
    for node in sorted(G.nodes()):
        x = int(pos[node][0] * scale_x + cx_offset)
        y = int(pos[node][1] * scale_y + cy_offset)
        deg = degrees.get(node, 1)
        r = 14 + int((deg / max_deg) * 14)
        cat = get_skill_category(node)
        color = cat_colors.get(cat, "#38BDF8")

        node_tooltip = f"Canonical Skill: {node}&#10;Domain: {cat}&#10;Network Degree: {G.degree(node)}&#10;Weighted Volume: {deg:.1f}"

        # Outer glow
        svg.append(f'<circle cx="{x}" cy="{y}" r="{r + 6}" fill="{color}" fill-opacity="0.18" />')
        # Main Node circle
        svg.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="#0F172A" stroke="{color}" stroke-width="2.5">'
            f'<title>{node_tooltip}</title>'
            f'</circle>'
        )
        # Node text label
        svg.append(
            f'<text x="{x}" y="{y + r + 15}" fill="#F1F5F9" font-size="12" font-weight="600" '
            f'text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, sans-serif">'
            f'<title>{node_tooltip}</title>'
            f'{node}</text>'
        )

    svg.append("</svg></div>")
    return "".join(svg), len(G.nodes), len(G.edges)


def render_skill_networks(analytics_dir: Path):
    path_edges = analytics_dir / "skill_network_edges.csv"
    if not path_edges.exists():
        return

    df_edges = pd.read_csv(path_edges)
    if df_edges.empty:
        return

    st.subheader("🕸️ Interactive Skill Relationship Network Graph")
    st.markdown(
        "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>"
        "Topological network of canonical skills. Nodes represent technologies (colored by domain, sized by degree); "
        "edges represent co-occurrence strength. Zero co-occurrence pairs are excluded."
        "</p>",
        unsafe_allow_html=True,
    )

    # Filter controls
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        max_pair = int(df_edges["pair_count"].max()) if "pair_count" in df_edges.columns else 1
        slider_max = max(2, max_pair)
        min_cooc = st.slider("Minimum Co-occurrence Count", min_value=1, max_value=slider_max, value=1)
    with col_c2:
        min_strength = st.slider("Minimum Relationship Strength", min_value=0.0, max_value=2.0, value=0.0, step=0.1)
    with col_c3:
        weight_metric = st.selectbox(
            "Edge Weighting Metric:",
            options=["weight", "jaccard", "relationship_strength", "pmi"],
            format_func=lambda x: {
                "weight": "Pair Count (Frequency)",
                "jaccard": "Jaccard Similarity",
                "relationship_strength": "Composite Strength",
                "pmi": "PMI Score",
            }.get(x, x),
        )

    # Generate interactive SVG network graph
    svg_html, node_count, edge_count = _generate_network_svg(
        df_edges,
        weight_metric=weight_metric,
        min_count=min_cooc,
        min_strength=min_strength,
    )

    if svg_html:
        st.markdown(svg_html, unsafe_allow_html=True)
        st.caption(f"Active Network Subgraph: **{node_count}** canonical skills connected by **{edge_count}** relationship edges.")
    else:
        st.warning(
            f"No skill relationships meet the selected filter criteria "
            f"(Minimum Co-occurrence = {min_cooc}, Minimum Strength = {min_strength:.1f}). "
            "Please lower the slider thresholds to display lower-frequency connections."
        )

    with st.expander("📋 View Network Edges Table", expanded=False):
        df_display = df_edges.copy()
        if "relationship_strength" not in df_display.columns and "jaccard" in df_display.columns and "pmi" in df_display.columns:
            df_display["relationship_strength"] = (df_display["jaccard"] * df_display["pmi"].clip(lower=0)).round(6)

        headers = ["Source Skill", "Target Skill", "Weight (Count)", "Jaccard", "PMI", "Rel. Strength"]
        rows = [
            [
                str(r.get("source_skill", "")),
                str(r.get("target_skill", "")),
                str(r.get("pair_count", r.get("weight", ""))),
                f"{float(r.get('jaccard', 0.0)):.4f}",
                f"{float(r.get('pmi', 0.0)):.4f}",
                f"{float(r.get('relationship_strength', 0.0)):.4f}",
            ]
            for _, r in df_display.iterrows()
        ]
        st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 9. Association Rules (Phase 3 & 4)
# -----------------------------------------------------------------------------

def render_association_rules(analytics_dir: Path):
    path = analytics_dir / "association_rules.csv"
    if not path.exists():
        return

    df = pd.read_csv(path)
    if df.empty:
        return

    st.subheader("🎯 Directional Market Association Rules")
    st.markdown(
        "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:14px;'>"
        "Directional dependencies (Antecedent → Consequent) based on market support, confidence, and lift. "
        "<b>Lift > 1.0</b> confirms positive synergistic demand."
        "</p>",
        unsafe_allow_html=True,
    )

    df_display = df.sort_values(["lift", "confidence"], ascending=[False, False]).head(30)
    headers = ["Antecedent (If)", "Consequent (Then)", "Pair Count", "Support", "Confidence", "Lift"]
    rows = [
        [
            str(r["antecedent"]),
            str(r["consequent"]),
            str(r.get("pair_count", "-")),
            f"{float(r['support']):.4f}",
            f"{float(r['confidence']):.4f}",
            f"{float(r['lift']):.4f}",
        ]
        for _, r in df_display.iterrows()
    ]
    st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 10. Technology Stack Patterns & Evidence Drilldown (Phase 2.E)
# -----------------------------------------------------------------------------

def render_technology_stacks(analytics_dir: Path):
    path = analytics_dir / "technology_stacks.csv"
    if not path.exists():
        return

    df = pd.read_csv(path)
    if df.empty:
        return

    st.subheader("📦 Technology Stack Patterns")
    st.markdown(
        "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:14px;'>"
        "Recurring multi-skill technology combinations (2 to 4 skills) found in individual job advertisements. "
        "<i>Note: A pairwise relationship alone does not prove a complete stack; multi-skill combinations provide empirical evidence of cohesive ecosystem adoption.</i>"
        "</p>",
        unsafe_allow_html=True,
    )

    df_display = df.sort_values(["stack_size", "job_count"], ascending=[False, False]).head(25).copy()

    headers = ["Technology Stack", "Stack Size", "Job Count", "Support Ratio"]
    rows = [
        [
            str(r["stack"]).replace("'", "").replace("[", "").replace("]", ""),
            str(r["stack_size"]),
            str(r["job_count"]),
            f"{float(r['support']):.4f}",
        ]
        for _, r in df_display.iterrows()
    ]
    st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

    # Supporting Records Drilldown
    if "supporting_jobs" in df.columns:
        st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 18px;'>🔍 Evidence Drilldown: Supporting Job Records</h4>", unsafe_allow_html=True)
        stack_options = df["stack"].tolist()
        selected_stack = st.selectbox("Select Technology Stack Pattern to Inspect Supporting Postings:", options=stack_options, key="stack_drilldown_select")

        selected_row = df[df["stack"] == selected_stack].iloc[0]
        supp_raw = selected_row.get("supporting_jobs", "[]")
        try:
            records = json.loads(supp_raw) if isinstance(supp_raw, str) else []
        except Exception:
            records = []

        if records:
            st.markdown(f"<p style='color: #38BDF8; font-size: 13px;'>Found <b>{len(records)}</b> supporting job advertisement(s) containing the stack: <b>{selected_stack}</b></p>", unsafe_allow_html=True)
            supp_headers = ["Job Title", "Company", "Location", "Job ID"]
            supp_rows = [[r.get("title", "N/A"), r.get("company", "N/A"), r.get("location", "N/A"), r.get("job_id", "N/A")] for r in records]
            st.markdown(render_custom_table(supp_headers, supp_rows), unsafe_allow_html=True)
        else:
            st.caption(f"Stack {selected_stack} is supported by {selected_row['job_count']} job(s). Detailed raw flyer metadata is recorded in jobs_extracted.csv.")


# -----------------------------------------------------------------------------
# 11. Unified Analytics Dashboard Orchestrator
# -----------------------------------------------------------------------------

def render_all_analytics(report: dict, mode: str, output_dir: Path):
    """Assembles the complete Phase 4 analytics dashboard."""
    analytics_dir = output_dir / mode

    # 1. Overview KPIs & Extraction Mode
    render_analysis_overview(report, mode, analytics_dir)

    # 2. Charts Row: Frequency Distribution & Relationship Ranking
    col1, col2 = st.columns(2)
    with col1:
        render_top_skills(analytics_dir)
    with col2:
        render_skill_pairs(analytics_dir)

    st.write("---")

    # 3. Co-occurrence Matrix & Heatmap
    render_cooccurrence(analytics_dir)

    st.write("---")

    # 4. Interactive Skill Network Graph
    render_skill_networks(analytics_dir)

    st.write("---")

    # 5. Formal Quantitative Tables (Jaccard, PMI, Composite Strength)
    col3, col4 = st.columns(2)
    with col3:
        render_jaccard(analytics_dir)
    with col4:
        render_pmi(analytics_dir)

    render_relationship_strength(analytics_dir)

    st.write("---")

    # 6. Directional Association Rules
    render_association_rules(analytics_dir)

    st.write("---")

    # 7. Technology Stack Patterns & Supporting Records
    render_technology_stacks(analytics_dir)
