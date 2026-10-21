"""Dashboard page: Regional Analysis."""
import streamlit as st

st.set_page_config(
    page_title="Regional Analysis — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *  # noqa: F401,F403

render_page_shell()

analysis_mode = st.radio(
    "Analytical Scope",
    [
        "Comparative Regional Market Analysis (Sri Lanka vs. India, Singapore, Malaysia)",
        "Single-Batch Role Segmentation",
    ],
    horizontal=True,
    key="regional_vs_role_mode",
)

if "Comparative Regional" in analysis_mode:
    render_regional_analysis_view(current_dir)
else:
    st.subheader("Role based skill demand segmentation")
    st.caption(
        "Groups job postings by IT role, then shows how often each skill "
        "appears within that role, separating skills that are core to "
        "the role from ones that only show up in a few postings."
    )

    if not st.session_state.extraction_completed or st.session_state.extracted_df.empty:
        st.info(
            "Please run skill extraction on the 'Extract Skills' tab first -- "
            "role analysis builds on top of its lexical_skills/semantic_skills output."
        )
    else:
        if st.button("Classify roles & analyze skill demand"):
            with st.spinner("Classifying job postings into role categories..."):
                try:
                    role_df = classify_roles(st.session_state.extracted_df)
                    freq_df = build_role_skill_frequency_table(role_df)

                    st.session_state.role_classified_df = role_df
                    st.session_state.role_skill_freq_df = freq_df
                    st.session_state.role_analysis_completed = True

                    analysis_dir = current_dir / "data" / "analysis"
                    analysis_dir.mkdir(parents=True, exist_ok=True)
                    freq_df.to_csv(
                        analysis_dir / "role_skill_frequencies.csv",
                        index=False,
                        encoding="utf-8",
                    )

                    st.success("Role classification and skill demand analysis complete.")
                except Exception as e:
                    st.error(f"Role analysis failed: {e}")

        if st.session_state.role_analysis_completed:
            role_df = st.session_state.role_classified_df
            freq_df = st.session_state.role_skill_freq_df

            st.subheader("Job postings by role category")
            st.bar_chart(role_df["role_name"].value_counts(), horizontal=True, height=400)

            st.subheader("Skill demand by role — lexical vs semantic")
            role_options = sorted(freq_df["role_name"].unique())

            if not role_options:
                st.info("No roles were classified yet -- this can happen with a very small sample.")
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
                    st.bar_chart(top_skills, horizontal=True, height=400)

            st.subheader("Skill demand by role table")
            freq_cols = list(freq_df.columns)
            headers = [c.replace("_", " ").title() for c in freq_cols]
            rows = []
            for _, row in freq_df.iterrows():
                row_cells = []
                for col in freq_cols:
                    val = row[col]
                    if col == "pct_of_role":
                        row_cells.append(f"{val}%")
                    else:
                        row_cells.append(str(val))
                rows.append(row_cells)
            st.markdown(render_custom_table(headers, rows), unsafe_allow_html=True)

            csv_role_freq = freq_df.to_csv(index=False, encoding="utf-8")
            st.download_button(
                label="Download role x skill frequency CSV",
                data=csv_role_freq,
                file_name="role_skill_frequencies.csv",
                mime="text/csv",
            )
