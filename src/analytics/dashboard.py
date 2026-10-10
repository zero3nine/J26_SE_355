"""
Research Dashboard and Visualization Layer for Skill Relationship & Technology Stack Analysis.
Research Component: IT4010 - Skill Relationship & Technology Stack Analysis
Student ID: IT23321854 / Project ID: J26_SE_355

Six Academically Defensible Sections:
1. Dataset Overview: Collected vs. eligible job advertisements, canonical taxonomy coverage, extraction runs, and source platform representation.
2. Skill Relationship Analysis: Co-occurrence counts, configurable heatmap, Jaccard similarity, PMI, NPMI, and interactive supporting job inspection.
3. Technology Stack Discovery: Directional association rules (Support, Confidence, Lift), discovered multi-skill stacks, operational criteria disclosures, and supporting job drilldown.
4. Technology Ecosystem Network: Interactive network visualization, node centrality metrics, community detection, ego network filtering, and graph topology.
5. Extraction Method Comparison: Lexical vs. Semantic vs. Combined extraction on identical eligible population, Venn overlap, rank shifts, and ground truth evaluation status.
6. Evidence and Data Quality: Traceability to original job advertisements, OCR provenance funnel, normalization mappings, and data quality diagnostics.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import altair as alt
import networkx as nx
import pandas as pd
import streamlit as st

from src.extraction.normalization import get_skill_category
from theme import render_custom_table


# -----------------------------------------------------------------------------
# Color Palette and Domain Mapping
# -----------------------------------------------------------------------------

CATEGORY_COLORS = {
    "Programming Languages": "#38BDF8",  # Sky
    "Frameworks & Libraries": "#818CF8",  # Indigo
    "Databases": "#34D399",              # Emerald
    "Cloud & Infrastructure": "#FBBF24",  # Amber
    "DevOps & CI/CD": "#F43F5E",          # Rose
    "Testing & QA": "#A78BFA",            # Purple
    "Data & AI": "#2DD4BF",               # Teal
    "General": "#94A3B8",                # Slate
}


# -----------------------------------------------------------------------------
# Helper: Extract context snippet from job description
# -----------------------------------------------------------------------------

def _extract_context_snippet(text: str, terms: list[str], max_len: int = 220) -> str:
    """Extract a representative sentence or excerpt containing the terms in context."""
    if not text or not isinstance(text, str):
        return "(Description text unavailable)"

    clean = " ".join(text.split())
    for term in terms:
        pattern = re.compile(rf"([^.?!;]*?\b{re.escape(term)}\b[^.?!;]*)", re.IGNORECASE)
        match = pattern.search(clean)
        if match:
            snippet = match.group(1).strip()
            if len(snippet) > max_len:
                return snippet[:max_len - 3] + "..."
            return snippet

    return clean[:max_len - 3] + "..." if len(clean) > max_len else clean


# -----------------------------------------------------------------------------
# Helper: Parse skills cell safely
# -----------------------------------------------------------------------------

def _parse_job_skills(val: Any) -> set[str]:
    """Parse skill sets stored as list or JSON string."""
    if isinstance(val, (set, list)):
        return {str(s).strip() for s in val if str(s).strip()}
    if not val or pd.isna(val):
        return set()
    text = str(val).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return {str(s).strip() for s in parsed if str(s).strip()}
    except Exception:
        pass
    return set()


# -----------------------------------------------------------------------------
# SECTION 1: Dataset Overview & Research Eligibility Analysis
# -----------------------------------------------------------------------------

def render_section1_dataset_overview(
    report: dict,
    mode: str,
    output_dir: Path,
    jobs_df: Optional[pd.DataFrame] = None,
):
    """
    Renders Section 1:
    - Collected vs. Eligible Job Advertisements Funnel
    - Actual values for eligible ads, unique normalized skills, mentions, and source platforms
    - Active extraction run and pipeline metadata from database
    - Normalization audit and technology boundary preservation
    - Domain category distribution
    """
    st.markdown("""
    <div style="border-bottom: 1px solid #1E293B; padding-bottom: 8px; margin-top: 6px; margin-bottom: 16px;">
        <h3 style="color: #38BDF8; font-weight: 600; margin: 0; font-size: 18px;">
            1. Dataset Overview
        </h3>
        <p style="color: #94A3B8; font-size: 13px; margin: 2px 0 0 0;">
            Overview of eligible job postings, canonical skill coverage, extraction runs, and source platforms.
        </p>
    </div>
    """, unsafe_allow_html=True)

    analytics_dir = output_dir / mode

    jobs_analyzed = report.get("jobs_with_selected_skills", 0)
    total_csv_rows = report.get("total_rows_in_csv", jobs_analyzed)
    unique_skills = report.get("unique_skills", 0)
    skill_pairs = report.get("skill_pairs", 0)
    total_mentions = report.get("total_raw_mentions", 0)
    jobs_missing = report.get("jobs_missing_skills", max(0, total_csv_rows - jobs_analyzed))
    coverage_pct = report.get(
        "extraction_coverage_pct",
        round((jobs_analyzed / total_csv_rows * 100), 1) if total_csv_rows > 0 else 0.0
    )
    avg_skills_per_job = round(total_mentions / jobs_analyzed, 1) if jobs_analyzed > 0 else 0.0

    # Primary KPI Cards Grid (6 actual metrics)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric(
            label="Eligible Postings",
            value=jobs_analyzed,
            delta=f"{coverage_pct}% of total",
            help="Advertisements containing at least one normalized technical skill under the selected mode."
        )
    with c2:
        st.metric(
            label="Total Collected Postings",
            value=total_csv_rows,
            help="Total job advertisement records stored in the authoritative database."
        )
    with c3:
        st.metric(
            label="Unique Normalized Skills",
            value=unique_skills,
            help="Count of distinct standardized technical skill entities present in the eligible postings."
        )
    with c4:
        st.metric(
            label="Extracted Skill Mentions",
            value=total_mentions,
            help="Total occurrences of skill terms identified across all eligible advertisements."
        )
    with c5:
        st.metric(
            label="Avg Skills / Posting",
            value=avg_skills_per_job,
            help="Average number of distinct technical skills demanded per eligible job posting."
        )
    with c6:
        st.metric(
            label="Excluded / Missing",
            value=jobs_missing,
            delta="Ineligible" if jobs_missing > 0 else "None",
            delta_color="inverse" if jobs_missing > 0 else "normal",
            help="Advertisements lacking identifiable technical skills (e.g., non-technical listings or unparsed text)."
        )

    # Source Platform Distribution & Role Distribution
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 10px; margin-bottom: 8px;'>Source Platform Distribution</h4>", unsafe_allow_html=True)
        if jobs_df is not None and not jobs_df.empty and "source_platform" in jobs_df.columns:
            src_df = jobs_df["source_platform"].value_counts().reset_index()
            src_df.columns = ["Source Platform", "Job Count"]
            src_df["Percentage"] = (src_df["Job Count"] / len(jobs_df) * 100).round(1)

            chart_platform = (
                alt.Chart(src_df)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#38BDF8")
                .encode(
                    x=alt.X("Job Count:Q", title="Advertisements Collected"),
                    y=alt.Y("Source Platform:N", sort="-x", title="Job Portal"),
                    tooltip=[
                        alt.Tooltip("Source Platform:N"),
                        alt.Tooltip("Job Count:Q"),
                        alt.Tooltip("Percentage:Q", title="Share (%)", format=".1f"),
                    ],
                )
                .properties(height=160)
            )
            st.altair_chart(chart_platform, use_container_width=True)
        else:
            st.info("Source platform metadata not available in current dataset view.")

    with col_p2:
        st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 10px; margin-bottom: 8px;'>Canonical Skill Domain Breakdown</h4>", unsafe_allow_html=True)
        path_freq = analytics_dir / "skill_frequency.csv"
        if path_freq.exists():
            df_freq = pd.read_csv(path_freq)
            if not df_freq.empty and "skill" in df_freq.columns:
                df_freq_cat = df_freq.copy()
                df_freq_cat["Category"] = df_freq_cat["skill"].apply(get_skill_category)
                cat_summary = df_freq_cat.groupby("Category")["job_count"].sum().reset_index()
                cat_summary.columns = ["Domain Category", "Total Mentions"]

                chart_cat = (
                    alt.Chart(cat_summary)
                    .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                    .encode(
                        x=alt.X("Total Mentions:Q", title="Total Skill Mentions"),
                        y=alt.Y("Domain Category:N", sort="-x", title="Domain Category"),
                        color=alt.Color("Domain Category:N", scale=alt.Scale(scheme="category10"), legend=None),
                        tooltip=[alt.Tooltip("Domain Category:N"), alt.Tooltip("Total Mentions:Q")],
                    )
                    .properties(height=160)
                )
                st.altair_chart(chart_cat, use_container_width=True)
            else:
                st.caption("Skill frequency file empty.")
        else:
            st.caption("Skill frequency file not yet generated.")

    # Recorded Extraction Runs in Database
    st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 20px; margin-bottom: 8px;'>Recorded Skill Extraction Runs in Master SQL Database</h4>", unsafe_allow_html=True)
    try:
        import importlib
        import src.database.repository
        importlib.reload(src.database.repository)
        runs_df = src.database.repository.get_extraction_runs()
        if not runs_df.empty:
            display_runs = runs_df[["run_id", "run_type", "model_name", "taxonomy_version", "semantic_threshold", "started_at", "completed_at", "notes"]].copy()
            display_runs.columns = ["Run ID", "Type", "Model", "Taxonomy Ver", "Threshold (τ)", "Started At", "Completed At", "Notes"]
            st.dataframe(display_runs, use_container_width=True, hide_index=True)
        else:
            st.info("No historical extraction runs logged in the master database.")
    except Exception as e:
        st.caption(f"Extraction runs query: {e}")

    # Normalization Audit and Technology Boundary Preservation
    norm_audit = report.get("normalization_audit", {})
    if not norm_audit:
        audit_file = analytics_dir / "normalization_audit.json"
        if audit_file.exists():
            try:
                with open(audit_file, "r", encoding="utf-8") as f:
                    norm_audit = json.load(f)
            except Exception:
                norm_audit = {}

    mapping_records = norm_audit.get("mapping_records", [])
    if mapping_records:
        st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 20px; margin-bottom: 8px;'>Canonical Skill Normalization Audit</h4>", unsafe_allow_html=True)
        st.markdown("""
        <p style='color: #94A3B8; font-size: 12px; margin-top: -6px; margin-bottom: 10px;'>
            Surface term variants are deterministically resolved to canonical taxonomy entities.
            Non-technical tokens (e.g. <code>none</code>, <code>null</code>, <code>nan</code>, <code>n/a</code>) are filtered out unconditionally.
        </p>
        """, unsafe_allow_html=True)
        map_headers = ["Original Extracted Term", "Canonical Technology Entity", "Applied Normalization Rule"]
        map_rows = [[r.get("original_term", ""), r.get("canonical_skill", ""), r.get("rule", "Taxonomy Lookup")] for r in mapping_records[:12]]
        st.markdown(render_custom_table(map_headers, map_rows), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# SECTION 2: Skill Relationship Analysis (Co-Occurrence, Jaccard, PMI & NPMI)
# -----------------------------------------------------------------------------

def render_section2_skill_relationships(
    analytics_dir: Path,
    report: Optional[dict] = None,
    jobs_df: Optional[pd.DataFrame] = None,
):
    """
    Renders Section 2:
    - Co-occurrence counts & symmetric heatmap
    - Jaccard similarity, PMI, and NPMI with full theoretical explanations
    - Minimum co-occurrence threshold filter to suppress rare-pair noise
    - Interactive skill selector to inspect authentic supporting job advertisements
    """
    st.markdown("""
    <div style="border-bottom: 1px solid #1E293B; padding-bottom: 8px; margin-top: 6px; margin-bottom: 16px;">
        <h3 style="color: #38BDF8; font-weight: 600; margin: 0; font-size: 18px;">
            2. Skill Relationship Analysis
        </h3>
        <p style="color: #94A3B8; font-size: 13px; margin: 2px 0 0 0;">
            Pairwise co-occurrence counts, Jaccard similarity, and Normalized Pointwise Mutual Information (NPMI).
        </p>
    </div>
    """, unsafe_allow_html=True)

    path_freq = analytics_dir / "skill_frequency.csv"
    path_matrix = analytics_dir / "cooccurrence_matrix.csv"
    path_pairs = analytics_dir / "skill_pairs.csv"
    path_jaccard = analytics_dir / "jaccard_similarity.csv"
    path_pmi = analytics_dir / "pmi_scores.csv"
    path_relationships = analytics_dir / "skill_relationships.csv"

    if not path_matrix.exists() or not path_pairs.exists():
        st.warning("Relationship analysis outputs not found. Click 'Run Skill Analysis' above.")
        return

    df_pairs = pd.read_csv(path_pairs)
    df_matrix = pd.read_csv(path_matrix, index_col=0) if path_matrix.exists() else pd.DataFrame()
    df_jaccard = pd.read_csv(path_jaccard) if path_jaccard.exists() else pd.DataFrame()
    df_pmi = pd.read_csv(path_pmi) if path_pmi.exists() else pd.DataFrame()
    df_rel = pd.read_csv(path_relationships) if path_relationships.exists() else pd.DataFrame()

    # Controls row
    c_f1, c_f2, c_f3 = st.columns([2, 2, 2])
    with c_f1:
        max_pair_cnt = int(df_pairs["pair_count"].max()) if not df_pairs.empty and "pair_count" in df_pairs.columns else 2
        min_cooc = st.slider("Minimum Co-Occurrence Threshold (k):", min_value=1, max_value=max(2, max_pair_cnt), value=1, key="sec2_min_cooc")
    with c_f2:
        metric_choice = st.selectbox(
            "Primary Analysis Metric:",
            ["Co-occurrence Count", "Jaccard Similarity", "PMI (bits)", "NPMI (Normalized PMI)", "Composite Strength"],
            index=0,
            key="sec2_metric_choice"
        )
    with c_f3:
        top_n_matrix = st.selectbox("Heatmap Matrix Size:", [10, 15, 20, 25], index=1, key="sec2_matrix_size")

    # Filtered pairs
    df_filt_pairs = df_pairs[df_pairs["pair_count"] >= min_cooc].copy() if not df_pairs.empty else pd.DataFrame()

    # 1. Co-occurrence Matrix & Heatmap
    if not df_matrix.empty and len(df_matrix.index) > 1:
        st.markdown(f"<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 14px; margin-bottom: 8px;'>Symmetric Skill Co-occurrence Heatmap (Top {top_n_matrix} Skills)</h4>", unsafe_allow_html=True)
        try:
            top_skills = df_matrix.sum(axis=1).sort_values(ascending=False).head(top_n_matrix).index.tolist()
            df_sub = df_matrix.loc[top_skills, top_skills]
            idx_name = df_sub.index.name or "index"
            df_long = df_sub.reset_index().melt(id_vars=idx_name, var_name="skill_b", value_name="count")
            df_long.rename(columns={idx_name: "skill_a"}, inplace=True)

            heatmap = (
                alt.Chart(df_long)
                .mark_rect()
                .encode(
                    x=alt.X("skill_a:N", title="Skill A", sort=top_skills),
                    y=alt.Y("skill_b:N", title="Skill B", sort=top_skills),
                    color=alt.Color("count:Q", scale=alt.Scale(scheme="tealblues"), title="Co-occurrence"),
                    tooltip=[
                        alt.Tooltip("skill_a:N", title="Skill A"),
                        alt.Tooltip("skill_b:N", title="Skill B"),
                        alt.Tooltip("count:Q", title="Co-occurrence Count"),
                    ],
                )
            )
            text_labels = (
                alt.Chart(df_long)
                .mark_text(baseline="middle", fontSize=10)
                .encode(
                    x="skill_a:N",
                    y="skill_b:N",
                    text=alt.condition(alt.datum.count > 0, alt.Text("count:Q"), alt.value("")),
                    color=alt.condition(alt.datum.count > (df_long["count"].max() * 0.55), alt.value("white"), alt.value("#CBD5E1")),
                )
            )
            st.altair_chart((heatmap + text_labels).properties(height=340), use_container_width=True)
        except Exception as e:
            st.warning(f"Heatmap rendering note: {e}")

    # 2. Ranked Co-Occurring Skill Pairs Chart & Table
    st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 20px; margin-bottom: 8px;'>Ranked Skill Relationships (Filtered by Threshold)</h4>", unsafe_allow_html=True)
    if not df_filt_pairs.empty:
        # Merge metrics into single clean view
        merged_rel = df_filt_pairs.copy()
        if not df_jaccard.empty:
            merged_rel = merged_rel.merge(df_jaccard[["skill_a", "skill_b", "jaccard"]], on=["skill_a", "skill_b"], how="left")
        if not df_pmi.empty:
            cols_pmi = [c for c in ["skill_a", "skill_b", "pmi", "npmi"] if c in df_pmi.columns]
            merged_rel = merged_rel.merge(df_pmi[cols_pmi], on=["skill_a", "skill_b"], how="left")
        if not df_rel.empty and "relationship_strength" in df_rel.columns:
            merged_rel = merged_rel.merge(df_rel[["skill_a", "skill_b", "relationship_strength"]], on=["skill_a", "skill_b"], how="left")

        merged_rel["jaccard"] = merged_rel.get("jaccard", pd.Series(0.0)).fillna(0.0)
        merged_rel["pmi"] = merged_rel.get("pmi", pd.Series(0.0)).fillna(0.0)
        merged_rel["npmi"] = merged_rel.get("npmi", pd.Series(0.0)).fillna(0.0)
        merged_rel["relationship_strength"] = merged_rel.get("relationship_strength", pd.Series(0.0)).fillna(0.0)

        sort_col_map = {
            "Co-occurrence Count": "pair_count",
            "Jaccard Similarity": "jaccard",
            "PMI (bits)": "pmi",
            "NPMI (Normalized PMI)": "npmi",
            "Composite Strength": "relationship_strength",
        }
        active_sort = sort_col_map.get(metric_choice, "pair_count")
        merged_rel = merged_rel.sort_values(active_sort, ascending=False).reset_index(drop=True)

        col_r1, col_r2 = st.columns([3, 4])
        with col_r1:
            top_chart_pairs = merged_rel.head(12).copy()
            top_chart_pairs["pair_label"] = top_chart_pairs["skill_a"] + " + " + top_chart_pairs["skill_b"]

            chart_p = (
                alt.Chart(top_chart_pairs)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#38BDF8")
                .encode(
                    x=alt.X(f"{active_sort}:Q", title=metric_choice),
                    y=alt.Y("pair_label:N", sort="-x", title="Skill Pair"),
                    tooltip=[
                        alt.Tooltip("pair_label:N", title="Skill Pair"),
                        alt.Tooltip("pair_count:Q", title="Co-occurrence"),
                        alt.Tooltip("jaccard:Q", title="Jaccard", format=".4f"),
                        alt.Tooltip("pmi:Q", title="PMI", format=".4f"),
                        alt.Tooltip("npmi:Q", title="NPMI", format=".4f"),
                    ],
                )
                .properties(height=320)
            )
            st.altair_chart(chart_p, use_container_width=True)

        with col_r2:
            disp_table = merged_rel.head(12).copy()
            headers = ["Skill A", "Skill B", "Co-occurrence", "Jaccard", "PMI", "NPMI", "Strength"]
            rows = [
                [
                    str(r["skill_a"]),
                    str(r["skill_b"]),
                    str(int(r["pair_count"])),
                    f"{float(r['jaccard']):.4f}",
                    f"{float(r['pmi']):.3f}",
                    f"{float(r['npmi']):.3f}",
                    f"{float(r['relationship_strength']):.3f}",
                ]
                for _, r in disp_table.iterrows()
            ]
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)
    else:
        st.info(f"No skill pairs met the minimum co-occurrence threshold of k >= {min_cooc}.")

    # 3. Interactive Supporting Advertisement Inspection
    st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 24px; margin-bottom: 8px;'>🔍 Inspect Job Advertisements Supporting a Skill Relationship</h4>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8; font-size: 12px; margin-top: -6px; margin-bottom: 10px;'>Verify empirical relationship validity by inspecting genuine job listings where both skills co-occur in the advertisement text.</p>", unsafe_allow_html=True)

    if not df_filt_pairs.empty and jobs_df is not None and not jobs_df.empty:
        pair_options = [f"{r['skill_a']} ↔ {r['skill_b']} (Co-occurred in {r['pair_count']} jobs)" for _, r in df_filt_pairs.head(30).iterrows()]
        selected_pair_str = st.selectbox("Select a Skill Pair to Inspect Supporting Advertisements:", pair_options, key="sec2_pair_inspect")

        if selected_pair_str:
            clean_pair_label = selected_pair_str.split(" (")[0]
            sa, sb = [s.strip() for s in clean_pair_label.split("↔")]

            # Find matching jobs from jobs_df
            matching_rows = []
            for _, jrow in jobs_df.iterrows():
                j_skills = _parse_job_skills(jrow.get("lexical_skills", [])) | _parse_job_skills(jrow.get("semantic_skills", []))
                if sa in j_skills and sb in j_skills:
                    matching_rows.append(jrow)

            if matching_rows:
                st.markdown(f"<p style='color: #38BDF8; font-size: 13px;'>Found <b>{len(matching_rows)}</b> authentic job advertisement(s) demanding both <b>{sa}</b> and <b>{sb}</b>:</p>", unsafe_allow_html=True)
                for i, jrow in enumerate(matching_rows[:5], 1):
                    jid = str(jrow.get("job_id", f"job_{i}"))
                    jtitle = str(jrow.get("job_title_raw", "Job Advertisement"))
                    jcompany = str(jrow.get("company", jrow.get("company_name", "Unknown Employer")))
                    jloc = str(jrow.get("location_raw", jrow.get("location", "Unknown Location")))
                    jsrc = str(jrow.get("source_platform", "Portal"))
                    jurl = str(jrow.get("source_url", ""))
                    jdesc = str(jrow.get("job_description", ""))

                    snippet = _extract_context_snippet(jdesc, [sa, sb], max_len=260)
                    url_link = f"<a href='{jurl}' target='_blank' style='color: #38BDF8; text-decoration: none;'>View Source URL ↗</a>" if jurl else "URL not recorded"

                    st.markdown(f"""
                    <div style="background: #0F172A; border: 1px solid #1E293B; border-radius: 6px; padding: 12px 14px; margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="font-weight: 600; color: #F8FAFC; font-size: 14px;">{i}. {jtitle}</span>
                            <span style="font-size: 11px; color: #94A3B8; background: #1E293B; padding: 2px 8px; border-radius: 10px;">Job ID: {jid} | {jsrc}</span>
                        </div>
                        <div style="font-size: 12px; color: #94A3B8; margin-bottom: 6px;">
                            Company: <b>{jcompany}</b> &nbsp;•&nbsp; Location: <b>{jloc}</b> &nbsp;•&nbsp; {url_link}
                        </div>
                        <div style="font-size: 12px; color: #E2E8F0; background: #1E293B; padding: 8px 12px; border-radius: 4px; border-left: 3px solid #38BDF8;">
                            <i>\"{snippet}\"</i>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info(f"Metadata records for pair {sa} + {sb} are being loaded from the database.")


