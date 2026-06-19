import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import math

st.set_page_config(
    page_title="Monitoring Dedolarisasi ASEAN",
    layout="wide",
    page_icon="\U0001F4C8",
    initial_sidebar_state="expanded",
)

# Auto-refresh tiap 60 detik (opsional, degrade gracefully kalau paket tak ada)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60000, key="auto_refresh")
except Exception:
    pass

# ─── Design tokens + komponen (dark theme ala Notion) ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root{
  /* Palette */
  --bg:#191917; --bg-soft:#211f1e; --surface:#242322; --surface-2:#2b2a28;
  --text:#f5f4f2; --text-soft:rgba(255,255,255,.56); --text-faint:rgba(255,255,255,.32);
  --border:rgba(255,255,255,.10); --border-soft:rgba(255,255,255,.07);
  --shadow:0 1px 2px rgba(0,0,0,.30), 0 4px 14px rgba(0,0,0,.32);
  --blue:#5e9fe8; --orange:#de9255; --red:#e97366;
  --blue-bg:rgba(94,159,232,.12); --yellow-bg:rgba(203,145,47,.10);
  --orange-bg:rgba(222,146,85,.10); --green-bg:rgba(114,188,143,.10);
  --red-bg:rgba(233,115,102,.10); --gray-bg:#322f2d;
  --c-green:#72BC8F; --c-yellow:#EAC26B; --c-red:#E97366;
  /* Accent ganti per-lensa (di-override dari Python) */
  --lens-accent:#5e9fe8; --lens-bg:rgba(94,159,232,.12);
  /* Skala radius & spasi */
  --r:12px; --r-sm:8px; --r-pill:999px;
}

html, body, .stApp, [class*="css"]{ font-family:'Inter', -apple-system, system-ui, sans-serif; }
.stApp{ background:var(--bg) !important; color:var(--text); }
.block-container{ padding-top:22px !important; padding-bottom:64px !important; max-width:1320px !important; }
#MainMenu, header, footer{ visibility:hidden; }
h1,h2,h3,h4,h5,h6,p,span,div,li,label{ color:var(--text); }
.stCaption, .stMarkdown p, [data-testid="stMarkdownContainer"] p{ color:var(--text); }
.stAlert{ background:var(--surface) !important; border:1px solid var(--border-soft) !important; color:var(--text-soft) !important; border-radius:var(--r) !important; }
.ticker .px{ color:var(--text); } .kpi .v{ color:var(--text); }

.section-gap{ height:22px; }

/* Small-caps section label */
.sec-label{ font-size:11px; font-weight:700; letter-spacing:.13em; text-transform:uppercase; color:var(--text-faint); margin:0 0 10px; }

/* Topbar */
.topbar{ display:flex; align-items:flex-start; justify-content:space-between; gap:16px; margin-bottom:4px; }
.dash-title h1{ font-size:23px; font-weight:800; margin:0; letter-spacing:-.02em; }
.dash-title .sub{ color:var(--text-soft); font-size:13px; margin-top:3px; }
.live-badge{ display:inline-flex; align-items:center; font-size:12px; font-weight:600; color:var(--text-soft); }
.live-dot{ width:8px;height:8px;border-radius:50%;background:var(--c-green);display:inline-block;margin-right:6px;
  box-shadow:0 0 0 0 rgba(114,188,143,.6); animation:pulse 1.8s infinite; }
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(114,188,143,.5)}70%{box-shadow:0 0 0 8px rgba(114,188,143,0)}100%{box-shadow:0 0 0 0 rgba(114,188,143,0)}}

/* Lens pill (penanda lensa aktif) */
.lens-pill{ display:inline-flex; align-items:center; gap:8px; padding:8px 14px; border-radius:var(--r-pill);
  background:var(--lens-bg); border:1px solid var(--lens-accent); white-space:nowrap; }
.lens-pill .lp-ico{ font-size:15px; }
.lens-pill .lp-txt{ font-size:12px; font-weight:700; color:var(--lens-accent); letter-spacing:.01em; }
.lens-pill .lp-sub{ font-size:11px; color:var(--text-soft); font-weight:500; }

