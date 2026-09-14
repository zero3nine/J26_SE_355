import pandas as pd
import streamlit as st
from pathlib import Path
import altair as alt
import networkx as nx

from theme import render_custom_table


def render_analysis_overview(report: dict, analytics_dir: Path):
    """Render high level KPI metrics."""
    jobs_analyzed = report.get("jobs_with_selected_skills", 0)
    unique_skills = report.get("unique_skills", 0)
    skill_pairs = report.get("skill_pairs", 0)
    
    # Check if there are edges or technology stacks generated
    has_rules = report.get("association_rules_generated", False)
    
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
        <div class="kpi-card clean">
            <div class="kpi-label">Jobs Analysed</div>
            <div class="kpi-value">{jobs_analyzed}</div>
            <div class="kpi-trend">
                <span class="trend-up">With usable skills</span>
            </div>
        </div>
        <div class="kpi-card scraped">
            <div class="kpi-label">Unique Skills</div>
            <div class="kpi-value">{unique_skills}</div>
            <div class="kpi-trend">
                <span class="trend-up">Extracted terms</span>
            </div>
        </div>
        <div class="kpi-card partial">
            <div class="kpi-label">Skill Pairs</div>
            <div class="kpi-value">{skill_pairs}</div>
            <div class="kpi-trend">
                <span class="trend-neutral">Co-occurring</span>
            </div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Assoc. Rules</div>
            <div class="kpi-value">{"Yes" if has_rules else "No"}</div>
            <div class="kpi-trend">
                <span class="trend-up" style="color: #A78BFA;">Generated</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_top_skills(analytics_dir: Path):
    path = analytics_dir / "skill_frequency.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not df.empty:
            st.subheader("Top Skills")
            
            # Interactive Altair Bar Chart
            df_chart = df.head(15).copy()
            chart = (
                alt.Chart(df_chart)
                .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5, color="#38BDF8")
                .encode(
                    x=alt.X("job_count:Q", title="Job Postings Count"),
                    y=alt.Y("skill:N", sort="-x", title="Technical Skill"),
                    tooltip=[
                        alt.Tooltip("skill:N", title="Skill"),
                        alt.Tooltip("job_count:Q", title="Job Count"),
                        alt.Tooltip("frequency_pct:Q", title="Percentage (%)", format=".1f"),
                    ],
                )
                .properties(height=320)
            )
            st.altair_chart(chart, use_container_width=True)

            with st.expander("📋 View Detailed Top Skills Table", expanded=False):
                df_display = df.head(30)
                headers = ["Skill", "Frequency", "Percentage"]
                rows = []
                for _, row in df_display.iterrows():
                    rows.append([
                        str(row.get("skill", "")), 
                        str(row.get("job_count", 0)), 
                        f"{row.get('frequency_pct', 0)}%"
                    ])
                st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


def render_skill_pairs(analytics_dir: Path):
    path = analytics_dir / "skill_pairs.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not df.empty:
            st.subheader("Skill Pair Relationships")
            
            # Interactive Altair Bar Chart
            df_top = df.sort_values("pair_count", ascending=False).head(15).copy()
            df_top["pair_label"] = df_top["skill_a"].astype(str) + " + " + df_top["skill_b"].astype(str)
            
            chart = (
                alt.Chart(df_top)
                .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5, color="#818CF8")
                .encode(
                    x=alt.X("pair_count:Q", title="Co-occurrence Frequency"),
                    y=alt.Y("pair_label:N", sort="-x", title="Skill Pair"),
                    tooltip=[
                        alt.Tooltip("pair_label:N", title="Skill Pair"),
                        alt.Tooltip("pair_count:Q", title="Pair Co-occurrence"),
                    ],
                )
                .properties(height=320)
            )
            st.altair_chart(chart, use_container_width=True)

            with st.expander("📋 View Detailed Skill Pairs Table", expanded=False):
                df_display = df.sort_values("pair_count", ascending=False).head(30)
                headers = ["Source Skill", "Target Skill", "Pair Count"]
                rows = [[str(r["skill_a"]), str(r["skill_b"]), str(r["pair_count"])] for _, r in df_display.iterrows()]
                st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


def render_cooccurrence(analytics_dir: Path):
    path = analytics_dir / "cooccurrence_matrix.csv"
    if path.exists():
        df = pd.read_csv(path, index_col=0)
        if not df.empty:
            st.subheader("Skill Co-occurrence")
            st.markdown(
                "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>"
                "Matrix representing how often two technical skills occur within the same job advertisement."
                "</p>",
                unsafe_allow_html=True,
            )
            
            # Interactive Altair Heatmap
            try:
                df_long = df.reset_index().melt(id_vars=df.index.name or "index", var_name="skill_b", value_name="count")
                index_col = df.index.name or "index"
                df_long.rename(columns={index_col: "skill_a"}, inplace=True)
                
                heatmap = (
                    alt.Chart(df_long)
                    .mark_rect()
                    .encode(
                        x=alt.X("skill_a:N", title="Skill A"),
                        y=alt.Y("skill_b:N", title="Skill B"),
                        color=alt.Color(
                            "count:Q",
                            scale=alt.Scale(scheme="tealblues"),
                            title="Co-occurrence",
                        ),
                        tooltip=[
                            alt.Tooltip("skill_a:N", title="Skill A"),
                            alt.Tooltip("skill_b:N", title="Skill B"),
                            alt.Tooltip("count:Q", title="Co-occurrence"),
                        ],
                    )
                    .properties(height=380)
                )
                st.altair_chart(heatmap, use_container_width=True)
            except Exception:
                pass

            st.dataframe(df, height=300, use_container_width=True)


