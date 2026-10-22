"""User-facing IT skill demand dashboard.

Reads the project's master SQLite database and presents the analytical results
without exposing scraping, review, or pipeline-administration controls.
"""
from pathlib import Path
import sys
import sqlite3
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from src.database.connection import get_connection, initialize_database, DB_PATH
except Exception as exc:
    st.set_page_config(page_title="IT Skills | Market Dashboard", page_icon="📊", layout="wide")
    st.error(f"Could not load the project database module: {exc}")
    st.stop()

st.set_page_config(page_title="IT Skills | Market Dashboard", page_icon="📊", layout="wide")

# Clean, user-facing visual system. The dashboard deliberately avoids admin workflow language.
st.markdown("""
<style>
:root { --ink:#172b3a; --muted:#687985; --line:#e4ebef; --accent:#16a085; --soft:#eef8f5; }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1500px; }
#MainMenu, footer {visibility:hidden;}
.hero { background:linear-gradient(120deg,#102b3a 0%,#174d58 60%,#167d70 100%); color:#fff; padding:1.65rem 1.8rem; border-radius:20px; margin-bottom:1.2rem; }
.hero h1 { color:#fff; font-size:2rem; margin:0 0 .4rem 0; letter-spacing:-.035em; }
.hero p { color:#d9eceb; margin:0; font-size:1rem; }
.eyebrow { color:#a9e4d6; text-transform:uppercase; font-size:.72rem; font-weight:700; letter-spacing:.14em; margin-bottom:.55rem; }
.section-title { color:#fff; font-size:1.2rem; font-weight:750; letter-spacing:-.02em; margin:.6rem 0 .15rem; }
.section-subtitle { color:#71818b; font-size:.88rem; margin-bottom:.75rem; }
div[data-testid="stMetric"] { background:#183342; border:1px solid var(--line); padding:1rem 1.1rem; border-radius:15px; box-shadow:0 3px 12px rgba(25,55,70,.035); }
div[data-testid="stMetricLabel"] { color:#6c7e88; }
div[data-testid="stMetricValue"] { color:#fff; font-weight:750; }
div[data-testid="stTabs"] button { font-weight:650; }
div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
div[data-testid="stAlert"] { border-radius:12px; }
.filter-note { background:#f3f8f8; border:1px solid #e1eeee; border-radius:12px; padding:.7rem .9rem; color:#4f6872; font-size:.84rem; }
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)


def read_table(conn, query, params=()):
    try:
        return pd.read_sql_query(query, conn, params=params)
    except (sqlite3.OperationalError, pd.errors.DatabaseError):
        return pd.DataFrame()


def clean_text(series):
    return series.fillna("Unknown").astype(str).replace({"": "Unknown", "None": "Unknown", "nan": "Unknown"})


def infer_role(title):
    value = str(title or "").lower()
    rules = [
        ("QA & Testing", r"\b(qa|quality assurance|test engineer|software tester|automation tester)\b"),
        ("Data & AI", r"\b(data|machine learning|\bai\b|analytics|data scientist|business intelligence)\b"),
        ("DevOps & Cloud", r"\b(devops|site reliability|cloud engineer|platform engineer|\bsre\b)\b"),
        ("Security", r"\b(security|penetration tester|cybersecurity)\b"),
        ("Design & UX", r"\b(ui/ux|ux designer|ui designer|product designer)\b"),
        ("Frontend", r"\b(front.?end|frontend|web designer)\b"),
        ("Backend", r"\b(back.?end|backend|api engineer)\b"),
        ("Software Development", r"\b(software engineer|software developer|full.?stack|programmer|application developer)\b"),
        ("IT Support & Networks", r"\b(it support|help.?desk|network engineer|system administrator)\b"),
    ]
    for label, pattern in rules:
        if re.search(pattern, value):
            return label
    return "Other / unclassified"


try:
    initialize_database()
    with get_connection() as conn:
        jobs = read_table(conn, """
            SELECT job_id, source_platform, source_hostname, job_title, company_name,
                   location, country, posting_date, work_mode, salary_disclosed,
                   salary_min_normalized, salary_max_normalized,
                   salary_currency_normalized, role_name, classification_status
            FROM jobs
        """)
        skills = read_table(conn, """
            SELECT es.job_id, es.method, es.skill_name, es.canonical_skill_id,
                   es.confidence, j.country, j.source_platform, j.job_title,
                   j.posting_date, j.role_name, j.salary_min_normalized,
                   j.salary_max_normalized, j.salary_currency_normalized
            FROM extracted_skills es
            JOIN jobs j ON j.job_id = es.job_id
        """)
        method_rows = read_table(conn, "SELECT DISTINCT method FROM extracted_skills WHERE method IS NOT NULL ORDER BY method")
except Exception as exc:
    st.error(f"Unable to read the master database at `{DB_PATH}`: {exc}")
    st.stop()

if jobs.empty:
    st.markdown('<div class="hero"><div class="eyebrow">Labour-market intelligence</div><h1>IT Skills Market Dashboard</h1><p>Explore technical skills employers request, how demand varies by role, and how it changes over time.</p></div>', unsafe_allow_html=True)
    st.warning("The master dataset is empty. Import job advertisements through the existing data workflow, then extract and save their skills to populate this dashboard.")
    st.stop()

for col in ["country", "source_platform", "job_title", "role_name", "work_mode"]:
    if col not in jobs.columns:
        jobs[col] = None
    jobs[col] = clean_text(jobs[col])
if not skills.empty:
    for col in ["country", "source_platform", "job_title", "role_name", "method", "skill_name"]:
        if col not in skills.columns:
            skills[col] = None
        skills[col] = clean_text(skills[col])
    skills["posting_date"] = pd.to_datetime(skills["posting_date"], errors="coerce")
jobs["posting_date"] = pd.to_datetime(jobs["posting_date"], errors="coerce")
jobs["role_family"] = jobs["role_name"].where(jobs["role_name"].ne("Unknown"), jobs["job_title"].map(infer_role))
if not skills.empty:
    skills["role_family"] = skills["role_name"].where(skills["role_name"].ne("Unknown"), skills["job_title"].map(infer_role))

st.markdown('<div class="hero"><div class="eyebrow">Sri Lanka & regional IT labour market</div><h1>IT Skills Market Dashboard</h1><p>Discover in-demand technologies, compare career paths, and explore skill-demand changes using observed job advertisements.</p></div>', unsafe_allow_html=True)

# User-facing filters: one shared scope for all charts and tables.
with st.container(border=True):
    st.markdown("**Explore the market**")
    fc1, fc2, fc3, fc4 = st.columns([1.05, 1.05, 1.25, 1.25])
    country_options = sorted(jobs["country"].unique().tolist())
    source_options = sorted(jobs["source_platform"].unique().tolist())
    role_options = sorted(jobs["role_family"].unique().tolist())
    method_options = sorted(skills["method"].unique().tolist()) if not skills.empty else []
    chosen_country = fc1.selectbox("Market", ["All markets"] + country_options)
    chosen_source = fc2.selectbox("Job source", ["All sources"] + source_options)
    chosen_role = fc3.selectbox("Career area", ["All career areas"] + role_options)
    chosen_method = fc4.selectbox("Skill representation", ["All methods"] + method_options)

    date_values = jobs["posting_date"].dropna()
    if not date_values.empty:
        min_date, max_date = date_values.min().date(), date_values.max().date()
        dc1, dc2, dc3 = st.columns([1, 1, 2])
        start_date = dc1.date_input("Posted from", value=min_date, min_value=min_date, max_value=max_date)
        end_date = dc2.date_input("Posted to", value=max_date, min_value=min_date, max_value=max_date)
    else:
        start_date = end_date = None
        st.caption("No reliable posting dates are currently available. Time-based analysis will be limited until dated records are imported.")

if start_date and end_date and start_date > end_date:
    st.error("The start date must be on or before the end date.")
    st.stop()

job_scope = jobs.copy()
if chosen_country != "All markets": job_scope = job_scope[job_scope["country"].eq(chosen_country)]
if chosen_source != "All sources": job_scope = job_scope[job_scope["source_platform"].eq(chosen_source)]
if chosen_role != "All career areas": job_scope = job_scope[job_scope["role_family"].eq(chosen_role)]
if start_date and end_date:
    job_scope = job_scope[job_scope["posting_date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1) )]

job_ids = set(job_scope["job_id"].astype(str))
skill_scope = skills[skills["job_id"].astype(str).isin(job_ids)].copy() if not skills.empty else pd.DataFrame()
if not skill_scope.empty and chosen_method != "All methods":
    skill_scope = skill_scope[skill_scope["method"].eq(chosen_method)]

unique_skills = skill_scope.groupby("skill_name")["job_id"].nunique().sort_values(ascending=False) if not skill_scope.empty else pd.Series(dtype=int)
job_count = len(job_scope)
job_with_skills = skill_scope["job_id"].nunique() if not skill_scope.empty else 0
coverage = (job_with_skills / job_count * 100) if job_count else 0
country_count = job_scope["country"].nunique()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Job advertisements", f"{job_count:,}", help="Records matching the current filters.")
m2.metric("Distinct skills found", f"{skill_scope['skill_name'].nunique():,}" if not skill_scope.empty else "0")
m3.metric("Jobs with extracted skills", f"{job_with_skills:,}", help="Distinct jobs with at least one saved skill mention.")
m4.metric("Skill extraction coverage", f"{coverage:.1f}%", help="Jobs with saved skill mentions divided by filtered jobs.")

if job_count == 0:
    st.warning("No job advertisements match the selected filters. Broaden the market, source, role, or date range.")
    st.stop()
if skill_scope.empty:
    st.warning("No saved skill mentions match this scope. Try another extraction method or check that skills have been extracted and persisted.")
    st.stop()

# Summary tabs keep the page approachable while providing detail when requested.
tab_overview, tab_skills, tab_roles, tab_timeline, tab_jobs = st.tabs(["Overview", "Skills explorer", "Career areas", "Demand over time", "Job listings"])

with tab_overview:
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown('<div class="section-title">Most requested technical skills</div><div class="section-subtitle">Ranked by distinct job advertisements, not raw keyword occurrences.</div>', unsafe_allow_html=True)
        top = unique_skills.head(12).sort_values(ascending=True).reset_index()
        top.columns = ["Skill", "Job advertisements"]
        fig = px.bar(top, x="Job advertisements", y="Skill", orientation="h", text="Job advertisements", color="Job advertisements", color_continuous_scale=["#d9eee8", "#168a78"])
        fig.update_layout(height=420, margin=dict(l=5,r=10,t=10,b=5), coloraxis_showscale=False, xaxis_title="Number of job ads", yaxis_title="", font=dict(color="#294653"))
        fig.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown('<div class="section-title">Where opportunities are listed</div><div class="section-subtitle">Distribution of filtered job advertisements by career area.</div>', unsafe_allow_html=True)
        role_counts = job_scope["role_family"].value_counts().head(10).rename_axis("Career area").reset_index(name="Job advertisements")
        fig = px.pie(role_counts, names="Career area", values="Job advertisements", hole=.62, color_discrete_sequence=px.colors.qualitative.Safe)
        fig.update_layout(height=420, margin=dict(l=5,r=5,t=10,b=5), legend_title_text="Career area", font=dict(color="#294653"))
        fig.update_traces(textposition="inside", textinfo="percent")
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('<div class="section-title">Quick insights</div>', unsafe_allow_html=True)
    q1, q2, q3 = st.columns(3)
    top_name = str(unique_skills.index[0]) if len(unique_skills) else "Not available"
    q1.markdown(f"**Leading skill**\n\n{top_name}\n\n{int(unique_skills.iloc[0]) if len(unique_skills) else 0:,} job ads mention this skill.")
    q2.markdown(f"**Largest career area**\n\n{job_scope['role_family'].value_counts().index[0]}\n\n{int(job_scope['role_family'].value_counts().iloc[0]):,} matching job ads.")
    dated_share = job_scope["posting_date"].notna().mean() * 100
    q3.markdown(f"**Date coverage**\n\n{dated_share:.1f}%\n\nOf filtered advertisements have a usable posting date.")

with tab_skills:
    st.markdown('<div class="section-title">Find and compare skills</div><div class="section-subtitle">Search a technology, change the ranking metric, or inspect the job-ad evidence behind a skill.</div>', unsafe_allow_html=True)
    s1, s2, s3 = st.columns([1.5, 1, 1])
    search = s1.text_input("Search skills", placeholder="e.g. Python, React, AWS")
    rank_metric = s2.selectbox("Rank by", ["Job advertisements", "Share of filtered jobs", "Average confidence"])
    top_n = s3.selectbox("Rows to show", [10, 20, 50, 100], index=1)
    grouped = skill_scope.groupby("skill_name").agg(job_ad_count=("job_id", "nunique"), mention_count=("job_id", "size"), avg_confidence=("confidence", "mean")).reset_index()
    grouped["share_of_jobs_pct"] = grouped["job_ad_count"] / max(job_count, 1) * 100
    if search.strip(): grouped = grouped[grouped["skill_name"].str.contains(search.strip(), case=False, na=False)]
    metric_map = {"Job advertisements":"job_ad_count", "Share of filtered jobs":"share_of_jobs_pct", "Average confidence":"avg_confidence"}
    grouped = grouped.sort_values(metric_map[rank_metric], ascending=False, na_position="last")
    display = grouped.head(top_n).rename(columns={"skill_name":"Skill", "job_ad_count":"Job ads", "mention_count":"Skill mentions", "share_of_jobs_pct":"Share of jobs (%)", "avg_confidence":"Average confidence"})
    st.dataframe(display.round(3), use_container_width=True, hide_index=True)
    st.download_button("Export skill ranking CSV", grouped.to_csv(index=False).encode("utf-8-sig"), "skill_demand_ranking.csv", "text/csv")
    if not grouped.empty:
        selected_skill = st.selectbox("Inspect a skill", grouped["skill_name"].tolist(), key="inspect_skill")
        evidence = skill_scope[skill_scope["skill_name"].eq(selected_skill)].drop_duplicates("job_id")
        st.caption(f"{selected_skill} appears in {len(evidence):,} distinct job advertisements ({len(evidence)/max(job_count,1)*100:.1f}% of the current filtered sample).")
        evidence_cols = [c for c in ["job_title", "country", "source_platform", "posting_date", "confidence"] if c in evidence.columns]
        st.dataframe(evidence[evidence_cols].sort_values("posting_date", ascending=False, na_position="last"), use_container_width=True, hide_index=True)

with tab_roles:
    st.markdown('<div class="section-title">Skills by career area</div><div class="section-subtitle">Compare the technical requirements associated with different role families in the collected sample.</div>', unsafe_allow_html=True)
    role_skill = skill_scope.groupby(["role_family", "skill_name"])["job_id"].nunique().reset_index(name="Job advertisements")
    role_totals = job_scope.groupby("role_family")["job_id"].nunique().to_dict()
    role_skill["Share within role (%)"] = role_skill.apply(lambda r: r["Job advertisements"] / max(role_totals.get(r["role_family"], 0), 1) * 100, axis=1)
    r1, r2 = st.columns([1, 1.3])
    with r1:
        role_choice = st.selectbox("Choose a career area", ["All career areas"] + sorted(role_skill["role_family"].unique()), key="role_drill")
        if role_choice != "All career areas": role_view = role_skill[role_skill["role_family"].eq(role_choice)]
        else: role_view = role_skill
        role_top = role_view.sort_values("Job advertisements", ascending=False).head(15).sort_values("Job advertisements")
        fig = px.bar(role_top, x="Job advertisements", y="skill_name", orientation="h", color="role_family", labels={"skill_name":"Skill"}, color_discrete_sequence=["#168a78", "#3c8dba", "#edaa54"])
        fig.update_layout(height=470, margin=dict(l=5,r=5,t=10,b=5), yaxis_title="", legend_title_text="Career area")
        st.plotly_chart(fig, use_container_width=True)
    with r2:
        pivot = role_skill.sort_values("Job advertisements", ascending=False).groupby("role_family").head(8)
        if not pivot.empty:
            heat = pivot.pivot_table(index="role_family", columns="skill_name", values="Share within role (%)", fill_value=0, aggfunc="max")
            # Keep the heatmap readable by limiting columns to the most frequent skills.
            common = role_skill.groupby("skill_name")["Job advertisements"].sum().nlargest(14).index
            heat = heat.loc[:, heat.columns.intersection(common)]
            fig = px.imshow(heat, aspect="auto", color_continuous_scale="Teal", labels=dict(x="Skill", y="Career area", color="Share of role jobs (%)"))
            fig.update_layout(height=470, margin=dict(l=5,r=5,t=10,b=5), xaxis_tickangle=-35)
            st.plotly_chart(fig, use_container_width=True)
    st.dataframe(role_skill.sort_values(["role_family", "Job advertisements"], ascending=[True, False]).rename(columns={"role_family":"Career area", "skill_name":"Skill"}).round(2), use_container_width=True, hide_index=True)

with tab_timeline:
    st.markdown('<div class="section-title">How skill demand changes over time</div><div class="section-subtitle">Demand rate is the percentage of dated job advertisements in a period that mention a skill. It is not a forecast of the entire labour market.</div>', unsafe_allow_html=True)
    dated_jobs = job_scope.dropna(subset=["posting_date"]).copy()
    dated_skills = skill_scope.dropna(subset=["posting_date"]).copy()
    if dated_jobs.empty or dated_skills.empty:
        st.info("There are not enough dated job advertisements and skill mentions to show a temporal trend. Check posting-date coverage.")
    else:
        period_label = st.radio("Time interval", ["Monthly", "Quarterly"], horizontal=True)
        freq = "MS" if period_label == "Monthly" else "QS"
        dated_jobs["period"] = dated_jobs["posting_date"].dt.to_period("M" if freq == "MS" else "Q").dt.start_time
        dated_skills["period"] = dated_skills["posting_date"].dt.to_period("M" if freq == "MS" else "Q").dt.start_time
        denominator = dated_jobs.groupby("period")["job_id"].nunique().rename("Eligible job ads")
        counts = dated_skills.groupby(["period", "skill_name"])["job_id"].nunique().rename("Jobs mentioning skill").reset_index()
        counts = counts.join(denominator, on="period")
        counts["Demand rate (%)"] = counts["Jobs mentioning skill"] / counts["Eligible job ads"] * 100
        timeline_skills = counts.groupby("skill_name")["Jobs mentioning skill"].sum().nlargest(12).index.tolist()
        selected_timeline = st.multiselect("Skills to track", sorted(counts["skill_name"].unique()), default=timeline_skills, key="timeline_skills")
        if selected_timeline:
            chart = counts[counts["skill_name"].isin(selected_timeline)]
            fig = px.line(chart, x="period", y="Demand rate (%)", color="skill_name", markers=True, hover_data=["Jobs mentioning skill", "Eligible job ads"], labels={"period":"Posting period", "skill_name":"Skill"})
            fig.update_layout(height=470, hovermode="x unified", legend_title_text="Skill", margin=dict(l=5,r=5,t=10,b=5))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(chart.sort_values(["period", "Demand rate (%)"], ascending=[False, False]), use_container_width=True, hide_index=True)
            st.download_button("Export temporal demand CSV", chart.to_csv(index=False).encode("utf-8-sig"), "temporal_skill_demand.csv", "text/csv")
        st.caption("Periods with zero eligible jobs are not assigned a demand rate. Historical coverage and source mix can affect the apparent trend.")

with tab_jobs:
    st.markdown('<div class="section-title">Explore matching job advertisements</div><div class="section-subtitle">Use the current filters to inspect the job sample behind the aggregate insights.</div>', unsafe_allow_html=True)
    job_search = st.text_input("Search job title or company", placeholder="Search by role or employer")
    listing = job_scope.copy()
    if job_search.strip():
        mask = listing["job_title"].str.contains(job_search.strip(), case=False, na=False) | listing["company_name"].fillna("").astype(str).str.contains(job_search.strip(), case=False, na=False)
        listing = listing[mask]
    listing["posting_date"] = listing["posting_date"].dt.strftime("%Y-%m-%d")
    cols = [c for c in ["job_title", "company_name", "country", "location", "source_platform", "posting_date", "work_mode"] if c in listing.columns]
    st.dataframe(listing[cols].sort_values("posting_date", ascending=False, na_position="last"), use_container_width=True, hide_index=True)
    st.download_button("Export filtered job list CSV", listing[cols].to_csv(index=False).encode("utf-8-sig"), "filtered_job_advertisements.csv", "text/csv")

st.markdown("---")
st.caption("Research note: findings describe the job advertisements collected and retained in this project database. They should not be interpreted as a complete census of the Sri Lankan or regional IT labour market. Role labels may be inferred from job titles where a normalized role is unavailable.")
