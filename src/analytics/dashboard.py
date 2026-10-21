import pandas as pd
import streamlit as st
from pathlib import Path

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
            df_display = df.head(30)
            headers = ["Skill", "Frequency", "Percentage"]
            rows = []
            for _, row in df_display.iterrows():
                rows.append([
                    str(row.get('skill', '')), 
                    str(row.get('job_count', 0)), 
                    f"{row.get('frequency_pct', 0)}%"
                ])
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

def render_skill_pairs(analytics_dir: Path):
    path = analytics_dir / "skill_pairs.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not df.empty:
            st.subheader("Skill Pair Relationships")
            df_display = df.sort_values("pair_count", ascending=False).head(30)
            headers = ["Source Skill", "Target Skill", "Pair Count"]
            rows = [[str(r['skill_a']), str(r['skill_b']), str(r['pair_count'])] for _, r in df_display.iterrows()]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

def render_cooccurrence(analytics_dir: Path):
    path = analytics_dir / "cooccurrence_matrix.csv"
    if path.exists():
        df = pd.read_csv(path, index_col=0)
        if not df.empty:
            st.subheader("Skill Co-occurrence")
            st.markdown("<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>Matrix representing how often two skills occur within the same job advertisement.</p>", unsafe_allow_html=True)
            st.dataframe(df, height=350, use_container_width=True)

def render_jaccard(analytics_dir: Path):
    path = analytics_dir / "jaccard_similarity.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not df.empty:
            st.subheader("Jaccard Similarity")
            st.markdown("<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>Jaccard measures how much two skills overlap across job advertisements.</p>", unsafe_allow_html=True)
            df_display = df.sort_values("jaccard", ascending=False).head(30)
            headers = ["Skill A", "Skill B", "Score"]
            rows = [[str(r['skill_a']), str(r['skill_b']), f"{r['jaccard']:.4f}"] for _, r in df_display.iterrows()]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

def render_pmi(analytics_dir: Path):
    path = analytics_dir / "pmi_scores.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not df.empty:
            st.subheader("PMI")
            st.markdown("<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>PMI measures how strongly two skills occur together relative to what would be expected by chance.</p>", unsafe_allow_html=True)
            df_display = df.sort_values("pmi", ascending=False).head(30)
            headers = ["Skill A", "Skill B", "PMI"]
            rows = [[str(r['skill_a']), str(r['skill_b']), f"{r['pmi']:.4f}"] for _, r in df_display.iterrows()]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

def render_association_rules(analytics_dir: Path):
    path = analytics_dir / "association_rules.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not df.empty:
            st.subheader("Association Rules")
            st.markdown("<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>Identify directional relationships between skills using support, confidence, and lift.</p>", unsafe_allow_html=True)
            df_display = df.sort_values(["confidence", "lift"], ascending=[False, False]).head(30)
            headers = ["Antecedent", "Consequent", "Support", "Confidence", "Lift"]
            rows = [[str(r['antecedent']), str(r['consequent']), f"{r['support']:.4f}", f"{r['confidence']:.4f}", f"{r['lift']:.4f}"] for _, r in df_display.iterrows()]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

def render_technology_stacks(analytics_dir: Path):
    path = analytics_dir / "technology_stacks.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not df.empty:
            st.subheader("Technology Stacks")
            st.markdown("<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>Identify frequently occurring combinations of multiple technical skills.</p>", unsafe_allow_html=True)
            df_display = df.sort_values("job_count", ascending=False).head(30)
            headers = ["Technology Stack", "Stack Size", "Job Count", "Support"]
            rows = [[str(r['stack']).replace("'", "").replace("[", "").replace("]", ""), str(r['stack_size']), str(r['job_count']), f"{r['support']:.4f}"] for _, r in df_display.iterrows()]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

def render_skill_networks_and_strength(analytics_dir: Path):
    path_rel = analytics_dir / "skill_relationships.csv"
    if path_rel.exists():
        df = pd.read_csv(path_rel)
        if not df.empty:
            st.subheader("Relationship Strength")
            df_display = df.sort_values("relationship_strength", ascending=False).head(30)
            headers = ["Source Skill", "Target Skill", "Pair Count", "Jaccard", "PMI", "Rel. Strength"]
            rows = [[str(r['skill_a']), str(r['skill_b']), str(r['pair_count']), f"{r['jaccard']:.4f}", f"{r['pmi']:.4f}", f"{r['relationship_strength']:.4f}"] for _, r in df_display.iterrows()]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

    path_edges = analytics_dir / "skill_network_edges.csv"
    if path_edges.exists():
        df_edges = pd.read_csv(path_edges)
        if not df_edges.empty:
            st.subheader("Skill Network")
            st.markdown("<p style='color: #94A3B8; font-size: 13px; margin-top:-10px; margin-bottom:16px;'>Represents skills as nodes and their relationships as weighted edges.</p>", unsafe_allow_html=True)
            df_display = df_edges.head(30)
            headers = ["Source", "Target", "Weight"]
            rows = [[str(r['source_skill']), str(r['target_skill']), str(r['weight'])] for _, r in df_display.iterrows()]
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
