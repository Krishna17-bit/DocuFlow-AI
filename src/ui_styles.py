APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg-primary: #f8fafc;
    --bg-card: #ffffff;
    --border-color: #e2e8f0;
    --text-main: #0f172a;
    --text-muted: #64748b;
    --accent-blue: #4f46e5;
    --accent-teal: #0d9488;
    --accent-orange: #ea580c;
}

/* Base Body Styles */
.stApp {
    background: var(--bg-primary);
    color: var(--text-main);
    font-family: 'Plus Jakarta Sans', sans-serif;
}

section[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid var(--border-color);
}

/* Typography & Titles */
h1, h2, h3, h4, h5, h6, p, label, span, div {
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* Premium Gradient Hero Panel */
.hero {
    padding: 36px 40px;
    background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 50%, #e0e7ff 100%);
    border: 1px solid var(--border-color);
    border-radius: 24px;
    margin-bottom: 28px;
    box-shadow: 0 10px 30px -10px rgba(79, 70, 229, 0.1);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.hero:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 35px -8px rgba(79, 70, 229, 0.15);
}

.hero-title {
    font-size: 48px;
    font-weight: 800;
    letter-spacing: -1.6px;
    background: linear-gradient(135deg, #0f172a 0%, #4f46e5 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-subtitle {
    color: var(--text-muted);
    font-size: 16px;
    line-height: 1.6;
    margin-top: 8px;
}

/* Metric Cards with subtle hover animation */
.metric-card {
    background: var(--bg-card);
    padding: 22px;
    border-radius: 20px;
    border: 1px solid var(--border-color);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.02);
    border-color: #cbd5e1;
}

.metric-label {
    color: var(--text-muted);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .1em;
}

.metric-value {
    color: var(--text-main);
    font-size: 32px;
    font-weight: 800;
    margin-top: 6px;
}

.metric-note {
    color: var(--text-muted);
    font-size: 13px;
    margin-top: 4px;
}

/* General Custom Panels */
.panel {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 20px;
    padding: 22px;
    color: var(--text-main);
    line-height: 1.6;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
    transition: border-color 0.2s ease;
}

.panel:hover {
    border-color: #cbd5e1;
}

/* Modern Status Pills */
.status-pill {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-right: 8px;
    border: 1px solid var(--border-color);
    background: #f1f5f9;
    color: var(--text-main);
}

.pill-ok { background: #f0fdf4; border-color: #bbf7d0; color: #166534; }
.pill-warn { background: #fffbeb; border-color: #fef08a; color: #854d0e; }
.pill-danger { background: #fef2f2; border-color: #fecaca; color: #991b1b; }
.pill-blue { background: #eff6ff; border-color: #bfdbfe; color: #1e40af; }

/* Citations and Evidence Highlights */
.evidence {
    background: #ffffff;
    border: 1px solid var(--border-color);
    border-left: 6px solid var(--accent-blue);
    border-radius: 16px;
    padding: 16px;
    margin: 10px 0;
    color: var(--text-main);
    font-size: 14px;
    line-height: 1.5;
    box-shadow: 0 2px 4px rgba(0,0,0,0.01);
}

/* Interactive Buttons */
div.stButton > button {
    background: var(--accent-orange) !important;
    color: white !important;
    border: 0 !important;
    border-radius: 14px !important;
    font-weight: 700 !important;
    padding: 10px 24px !important;
    box-shadow: 0 4px 6px -1px rgba(234, 88, 12, 0.2) !important;
    transition: all 0.2s ease !important;
}

div.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 10px 15px -3px rgba(234, 88, 12, 0.3) !important;
}

div.stDownloadButton > button {
    background: var(--accent-blue) !important;
    color: white !important;
    border: 0 !important;
    border-radius: 14px !important;
    font-weight: 700 !important;
    padding: 10px 24px !important;
    box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2) !important;
    transition: all 0.2s ease !important;
}

div.stDownloadButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.3) !important;
}

/* Dataframe & Tables Styling */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border-color);
    border-radius: 16px;
    overflow: hidden;
}
</style>
"""
