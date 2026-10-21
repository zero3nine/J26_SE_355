"""Dashboard page: External Domains."""
import streamlit as st

st.set_page_config(
    page_title="External Domains — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import *  # noqa: F401,F403

render_page_shell()

st.subheader("External vacancy detail links review queue")
queue_path = current_dir / "data" / "external_links_queue.json"
if not queue_path.exists():
    st.info("No external links recorded in the queue.")
else:
    try:
        with open(queue_path, "r", encoding="utf-8") as f:
            queue_data = json.load(f)
    except Exception as e:
        st.error(f"Failed to read queue: {e}")
        queue_data = []

    if not queue_data:
        st.info("External queue is empty.")
    else:
        df_queue = pd.DataFrame(queue_data)

        # Display domain queue as sleek card list
        st.markdown('<div class="queue-list">', unsafe_allow_html=True)
        for idx, item in df_queue.iterrows():
            host = item.get("destination_hostname", "")
            status = item.get("review_status", "pending")
            status_style = "warning" if status == "pending" else "success"
            status_pill = make_status_pill(status, status_style)
            source = item.get("source_url", "")
            st.markdown(f"""
            <div class="queue-item">
                <div>
                    <div class="queue-host">{host}</div>
                    <div class="queue-meta">Discovered on: <a href="{source}" target="_blank" style="color:#3B82F6; text-decoration:none;">{source[:80]}...</a></div>
                </div>
                <div>{status_pill}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Domain Approval Action
        pending_hosts = sorted(list(set(
            item["destination_hostname"] for item in queue_data if item.get("review_status") == "pending"
        )))

        if not pending_hosts:
            st.success("All identified external domains have been processed/approved!")
        else:
            st.write("---")
            st.subheader("Approve External Domain")
            with st.container(border=True):
                c_sel, c_act = st.columns([3, 1])
                with c_sel:
                    selected_host = st.selectbox("Select external domain to approve:", pending_hosts, label_visibility="collapsed")
                with c_act:
                    if st.button("Approve Domain", use_container_width=True):
                        from src.security.url_validator import approve_external_domain
                        approve_external_domain(selected_host)
                        st.success(f"Domain '{selected_host}' is approved!")
                        st.rerun()