def render_jaccard(analytics_dir: Path):
    path = analytics_dir / "jaccard_similarity.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not df.empty:
            st.subheader("Jaccard Similarity")
            st.markdown(
                "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>"
                "Jaccard measures normalized co-occurrence overlap: J(A, B) = |J_A ∩ J_B| / |J_A ∪ J_B|."
                "</p>",
                unsafe_allow_html=True,
            )
            
            df_display = df.sort_values("jaccard", ascending=False).head(30)
            headers = ["Skill A", "Skill B", "Jaccard Score"]
            rows = [[str(r["skill_a"]), str(r["skill_b"]), f"{r['jaccard']:.4f}"] for _, r in df_display.iterrows()]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


def render_pmi(analytics_dir: Path):
    path = analytics_dir / "pmi_scores.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not df.empty:
            st.subheader("Pointwise Mutual Information (PMI)")
            st.markdown(
                "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>"
                "PMI measures statistical affinity: PMI > 0 indicates complementary technology ecosystems; "
                "PMI < 0 indicates technology substitution."
                "</p>",
                unsafe_allow_html=True,
            )
            df_display = df.sort_values("pmi", ascending=False).head(30)
            headers = ["Skill A", "Skill B", "PMI Score"]
            rows = [[str(r["skill_a"]), str(r["skill_b"]), f"{r['pmi']:.4f}"] for _, r in df_display.iterrows()]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


def render_association_rules(analytics_dir: Path):
    path = analytics_dir / "association_rules.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not df.empty:
            st.subheader("Association Rules")
            st.markdown(
                "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>"
                "Identify directional market dependencies (Antecedent → Consequent) using Support, Confidence, and Lift."
                "</p>",
                unsafe_allow_html=True,
            )
            df_display = df.sort_values(["confidence", "lift"], ascending=[False, False]).head(30)
            headers = ["Antecedent", "Consequent", "Support", "Confidence", "Lift"]
            rows = [
                [
                    str(r["antecedent"]),
                    str(r["consequent"]),
                    f"{r['support']:.4f}",
                    f"{r['confidence']:.4f}",
                    f"{r['lift']:.4f}",
                ]
                for _, r in df_display.iterrows()
            ]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


def render_technology_stacks(analytics_dir: Path):
    path = analytics_dir / "technology_stacks.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not df.empty:
            st.subheader("Technology Stacks")
            st.markdown(
                "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>"
                "Identify frequently recurring multi-skill technology combinations (3 to 4 skills)."
                "</p>",
                unsafe_allow_html=True,
            )
            df_display = df.sort_values("job_count", ascending=False).head(30)
            headers = ["Technology Stack", "Stack Size", "Job Count", "Support"]
            rows = [
                [
                    str(r["stack"]).replace("'", "").replace("[", "").replace("]", ""),
                    str(r["stack_size"]),
                    str(r["job_count"]),
                    f"{r['support']:.4f}",
                ]
                for _, r in df_display.iterrows()
            ]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