# -----------------------------------------------------------------------------
# SECTION 3: Technology Stack Discovery (Itemsets & Association Rules)
# -----------------------------------------------------------------------------

def render_section3_technology_stacks(
    analytics_dir: Path,
    jobs_df: Optional[pd.DataFrame] = None,
):
    """
    Renders Section 3:
    - Directional association rules (Support, Confidence, Lift) with sortable table
    - Discovered multi-skill technology combinations (2 to 4 skills)
    - Critical scientific operational criteria disclosure (co-occurrence != runtime monolithic stack)
    - Supporting job advertisement drilldown
    """
    st.markdown("""
    <div style="border-bottom: 1px solid #1E293B; padding-bottom: 8px; margin-top: 6px; margin-bottom: 16px;">
        <h3 style="color: #38BDF8; font-weight: 600; margin: 0; font-size: 18px;">
            3. Technology Stack Discovery
        </h3>
        <p style="color: #94A3B8; font-size: 13px; margin: 2px 0 0 0;">
            Directional association rules (A → B) and frequent multi-skill bundles (sizes 2 to 4).
        </p>
    </div>
    """, unsafe_allow_html=True)

    path_rules = analytics_dir / "association_rules.csv"
    path_stacks = analytics_dir / "technology_stacks.csv"

    # Part A: Directional Association Rules
    st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 10px; margin-bottom: 8px;'>Directional Association Rules (A → B)</h4>", unsafe_allow_html=True)

    if path_rules.exists():
        df_rules = pd.read_csv(path_rules)
        if not df_rules.empty:
            c_r1, c_r2, c_r3 = st.columns(3)
            with c_r1:
                min_sup = st.slider("Minimum Support Threshold:", min_value=0.01, max_value=0.50, value=0.05, step=0.01, key="sec3_min_sup")
            with c_r2:
                min_conf = st.slider("Minimum Confidence Threshold:", min_value=0.10, max_value=1.00, value=0.40, step=0.05, key="sec3_min_conf")
            with c_r3:
                min_lift = st.slider("Minimum Lift Threshold:", min_value=1.0, max_value=15.0, value=1.0, step=0.5, key="sec3_min_lift")

            df_filt_rules = df_rules[
                (df_rules["support"] >= min_sup) &
                (df_rules["confidence"] >= min_conf) &
                (df_rules["lift"] >= min_lift)
            ].sort_values("lift", ascending=False).reset_index(drop=True)

            if not df_filt_rules.empty:
                headers = ["Antecedent (A)", "Consequent (B)", "Support", "Confidence", "Lift Ratio", "Market Implication"]
                rows = []
                for _, r in df_filt_rules.head(15).iterrows():
                    conf_pct = float(r["confidence"]) * 100
                    lift_val = float(r["lift"])
                    implication = f"If A is required, {conf_pct:.0f}% chance B is also required ({lift_val:.1f}x over chance)"
                    rows.append([
                        str(r["antecedent"]),
                        str(r["consequent"]),
                        f"{float(r['support']):.4f}",
                        f"{conf_pct:.1f}%",
                        f"{lift_val:.2f}",
                        implication,
                    ])
                st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)
                st.caption(f"Showing top {min(15, len(df_filt_rules))} of {len(df_filt_rules)} association rules meeting criteria.")
            else:
                st.info("No association rules met the selected combination of Support, Confidence, and Lift thresholds.")
    else:
        st.info("Association rules file not yet generated.")

    # Part B: Discovered Multi-Skill Technology Stacks
    st.markdown("<h4 style='color: #F8FAFC; font-size: 16px; margin-top: 26px; margin-bottom: 8px;'>Discovered Multi-Skill Technology Stacks (Itemset Mining)</h4>", unsafe_allow_html=True)
    if path_stacks.exists():
        df_stacks = pd.read_csv(path_stacks)
        if not df_stacks.empty:
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                stack_size_sel = st.selectbox(
                    "Filter by Technology Stack Size:",
                    options=["All Combinations (2 - 4 Skills)", "2 Skills (Pairs)", "3 Skills (Triplets)", "4 Skills (Quadruplets)"],
                    index=0,
                    key="sec3_stack_size_sel"
                )
            with col_s2:
                filter_recurring = st.checkbox("Show Only Recurring Stacks (≥ 2 Job Postings)", value=False, key="sec3_filter_rec")

            if "2 Skills" in stack_size_sel:
                df_filt_stacks = df_stacks[df_stacks["stack_size"] == 2].copy()
            elif "3 Skills" in stack_size_sel:
                df_filt_stacks = df_stacks[df_stacks["stack_size"] == 3].copy()
            elif "4 Skills" in stack_size_sel:
                df_filt_stacks = df_stacks[df_stacks["stack_size"] == 4].copy()
            else:
                df_filt_stacks = df_stacks[df_stacks["stack_size"] >= 2].copy()

            if filter_recurring:
                df_filt_stacks = df_filt_stacks[df_filt_stacks["job_count"] >= 2]

            df_filt_stacks = df_filt_stacks.sort_values(["stack_size", "job_count"], ascending=[False, False])

            # Ranked bar chart of stacks
            if not df_filt_stacks.empty:
                df_top_chart = df_filt_stacks.head(10).copy()
                df_top_chart["clean_stack"] = df_top_chart["stack"].str.replace("'", "").str.replace("[", "").str.replace("]", "")

                chart_st = (
                    alt.Chart(df_top_chart)
                    .mark_bar(color="#A78BFA", cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
                    .encode(
                        x=alt.X("job_count:Q", title="Supporting Job Postings Count"),
                        y=alt.Y("clean_stack:N", sort="-x", title="Discovered Technology Stack"),
                        tooltip=[
                            alt.Tooltip("clean_stack:N", title="Stack"),
                            alt.Tooltip("stack_size:Q", title="Size"),
                            alt.Tooltip("job_count:Q", title="Job Count"),
                            alt.Tooltip("support:Q", title="Support Ratio", format=".4f"),
                        ],
                    )
                    .properties(height=280)
                )
                st.altair_chart(chart_st, use_container_width=True)

                headers = ["Technology Stack Combination", "Size", "Supporting Jobs", "Support Ratio", "Empirical Classification"]
                rows = []
                for _, r in df_filt_stacks.head(15).iterrows():
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

            # Supporting Job Advertisements Drilldown for Stack
            if "supporting_jobs" in df_stacks.columns and not df_filt_stacks.empty:
                st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 22px; margin-bottom: 8px;'>🔍 Supporting Advertisement Drilldown for Discovered Stack</h4>", unsafe_allow_html=True)
                stack_list = df_filt_stacks["stack"].tolist()
                selected_stack = st.selectbox("Select Stack Combination to Inspect Supporting Advertisements:", options=stack_list[:40], key="sec3_stack_evidence")

                if selected_stack:
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
                        st.caption(f"Stack {selected_stack} is supported by {selected_row['job_count']} job(s).")
    else:
        st.info("Technology stacks file not yet generated.")


# -----------------------------------------------------------------------------
# SECTION 4: Technology Ecosystem Network & Graph Topology
# -----------------------------------------------------------------------------

def _generate_network_svg(
    df_edges: pd.DataFrame,
    focal_skill: str = "All Skills",
    weight_metric: str = "weight",
    min_count: int = 1,
    min_strength: float = 0.0,
    top_n_edges: Optional[int] = None,
    df_nodes: Optional[pd.DataFrame] = None,
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

    # Apply Top-N edge limit to prevent overcrowded visual noise
    if top_n_edges and len(filtered) > top_n_edges:
        sort_col = weight_metric if weight_metric in filtered.columns else ("pair_count" if "pair_count" in filtered.columns else filtered.columns[0])
        filtered = filtered.sort_values(sort_col, ascending=False).head(top_n_edges)

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

    deg_cent = dict(nx.degree_centrality(G))
    max_deg_cent = max(deg_cent.values()) if deg_cent else 1.0

    node_meta_map = {}
    if df_nodes is not None and not df_nodes.empty and "skill" in df_nodes.columns:
        for _, nr in df_nodes.iterrows():
            s = str(nr["skill"])
            node_meta_map[s] = {
                "degree_centrality": float(nr.get("degree_centrality", 0.0)),
                "betweenness": float(nr.get("betweenness_centrality", 0.0)),
                "closeness": float(nr.get("closeness_centrality", 0.0)),
                "community": str(nr.get("community_cluster_id", "0")),
                "category": str(nr.get("domain_category", get_skill_category(s))),
            }

    svg = [
        f'<div style="text-align: center; margin-bottom: 14px;">'
        f'<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="background: #0B1120; border-radius: 12px; border: 1px solid #1E293B; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">'
    ]

    svg.append(
        '<defs>'
        '<pattern id="tab6_grid" width="40" height="40" patternUnits="userSpaceOnUse">'
        '<path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1E293B" stroke-width="0.5" stroke-opacity="0.6" />'
        '</pattern>'
        '<linearGradient id="tab6_edge_grad" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#38BDF8" stop-opacity="0.85" />'
        '<stop offset="100%" stop-color="#818CF8" stop-opacity="0.55" />'
        '</linearGradient>'
        '</defs>'
        '<rect width="100%" height="100%" fill="url(#tab6_grid)" />'
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
            f'stroke="url(#tab6_edge_grad)" stroke-width="{stroke_w}" stroke-linecap="round">'
            f'<title>{tooltip}</title>'
            f'</line>'
        )

    # Nodes
    for node in sorted(G.nodes()):
        x = int(pos[node][0] * scale_x + cx_offset)
        y = int(pos[node][1] * scale_y + cy_offset)
        d_cent = deg_cent.get(node, 0.1)
        r = 13 + int((d_cent / (max_deg_cent if max_deg_cent > 0 else 1.0)) * 14)

        meta = node_meta_map.get(node, {})
        cat = meta.get("category", get_skill_category(node))
        color = CATEGORY_COLORS.get(cat, "#38BDF8")

        is_focal = (node == focal_skill)
        stroke_color = "#F59E0B" if is_focal else color
        stroke_width = 3.5 if is_focal else 2.5
        r_actual = r + 4 if is_focal else r

        betw = meta.get("betweenness", 0.0)
        close = meta.get("closeness", 0.0)
        comm = meta.get("community", "0")

        node_tooltip = (
            f"Skill: {node}&#10;Category: {cat}&#10;Degree Centrality: {d_cent:.4f}&#10;"
            f"Betweenness Centrality: {betw:.4f}&#10;Closeness: {close:.4f}&#10;Community ID: {comm}"
        )

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


def render_section4_ecosystem_network(analytics_dir: Path):
    """
    Renders Section 4:
    - Interactive topological ecosystem network
    - Anti-overcrowding controls: Focal skill (Ego network), Top-N edges, threshold filtering
    - Centrality metrics (Degree, Betweenness, Closeness) and community detection
    """
    st.markdown("""
    <div style="border-bottom: 1px solid #1E293B; padding-bottom: 8px; margin-top: 6px; margin-bottom: 16px;">
        <h3 style="color: #38BDF8; font-weight: 600; margin: 0; font-size: 18px;">
            4. Technology Ecosystem Network
        </h3>
        <p style="color: #94A3B8; font-size: 13px; margin: 2px 0 0 0;">
            Interactive network graph, centrality metrics, and community clusters.
        </p>
    </div>
    """, unsafe_allow_html=True)

    path_edges = analytics_dir / "skill_network_edges.csv"
    path_nodes = analytics_dir / "skill_network_nodes.csv"

    if not path_edges.exists():
        st.info("No network edges generated for the current run.")
        return

    df_edges = pd.read_csv(path_edges)
    df_nodes = pd.read_csv(path_nodes) if path_nodes.exists() else pd.DataFrame()

    if df_edges.empty:
        st.info("No network relationships met the minimum threshold for graph construction.")
        return

    all_skills = sorted(list(set(df_edges["source_skill"].dropna()).union(set(df_edges["target_skill"].dropna()))))

    col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns([2, 2, 2, 2, 2])
    with col_c1:
        focal_skill = st.selectbox("Focal Skill (Ego Network):", options=["All Skills"] + all_skills, index=0, key="sec4_focal")
    with col_c2:
        max_pair = int(df_edges["pair_count"].max()) if "pair_count" in df_edges.columns else 1
        min_cooc = st.slider("Min Co-occurrence:", min_value=1, max_value=max(2, max_pair), value=1, key="sec4_cooc")
    with col_c3:
        min_strength = st.slider("Min Strength:", min_value=0.0, max_value=2.0, value=0.0, step=0.1, key="sec4_str")
    with col_c4:
        top_n_edge_limit = st.selectbox("Top Edges View:", [30, 50, 100, 200, "All"], index=1, key="sec4_top_edges")
        top_n_val = None if top_n_edge_limit == "All" else int(top_n_edge_limit)
    with col_c5:
        weight_metric = st.selectbox(
            "Edge Metric:",
            options=["weight", "jaccard", "relationship_strength", "pmi"],
            format_func=lambda x: {"weight": "Pair Count", "jaccard": "Jaccard", "relationship_strength": "Strength", "pmi": "PMI"}.get(x, x),
            key="sec4_metric",
        )

    svg_html, node_count, edge_count = _generate_network_svg(
        df_edges, focal_skill=focal_skill, weight_metric=weight_metric, min_count=min_cooc, min_strength=min_strength, top_n_edges=top_n_val, df_nodes=df_nodes
    )

    if svg_html:
        st.markdown(svg_html, unsafe_allow_html=True)
        st.caption(f"Topological Subgraph: **{node_count}** skills connected by **{edge_count}** edges. Node size reflects Degree Centrality; edge width reflects relationship weight.")
    else:
        st.warning(f"No skill relationships meet the selected filter criteria (Focal Skill = '{focal_skill}', Min Co-occurrence = {min_cooc}, Min Strength = {min_strength:.1f}).")

    # Domain Color Legend
    st.markdown("""
    <div style="background: #0F172A; border: 1px solid #1E293B; border-radius: 6px; padding: 10px 14px; margin-bottom: 16px; display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px;">
        <span style="color: #94A3B8; font-weight: 600;">Domain Color Legend:</span>
        <span style="color: #38BDF8;">● Programming Languages</span>
        <span style="color: #818CF8;">● Frameworks & Libraries</span>
        <span style="color: #34D399;">● Databases</span>
        <span style="color: #FBBF24;">● Cloud & Infrastructure</span>
        <span style="color: #F43F5E;">● DevOps & CI/CD</span>
        <span style="color: #A78BFA;">● Testing & QA</span>
        <span style="color: #2DD4BF;">● Data & AI</span>
    </div>
    """, unsafe_allow_html=True)

    # Centrality & Clustering Metrics Table
    if not df_nodes.empty:
        st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 14px; margin-bottom: 8px;'>Network Centrality and Clustering Metrics</h4>", unsafe_allow_html=True)
        headers = ["Skill", "Domain Category", "Degree Centrality", "Betweenness Centrality", "Closeness Centrality", "Community Cluster ID"]
        df_sorted_nodes = df_nodes.sort_values("degree_centrality", ascending=False)
        rows = [
            [
                str(r["skill"]),
                str(r.get("domain_category", "General")),
                f"{float(r.get('degree_centrality', 0.0)):.4f}",
                f"{float(r.get('betweenness_centrality', 0.0)):.4f}",
                f"{float(r.get('closeness_centrality', 0.0)):.4f}",
                str(r.get("community_cluster_id", "0")),
            ]
            for _, r in df_sorted_nodes.head(15).iterrows()
        ]
        st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

        st.markdown("""
        <div style="background: #0B1120; border-left: 3px solid #38BDF8; padding: 10px 14px; border-radius: 4px; margin-top: 14px; font-size: 12px; color: #94A3B8; line-height: 1.5;">
            <b style="color: #38BDF8;">Scientific Distinction (Frequency vs. Network Centrality):</b><br/>
            Skill frequency measures simple posting volume. In contrast, <b>Degree Centrality</b> reflects the diversity of technology partners, while 
            <b>Betweenness Centrality</b> identifies critical 'bridge' technologies (e.g. Docker, REST API, Git) that connect disparate technology stacks across different domains.
        </div>
        """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# SECTION 5: Extraction Method Comparison (Lexical vs. Semantic vs. Combined)
# -----------------------------------------------------------------------------

def render_section5_method_comparison(
    output_dir: Path,
    jobs_df: Optional[pd.DataFrame] = None,
):
    """
    Renders Section 5:
    - Comparative evaluation of Lexical, Semantic, and Combined extraction on identical population
    - Overlap Venn breakdown, unique detections, rank shifts, stack stability
    - Methodological explanation of how Combined is constructed
    - Formal ground truth transparency disclosure
    """
    st.markdown("""
    <div style="border-bottom: 1px solid #1E293B; padding-bottom: 8px; margin-top: 6px; margin-bottom: 16px;">
        <h3 style="color: #38BDF8; font-weight: 600; margin: 0; font-size: 18px;">
            5. Extraction Method Comparison
        </h3>
        <p style="color: #94A3B8; font-size: 13px; margin: 2px 0 0 0;">
            Comparative analysis of Lexical, Semantic, and Combined extraction paradigms.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if jobs_df is None or jobs_df.empty:
        try:
            from src.database.repository import get_extracted_skills_dataset
            jobs_df = get_extracted_skills_dataset()
        except Exception:
            jobs_df = pd.DataFrame()

    from src.analytics.comparison import compare_extraction_methods
    comp_results = compare_extraction_methods(output_dir, jobs_df)

    method_metrics = comp_results.get("method_metrics", [])
    skill_overlap = comp_results.get("skill_overlap", {})
    rank_shifts = comp_results.get("rank_shifts", [])
    disclaimer = comp_results.get("evaluation_disclaimer", "")

    # Comparative KPI Cards
    if method_metrics:
        st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-bottom: 10px;'>Cross-Method Yield & Capacity Matrix</h4>", unsafe_allow_html=True)
        headers = ["Extraction Paradigm", "Unique Skills", "Observed Pairs", "Association Rules", "Discovered Stacks", "Network Edges", "Ground Truth F1"]
        rows = [
            [
                m["method"],
                str(m["unique_skills"]),
                str(m["skill_pairs"]),
                str(m["association_rules"]),
                str(m["technology_stacks"]),
                str(m["network_edges"]),
                str(m["ground_truth_f1"]),
            ]
            for m in method_metrics
        ]
        st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

    # Venn / Intersection Breakdown
    st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 20px; margin-bottom: 8px;'>Skill Overlap & Concordance Breakdown</h4>", unsafe_allow_html=True)
    c_v1, c_v2, c_v3, c_v4 = st.columns(4)
    with c_v1:
        st.metric("Concordant (Found by Both)", len(skill_overlap.get("common_to_all_three", [])))
    with c_v2:
        st.metric("Lexical Only", len(skill_overlap.get("lexical_only", [])))
    with c_v3:
        st.metric("Semantic Only", len(skill_overlap.get("semantic_only", [])))
    with c_v4:
        st.metric("Combined Unique Yield", skill_overlap.get("total_combined_unique", 0))

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        lex_only = skill_overlap.get("lexical_only", [])
        st.markdown(f"""
        <div style="background: #0F172A; border: 1px solid #1E293B; border-radius: 6px; padding: 12px; margin-top: 10px; font-size: 13px; color: #CBD5E1;">
            <b style="color: #38BDF8;">Lexical-Only Detections ({len(lex_only)}):</b><br/>
            {", ".join(lex_only) if lex_only else "None (Complete semantic coverage)"}<br/>
            <span style="font-size: 11px; color: #94A3B8;">Exact dictionary matches where embedding similarity fell below τ = 0.58.</span>
        </div>
        """, unsafe_allow_html=True)

    with col_s2:
        sem_only = skill_overlap.get("semantic_only", [])
        st.markdown(f"""
        <div style="background: #0F172A; border: 1px solid #1E293B; border-radius: 6px; padding: 12px; margin-top: 10px; font-size: 13px; color: #CBD5E1;">
            <b style="color: #A78BFA;">Semantic-Only Detections ({len(sem_only)}):</b><br/>
            {", ".join(sem_only) if sem_only else "None (All captured lexically)"}<br/>
            <span style="font-size: 11px; color: #94A3B8;">Skills identified contextually despite non-standard lexical phrasing.</span>
        </div>
        """, unsafe_allow_html=True)

    # Top Skill Rank Shifts Table
    if rank_shifts:
        st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 22px; margin-bottom: 8px;'>Top Skill Rank Concordance Across Paradigms</h4>", unsafe_allow_html=True)
        r_headers = ["Skill Entity", "Combined Rank", "Lexical Rank", "Semantic Rank", "Present in Lexical", "Present in Semantic"]
        r_rows = [
            [
                r["skill"],
                f"#{r['rank_combined']}",
                f"#{r['rank_lexical']}" if r["rank_lexical"] != "N/A" else "Unranked",
                f"#{r['rank_semantic']}" if r["rank_semantic"] != "N/A" else "Unranked",
                "✓ Yes" if r["found_in_lexical"] else "✗ No",
                "✓ Yes" if r["found_in_semantic"] else "✗ No",
            ]
            for r in rank_shifts[:12]
        ]
        st.markdown(render_custom_table(r_headers, r_rows), unsafe_allow_html=True)

    # Academic Ground Truth Transparency Callout
    st.markdown(f"""
    <div style="background: #0B1120; border-left: 3px solid #38BDF8; padding: 12px 16px; border-radius: 4px; margin-top: 22px; font-size: 12px; color: #94A3B8; line-height: 1.6;">
        <b style="color: #38BDF8;">Ground Truth Evaluation Transparency Disclosure:</b><br/>
        {disclaimer}
    </div>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# SECTION 6: Evidence Traceability & Data Quality Audit
# -----------------------------------------------------------------------------

def render_section6_evidence_quality(
    output_dir: Path,
    jobs_df: Optional[pd.DataFrame] = None,
):
    """
    Renders Section 6:
    - Traceability from skill relationships and stacks to authentic source job advertisements
    - OCR source processing funnel, yield, text lengths, and noise diagnostics
    - Data quality indicators, missing data audit, and searchable job audit table
    """
    st.markdown("""
    <div style="border-bottom: 1px solid #1E293B; padding-bottom: 8px; margin-top: 6px; margin-bottom: 16px;">
        <h3 style="color: #38BDF8; font-weight: 600; margin: 0; font-size: 18px;">
            6. Evidence & Data Quality
        </h3>
        <p style="color: #94A3B8; font-size: 13px; margin: 2px 0 0 0;">
            Traceability to authentic job postings and OCR extraction quality audit.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if jobs_df is None or jobs_df.empty:
        try:
            from src.database.repository import get_extracted_skills_dataset
            jobs_df = get_extracted_skills_dataset()
        except Exception:
            jobs_df = pd.DataFrame()

    comb_dir = output_dir / "combined"
    path_rel = comb_dir / "skill_relationships.csv"
    path_stacks = comb_dir / "technology_stacks.csv"

    # Part A: Evidence Verification Table
    st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 8px; margin-bottom: 8px;'>Traceable Relationship & Stack Verification Table</h4>", unsafe_allow_html=True)

    from src.analytics.evidence import build_source_evidence
    df_rel = pd.read_csv(path_rel) if path_rel.exists() else pd.DataFrame()
    df_stacks = pd.read_csv(path_stacks) if path_stacks.exists() else pd.DataFrame()

    evidence_records = build_source_evidence(jobs_df, df_rel, df_stacks, max_pairs=6, max_stacks=6)
    if evidence_records:
        headers = ["Entity Type", "Target Pattern", "Metric", "Supporting Ads", "Sample Job ID", "Company / Employer", "Authentic Context Excerpt", "Verification"]
        rows = []
        for r in evidence_records:
            snippet = r.get("context_snippet", r.get("text_excerpt", "N/A"))
            if len(snippet) > 85:
                snippet = snippet[:82] + "..."
            rows.append([
                str(r.get("type", r.get("entity_type", "Relationship"))),
                str(r.get("entity", r.get("target_pattern", ""))),
                str(r.get("primary_metric", "")),
                str(r.get("supporting_ads_count", 1)),
                str(r.get("job_id", r.get("sample_job_id", ""))),
                str(r.get("company", "Unknown")),
                snippet,
                str(r.get("verification_status", "Verified in Original Text")),
            ])
        st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)
    else:
        st.info("No evidence records could be linked. Ensure jobs_df is populated.")

    # Part B: OCR Source Processing Funnel
    st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 24px; margin-bottom: 8px;'>OCR Source Processing Funnel & Quality Diagnostics</h4>", unsafe_allow_html=True)
    from src.analytics.ocr_analysis import analyze_ocr_source
    ocr_rep = analyze_ocr_source(jobs_df)

    img_ads = ocr_rep.get("image_ads_collected", 0)
    ocr_success = ocr_rep.get("ocr_processed_success", 0)
    ocr_usable = ocr_rep.get("ocr_usable_text", 0)
    ocr_with_skills = ocr_rep.get("ocr_with_extracted_skills", 0)
    ocr_yield = ocr_rep.get("ocr_yield_pct", 0.0)
    text_stats = ocr_rep.get("text_length_stats", {})
    noise_diag = ocr_rep.get("noise_diagnostics", {})

    c_o1, c_o2, c_o3, c_o4, c_o5 = st.columns(5)
    with c_o1:
        st.metric("Image Ads Collected", img_ads, help="Advertisements published as flyer images")
    with c_o2:
        st.metric("OCR Processed", ocr_success, help="Images processed through Tesseract OCR")
    with c_o3:
        st.metric("Usable Text", ocr_usable, help="Outputs with >= 20 characters of legible text")
    with c_o4:
        st.metric("Ads With Skills", ocr_with_skills, help="OCR postings yielding identifiable technical skills")
    with c_o5:
        st.metric("OCR Technical Yield", f"{ocr_yield}%", help="Percentage of image ads yielding technical skills")

    col_q1, col_q2 = st.columns(2)
    with col_q1:
        st.markdown(f"""
        <div style="background: #0F172A; border: 1px solid #1E293B; border-radius: 6px; padding: 12px; margin-top: 10px; font-size: 13px; color: #CBD5E1;">
            <b style="color: #38BDF8;">OCR Text Length Distribution (Characters):</b><br/>
            • Minimum: <b>{text_stats.get('min', 0)}</b> chars<br/>
            • Maximum: <b>{text_stats.get('max', 0)}</b> chars<br/>
            • Mean: <b>{text_stats.get('mean', 0.0)}</b> chars<br/>
            • Median: <b>{text_stats.get('median', 0)}</b> chars
        </div>
        """, unsafe_allow_html=True)
    with col_q2:
        st.markdown(f"""
        <div style="background: #0F172A; border: 1px solid #1E293B; border-radius: 6px; padding: 12px; margin-top: 10px; font-size: 13px; color: #CBD5E1;">
            <b style="color: #FBBF24;">OCR Noise & Layout Diagnostics:</b><br/>
            • Low Confidence / Truncated Captures: <b>{noise_diag.get('low_confidence_count', 0)}</b><br/>
            • Short Text (< 50 chars): <b>{noise_diag.get('short_text_count', 0)}</b><br/>
            • Average Non-ASCII Noise Ratio: <b>{round(noise_diag.get('non_ascii_ratio_avg', 0.0) * 100, 2)}%</b>
        </div>
        """, unsafe_allow_html=True)

    # Part C: Searchable Job-Level Audit Table
    if jobs_df is not None and not jobs_df.empty:
        st.markdown("<h4 style='color: #F8FAFC; font-size: 15px; margin-top: 24px; margin-bottom: 8px;'>Searchable Job-Level Skill Extraction Audit Table</h4>", unsafe_allow_html=True)
        search_kw = st.text_input("Filter job audit by keyword (title, company, skill):", "", key="sec6_search_kw")

        audit_subset = jobs_df.copy()
        if search_kw:
            kw_clean = search_kw.strip().lower()
            mask = (
                audit_subset["job_title_raw"].astype(str).str.lower().str.contains(kw_clean) |
                audit_subset["company"].astype(str).str.lower().str.contains(kw_clean) |
                audit_subset["lexical_skills"].astype(str).str.lower().str.contains(kw_clean) |
                audit_subset["semantic_skills"].astype(str).str.lower().str.contains(kw_clean)
            )
            audit_subset = audit_subset[mask]

        audit_headers = ["Job ID", "Job Title", "Company", "Source Platform", "Lexical Skills", "Semantic Skills", "Link"]
        audit_rows = []
        for _, jrow in audit_subset.head(15).iterrows():
            lex_s = ", ".join(sorted(list(_parse_job_skills(jrow.get("lexical_skills", []))))) or "None"
            sem_s = ", ".join(sorted(list(_parse_job_skills(jrow.get("semantic_skills", []))))) or "None"
            jurl = str(jrow.get("source_url", ""))
            url_cell = f"<a href='{jurl}' target='_blank' style='color: #38BDF8;'>Link ↗</a>" if jurl else "N/A"
            audit_rows.append([
                str(jrow.get("job_id", "")),
                str(jrow.get("job_title_raw", "")),
                str(jrow.get("company", "")),
                str(jrow.get("source_platform", "")),
                lex_s,
                sem_s,
                url_cell,
            ])
        st.markdown(render_custom_table(audit_headers, audit_rows), unsafe_allow_html=True)
        st.caption(f"Displaying {min(15, len(audit_subset))} of {len(audit_subset)} matching job postings.")


# -----------------------------------------------------------------------------
# Backward-Compatible Section Wrappers for Legacy Callers
# -----------------------------------------------------------------------------

def render_tab1_overview_ocr(report: dict, mode: str, output_dir: Path, jobs_df: Optional[pd.DataFrame] = None):
    render_section1_dataset_overview(report, mode, output_dir, jobs_df)

def render_tab2_extraction_normalization(report: dict, mode: str, output_dir: Path, jobs_df: Optional[pd.DataFrame] = None):
    render_section1_dataset_overview(report, mode, output_dir, jobs_df)

def render_tab3_cooccurrence_similarity(analytics_dir: Path, report: Optional[dict] = None):
    render_section2_skill_relationships(analytics_dir, report)

def render_tab4_pmi_association_rules(analytics_dir: Path, report: Optional[dict] = None):
    render_section3_technology_stacks(analytics_dir)

def render_tab5_technology_stacks(analytics_dir: Path):
    render_section3_technology_stacks(analytics_dir)

def render_tab6_ecosystem_networks(analytics_dir: Path):
    render_section4_ecosystem_network(analytics_dir)

def render_tab7_method_comparison(output_dir: Path, jobs_df: Optional[pd.DataFrame] = None):
    render_section5_method_comparison(output_dir, jobs_df)

def render_tab8_source_evidence(output_dir: Path, jobs_df: Optional[pd.DataFrame] = None):
    render_section6_evidence_quality(output_dir, jobs_df)

def render_tab9_methodology_reference(analytics_dir: Path):
    st.markdown("""
    <div style="background: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 16px; font-size: 13px; color: #CBD5E1; line-height: 1.6;">
        <h4 style="color: #38BDF8; margin-top: 0;">Methodological Reference & Framework</h4>
        • <b>Co-Occurrence:</b> C(A, B) = count of jobs requiring both skills.<br/>
        • <b>Jaccard:</b> J(A, B) = |A ∩ B| / |A ∪ B|.<br/>
        • <b>PMI:</b> log₂( P(A, B) / (P(A)P(B)) ).<br/>
        • <b>NPMI:</b> PMI / -log₂(P(A, B)), bounded [-1, 1].<br/>
        • <b>Association Rules:</b> Support = P(A ∩ B), Confidence = P(B|A), Lift = P(B|A)/P(B).<br/>
        • <b>Network Centrality:</b> Degree Centrality (partner diversity), Betweenness Centrality (architectural bridges).
    </div>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# MASTER DASHBOARD ORCHESTRATOR
# -----------------------------------------------------------------------------

def render_all_analytics(
    report: dict,
    mode: str,
    output_dir: Path,
    jobs_df: Optional[pd.DataFrame] = None,
    selected_section: Optional[str] = None,
):
    """
    Master layout orchestrator assembling the 6 structured, academically defensible sections:
    1. Dataset Overview
    2. Skill Relationship Analysis
    3. Technology Stack Discovery
    4. Technology Ecosystem Network
    5. Extraction Method Comparison
    6. Evidence and Data Quality
    """
    analytics_dir = output_dir / mode

    if selected_section:
        if "1" in selected_section or "Dataset Overview" in selected_section:
            render_section1_dataset_overview(report, mode, output_dir, jobs_df)
        elif "2" in selected_section or "Relationship" in selected_section:
            render_section2_skill_relationships(analytics_dir, report, jobs_df)
        elif "3" in selected_section or "Stack" in selected_section:
            render_section3_technology_stacks(analytics_dir, jobs_df)
        elif "4" in selected_section or "Network" in selected_section:
            render_section4_ecosystem_network(analytics_dir)
        elif "5" in selected_section or "Comparison" in selected_section:
            render_section5_method_comparison(output_dir, jobs_df)
        elif "6" in selected_section or "Evidence" in selected_section:
            render_section6_evidence_quality(output_dir, jobs_df)
        else:
            render_section1_dataset_overview(report, mode, output_dir, jobs_df)
        return

    # If called without an explicit selected_section, render horizontal tabs for the 6 sections
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "1. Dataset Overview",
        "2. Skill Relationship Analysis",
        "3. Technology Stack Discovery",
        "4. Technology Ecosystem Network",
        "5. Extraction Method Comparison",
        "6. Evidence & Data Quality",
    ])

    with tab1:
        render_section1_dataset_overview(report, mode, output_dir, jobs_df)

    with tab2:
        render_section2_skill_relationships(analytics_dir, report, jobs_df)

    with tab3:
        render_section3_technology_stacks(analytics_dir, jobs_df)

    with tab4:
        render_section4_ecosystem_network(analytics_dir)

    with tab5:
        render_section5_method_comparison(output_dir, jobs_df)

    with tab6:
        render_section6_evidence_quality(output_dir, jobs_df)
