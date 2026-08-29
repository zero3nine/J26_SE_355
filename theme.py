"""
Theme and Component Definitions for the IT Job Advertisement Data Collector.
Contains styling variables and reusable custom HTML components.
"""

# Custom CSS for modern dark data-ops style dashboard
THEME_CSS = """
<style>
/* Load Geist and Inter font family */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Geist+Mono:wght@300;400;500;600&display=swap');

/* Main layouts and margins */
.stApp {
    background-color: #0B0F19 !important;
    color: #F8FAFC !important;
    font-family: 'Inter', sans-serif !important;
}

/* Make headers premium */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    color: #F8FAFC !important;
    letter-spacing: -0.02em !important;
}

/* Custom header layout styling */
.header-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #1E293B;
    padding-bottom: 16px;
    margin-bottom: 24px;
}
.header-title-block {
    display: flex;
    flex-direction: column;
}
.header-tagline {
    color: #94A3B8;
    font-size: 14px;
    margin-top: 4px;
}
.status-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    background-color: #161D30;
    border: 1px solid #1E293B;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    color: #10B981;
    font-weight: 500;
}
.status-dot {
    width: 8px;
    height: 8px;
    background-color: #10B981;
    border-radius: 50%;
    box-shadow: 0 0 8px #10B981;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

/* Style the default stTabs as pill segmented bar */
div[data-testid="stTabBar"] {
    background-color: #111827 !important;
    border-radius: 12px !important;
    padding: 6px !important;
    border: 1px solid #1E293B !important;
    margin-bottom: 24px !important;
    gap: 4px !important;
}
div[data-testid="stTabBar"] > button {
    background-color: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    color: #94A3B8 !important;
    padding: 10px 20px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    transition: all 0.2s ease !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
}
div[data-testid="stTabBar"] > button:hover {
    color: #F8FAFC !important;
    background-color: #1E293B !important;
}
div[data-testid="stTabBar"] > button[aria-selected="true"] {
    background-color: #3B82F6 !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
}

/* Clean SVG Icon attachments for Streamlit Tabs */
div[data-testid="stTabBar"] > button:nth-of-type(1)::before {
    content: "";
    width: 16px;
    height: 16px;
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%2394A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>');
    background-size: contain;
    background-repeat: no-repeat;
    opacity: 0.8;
}
div[data-testid="stTabBar"] > button[aria-selected="true"]:nth-of-type(1)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(2)::before {
    content: "";
    width: 16px;
    height: 16px;
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%2394A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"></path></svg>');
    background-size: contain;
    background-repeat: no-repeat;
    opacity: 0.8;
}
div[data-testid="stTabBar"] > button[aria-selected="true"]:nth-of-type(2)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"></path></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(3)::before {
    content: "";
    width: 16px;
    height: 16px;
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%2394A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m11.314 11.314l.707.707M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"></svg>');
    background-size: contain;
    background-repeat: no-repeat;
    opacity: 0.8;
}
div[data-testid="stTabBar"] > button[aria-selected="true"]:nth-of-type(3)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m11.314 11.314l.707.707M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(4)::before {
    content: "";
    width: 16px;
    height: 16px;
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%2394A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><path d="m9 11 2 2 4-4"></path></svg>');
    background-size: contain;
    background-repeat: no-repeat;
    opacity: 0.8;
}
div[data-testid="stTabBar"] > button[aria-selected="true"]:nth-of-type(4)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><path d="m9 11 2 2 4-4"></path></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(5)::before {
    content: "";
    width: 16px;
    height: 16px;
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%2394A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>');
    background-size: contain;
    background-repeat: no-repeat;
    opacity: 0.8;
}
div[data-testid="stTabBar"] > button[aria-selected="true"]:nth-of-type(5)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(6)::before {
    content: "";
    width: 16px;
    height: 16px;
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%2394A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>');
    background-size: contain;
    background-repeat: no-repeat;
    opacity: 0.8;
}
div[data-testid="stTabBar"] > button[aria-selected="true"]:nth-of-type(6)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(7)::before {
    content: "";
    width: 16px;
    height: 16px;
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%2394A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><polyline points="16 11 18 13 22 9"></polyline></svg>');
    background-size: contain;
    background-repeat: no-repeat;
    opacity: 0.8;
}
div[data-testid="stTabBar"] > button[aria-selected="true"]:nth-of-type(7)::before {
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><polyline points="16 11 18 13 22 9"></polyline></svg>');
}

/* Hide Streamlit default tabs line */
div[data-testid="stTabBar"]::after {
    display: none !important;
}

/* Style cards container */
.console-card {
    background-color: #111827;
    border: 1px solid #1E293B;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.kpi-card {
    background-color: #111827;
    border: 1px solid #1E293B;
    border-left: 4px solid #3B82F6;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.kpi-card:hover {
    transform: translateY(-2px);
    border-color: #3B82F6;
}
.kpi-card.scraped {
    border-left-color: #10B981;
}
.kpi-card.failed {
    border-left-color: #EF4444;
}
.kpi-card.clean {
    border-left-color: #8B5CF6;
}
.kpi-label {
    font-size: 12px;
    font-weight: 500;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.kpi-value {
    font-size: 28px;
    font-weight: 700;
    color: #F8FAFC;
    margin-top: 6px;
    margin-bottom: 4px;
}
.kpi-trend {
    font-size: 11px;
    color: #94A3B8;
    display: flex;
    align-items: center;
    gap: 4px;
}
.trend-up {
    color: #10B981;
}
.trend-neutral {
    color: #64748B;
}

/* Styled HTML tables */
.table-container {
    width: 100%;
    overflow-x: auto;
    border: 1px solid #1E293B;
    border-radius: 8px;
    background-color: #111827;
    margin-bottom: 16px;
}
table.console-table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 13px;
    color: #E2E8F0;
}
table.console-table th {
    background-color: #1E293B;
    color: #94A3B8;
    font-weight: 600;
    padding: 12px 16px;
    border-bottom: 1px solid #334155;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.05em;
    position: sticky;
    top: 0;
    z-index: 10;
}
table.console-table td {
    padding: 12px 16px;
    border-bottom: 1px solid #1E293B;
    vertical-align: middle;
}
table.console-table tr:nth-child(even) {
    background-color: #161D30;
}
table.console-table tr:hover {
    background-color: #1E293B;
}

/* Status pills for custom table */
.status-pill {
    display: inline-flex;
    align-items: center;
    padding: 3px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
}
.status-pill.success {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10B981;
}
.status-pill.partial {
    background-color: rgba(59, 130, 246, 0.15);
    color: #3B82F6;
}
.status-pill.warning {
    background-color: rgba(245, 158, 11, 0.15);
    color: #F59E0B;
}
.status-pill.error {
    background-color: rgba(239, 68, 68, 0.15);
    color: #EF4444;
}
.status-pill.info {
    background-color: rgba(100, 116, 139, 0.15);
    color: #94A3B8;
}

/* Monospace code / link icons */
.icon-link {
    color: #3B82F6;
    text-decoration: none;
    font-weight: bold;
    display: inline-flex;
    align-items: center;
}
.icon-link:hover {
    text-decoration: underline;
    color: #60A5FA;
}

/* Terminal Console View styling */
.terminal {
    background-color: #020617;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 16px;
    font-family: 'Geist Mono', monospace;
    font-size: 12px;
    color: #38BDF8;
    height: 250px;
    overflow-y: auto;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.6);
}
.terminal-line {
    margin-bottom: 6px;
    line-height: 1.4;
    white-space: pre-wrap;
}
.terminal-line-time {
    color: #64748B;
    margin-right: 8px;
}
.terminal-line-success {
    color: #4ADE80;
}
.terminal-line-error {
    color: #F87171;
}
.terminal-line-info {
    color: #93C5FD;
}

/* Info banner styling */
.info-banner {
    background-color: #161D30;
    border: 1px solid #1E293B;
    border-left: 4px solid #F59E0B;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    color: #E2E8F0;
    font-size: 13px;
}
.info-banner svg {
    color: #F59E0B;
    flex-shrink: 0;
}
.info-banner-content {
    flex-grow: 1;
}

/* Funnel Pipeline Visualisation styling */
.funnel-container {
    display: flex;
    justify-content: space-between;
    align-items: stretch;
    gap: 8px;
    margin-bottom: 24px;
    width: 100%;
}
.funnel-step {
    flex: 1;
    background-color: #111827;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    position: relative;
}
.funnel-step-title {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94A3B8;
    margin-bottom: 8px;
    font-weight: 600;
}
.funnel-step-value {
    font-size: 24px;
    font-weight: 700;
    color: #F8FAFC;
    margin-bottom: 6px;
}
.funnel-step-sub {
    font-size: 11px;
    color: #EF4444;
}
.funnel-step-sub.success {
    color: #10B981;
}
.funnel-arrow {
    display: flex;
    align-items: center;
    color: #334155;
    font-size: 20px;
    font-weight: bold;
}
.funnel-bar-container {
    width: 100%;
    background-color: #1E293B;
    height: 6px;
    border-radius: 3px;
    margin-top: 10px;
    overflow: hidden;
}
.funnel-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #3B82F6, #6366F1);
    border-radius: 3px;
}

/* Modern Document frame for Markdown Reports */
.document-frame {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 32px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    margin-top: 16px;
    max-height: 500px;
    overflow-y: auto;
}

/* Domain queue list style */
.queue-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 16px;
}
.queue-item {
    background-color: #161D30;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: border-color 0.2s ease;
}
.queue-item:hover {
    border-color: #334155;
}
.queue-host {
    font-family: 'Geist Mono', monospace;
    font-size: 13px;
    color: #E2E8F0;
    font-weight: 500;
}
.queue-meta {
    font-size: 11px;
    color: #94A3B8;
}

/* Styled override and validation list */
.validation-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 20px;
}
.validation-row {
    background-color: #111827;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.validation-icon {
    font-size: 16px;
    flex-shrink: 0;
}
.validation-name {
    font-weight: 600;
    color: #F8FAFC;
    font-size: 13px;
    width: 200px;
}
.validation-details {
    color: #94A3B8;
    font-size: 12px;
}

/* Override Panel styling */
.action-panel {
    background-color: #1E1B4B; /* Deep indigo warning tint */
    border: 1px solid #4338CA;
    border-radius: 8px;
    padding: 16px;
    margin-top: 16px;
}
.action-panel-title {
    color: #C7D2FE;
    font-weight: 600;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Tag chips styling */
.chip-container {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
}
.chip {
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1px solid #334155;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
}
.chip.blue {
    background-color: rgba(59, 130, 246, 0.1);
    color: #93C5FD;
    border-color: rgba(59, 130, 246, 0.2);
}
.chip.purple {
    background-color: rgba(139, 92, 246, 0.1);
    color: #C084FC;
    border-color: rgba(139, 92, 246, 0.2);
}
.chip.amber {
    background-color: rgba(245, 158, 11, 0.1);
    color: #FCD34D;
    border-color: rgba(245, 158, 11, 0.2);
}
</style>
"""

