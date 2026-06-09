APP_CSS = """
<style>
:root { --bg:#f6f7fb; --card:#ffffff; --text:#111827; --muted:#5b6472; --line:#d9dee8; --blue:#2563eb; --orange:#f97316; }
.stApp { background: var(--bg); color: var(--text); }
section[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid var(--line); }
h1,h2,h3,h4,h5,h6,p,label,span,div { color: var(--text); }
.hero { padding:28px 30px; background:linear-gradient(135deg,#ffffff 0%,#eef4ff 100%); border:1px solid var(--line); border-radius:24px; margin-bottom:20px; box-shadow:0 10px 24px rgba(15,23,42,.06); }
.hero-title { font-size:44px; font-weight:850; letter-spacing:-1.4px; color:#0f172a; }
.hero-subtitle { color:#475569; font-size:16px; line-height:1.6; max-width:1120px; }
.metric-card { background:var(--card); padding:18px; border-radius:18px; border:1px solid var(--line); box-shadow:0 8px 20px rgba(15,23,42,.05); }
.metric-label { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }
.metric-value { color:var(--text); font-size:30px; font-weight:850; margin-top:5px; }
.metric-note { color:var(--muted); font-size:13px; margin-top:4px; }
.panel { background:var(--card); border:1px solid var(--line); border-radius:18px; padding:18px; color:var(--text); line-height:1.55; box-shadow:0 8px 20px rgba(15,23,42,.04); }
.status-pill { display:inline-block; padding:5px 11px; border-radius:999px; font-size:12px; font-weight:700; margin-right:6px; border:1px solid var(--line); background:#f8fafc; color:#111827; }
.pill-ok { background:#ecfdf5; border-color:#a7f3d0; color:#047857; }
.pill-warn { background:#fffbeb; border-color:#fde68a; color:#92400e; }
.pill-danger { background:#fef2f2; border-color:#fecaca; color:#b91c1c; }
.pill-blue { background:#eff6ff; border-color:#bfdbfe; color:#1d4ed8; }
.evidence { background:#ffffff; border:1px solid var(--line); border-left:5px solid var(--blue); border-radius:14px; padding:14px; margin:8px 0; color:var(--text); }
div.stButton > button { background:var(--orange)!important; color:white!important; border:0!important; border-radius:12px!important; font-weight:800!important; }
div.stDownloadButton > button { background:var(--blue)!important; color:white!important; border:0!important; border-radius:12px!important; font-weight:800!important; }
[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:14px; overflow:hidden; }
</style>
"""