/* Sidebar */
section[data-testid="stSidebar"]{ background:var(--surface); border-right:1px solid var(--border-soft); min-width:268px; }
section[data-testid="stSidebar"] .stMarkdown{ color:var(--text-soft); }
section[data-testid="stSidebar"] .stRadio label{ font-size:14.5px; font-weight:600; padding:10px 12px; border-radius:var(--r-sm); transition:all .15s ease; }
section[data-testid="stSidebar"] .stRadio label:hover{ background:var(--bg-soft); }
section[data-testid="stSidebar"] .stRadio label:has(input:checked){ background:var(--lens-bg); color:var(--lens-accent); box-shadow:inset 0 0 0 1px var(--lens-accent); }
section[data-testid="stSidebar"] .stRadio label div:first-child{ display:none; }
section[data-testid="stSidebar"] .stButton button{ background:var(--bg); color:var(--text-soft); border:1px solid var(--border-soft); border-radius:var(--r-sm); font-weight:600; transition:all .15s ease; }
section[data-testid="stSidebar"] .stButton button:hover{ border-color:var(--lens-accent); color:var(--text); }
.lens-note{ font-size:12px; line-height:1.55; color:var(--text-soft); background:var(--bg-soft); border:1px solid var(--border-soft);
  border-left:3px solid var(--lens-accent); border-radius:var(--r-sm); padding:11px 13px; margin-top:6px; }
.lens-note b{ color:var(--text); }

/* Callout banner */
.callout{ display:flex; align-items:flex-start; gap:12px; padding:14px 18px; border-radius:var(--r); margin-bottom:16px; }
.callout-warn{ background:var(--orange-bg); border:1px solid rgba(222,146,85,.28); }
.callout-kritis{ background:var(--red-bg); border:1px solid rgba(233,115,102,.28); }
.callout-aman{ background:var(--green-bg); border:1px solid rgba(114,188,143,.28); }
.callout .co-icon{ font-size:18px; flex-shrink:0; margin-top:1px; }
.callout .co-title{ font-size:14px; font-weight:700; }
.callout .co-body{ font-size:12px; color:var(--text-soft); margin-top:2px; line-height:1.5; }

/* Ticker */
.ticker{ display:flex; gap:0; overflow-x:auto; border:1px solid var(--border-soft); border-radius:var(--r);
  background:var(--surface); margin:16px 0; box-shadow:var(--shadow); }
.ticker::-webkit-scrollbar{ height:0; display:none; }
.ticker .tk{ flex:0 0 auto; min-width:112px; padding:11px 16px; border-right:1px solid var(--border-soft); text-align:center; transition:background .15s ease; }
.ticker .tk:hover{ background:var(--surface-2); }
.ticker .tk:last-child{ border-right:none; }
.ticker .sym{ font-size:11px; font-weight:700; color:var(--text-soft); letter-spacing:.02em; }
.ticker .px{ font-size:14px; font-weight:600; font-variant-numeric:tabular-nums; margin-top:3px; }
.ticker .ch{ font-size:11px; font-weight:600; font-variant-numeric:tabular-nums; margin-top:1px; }
.up{ color:var(--c-green); } .down{ color:var(--c-red); } .flat{ color:var(--text-faint); }

/* KPI cards */
.kpi-row{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:6px; }
.kpi{ position:relative; border:1px solid var(--border-soft); border-radius:var(--r); background:var(--surface); box-shadow:var(--shadow); padding:15px 16px; transition:transform .15s ease, border-color .15s ease; overflow:hidden; }
.kpi:hover{ transform:translateY(-2px); border-color:var(--border); }
.kpi.kpi--accent{ border-color:var(--lens-accent); }
.kpi.kpi--accent::before{ content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--lens-accent); }
.kpi .l{ font-size:12px; color:var(--text-soft); font-weight:600; }
.kpi .v{ font-size:27px; font-weight:800; letter-spacing:-.03em; font-variant-numeric:tabular-nums; margin-top:5px; line-height:1.1; }
.kpi .c{ font-size:12px; color:var(--text-soft); margin-top:6px; }

/* Chips */
.chip{ display:inline-block; padding:2px 9px; border-radius:var(--r-pill); font-size:11px; font-weight:700; }
.chip-red{ background:var(--red-bg); color:var(--c-red); }
.chip-orange{ background:var(--orange-bg); color:var(--orange); }
.chip-green{ background:var(--green-bg); color:var(--c-green); }
.chip-blue{ background:var(--blue-bg); color:var(--blue); }
.chip-gray{ background:var(--gray-bg); color:var(--text-soft); }

/* Card header */
.card-h{ font-size:14.5px; font-weight:700; margin:0 0 3px; letter-spacing:-.01em; }
.card-hint{ font-size:12px; color:var(--text-soft); margin:0 0 10px; line-height:1.45; }
[data-testid="stVerticalBlockBorderWrapper"]{ border-radius:var(--r); }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.card-h){ background:var(--surface); border:1px solid var(--border-soft) !important; box-shadow:var(--shadow); }

