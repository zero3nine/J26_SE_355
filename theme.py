"""
Theme and Component Definitions for the IT Job Advertisement Data Collector.
Contains styling variables and reusable custom HTML components.
"""

# Streamlit sets color-scheme on the app view when its appearance changes.
THEME_CSS = """
<style>

:root {
    --admin-card: light-dark(#ffffff, #172232);
    --admin-ink: light-dark(#202124, #edf3ff);
    --admin-muted: light-dark(#526174, #b2c1d5);
    --admin-line: light-dark(#d7e0ed, #34455e);
    --admin-primary: light-dark(#0b57d0, #a8c7fa);
    --admin-action: light-dark(#0b57d0, #254f8e);
    --admin-soft: light-dark(#eaf1fb, #233854);
    --admin-input: light-dark(#f8fafd, #121d2e);
    --admin-positive: light-dark(#196739, #92d6aa);
    --admin-positive-bg: light-dark(#e6f4ea, #163527);
    --admin-negative: light-dark(#a32922, #ffb4ac);
    --admin-negative-bg: light-dark(#fce8e6, #472823);
    --admin-warning: light-dark(#705000, #f7cd77);
    --admin-warning-bg: light-dark(#fef3d6, #392d16);
    --admin-warning-line: light-dark(#d9b962, #8e7139);
    --admin-purple: light-dark(#8430a8, #deb5fb);
    --admin-purple-bg: light-dark(#f3eafa, #35274a);
    --admin-indigo: light-dark(#5145a5, #bfb7ff);
    --admin-teal: light-dark(#087b73, #7ad5ca);
}


/* Main layouts and margins */
.stApp {
    font-family: Arial, "Segoe UI", sans-serif !important;
}

/* Make headers premium */
h1, h2, h3, h4, h5, h6 {
    font-family: Arial, "Segoe UI", sans-serif !important;
    font-weight: 600 !important;
    color: var(--admin-ink) !important;
    letter-spacing: -0.02em !important;
}

/* Custom header layout styling */
.header-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--admin-line);
    padding-bottom: 16px;
    margin-bottom: 24px;
}
.header-title-block {
    display: flex;
    flex-direction: column;
}
.header-tagline {
    color: var(--admin-muted);
    font-size: 14px;
    margin-top: 4px;
}
.status-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    background-color: var(--admin-soft);
    border: 1px solid var(--admin-line);
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    color: var(--admin-positive);
    font-weight: 500;
}
.status-dot {
    width: 8px;
    height: 8px;
    background-color: var(--admin-positive);
    border-radius: 50%;
    box-shadow: 0 0 8px var(--admin-positive);
    animation: none;
}

@keyframes pulse {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

/* Style the default stTabs as pill segmented bar */
div[data-testid="stTabBar"] {
    background-color: var(--admin-card) !important;
    border-radius: 12px !important;
    padding: 6px !important;
    border: 1px solid var(--admin-line) !important;
    margin-bottom: 24px !important;
    gap: 4px !important;
}
div[data-testid="stTabBar"] > button {
    background-color: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    color: var(--admin-muted) !important;
    padding: 10px 20px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    transition: all 0.2s ease !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
}
div[data-testid="stTabBar"] > button:hover {
    color: var(--admin-ink) !important;
    background-color: var(--admin-line) !important;
}
div[data-testid="stTabBar"] > button[aria-selected="true"] {
    background-color: var(--admin-action) !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
}

/* Streamlit tab icons use the button's active text color. */
div[data-testid="stTabBar"] > button:nth-of-type(-n+11)::before {
    content: "";
    flex: 0 0 16px;
    height: 16px;
    background-color: currentColor;
    mask-size: contain;
    mask-repeat: no-repeat;
}
div[data-testid="stTabBar"] > button:nth-of-type(1)::before {
    mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(2)::before {
    mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"></path></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(3)::before {
    mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m11.314 11.314l.707.707M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(4)::before {
    mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><path d="m9 11 2 2 4-4"></path></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(5)::before {
    mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(6)::before {
    mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(7)::before {
    mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><polyline points="16 11 18 13 22 9"></polyline></svg>');
}
div[data-testid="stTabBar"] > button:nth-of-type(8)::before {
    mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(9)::before {
    mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(10)::before {
    mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>');
}

div[data-testid="stTabBar"] > button:nth-of-type(11)::before {
    mask-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>');
}

/* Hide Streamlit default tabs line */
div[data-testid="stTabBar"]::after {
    display: none !important;
}

/* Style cards container */
.console-card {
    background-color: var(--admin-card);
    border: 1px solid var(--admin-line);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.kpi-card {
    background-color: var(--admin-card);
    border: 1px solid var(--admin-line);
    border-left: 4px solid var(--admin-primary);
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.kpi-card:hover {
    transform: translateY(-2px);
    border-color: var(--admin-primary);
}
.kpi-card.scraped {
    border-left-color: var(--admin-positive);
}
.kpi-card.failed {
    border-left-color: var(--admin-negative);
}
.kpi-card.clean {
    border-left-color: var(--admin-purple);
}
.kpi-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--admin-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.kpi-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--admin-ink);
    margin-top: 6px;
    margin-bottom: 4px;
}
.kpi-trend {
    font-size: 11px;
    color: var(--admin-muted);
    display: flex;
    align-items: center;
    gap: 4px;
}
.trend-up {
    color: var(--admin-positive);
}
.trend-neutral {
    color: var(--admin-muted);
}

/* Styled HTML tables */
.table-container {
    width: 100%;
    overflow-x: auto;
    border: 1px solid var(--admin-line);
    border-radius: 8px;
    background-color: var(--admin-card);
    margin-bottom: 16px;
}
table.console-table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 13px;
    color: var(--admin-ink);
}
table.console-table th {
    background-color: var(--admin-line);
    color: var(--admin-muted);
    font-weight: 600;
    padding: 12px 16px;
    border-bottom: 1px solid var(--admin-line);
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.05em;
    position: sticky;
    top: 0;
    z-index: 10;
}
table.console-table td {
    padding: 12px 16px;
    border-bottom: 1px solid var(--admin-line);
    vertical-align: middle;
}
table.console-table tr:nth-child(even) {
    background-color: var(--admin-soft);
}
table.console-table tr:hover {
    background-color: var(--admin-line);
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
    background-color: var(--admin-positive-bg);
    color: var(--admin-positive);
}
.status-pill.partial {
    background-color: var(--admin-soft);
    color: var(--admin-primary);
}
.status-pill.warning {
    background-color: var(--admin-warning-bg);
    color: var(--admin-warning);
}
.status-pill.error {
    background-color: var(--admin-negative-bg);
    color: var(--admin-negative);
}
.status-pill.info {
    background-color: var(--admin-soft);
    color: var(--admin-muted);
}

/* Monospace code / link icons */
.icon-link {
    color: var(--admin-primary);
    text-decoration: none;
    font-weight: bold;
    display: inline-flex;
    align-items: center;
}
.icon-link:hover {
    text-decoration: underline;
    color: var(--admin-primary);
}

/* Terminal Console View styling */
.terminal {
    background-color: var(--admin-input);
    border: 1px solid var(--admin-line);
    border-radius: 8px;
    padding: 16px;
    font-family: ui-monospace, Consolas, monospace;
    font-size: 12px;
    color: var(--admin-primary);
    height: 250px;
    overflow-y: auto;
    box-shadow: none;
}
.terminal-line {
    margin-bottom: 6px;
    line-height: 1.4;
    white-space: pre-wrap;
}
.terminal-line-time {
    color: var(--admin-muted);
    margin-right: 8px;
}
.terminal-line-success {
    color: var(--admin-positive);
}
.terminal-line-error {
    color: var(--admin-negative);
}
.terminal-line-info {
    color: var(--admin-primary);
}

/* Info banner styling */
.info-banner {
    background-color: var(--admin-soft);
    border: 1px solid var(--admin-line);
    border-left: 4px solid var(--admin-warning);
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    color: var(--admin-ink);
    font-size: 13px;
}
.info-banner svg {
    color: var(--admin-warning);
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
    background-color: var(--admin-card);
    border: 1px solid var(--admin-line);
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    position: relative;
}
.funnel-step-title {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--admin-muted);
    margin-bottom: 8px;
    font-weight: 600;
}
.funnel-step-value {
    font-size: 24px;
    font-weight: 700;
    color: var(--admin-ink);
    margin-bottom: 6px;
}
.funnel-step-sub {
    font-size: 11px;
    color: var(--admin-negative);
}
.funnel-step-sub.success {
    color: var(--admin-positive);
}
.funnel-arrow {
    display: flex;
    align-items: center;
    color: var(--admin-line);
    font-size: 20px;
    font-weight: bold;
}
.funnel-bar-container {
    width: 100%;
    background-color: var(--admin-line);
    height: 6px;
    border-radius: 3px;
    margin-top: 10px;
    overflow: hidden;
}
.funnel-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--admin-primary), var(--admin-primary));
    border-radius: 3px;
}

/* Modern Document frame for Markdown Reports */
.document-frame {
    background-color: var(--admin-input);
    border: 1px solid var(--admin-line);
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
    background-color: var(--admin-soft);
    border: 1px solid var(--admin-line);
    border-radius: 8px;
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: border-color 0.2s ease;
}
.queue-item:hover {
    border-color: var(--admin-line);
}
.queue-host {
    font-family: ui-monospace, Consolas, monospace;
    font-size: 13px;
    color: var(--admin-ink);
    font-weight: 500;
}
.queue-meta {
    font-size: 11px;
    color: var(--admin-muted);
}

/* Styled override and validation list */
.validation-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 20px;
}
.validation-row {
    background-color: var(--admin-card);
    border: 1px solid var(--admin-line);
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
    color: var(--admin-ink);
    font-size: 13px;
    width: 200px;
}
.validation-details {
    color: var(--admin-muted);
    font-size: 12px;
}

/* Override Panel styling */
.action-panel {
    background-color: var(--admin-soft); /* Blue action tint */
    border: 1px solid var(--admin-primary);
    border-radius: 8px;
    padding: 16px;
    margin-top: 16px;
}
.action-panel-title {
    color: var(--admin-primary);
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
    background-color: var(--admin-line);
    color: var(--admin-ink);
    border: 1px solid var(--admin-line);
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
}
.chip.blue {
    background-color: var(--admin-soft);
    color: var(--admin-primary);
    border-color: rgba(59, 130, 246, 0.2);
}
.chip.purple {
    background-color: var(--admin-purple-bg);
    color: var(--admin-purple);
    border-color: rgba(139, 92, 246, 0.2);
}
.chip.amber {
    background-color: var(--admin-warning-bg);
    color: var(--admin-warning);
    border-color: rgba(245, 158, 11, 0.2);
}

/* Native surfaces and widgets use .streamlit/config.toml. */
[data-testid="stMainBlockContainer"] { padding-top: 2.5rem; padding-bottom: 3rem; }
[data-testid="stTabs"] [role="tablist"]:not([data-testid="stTabBar"]) [role="tab"][aria-selected="true"] {
    color: var(--admin-primary) !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #edf3ff !important; }
[data-testid="stSidebarNav"] a { color: #edf3ff; border-radius: 10px; margin: 3px 0; }
[data-testid="stSidebarNav"] a:hover { background: #ffffff14; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: #d3e3fd; color: #062e6f; }
[data-testid="stSidebarNav"] a[aria-current="page"] span { color: #062e6f; }
[data-testid="stMetric"] {
    background: var(--admin-card); border: 1px solid var(--admin-line);
    border-radius: 14px; padding: 16px;
}
[data-testid="stExpander"], [data-testid="stFileUploader"] {
    border-radius: 12px;
}
.stApp a { text-underline-offset: 3px; }
.stApp :is(button, a, input, textarea, select, summary):focus-visible {
    outline: 3px solid var(--admin-primary) !important; outline-offset: 3px;
}
[data-testid="stSidebar"] :is(button, a):focus-visible { outline-color: #c2e7ff !important; }
.console-card, .kpi-card, .document-frame {
    border-radius: 16px;
    box-shadow: 0 3px 12px #143b6b0a;
}
.status-indicator { background: var(--admin-positive-bg); }
.info-banner { background: var(--admin-warning-bg); border-color: var(--admin-warning-line); }
.info-banner-content { color: var(--admin-warning); }
.header-container { gap: 16px; flex-wrap: wrap; }
.header-title-block { min-width: 0; }
.header-title-block h1 { overflow-wrap: anywhere; }
.validation-name { flex-shrink: 0; }
.queue-item { gap: 12px; flex-wrap: wrap; }
.queue-meta { overflow-wrap: anywhere; }
/* Keep multi-column HTML summaries and pipeline stages usable on narrow screens. */
@media (max-width: 900px) {
    [style*="grid-template-columns: repeat(4"],
    [style*="grid-template-columns: repeat(5"] { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
    .funnel-container { flex-wrap: wrap; }
    .funnel-step { flex: 1 1 180px; }
    .funnel-arrow { display: none; }
}
@media (max-width: 600px) {
    [data-testid="stMainBlockContainer"] { padding: 1.5rem 1rem; }
    .header-title-block h1 { font-size: 22px !important; }
    .info-banner { align-items: flex-start; }
    .validation-row { flex-wrap: wrap; }
    .validation-name { width: auto; }
    .document-frame { padding: 16px; }
    .console-table th, .console-table td { padding: 10px 12px; }
}
@media (prefers-reduced-motion: reduce) {
    .kpi-card, .queue-item { transition: none; }
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
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 24px;">
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
                <span class="trend-up" style="color: var(--admin-purple);">✨ Standardized exports</span>
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
