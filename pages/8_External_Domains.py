"""Dashboard page: External Domains — Migrated to React."""
import streamlit as st

st.set_page_config(
    page_title="External Domains — IT Job Advertisement Data Collector",
    page_icon="💼",
    layout="wide",
)

from app_shared import render_page_shell  # noqa: F401,F403

render_page_shell()

st.subheader("8. External Domains Review Queue (Migrated to React)")
st.caption("Governance portal for third-party vacancy hostnames discovered during automated link traversal. Approved domains are authorized for cross-site detail extraction.")

st.success("✨ **UI Migration Active:** The modern light-themed **External Domains Review Queue & Management Console** is now live on the React application at [http://localhost:3000](http://localhost:3000) (or [http://127.0.0.1:8000](http://127.0.0.1:8000)).")

st.markdown("""
> **Component Status: Disconnected from Streamlit**  
> In accordance with the partial UI migration requirements, this Streamlit interface has been cleanly disconnected to prevent dual-state mutation and session conflicts.
> All underlying Python security validation (`src.security.url_validator`), SSRF protections, and domain whitelist/blacklist storage mechanisms remain 100% active.
>
> **Active Capabilities in the New React Console:**
> - **External Review Queue:** Card-based review list for all candidate links discovered during multi-site crawling (`data/external_links_queue.json`).
> - **Domain Approval Pipeline:** Seamless authorization calling `approve_external_domain()` to append validated domains to `config/approved_domains.txt`.
> - **Domain Rejection & Blacklisting:** Ability to reject non-job links or permanently blacklist malicious domains in `config/blocked_domains.txt`.
> - **Approved Whitelist Registry:** Searchable inventory of all 20+ pre-approved research job portals with manual domain addition form.
> - **SSRF & Security Notice:** Standardized academic warning banner reinforcing local IP blocking and administrator governance rules.
""")

