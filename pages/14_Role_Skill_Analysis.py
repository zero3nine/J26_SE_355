import altair as alt
import streamlit as st

st.set_page_config(
    page_title="Role Skill Analysis — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *

from src.roles.role_skill_analysis import (
    build_role_skill_matrix,
    label_roles_with_totals,
    style_role_skill_matrix,
)
from src.roles.distinctiveness import (
    DEFAULT_N_RESAMPLES,
    DEFAULT_SIGNIFICANCE_LEVEL,
    DEFAULT_TOP_K,
    agreement_label,
    distinctiveness_verdict,
    run_distinctiveness_analysis,
    stability_label,
    times_more_common,
)

from src.database.connection import get_connection, initialize_database
from src.roles.db_loader import (
    database_summary,
    list_extraction_runs,
    load_extracted_jobs,
)

render_page_shell()

for _key, _default in {
    "distinctiveness_completed": False,
    "distinctiveness_df": pd.DataFrame(),
    "ranking_divergence_df": pd.DataFrame(),
    "distinctiveness_stability_df": pd.DataFrame(),
    "distinctiveness_stability_summary_df": pd.DataFrame(),
    "distinctiveness_report": "",
    "audit_result": None,
    "role_input_description": "",
    "audit_failed": False,
}.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default

METHOD_LABELS = {
    "lexical": "Lexical",
    "semantic": "Semantic",
    "both": "Confirmed by both methods",
}

def static_bar_chart(series, height=400):
    df = series.rename("Postings").rename_axis("Role").reset_index()
    return (
        alt.Chart(df).mark_bar()
        .encode(
            y=alt.Y("Role:N", sort="-x", title=None),
            x=alt.X("Postings:Q", axis=alt.Axis(tickMinStep=1)),
            tooltip=["Role", "Postings"],
        )
        .properties(width="container", height=height)
    )

def static_grouped_bar_chart(pivot, height=400):
    long_df = (
        pivot.rename_axis("Skill").reset_index()
        .melt(id_vars="Skill", var_name="Method", value_name="Postings")
    )
    return (
        alt.Chart(long_df).mark_bar()
        .encode(
            y=alt.Y("Skill:N", sort="-x", title=None),
            x=alt.X("Postings:Q", axis=alt.Axis(tickMinStep=1)),
            yOffset="Method:N",
            color="Method:N",
            tooltip=["Skill", "Method", "Postings"],
        )
        .properties(width="container", height=height)
    )

# Part 1: role segmentation

st.subheader("Role based skill demand segmentation")
st.caption(
    "Groups job postings by IT role, then shows how often each skill "
    "appears within that role, separating skills that are core to "
    "the role from ones that only show up in a few postings."
)

saved_csv = current_dir / "data" / "processed" / "jobs_extracted.csv"

input_df = None
input_description = ""
summary = None

try:
    initialize_database()
    with get_connection() as conn:
        summary = database_summary(conn)
        runs_df = list_extraction_runs(conn)
        if not runs_df.empty:
            latest_run = runs_df.iloc[0]["run_id"]
            input_df = load_extracted_jobs(conn, latest_run)
            input_description = f"Master database, latest extraction run ({str(latest_run)[:8]}), {len(input_df):,} postings"
except Exception as e:
    st.error(f"Could not read the master database: {e}")
    st.stop()

if summary is not None:
    m1, m2 = st.columns(2)
    m1.metric("Jobs in master database", f"{summary['jobs']:,}")
    m2.metric("Skill mentions", f"{summary['mentions']:,}")

if input_df is None or input_df.empty:
    have_session_data = (
        st.session_state.get("extraction_completed", False)
        and not st.session_state.extracted_df.empty
    )
    if not have_session_data:
        st.info(
            "No saved extraction results found. On the 'Extract Skills' page run the "
            "extraction and press 'Save lexical and semantic results', then come back here."
        )
        if saved_csv.exists() and st.button("Load the last saved extraction (data/processed/jobs_extracted.csv)"):
            try:
                st.session_state.extracted_df = pd.read_csv(saved_csv)
                st.session_state.extraction_completed = True
                st.rerun()
            except Exception as e:
                st.error(f"Could not read the saved extraction: {e}")
        st.stop()
    input_df = st.session_state.extracted_df
    input_description = f"Current session, {len(input_df):,} postings"

st.caption(f"Input: {input_description}")

input_changed = st.session_state.role_input_description != input_description
if st.button("Refresh role analysis from the latest data") or input_changed:
    with st.spinner("Classifying job postings into role categories..."):
        try:
            role_df = classify_roles(input_df)
            freq_df = build_role_skill_frequency_table(role_df)

            st.session_state.role_classified_df = role_df
            st.session_state.role_skill_freq_df = freq_df
            st.session_state.role_analysis_completed = True
            st.session_state.role_input_description = input_description
            st.session_state.distinctiveness_completed = False
            st.session_state.audit_result = None
            st.session_state.audit_failed = False

            analysis_dir = current_dir / "data" / "analysis"
            analysis_dir.mkdir(parents=True, exist_ok=True)
            freq_df.to_csv(analysis_dir / "role_skill_frequencies.csv", index=False, encoding="utf-8")

            st.success("Role classification and skill demand analysis complete.")
        except Exception as e:
            st.error(f"Role analysis failed: {e}")

if not st.session_state.role_analysis_completed:
    st.stop()

role_df = st.session_state.role_classified_df
freq_df = st.session_state.role_skill_freq_df
if st.session_state.role_input_description:
    st.caption(f"Results below were computed from: {st.session_state.role_input_description}")

st.subheader("Job postings by role category")
st.altair_chart(static_bar_chart(role_df["role_name"].value_counts()))

st.subheader("Skill demand by role — lexical vs semantic")
role_options = sorted(freq_df["role_name"].unique())

if not role_options:
    st.info("No roles were classified yet, this can happen with a very small sample.")
else:
    selected_role = st.selectbox("Choose a role category", role_options)

    role_data = freq_df[freq_df["role_name"] == selected_role]
    pivot = role_data.pivot_table(
        index="skill", columns="method", values="job_count", fill_value=0
    ).astype(int)

    if pivot.empty:
        st.info(f"No skills were extracted for '{selected_role}' yet.")
    else:
        pivot["_total"] = pivot.sum(axis=1)
        top_skills = pivot.sort_values("_total", ascending=False).head(10).drop(columns="_total")
        st.altair_chart(static_grouped_bar_chart(top_skills))

st.subheader("Skill demand by role table")
st.caption(
    "How many job postings in each role mention each skill."
)
matrix_mode = st.radio(
    "Skills counted from",
    ["lexical", "semantic", "both"],
    format_func=METHOD_LABELS.get,
    horizontal=True,
    key="role_matrix_mode",
    help="Lexical: skills found by exact keyword matching. "
         "Semantic: skills found by meaning-based matching. "
         "Confirmed by both methods: a posting counts for a skill only when both "
         "methods found that skill in that same posting.",
)

skill_matrix = build_role_skill_matrix(role_df, matrix_mode)
if skill_matrix.empty:
    st.info(
        "No skills to show for this selection with 'Confirmed by both methods' "
        "this means no skill was found by both methods in the same posting."
    )
else:
    st.dataframe(
        style_role_skill_matrix(label_roles_with_totals(skill_matrix, role_df)),
        height=400,
    )

with st.expander("Detailed table (one row per role, skill and method)"):
    freq_cols = list(freq_df.columns)
    headers = [c.replace("_", " ").title() for c in freq_cols]
    rows = []
    for _, row in freq_df.iterrows():
        rows.append([f"{row[c]}%" if c == "pct_of_role" else str(row[c]) for c in freq_cols])
    st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

st.download_button(
    label="Download role x skill frequency CSV",
    data=freq_df.to_csv(index=False, encoding="utf-8"),
    file_name="role_skill_frequencies.csv",
    mime="text/csv",
)

# Part 2: statistical distinctiveness

st.divider()
st.subheader("Statistical distinctiveness")
st.caption(
    "Frequency alone can't tell you whether a skill is actually distinctive to a "
    "role or just common across the whole IT sector. This test checks, for each "
    "skill a role mentions, whether that skill's in-role demand is significantly "
    "and consistently higher than its demand in every other role combined."
)

with st.expander("Distinctiveness test settings", expanded=False):
    significance_level = st.slider(
        "Significance threshold (p <)",
        min_value=0.01, max_value=0.20,
        value=DEFAULT_SIGNIFICANCE_LEVEL, step=0.01,
        help="A skill-role pair is only ranked as distinctive when its p-value is "
             "below this threshold and the skill's in-role rate is higher than its "
             "rate in all other roles combined.",
    )
    top_k = st.slider(
        "Top-K distinctive skills per role", min_value=3, max_value=15,
        value=DEFAULT_TOP_K, step=1,
        help="Used for the frequency vs distinctiveness comparison and the "
             "resampling stability check below.",
    )
    n_resamples = st.slider(
        "Bootstrap resamples (stability check)", min_value=10, max_value=100,
        value=DEFAULT_N_RESAMPLES, step=10,
        help="More resamples give a steadier stability estimate but take longer to run.",
    )

if st.button("Re-run distinctiveness analysis") or not st.session_state.distinctiveness_completed:
    with st.spinner("Running tests and resampling stability check..."):
        try:
            result = run_distinctiveness_analysis(
                role_df, freq_df,
                significance_level=significance_level,
                n_resamples=n_resamples,
                top_k=top_k,
            )
            st.session_state.distinctiveness_df = result["distinctiveness"]
            st.session_state.ranking_divergence_df = result["ranking_divergence"]
            st.session_state.distinctiveness_stability_df = result["stability"]
            st.session_state.distinctiveness_stability_summary_df = result["stability_summary"]
            st.session_state.distinctiveness_report = result["report"]
            st.session_state.distinctiveness_significance = significance_level
            st.session_state.distinctiveness_completed = True
            st.session_state.audit_result = None
            st.session_state.audit_failed = False

            analysis_dir = current_dir / "data" / "analysis"
            analysis_dir.mkdir(parents=True, exist_ok=True)
            for name, key in [
                ("skill_distinctiveness.csv", "distinctiveness"),
                ("ranking_divergence.csv", "ranking_divergence"),
                ("distinctiveness_stability.csv", "stability"),
                ("distinctiveness_stability_summary.csv", "stability_summary"),
            ]:
                result[key].to_csv(analysis_dir / name, index=False, encoding="utf-8")

            st.success("Distinctiveness analysis complete.")
        except Exception as e:
            st.error(f"Distinctiveness analysis failed: {e}")

if not st.session_state.distinctiveness_completed:
    st.stop()

distinct_df = st.session_state.distinctiveness_df
divergence_df = st.session_state.ranking_divergence_df
stability_df = st.session_state.distinctiveness_stability_df
stability_summary_df = st.session_state.distinctiveness_stability_summary_df
used_level = st.session_state.get("distinctiveness_significance", DEFAULT_SIGNIFICANCE_LEVEL)

distinct_role_options = sorted(distinct_df["role_name"].unique()) if not distinct_df.empty else []
if not distinct_role_options:
    st.info("No skill-role pairs were tested yet.")
    st.stop()

selected_distinct_role = st.selectbox(
    "Choose a role category", distinct_role_options, key="distinct_role_select"
)
selected_method = st.radio(
    "Skill extraction method",
    ["lexical", "semantic", "both"],
    format_func=METHOD_LABELS.get,
    horizontal=True,
    key="distinct_method_select",
)

role_method_df = distinct_df[
    (distinct_df["role_name"] == selected_distinct_role)
    & (distinct_df["method"] == selected_method)
]

PLAIN_HEADERS = [
    "Share of this role's postings (In-Role %)",
    "Share of other roles' postings (Other Roles %)",
    "How much more common",
    "Verdict (P-Value)",
]

def _plain_cells(row):
    return [
        f"{row['in_role_pct']}%",
        f"{row['other_roles_pct']}%",
        times_more_common(
            row["in_role_skill_count"], row["in_role_job_count"],
            row["other_roles_skill_count"], row["other_roles_job_count"],
        ),
        distinctiveness_verdict(
            row["p_value"], row["direction"], used_level,
            row["in_role_skill_count"], row["in_role_job_count"],
        ),
    ]

st.markdown(f"**Ranked distinctive skills -- {selected_distinct_role} ({METHOD_LABELS[selected_method]})**")
ranked = role_method_df.dropna(subset=["distinctiveness_rank"]).sort_values("distinctiveness_rank")
if ranked.empty:
    st.info(
        "No skill was found to be statistically distinctive for this role/method at "
        "the chosen significance threshold. This can happen with a small sample, or "
        "when a role's skills are all also common elsewhere."
    )
else:
    rows = [[int(r["distinctiveness_rank"]), r["skill"], *_plain_cells(r)] for _, r in ranked.iterrows()]
    st.markdown(render_custom_table(["Rank", "Skill", *PLAIN_HEADERS], rows), unsafe_allow_html=True)

with st.expander("All skills tested for this role (including non-distinctive)"):
    full_rows = [
        [
            r["skill"], *_plain_cells(r),
            int(r["distinctiveness_rank"]) if pd.notna(r["distinctiveness_rank"]) else "-",
        ]
        for _, r in role_method_df.sort_values("p_value", na_position="last").iterrows()
    ]
    st.markdown(render_custom_table(["Skill", *PLAIN_HEADERS, "Rank"], full_rows), unsafe_allow_html=True)

with st.expander("Advanced statistics (for researchers)"):
    adv_headers = [
        "Skill", "Chi2", "P-Value", "Odds Ratio", "Test Used",
        "Significant", "Direction", "Low-Expected Warning",
    ]
    adv_rows = [
        [
            r["skill"],
            r["chi2_statistic"] if pd.notna(r["chi2_statistic"]) else "-",
            r["p_value"] if pd.notna(r["p_value"]) else "-",
            r["odds_ratio"] if pd.notna(r["odds_ratio"]) else "-",
            r["test_used"],
            "Yes" if r["significant"] else "No",
            r["direction"],
            "Yes" if r["low_expected_frequency_warning"] else "No",
        ]
        for _, r in role_method_df.sort_values("p_value", na_position="last").iterrows()
    ]
    st.markdown(render_custom_table(adv_headers, adv_rows), unsafe_allow_html=True)

st.markdown("**Distinctiveness vs. frequency-only ranking (divergence check)**")
st.caption(
    "Confirms the test adds information beyond the plain frequency baseline: low "
    "agreement means the two rankings disagree meaningfully, i.e. the distinctiveness "
    "test is not redundant with simple frequency counting."
)
div_rows = [
    [
        r["role_name"], METHOD_LABELS.get(r["method"], r["method"]),
        agreement_label(r["spearman_rho"]),
        f"{r['top_k_overlap_count']}/{r['top_k']}",
        f"{r['top_k_overlap_pct']}%" if pd.notna(r["top_k_overlap_pct"]) else "-",
    ]
    for _, r in divergence_df.iterrows()
]
st.markdown(
    render_custom_table(["Role", "Method", "Agreement with frequency ranking", "Top-K Overlap", "Overlap %"], div_rows),
    unsafe_allow_html=True,
)

st.markdown("**Ranking stability under resampling**")
st.caption(
    "Each role's top distinctive skills are recomputed on repeated bootstrap "
    "resamples of the job postings. A high stability % means that skill keeps "
    "showing up as distinctive regardless of exactly which postings were sampled; "
    "a low % means the ranking may still be an artifact of this particular sample."
)
if stability_summary_df.empty:
    st.info("No roles had any distinctive skills to test for stability.")
else:
    stab_rows = [
        [
            r["role_name"], METHOD_LABELS.get(r["method"], r["method"]),
            r["n_resamples"], r["top_k"], stability_label(r["mean_top_k_stability_pct"]),
        ]
        for _, r in stability_summary_df.iterrows()
    ]
    st.markdown(
        render_custom_table(["Role", "Method", "Resamples", "Top-K", "Reliability (Mean Stability %)"], stab_rows),
        unsafe_allow_html=True,
    )
    with st.expander("Per-skill stability detail"):
        skill_stab_rows = [
            [
                r["role_name"], METHOD_LABELS.get(r["method"], r["method"]), r["skill"],
                r["times_in_top_k"], r["n_resamples"], stability_label(r["stability_pct"]),
            ]
            for _, r in stability_df.iterrows()
        ]
        st.markdown(
            render_custom_table(
                ["Role", "Method", "Skill", "Times in Top-K", "Resamples", "Reliability"], skill_stab_rows
            ),
            unsafe_allow_html=True,
        )

st.download_button(
    label="Download skill distinctiveness CSV",
    data=distinct_df.to_csv(index=False, encoding="utf-8"),
    file_name="skill_distinctiveness.csv",
    mime="text/csv",
)

# Part 3: output audit

st.divider()
st.subheader("Output audit")
st.caption(
    "Checks the files this analysis just produced against the job postings, "
    "using independently written counting code and the textbook chi-square / "
    "Fisher formulas. It reports how many checks ran and exactly which role, "
    "skill, method and field failed, if any."
)

if st.button("Re-run output audit") or (st.session_state.audit_result is None and not st.session_state.audit_failed):
    from src.roles.verify_output import run_audit

    with st.spinner("Auditing the output files..."):
        try:
            st.session_state.audit_result = run_audit(
                role_df,
                current_dir / "data" / "analysis",
                significance_level=used_level,
            )
        except Exception as e:
            st.session_state.audit_result = None
            st.session_state.audit_failed = True
            st.error(f"Output audit could not run: {e}")

audit = st.session_state.get("audit_result")
if audit:
    summary = audit["summary"]
    col1, col2, col3 = st.columns(3)
    col1.metric("Checks executed", f"{summary['checks_executed']:,}")
    col2.metric("Checks failed", f"{summary['checks_failed']:,}")
    col3.metric("Result", "PASS" if summary["passed"] else "FAIL")

    group_rows = [
        [g["group"], g["executed"], g["failed"], "OK" if g["failed"] == 0 else "FAIL"]
        for g in summary["by_group"]
    ]
    st.markdown(
        render_custom_table(["Check group", "Checks", "Failed", "Status"], group_rows),
        unsafe_allow_html=True,
    )

    failures = audit["checks"][audit["checks"]["status"] == "FAIL"]
    if not failures.empty:
        st.error(f"{len(failures)} check(s) failed. The first 50 are shown below.")
        st.dataframe(
            failures[["file", "role", "skill", "method", "field", "expected", "actual"]].head(50),
            hide_index=True,
        )

    st.download_button(
        label="Download full audit report CSV",
        data=audit["checks"].to_csv(index=False, encoding="utf-8"),
        file_name="audit_report.csv",
        mime="text/csv",
    )