def _generate_network_svg(df_edges: pd.DataFrame) -> str:
    """Constructs a responsive dark-themed SVG network graph using NetworkX spring layout."""
    G = nx.Graph()
    for _, r in df_edges.iterrows():
        u = str(r.get("source_skill", r.get("source", "")))
        v = str(r.get("target_skill", r.get("target", "")))
        w = float(r.get("weight", 1.0))
        if u and v:
            G.add_edge(u, v, weight=w)

    if len(G.nodes) == 0:
        return ""

    # Calculate layout
    k_val = 2.0 / (len(G.nodes) ** 0.5 if len(G.nodes) > 1 else 1)
    pos = nx.spring_layout(G, seed=42, k=k_val, iterations=50)

    # SVG Canvas dimensions
    width, height = 800, 480
    cx_offset, cy_offset = width / 2, height / 2
    scale_x, scale_y = 330, 190

    # Node degrees for sizing
    degrees = dict(G.degree(weight="weight"))
    max_deg = max(degrees.values()) if degrees else 1

    svg = [
        f'<div style="text-align: center; margin-bottom: 16px;">'
        f'<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="background: #0B1120; border-radius: 12px; border: 1px solid #1E293B; box-shadow: 0 4px 20px rgba(0,0,0,0.4);">'
    ]

    # Subtle grid lines
    svg.append(
        '<defs>'
        '<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">'
        '<path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1E293B" stroke-width="0.5" stroke-opacity="0.5" />'
        '</pattern>'
        '<linearGradient id="edgeGrad" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#38BDF8" stop-opacity="0.8" />'
        '<stop offset="100%" stop-color="#818CF8" stop-opacity="0.4" />'
        '</linearGradient>'
        '</defs>'
        '<rect width="100%" height="100%" fill="url(#grid)" />'
    )

    # 1. Draw Edges
    for u, v, data in G.edges(data=True):
        x1 = int(pos[u][0] * scale_x + cx_offset)
        y1 = int(pos[u][1] * scale_y + cy_offset)
        x2 = int(pos[v][0] * scale_x + cx_offset)
        y2 = int(pos[v][1] * scale_y + cy_offset)
        raw_w = data.get("weight", 1.0)
        stroke_w = max(1.5, min(raw_w * 1.5, 7.0))
        svg.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="url(#edgeGrad)" stroke-width="{stroke_w}" stroke-linecap="round" />'
        )

    # 2. Draw Nodes
    node_palette = ["#38BDF8", "#34D399", "#A78BFA", "#FBBF24", "#F43F5E", "#60A5FA"]
    for i, node in enumerate(sorted(G.nodes())):
        x = int(pos[node][0] * scale_x + cx_offset)
        y = int(pos[node][1] * scale_y + cy_offset)
        deg = degrees.get(node, 1)
        r = 14 + int((deg / max_deg) * 12)
        color = node_palette[i % len(node_palette)]

        # Outer glow
        svg.append(f'<circle cx="{x}" cy="{y}" r="{r + 4}" fill="{color}" fill-opacity="0.15" />')
        # Node circle
        svg.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="#0F172A" stroke="{color}" stroke-width="2.5" />'
        )
        # Skill text label
        svg.append(
            f'<text x="{x}" y="{y + r + 15}" fill="#F1F5F9" font-size="12" font-weight="600" '
            f'text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, sans-serif">'
            f'{node}</text>'
        )

    svg.append("</svg></div>")
    return "".join(svg)


def render_skill_networks_and_strength(analytics_dir: Path):
    path_edges = analytics_dir / "skill_network_edges.csv"
    if path_edges.exists():
        df_edges = pd.read_csv(path_edges)
        if not df_edges.empty:
            st.subheader("Skill Relationship Network Graph")
            st.markdown(
                "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>"
                "Interactive visual network showing skills as nodes and co-occurrences as weighted edges."
                "</p>",
                unsafe_allow_html=True,
            )

            # Visual Network Graph rendering
            svg_network = _generate_network_svg(df_edges)
            if svg_network:
                st.markdown(svg_network, unsafe_allow_html=True)

            with st.expander("📋 View Network Edges Table", expanded=False):
                df_display = df_edges.head(30)
                headers = ["Source Skill", "Target Skill", "Weight"]
                rows = [
                    [str(r["source_skill"]), str(r["target_skill"]), str(r["weight"])]
                    for _, r in df_display.iterrows()
                ]
                st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

    path_rel = analytics_dir / "skill_relationships.csv"
    if path_rel.exists():
        df = pd.read_csv(path_rel)
        if not df.empty:
            st.subheader("Relationship Strength")
            st.markdown(
                "<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>"
                "Composite strength: Strength(A, B) = Jaccard(A, B) × max(0, PMI(A, B))."
                "</p>",
                unsafe_allow_html=True,
            )
            df_display = df.sort_values("relationship_strength", ascending=False).head(30)
            headers = ["Source Skill", "Target Skill", "Pair Count", "Jaccard", "PMI", "Rel. Strength"]
            rows = [
                [
                    str(r["skill_a"]),
                    str(r["skill_b"]),
                    str(r["pair_count"]),
                    f"{r['jaccard']:.4f}",
                    f"{r['pmi']:.4f}",
                    f"{r['relationship_strength']:.4f}",
                ]
                for _, r in df_display.iterrows()
            ]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)


def render_all_analytics(report: dict, mode: str, output_dir: Path):
    analytics_dir = output_dir / mode
    render_analysis_overview(report, analytics_dir)
    
    col1, col2 = st.columns(2)
    with col1:
        render_top_skills(analytics_dir)
    with col2:
        render_skill_pairs(analytics_dir)
        
    st.write("---")
    render_cooccurrence(analytics_dir)
    
    st.write("---")
    col3, col4 = st.columns(2)
    with col3:
        render_jaccard(analytics_dir)
    with col4:
        render_pmi(analytics_dir)
        
    st.write("---")
    render_association_rules(analytics_dir)
    
    st.write("---")
    render_technology_stacks(analytics_dir)
    
    st.write("---")
    render_skill_networks_and_strength(analytics_dir)