# Utility helper to clean leading whitespaces from HTML lines to prevent markdown indented code blocks bug
def clean_html(html_str):
    return "\n".join(line.strip() for line in html_str.split("\n"))

# Reusable header component
def render_header():
    return clean_html(f"""
    <div class="header-container">
        <div class="header-title-block">
            <h1 style="margin:0;font-size:26px;">IT Job Advertisement Data Collector</h1>
            <div class="header-tagline">Multi-site academic console for scraping, cleaning, and preparing IT job boards data</div>
        </div>
        <div class="status-indicator">
            <div class="status-dot"></div>
            <span>System Active</span>
        </div>
    </div>
    """)

# Reusable info banner/ssrf notice
def render_ssrf_banner():
    return clean_html("""
    <div class="info-banner">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
        <div class="info-banner-content">
            <strong>Security Notice:</strong> Only submit publicly accessible and permitted job detail links.
            Local/private IP addresses are blocked, and unknown external hosts require administrator domain approval.
        </div>
    </div>
    """)

# Render KPI cards grid
def render_kpis(submitted, scraped, failed, clean):
    return clean_html(f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
        <div class="kpi-card">
            <div class="kpi-label">Submitted URLs</div>
            <div class="kpi-value">{submitted}</div>
            <div class="kpi-trend">
                <span class="trend-neutral">⚡ Active queue count</span>
            </div>
        </div>
        <div class="kpi-card scraped">
            <div class="kpi-label">Successfully Scraped</div>
            <div class="kpi-value">{scraped}</div>
            <div class="kpi-trend">
                <span class="trend-up">↑ Scraped successfully</span>
            </div>
        </div>
        <div class="kpi-card failed">
            <div class="kpi-label">Failed / Skipped</div>
            <div class="kpi-value">{failed}</div>
            <div class="kpi-trend">
                <span>🔴 Connection or parse error</span>
            </div>
        </div>
        <div class="kpi-card clean">
            <div class="kpi-label">Clean Records</div>
            <div class="kpi-value">{clean}</div>
            <div class="kpi-trend">
                <span class="trend-up" style="color: #A78BFA;">✨ Standardized exports</span>
            </div>
        </div>
    </div>
    """)

# Render a styled HTML table from data list (to avoid canvas-based st.dataframe visual limitations)
def render_custom_table(headers, rows):
    """
    headers: list of string column names
    rows: list of lists representing row cells
    """
    thead_content = "".join(f"<th>{h}</th>" for h in headers)
    tbody_content = ""
    for row in rows:
        row_content = ""
        for cell in row:
            row_content += f"<td>{cell}</td>"
        tbody_content += f"<tr>{row_content}</tr>"
        
    return clean_html(f"""
    <div class="table-container">
        <table class="console-table">
            <thead>
                <tr>{thead_content}</tr>
            </thead>
            <tbody>
                {tbody_content}
            </tbody>
        </table>
    </div>
    """)

# Render status pill inside table cell helper
def make_status_pill(status_text, style="info"):
    """
    style: success, partial, warning, error, info
    """
    return f'<span class="status-pill {style}">{status_text}</span>'

# Make link icon helper
def make_link_icon(url):
    return f'<a href="{url}" target="_blank" class="icon-link">🔗 <span style="font-size: 11px; margin-left: 2px;">Link</span></a>'

# Render Terminal logging panel
def render_terminal(log_lines):
    lines_html = ""
    for line in log_lines:
        if "Scraping" in line or "Fetching" in line:
            line_class = "terminal-line-info"
        elif "Error" in line or "Failed" in line or "Rejected" in line or "🔴" in line:
            line_class = "terminal-line-error"
        elif "success" in line.lower() or "completed" in line.lower() or "✅" in line:
            line_class = "terminal-line-success"
        else:
            line_class = "terminal-line-default"
            
        lines_html += f'<div class="terminal-line {line_class}">{line}</div>'
        
    return clean_html(f"""
    <div class="terminal">
        {lines_html}
    </div>
    """)

# Render step pipeline funnel
def render_pipeline_funnel(stats):
    total_raw = stats.get('total_raw_records', 0)
    title_exclusions = stats.get('filtered_short_title', 0)
    desc_exclusions = stats.get('filtered_short_desc', 0)
    date_exclusions = stats.get('filtered_future_date', 0)
    total_excl = title_exclusions + desc_exclusions + date_exclusions
    
    dedup_1 = stats.get('dedup_step1_removed', 0)
    dedup_2 = stats.get('dedup_step2_removed', 0)
    total_dedup = dedup_1 + dedup_2
    
    final_int = stats.get('final_internal_records', 0)
    final_team = stats.get('final_team_records', 0)
    
    # Calculate percentages
    pct_filtered = 100
    pct_dedup = int((total_raw - total_excl) / total_raw * 100) if total_raw > 0 else 0
    pct_final = int(final_int / total_raw * 100) if total_raw > 0 else 0
    pct_team = int(final_team / total_raw * 100) if total_raw > 0 else 0
    
    return clean_html(f"""
    <div class="funnel-container">
        <div class="funnel-step">
            <div class="funnel-step-title">1. Raw Input</div>
            <div class="funnel-step-value">{total_raw}</div>
            <div class="funnel-step-sub success">Initial batch</div>
            <div class="funnel-bar-container">
                <div class="funnel-bar-fill" style="width: 100%;"></div>
            </div>
        </div>
        
        <div class="funnel-arrow">➔</div>
        
        <div class="funnel-step">
            <div class="funnel-step-title">2. Filtering</div>
            <div class="funnel-step-value">{total_raw - total_excl}</div>
            <div class="funnel-step-sub">-{total_excl} exclusions</div>
            <div class="funnel-bar-container">
                <div class="funnel-bar-fill" style="width: {pct_dedup}%;"></div>
            </div>
        </div>
        
        <div class="funnel-arrow">➔</div>
        
        <div class="funnel-step">
            <div class="funnel-step-title">3. Deduplication</div>
            <div class="funnel-step-value">{final_int}</div>
            <div class="funnel-step-sub">-{total_dedup} duplicates</div>
            <div class="funnel-bar-container">
                <div class="funnel-bar-fill" style="width: {pct_final}%;"></div>
            </div>
        </div>
        
        <div class="funnel-arrow">➔</div>
        
        <div class="funnel-step">
            <div class="funnel-step-title">4. Final Export</div>
            <div class="funnel-step-value">{final_team}</div>
            <div class="funnel-step-sub success">{pct_team}% Yield</div>
            <div class="funnel-bar-container">
                <div class="funnel-bar-fill" style="width: {pct_team}%;"></div>
            </div>
        </div>
    </div>
    """)

# Validation checklist items builder
def render_validation_checklist(report_runs):
    checklist_html = '<div class="validation-list">'
    for check in report_runs:
        status = check["status"]
        if status == "PASS":
            icon = "✅"
            pill = make_status_pill("PASS", "success")
        elif status == "WARNING":
            icon = "⚠️"
            pill = make_status_pill("WARN", "warning")
        else:
            icon = "❌"
            pill = make_status_pill("FAIL", "error")
            
        checklist_html += f"""
        <div class="validation-row">
            <div class="validation-icon">{icon}</div>
            <div class="validation-name">{check['name']}</div>
            <div style="flex-grow: 1;" class="validation-details">{check['details']}</div>
            <div>{pill}</div>
        </div>
        """
    checklist_html += '</div>'
    return clean_html(checklist_html)