/* Legend */
.legend{ display:flex; flex-wrap:wrap; gap:14px; margin-top:10px; font-size:12px; color:var(--text-soft); }
.legend span{ display:inline-flex; align-items:center; gap:6px; }
.dot{ width:9px;height:9px;border-radius:50%;display:inline-block; }

/* Alert feed */
.alert{ display:flex; gap:10px; padding:11px; border-radius:var(--r-sm); background:var(--bg-soft); margin-bottom:8px; transition:background .15s ease; }
.alert:hover{ background:var(--surface-2); }
.alert .ic{ width:28px;height:28px;border-radius:8px;display:grid;place-items:center;flex-shrink:0;font-size:13px; }
.alert .msg{ font-size:13px; font-weight:600; line-height:1.35; }
.alert .meta{ font-size:11px; color:var(--text-soft); margin-top:2px; }

/* Ranking list */
.rank{ padding:0; margin:12px 0 0; }
.rank li{ display:flex; justify-content:space-between; font-size:13px; padding:7px 0; border-bottom:1px solid var(--border-soft); list-style:none; }
.rank li:last-child{ border-bottom:none; }
.rank .idr{ font-weight:700; color:var(--lens-accent); }

/* Tabel outlier */
.otable{ width:100%; border-collapse:collapse; }
.otable th{ text-align:left; padding:9px 10px; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--text-faint); border-bottom:1px solid var(--border); }
.otable td{ padding:10px; font-size:13px; border-bottom:1px solid var(--border-soft); }
.otable tbody tr{ transition:background .15s ease; }
.otable tbody tr:hover{ background:var(--bg-soft); }
.otable tr:last-child td{ border-bottom:none; }
</style>
""", unsafe_allow_html=True)

import os

API_BASE = os.getenv("API_BASE", "http://fastapi:8000")
PAIRS = ['IDR', 'THB', 'MYR', 'SGD', 'PHP', 'VND']
ALL = PAIRS + ['CNY', 'DXY']
CLUSTER_COLORS = {0: '#E97366', 1: '#EAC26B', 2: '#72BC8F'}
CLUSTER_NAMES = {0: 'Pro-Dollar', 1: 'Transisi', 2: 'Mendekati Yuan'}
CHIP_BY_CLUSTER = {0: 'red', 1: 'orange', 2: 'green'}


def api(path):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=5)
        return r.json() if r.ok else []
    except Exception:
        return []


def id_num(v, dec=2):
    if v is None or (isinstance(v, float) and v != v):
        return '—'
    s = f"{v:,.{dec}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_price(v):
    if v is None or (isinstance(v, float) and v != v):
        return '—'
    if v >= 1000:
        return id_num(v, 0)
    if v >= 10:
        return id_num(v, 2)
    return id_num(v, 3)


def fmt_val(v):
    if v is None or (isinstance(v, float) and v != v):
        return '-'
    return f"{v:.2f}"


@st.cache_data(ttl=5)
def get_forex(pair, limit=2):
    return api(f"/api/forex-rates/{pair}?limit={limit}") or []


@st.cache_data(ttl=10)
def get_features(pair, limit=20):
    return api(f"/api/features/{pair}?limit={limit}") or []


@st.cache_data(ttl=10)
def get_batches():
    return api("/api/batches?limit=5") or []


@st.cache_data(ttl=10)
def get_clustering(batch_id):
    return api(f"/api/clustering-results/{batch_id}") or []


@st.cache_data(ttl=10)
def get_notifs(limit=10):
    return api(f"/api/notifications?limit={limit}") or []


def get_latest_clustering():
    batches = get_batches()
    all_results = {}
    for b_id in batches:
        res = get_clustering(b_id)
        if res:
            for c in res:
                key = c['currency_pair']
                if key not in all_results or c['ts'] > all_results[key]['ts']:
                    all_results[key] = c
    return list(all_results.values())


def cur_prev(data):
    # Data dari Cassandra ORDER BY ts DESC -> index 0 = newest
    if len(data) >= 2:
        cur = data[0].get('close') or data[0].get('open') or 0
        prev = data[1].get('close') or data[1].get('open') or cur
    elif len(data) == 1:
        cur = data[0].get('close') or data[0].get('open') or 0
        prev = cur
    else:
        return None, None
    return cur, prev


def build_ikr(features, cluster_info):
    if not features:
        return 50, 'Sedang', 'orange'
    last = features[0]  # Cassandra DESC -> index 0 = newest
    c_dxy = last.get('corr_dxy_20d') if last.get('corr_dxy_20d') is not None else 0.5
    vol = last.get('volatility_20d') if last.get('volatility_20d') is not None else 0.2
    penalty = 0
    if cluster_info:
        idr = next((c for c in cluster_info if c.get('currency_pair') == 'IDR'), None)
        if idr:
            penalty += 20 if idr.get('is_outlier') else 0
            penalty += 15 if idr.get('cluster_label') == 2 else 0
    ikr = min(100, max(0, round((c_dxy * 50) + (vol * 80) + penalty)))
    if ikr >= 70:
        return ikr, 'Tinggi', 'red'
    if ikr >= 45:
        return ikr, 'Sedang–Tinggi', 'orange'
    if ikr >= 25:
        return ikr, 'Sedang', 'blue'
    return ikr, 'Rendah', 'green'


# ─── Data loading ───
with st.spinner('Memuat data...'):
    forex_data = {p: get_forex(p, 2) for p in ALL}
    features_idr = get_features('IDR', 50)
    cluster_latest = get_latest_clustering()
    notifs = get_notifs(10)

ikr_val, ikr_label, ikr_chip = build_ikr(features_idr, cluster_latest)

# ─── Sidebar ───
with st.sidebar:
    st.markdown("## \U0001F4C8 Monitoring")
    st.markdown("**Dedolarisasi ASEAN**")
    st.divider()
    st.markdown("**Pilih Sudut Pandang**")
    lens = st.radio("Lensa", ['\U0001F464 Investor', '\U0001F3DB\uFE0F Bank Indonesia'],
                    index=0, label_visibility="collapsed")
    is_investor = lens.startswith('\U0001F464')
    if is_investor:
        st.markdown('<div class="lens-note"><b>Lensa Investor</b><br>Fokus pada risiko portofolio valas: '
                    'sebaran cluster, mata uang volatil, dan sinyal hedging.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="lens-note"><b>Lensa Bank Indonesia</b><br>Fokus pada stabilitas makro Rupiah: '
                    'Indeks Kerentanan (IKR), ranking ASEAN, dan ambang intervensi.</div>', unsafe_allow_html=True)
    st.divider()
    st.caption("\U0001F504 Auto-refresh tiap 60 detik")
    st.caption(f"\u23F1 {datetime.now().strftime('%H:%M:%S')}")
    if st.button("\u21BB Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ─── Accent per-lensa (override variabel CSS) ───
LENS_ACCENT = '#5e9fe8' if is_investor else '#d99e3c'
LENS_BG = 'rgba(94,159,232,.12)' if is_investor else 'rgba(217,158,60,.12)'
st.markdown(f"<style>:root{{ --lens-accent:{LENS_ACCENT}; --lens-bg:{LENS_BG}; }}</style>",
            unsafe_allow_html=True)

# ─── Top bar (judul + penanda lensa aktif) ───
lens_ico = '\U0001F464' if is_investor else '\U0001F3DB\uFE0F'
lens_txt = 'LENSA INVESTOR' if is_investor else 'LENSA BANK INDONESIA'
lens_sub = 'Risiko portofolio' if is_investor else 'Stabilitas makro Rupiah'
st.markdown(
    '<div class="topbar">'
    '<div class="dash-title">'
    '<h1>\U0001F4C8 Monitoring Dedolarisasi ASEAN</h1>'
    '<div class="sub"><span class="live-badge"><span class="live-dot"></span>LIVE</span>'
    ' · 6 mata uang ASEAN + CNY + DXY · update tiap 60 detik</div>'
    '</div>'
    f'<div class="lens-pill"><span class="lp-ico">{lens_ico}</span>'
    f'<span><div class="lp-txt">{lens_txt}</div><div class="lp-sub">{lens_sub}</div></span></div>'
    '</div>',
    unsafe_allow_html=True,
)


# ─── Ticker ───
def ticker_cell(sym, price, pct, green=False):
    if pct is None:
        cls, ch = 'flat', '—'
    else:
        up = pct >= 0
        cls = 'up' if up else 'down'
        arrow = '▴' if up else '▾'
        ch = f"{arrow} {pct:+.2f}%".replace('.', ',')
    bg = "background:var(--green-bg);" if green else ""
    return (f'<div class="tk" style="{bg}"><div class="sym">{sym}</div>'
            f'<div class="px">{fmt_price(price)}</div>'
            f'<div class="ch {cls}">{ch}</div></div>')


cny_cur, cny_prev = cur_prev(forex_data.get('CNY', []))
cells = []
for p in PAIRS:
    cur, prev = cur_prev(forex_data.get(p, []))
    pct = ((cur - prev) / prev * 100) if (cur and prev) else None
    cells.append(ticker_cell(f"{p}/USD", cur, pct))
for p in PAIRS:
    cur, prev = cur_prev(forex_data.get(p, []))
    if cur and cny_cur:
        cross = cur / cny_cur
        cross_prev = (prev / cny_prev) if (prev and cny_prev) else cross
        pct = ((cross - cross_prev) / cross_prev * 100) if cross_prev else None
    else:
        cross, pct = None, None
    cells.append(ticker_cell(f"{p}/CNY", cross, pct, green=True))
for p in ['CNY', 'DXY']:
    cur, prev = cur_prev(forex_data.get(p, []))
    pct = ((cur - prev) / prev * 100) if (cur and prev) else None
    sym = 'CNY/USD' if p == 'CNY' else 'DXY'
    cells.append(ticker_cell(sym, cur, pct))
st.markdown(f'<div class="ticker">{"".join(cells)}</div>', unsafe_allow_html=True)


# ─── KPI row ───
def kpi(label, value, caption, accent=False):
    cls = 'kpi kpi--accent' if accent else 'kpi'
    return f'<div class="{cls}"><div class="l">{label}</div><div class="v">{value}</div><div class="c">{caption}</div></div>'


def chip(text, kind):
    return f'<span class="chip chip-{kind}">{text}</span>'


if is_investor:
    counts, outliers, hedges = {}, [], []
    for c in cluster_latest:
        lbl = c.get('cluster_label')
        counts[lbl] = counts.get(lbl, 0) + 1
        if c.get('is_outlier'):
            outliers.append(c['currency_pair'])
        if c.get('cluster_label') == 2:
            hedges.append(c['currency_pair'])
    cluster_str = ' · '.join(str(counts.get(i, 0)) for i in [2, 1, 0])
    most_vol, most_vol_val = '-', 0
    for p in PAIRS:
        f = get_features(p, 2)
        if f:
            v = f[0].get('volatility_20d') or 0
            if v > most_vol_val:
                most_vol_val, most_vol = v, p
    out_cap = chip(f"{', '.join(outliers)} anomali", 'red') if outliers else 'Tidak ada'
    cards = [
        kpi("Komposisi cluster", cluster_str or '-', "Pro-Dollar · Transisi · Yuan", accent=True),
        kpi("Outlier hari ini", str(len(outliers)), out_cap),
        kpi("Paling volatil", most_vol, f"volatility {fmt_val(most_vol_val)}" if most_vol_val else '-'),
        kpi("Sinyal hedging aktif", str(len(hedges)), ', '.join(hedges) if hedges else 'Tidak ada'),
    ]
else:
    total = len(cluster_latest) or 6
    idr_rank = 1
    if cluster_latest:
        ranked = sorted(cluster_latest, key=lambda c: (c.get('cluster_label') == 2, c.get('is_outlier')), reverse=True)
        for idx, c in enumerate(ranked):
            if c['currency_pair'] == 'IDR':
                idr_rank = idx + 1
                break
    idr_cl = next((c for c in cluster_latest if c['currency_pair'] == 'IDR'), None)
    corr = features_idr[0].get('corr_dxy_20d') if features_idr else None
    if corr is not None:
        corr_cap = chip(f"{'▲' if corr > 0 else '▼'} ketergantungan USD {'naik' if corr > 0 else 'turun'}",
                        'red' if corr > 0 else 'green')
    else:
        corr_cap = '-'
    if idr_cl and idr_cl.get('is_outlier'):
        status = chip('Kritis', 'red')
    elif ikr_val >= 45:
        status = chip('Waspada', 'orange')
    else:
        status = chip('Aman', 'green')
    cards = [
        kpi("Indeks Kerentanan IDR", f"{ikr_val}", chip(ikr_label, ikr_chip), accent=True),
        kpi("Ranking IDR", f"#{idr_rank} / {total}", f"paling rentan ke-{idr_rank} ASEAN"),
        kpi("Δ corr_dxy IDR", fmt_val(corr), corr_cap),
        kpi("Status alert IDR", "—", status),
    ]
st.markdown(f'<div class="kpi-row">{"".join(cards)}</div>', unsafe_allow_html=True)

st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

# ─── Investor Alert Banner ───
if is_investor:
    alert_pairs = []
    for c in cluster_latest:
        p = c['currency_pair']
        f = get_features(p, 1)
        fd = f[0] if f else {}
        vol = fd.get('volatility_20d') or 0
        is_alert = c.get('is_outlier') or vol > 0.5
        if is_alert:
            label = '⚠ outlier' if c.get('is_outlier') else '↗ volatile'
            alert_pairs.append(f'<strong>{p}</strong> ({label})')
    if alert_pairs:
        severity = 'kritis' if any(c.get('is_outlier') for c in cluster_latest) else 'warn'
        icon = '\U0001F6A8' if severity == 'kritis' else '\u26A0\uFE0F'
        title = 'Perhatian — perlu rebalancing portfolio' if severity == 'kritis' else 'Waspada — pergerakan signifikan terdeteksi'
        st.markdown(
            f'<div class="callout callout-{severity}">'
            f'<span class="co-icon">{icon}</span>'
            f'<div><div class="co-title">{title}</div>'
            f'<div class="co-body">{", ".join(alert_pairs)}. Pantau perkembangan dan pertimbangkan hedging.</div></div></div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="callout callout-aman">'
            '<span class="co-icon">\u2705</span>'
            '<div><div class="co-title">Tidak ada anomali</div>'
            '<div class="co-body">Seluruh mata uang ASEAN dalam kondisi stabil. Tidak diperlukan tindakan hedging saat ini.</div></div></div>',
            unsafe_allow_html=True)

PLOT_CFG = {'displayModeBar': False}
PLOT_LAYOUT = dict(margin=dict(l=10, r=10, t=6, b=10),
                   plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                   font=dict(color='rgba(255,255,255,.7)', size=12))

# ─── Row 1: Scatter + Gauge ───
r1l, r1r = st.columns([7.5, 4.5])
with r1l:
    with st.container(border=True):
        st.markdown('<div class="sec-label">Analisis Cluster</div>'
                    '<div class="card-h">Peta Cluster Mata Uang</div>'
                    f'<div class="card-hint">{"Kandidat diversifikasi; hindari kuadran Pro-Dollar (kanan-bawah)." if is_investor else "Pantau apakah IDR (biru) bergeser ke kuadran rentan dibanding peer ASEAN."}</div>',
                    unsafe_allow_html=True)
        if cluster_latest:
            feat = {}
            for c in cluster_latest:
                f = get_features(c['currency_pair'], 1)
                if f:
                    feat[c['currency_pair']] = f[0]
            xs, ys, sizes, colors, texts = [], [], [], [], []
            for c in cluster_latest:
                p = c['currency_pair']
                fdat = feat.get(p) or {}
                xs.append(fdat.get('corr_dxy_20d') if fdat.get('corr_dxy_20d') is not None else 0.5)
                ys.append(fdat.get('corr_cny_20d') if fdat.get('corr_cny_20d') is not None else 0.3)
                vol = fdat.get('volatility_20d') if fdat.get('volatility_20d') is not None else 0.2
                sizes.append(max(14, min(40, 14 + vol * 45)))
                colors.append('#097fe8' if p == 'IDR' else CLUSTER_COLORS.get(c.get('cluster_label'), '#B0BEC5'))
                texts.append(p)
            fig = go.Figure(go.Scatter(
                x=xs, y=ys, mode='markers+text', text=texts, textposition='middle center',
                textfont=dict(size=10, color='white'),
                marker=dict(size=sizes, color=colors, line=dict(width=1.5, color='white'), opacity=.9)))
            fig.update_layout(height=420, showlegend=False, **PLOT_LAYOUT)
            fig.update_xaxes(title_text='corr_dxy → ketergantungan USD', gridcolor='rgba(255,255,255,.06)', zeroline=False, title_font_size=11, title_font_color='rgba(255,255,255,.5)')
            fig.update_yaxes(title_text='corr_cny → kedekatan Yuan', gridcolor='rgba(255,255,255,.06)', zeroline=False, title_font_size=11, title_font_color='rgba(255,255,255,.5)')
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CFG)
            st.markdown(
                '<div class="legend">'
                '<span><span class="dot" style="background:#E97366"></span>Pro-Dollar</span>'
                '<span><span class="dot" style="background:#EAC26B"></span>Transisi</span>'
                '<span><span class="dot" style="background:#72BC8F"></span>Mendekati Yuan</span>'
                '<span><span class="dot" style="background:#097fe8"></span>IDR (fokus)</span>'
                '<span style="color:var(--text-faint)">○ ukuran = volatilitas</span></div>',
                unsafe_allow_html=True)
        else:
            st.info("Belum ada data clustering")
with r1r:
    with st.container(border=True):
        st.markdown('<div class="sec-label">Indikator Utama</div>'
                    '<div class="card-h">Indeks Kerentanan IDR (IKR)</div>'
                    f'<div class="card-hint">{"Risiko IDR untuk portofolio berbasis Rupiah." if is_investor else "Seberapa rentan IDR & apakah mendekati ambang intervensi."}</div>',
                    unsafe_allow_html=True)
        ikr = max(0, min(100, ikr_val))

        def gauge_svg(v):
            cx, cy, r = 110, 115, 88
            a = 180 + (v / 100) * 180
            rad = a * 3.1415926535 / 180
            nx = cx + (r - 18) * math.cos(rad)
            ny = cy + (r - 18) * math.sin(rad)

            def pt(a2):
                r2 = a2 * 3.1415926535 / 180
                return cx + r * math.cos(r2), cy + r * math.sin(r2)
            gx, gy = pt(225)
            yx, yy = pt(306)

            def arc(x1, y1, x2, y2):
                return f'M {x1:.1f} {y1:.1f} A {r} {r} 0 0 1 {x2:.1f} {y2:.1f}'
            return f'''<svg viewBox="0 0 220 135" width="100%" style="max-height:140px">
                <path d="{arc(cx-r, cy, gx, gy)}" fill="none" stroke="#72BC8F" stroke-width="16" stroke-linecap="round"/>
                <path d="{arc(gx, gy, yx, yy)}" fill="none" stroke="#EAC26B" stroke-width="16"/>
                <path d="{arc(yx, yy, cx+r, cy)}" fill="none" stroke="#E97366" stroke-width="16" stroke-linecap="round"/>
                <line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="var(--text)" stroke-width="3" stroke-linecap="round"/>
                <circle cx="{cx}" cy="{cy}" r="6" fill="var(--text)"/>
                <text x="16" y="{cy+3}" font-size="10" fill="var(--text-faint)">0</text>
                <text x="195" y="{cy+3}" font-size="10" fill="var(--text-faint)">100</text>
            </svg>'''
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">'
            f'{gauge_svg(ikr)}'
            f'<div style="text-align:center">'
            f'<div style="font-size:38px;font-weight:800;letter-spacing:-.03em">{ikr}</div>'
            f'{chip(ikr_label, ikr_chip)}</div></div>',
            unsafe_allow_html=True)
        if cluster_latest:
            ranked = sorted(cluster_latest, key=lambda c: (c.get('cluster_label') == 2, c.get('is_outlier')), reverse=True)
            items = []
            for idx, c in enumerate(ranked[:6]):
                p = c['currency_pair']
                val = c.get('cluster_name') or CLUSTER_NAMES.get(c.get('cluster_label'), '-')
                cls = ' class="idr"' if p == 'IDR' else ''
                items.append(f'<li{cls}><span>{idx+1}. {p}</span><span>{val}</span></li>')
            st.markdown(f'<ul class="rank">{"".join(items)}</ul>', unsafe_allow_html=True)

# ─── Row 2: Time series + Alert feed ───
r2l, r2r = st.columns([7, 5])
with r2l:
    with st.container(border=True):
        st.markdown('<div class="sec-label">Tren Historis</div>'
                    '<div class="card-h">Tren corr_dxy & Volatilitas IDR (20 hari)</div>'
                    f'<div class="card-hint">{"Timing hedging saat garis menembus pita ambang." if is_investor else "Early warning saat ketergantungan USD / volatilitas melonjak."}</div>',
                    unsafe_allow_html=True)
        if features_idr and len(features_idr) >= 2:
            df_f = pd.DataFrame(features_idr)
            if 'ts' in df_f.columns:
                df_f['ts'] = pd.to_datetime(df_f['ts'])
                df_f = df_f.sort_values('ts')
                fig2 = go.Figure()
                fig2.add_hrect(y0=0.6, y1=1.0, fillcolor='rgba(233,115,102,.12)', line_width=0,
                               annotation_text="zona ambang", annotation_position="top right",
                               annotation_font_size=9, annotation_font_color='#E97366')
                fig2.add_trace(go.Scatter(x=df_f['ts'], y=df_f['corr_dxy_20d'], mode='lines', name='corr_dxy IDR',
                                          line=dict(color='#097fe8', width=2.5), fill='tozeroy',
                                          fillcolor='rgba(9,127,232,.08)'))
                fig2.add_trace(go.Scatter(x=df_f['ts'], y=df_f['volatility_20d'], mode='lines', name='volatility IDR',
                                          line=dict(color='#D9730D', width=2, dash='dot')))
                fig2.update_layout(height=300, legend=dict(orientation='h', y=-0.22), **PLOT_LAYOUT)
                fig2.update_xaxes(gridcolor='rgba(255,255,255,.06)', zeroline=False)
                fig2.update_yaxes(gridcolor='rgba(255,255,255,.06)', zeroline=False)
                st.plotly_chart(fig2, use_container_width=True, config=PLOT_CFG)
            else:
                st.info("Data features tidak punya timestamp")
        else:
            st.info("Data features IDR belum cukup (min 2 titik)")
with r2r:
    with st.container(border=True):
        st.markdown('<div class="sec-label">Real-time</div>'
                    '<div class="card-h">\U0001F514 Alert Feed <span style="font-size:11px;font-weight:500;color:var(--text-soft)">(WebSocket)</span></div>'
                    f'<div class="card-hint">{"Trigger rebalancing / hedging." if is_investor else "Trigger evaluasi intervensi."}</div>',
                    unsafe_allow_html=True)
        icon_map = {'cluster_change': '⚠', 'clustering_done': '◉', 'outlier': '◉',
                    'high_volatility': '↗', 'forex_update': '↗', 'notification': 'ℹ', 'info': 'ℹ'}
        kind_map = {'cluster_change': 'red', 'clustering_done': 'orange', 'outlier': 'orange',
                    'high_volatility': 'orange', 'forex_update': 'blue', 'notification': 'blue', 'info': 'blue'}
        bg_map = {'red': ('var(--red-bg)', 'var(--c-red)'), 'orange': ('var(--orange-bg)', 'var(--orange)'),
                  'blue': ('var(--blue-bg)', 'var(--blue)')}
        if notifs:
            rows = []
            for n in notifs[:8]:
                ntype = n.get('type', 'info')
                k = kind_map.get(ntype, 'blue')
                bg, fg = bg_map[k]
                icon = icon_map.get(ntype, 'ℹ')
                title = n.get('title') or n.get('message') or 'Update'
                ts = n.get('ts', '')
                try:
                    t_str = datetime.fromisoformat(ts.replace('Z', '+00:00')).strftime('%H:%M') if ts else '-'
                except Exception:
                    t_str = '-'
                rows.append(
                    f'<div class="alert"><div class="ic" style="background:{bg};color:{fg}">{icon}</div>'
                    f'<div><div class="msg">{title}</div><div class="meta">{ntype} · {t_str}</div></div></div>')
            st.markdown(''.join(rows), unsafe_allow_html=True)
        else:
            st.info("Belum ada notifikasi")

# ─── Row 3: Outlier table ───
with st.container(border=True):
    st.markdown('<div class="sec-label">Deteksi Anomali</div>'
                '<div class="card-h">Tabel Outlier / Anomali (DBSCAN)</div>'
                f'<div class="card-hint">{"Mata uang yang harus diwaspadai sebelum mengambil posisi." if is_investor else "Deteksi tekanan tak normal pada IDR & kawasan."}</div>',
                unsafe_allow_html=True)
    if cluster_latest:
        body = []
        for c in cluster_latest:
            p = c['currency_pair']
            f = get_features(p, 1)
            fd = f[0] if f else {}
            cl_chip = chip(c.get('cluster_name') or CLUSTER_NAMES.get(c.get('cluster_label'), '-'),
                           CHIP_BY_CLUSTER.get(c.get('cluster_label'), 'gray'))
            status = chip('Outlier', 'red') if c.get('is_outlier') else chip('Normal', 'gray')
            body.append(
                f'<tr><td><strong>{p}</strong></td><td>{cl_chip}</td>'
                f'<td>{fmt_val(fd.get("corr_dxy_20d"))}</td><td>{fmt_val(fd.get("corr_cny_20d"))}</td>'
                f'<td>{fmt_val(fd.get("volatility_20d"))}</td><td>{status}</td></tr>')
        st.markdown(
            '<table class="otable"><thead><tr><th>Mata uang</th><th>Cluster</th><th>corr_dxy</th>'
            '<th>corr_cny</th><th>volatility</th><th>Status</th></tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table>', unsafe_allow_html=True)
    else:
        st.info("Belum ada data clustering — jalankan POST /api/run-clustering")

st.caption(f"\u23F1 Data diperbarui otomatis — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")