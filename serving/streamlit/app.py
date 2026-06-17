import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone
import time

st.set_page_config(page_title="Monitoring Dedolarisasi ASEAN", layout="wide", page_icon="📈")

API_BASE = "http://fastapi:8000"
PAIRS = ['IDR', 'THB', 'MYR', 'SGD', 'PHP', 'VND', 'CNY', 'DXY']
CLUSTER_COLORS = {0: '#72BC8F', 1: '#EAC26B', 2: '#E97366'}
CLUSTER_NAMES = {0: 'Mendekati Yuan', 1: 'Transisi', 2: 'Pro-Dollar'}

if 'lens' not in st.session_state:
    st.session_state.lens = 'Investor'
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

def api(path):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=5)
        return r.json() if r.ok else []
    except:
        return []

def api_post(path, data=None):
    try:
        r = requests.post(f"{API_BASE}{path}", json=data, timeout=10)
        return r.json() if r.ok else {}
    except:
        return {}

def fmt_val(v):
    if v is None or (isinstance(v, float) and (v != v)):
        return '-'
    return f"{v:.2f}"

def fmt_pct(v):
    if v is None or (isinstance(v, float) and (v != v)):
        return '-'
    prefix = '+' if v >= 0 else ''
    return f"{prefix}{v:.2f}%"

@st.cache_data(ttl=5)
def get_forex(pair, limit=50):
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

@st.cache_data(ttl=10)
def get_pairs():
    return api("/api/currency-pairs") or []

def get_latest_clustering():
    batches = get_batches()
    if not batches:
        return []
    results = []
    for b_id in batches[:3]:
        results.extend(get_clustering(b_id))
    df = pd.DataFrame(results)
    if df.empty:
        return []
    df = df.sort_values('ts')
    latest = df.groupby('currency_pair').last().reset_index()
    return latest.to_dict('records')

def build_ikr(features, cluster_info):
    if not features:
        return 50, 'Sedang', 'Kuning'
    last = features[-1]
    c_dxy = last.get('corr_dxy_20d') or 0.5
    vol = last.get('volatility_20d') or 0.2
    outlier_penalty = 0
    if cluster_info:
        is_ot = any(c.get('is_outlier') and c['currency_pair'] == 'IDR' for c in cluster_info)
        label = next((c['cluster_label'] for c in cluster_info if c['currency_pair'] == 'IDR'), 1)
        outlier_penalty = (20 if is_ot else 0) + (15 if label == 2 else 0)
    ikr = min(100, max(0, int((c_dxy * 50) + (vol * 80) + outlier_penalty)))
    if ikr >= 70:
        return ikr, 'Tinggi', 'Merah'
    elif ikr >= 45:
        return ikr, 'Sedang–Tinggi', 'Kuning'
    elif ikr >= 25:
        return ikr, 'Sedang', 'Biru'
    return ikr, 'Rendah', 'Hijau'

# ─── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Monitoring Dedolarisasi")
    st.markdown("**ASEAN + CNY + DXY**")
    st.divider()
    lens = st.radio("Lensa", ['Investor', 'Bank Indonesia'], index=0,
                    help="Investor: untuk portofolio. BI: untuk intervensi.")
    st.session_state.lens = lens
    st.divider()
    st.caption(f"Auto-refresh tiap 5 detik")
    st.caption(f"Update terakhir: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("↻ Refresh sekarang"):
        st.cache_data.clear()
        st.rerun()

is_investor = (lens == 'Investor')

# ─── Data Loading ───────────────────────────────────────────
forex_data = {}
for p in PAIRS:
    forex_data[p] = get_forex(p, 2)

features_idr = get_features('IDR', 20)
cluster_latest = get_latest_clustering()
notifs = get_notifs(10)

ikr_val, ikr_label, ikr_color = build_ikr(features_idr, cluster_latest)

# ─── Header ─────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("## Monitoring Dedolarisasi ASEAN")
    st.caption("6 mata uang ASEAN + CNY + DXY · real-time via FastAPI")
with col2:
    lens_icon = "👤" if is_investor else "🏛️"
    lens_name = "Investor" if is_investor else "Bank Indonesia"
    st.metric("Lensa aktif", f"{lens_icon} {lens_name}")

# ─── Ticker ─────────────────────────────────────────────────
cols = st.columns(8)
for i, p in enumerate(PAIRS):
    with cols[i]:
        data = forex_data.get(p, [])
        if len(data) >= 2:
            curr = data[-1]
            prev = data[-2]
            px = curr.get('close', 0) or curr.get('open', 0)
            prev_px = prev.get('close', 0) or prev.get('open', px)
            ch = px - prev_px
            pct = (ch / prev_px * 100) if prev_px else 0
            arrow = "▲" if ch >= 0 else "▼"
            color = "#72BC8F" if ch >= 0 else "#E97366"
        elif len(data) == 1:
            px = data[0].get('close', 0) or data[0].get('open', 0)
            ch = 0
            pct = 0
            arrow = "–"
            color = "#888"
        else:
            px = "—"
            ch = 0
            pct = 0
            arrow = "–"
            color = "#888"
        st.metric(label=f"{p}/USD", value=f"{px:,.2f}" if isinstance(px, (int, float)) else px,
                  delta=f"{arrow} {abs(pct):.2f}%" if isinstance(pct, float) else None,
                  delta_color="normal")

# ─── KPI Rows ───────────────────────────────────────────────
if is_investor:
    cluster_count = {}
    outlier_pairs = []
    volatile_pairs = []
    hedge_pairs = []
    if cluster_latest:
        for c in cluster_latest:
            lbl = c.get('cluster_label')
            cluster_count[lbl] = cluster_count.get(lbl, 0) + 1
            if c.get('is_outlier'):
                outlier_pairs.append(c['currency_pair'])
            if c.get('cluster_label') == 2:
                hedge_pairs.append(c['currency_pair'])
    cluster_str = ' · '.join(str(cluster_count.get(i, 0)) for i in [0, 1, 2])
    outlier_str = ', '.join(outlier_pairs) if outlier_pairs else 'Tidak ada'
    hedge_str = ', '.join(hedge_pairs) if hedge_pairs else 'Tidak ada'
    # Find most volatile from features
    most_vol = '-'
    most_vol_val = 0
    for p in PAIRS:
        if p in ('DXY', 'CNY'):
            continue
        f = get_features(p, 2)
        if f:
            v = f[-1].get('volatility_20d') or 0
            if v > most_vol_val:
                most_vol_val = v
                most_vol = p
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Komposisi cluster", cluster_str if cluster_str else "-", "Pro-Dollar · Transisi · Yuan")
    k2.metric("Outlier aktif", str(len(outlier_pairs)), outlier_str)
    k3.metric("Paling volatil", most_vol, f"volatility {most_vol_val:.2f}" if most_vol_val else "-")
    k4.metric("Sinyal hedging", str(len(hedge_pairs)), hedge_str)
else:
    idr_rank = 1
    total_pairs = len(cluster_latest) if cluster_latest else 6
    if cluster_latest:
        ranked = sorted(cluster_latest,
                       key=lambda c: (c.get('cluster_label') == 2, c.get('is_outlier')), reverse=True)
        for idx, c in enumerate(ranked):
            if c['currency_pair'] == 'IDR':
                idr_rank = idx + 1
                break
    idr_cluster = next((c for c in (cluster_latest or []) if c['currency_pair'] == 'IDR'), None)
    corr_val = features_idr[-1].get('corr_dxy_20d') if features_idr else None
    corr_delta = f"{'▲' if corr_val and corr_val > 0 else '▼'} ketergantungan USD naik" if corr_val else "-"
    status = "KRITIS" if (idr_cluster and idr_cluster.get('is_outlier')) else "Waspada" if ikr_val >= 45 else "Aman"
    status_color = "inverse" if status == "KRITIS" else "off" if status == "Waspada" else "normal"
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Indeks Kerentanan IDR", f"{ikr_val}", ikr_label)
    k2.metric("Ranking IDR", f"#{idr_rank} / {total_pairs if total_pairs else '?'}", "paling rentan ke-? ASEAN")
    k3.metric("Δ corr_dxy IDR", fmt_val(corr_val), corr_delta)
    k4.metric("Status alert IDR", status)

# ─── Main Charts ────────────────────────────────────────────
col_left, col_right = st.columns([7, 5])

with col_left:
    st.subheader("Peta Cluster Mata Uang")
    st.caption("Kandidat diversifikasi berdasarkan kedekatan dengan USD vs Yuan" if is_investor
               else "Pantau posisi IDR relatif terhadap peer ASEAN")
    if cluster_latest:
        df_cluster = pd.DataFrame(cluster_latest)
        feat_map = {}
        for c in cluster_latest:
            pair = c['currency_pair']
            f = get_features(pair, 1)
            if f:
                feat_map[pair] = f[-1]
        df_cluster['corr_dxy'] = df_cluster['currency_pair'].apply(
            lambda p: (feat_map.get(p) or {}).get('corr_dxy_20d') or 0.5)
        df_cluster['corr_cny'] = df_cluster['currency_pair'].apply(
            lambda p: (feat_map.get(p) or {}).get('corr_cny_20d') or 0.3)
        df_cluster['volatility'] = df_cluster['currency_pair'].apply(
            lambda p: (feat_map.get(p) or {}).get('volatility_20d') or 0.2)
        df_cluster['color'] = df_cluster.apply(
            lambda r: '#097fe8' if r['currency_pair'] == 'IDR'
            else CLUSTER_COLORS.get(r.get('cluster_label'), '#888'), axis=1)
        df_cluster['name'] = df_cluster['currency_pair'] + ' (' + df_cluster.get('cluster_name', '').astype(str) + ')'
        df_cluster['size'] = df_cluster['volatility'].apply(lambda v: max(8, min(25, 8 + v * 30)))

        fig = px.scatter(df_cluster, x='corr_dxy', y='corr_cny', size='size',
                         color='color', text='currency_pair',
                         hover_name='name',
                         hover_data={'cluster_label': True, 'volatility': ':.3f', 'color': False},
                         color_discrete_map='identity',
                         labels={'corr_dxy': 'corr_dxy (ketergantungan USD)',
                                 'corr_cny': 'corr_cny (kedekatan Yuan)'},
                         height=400)
        fig.update_traces(textposition='middle center', marker=dict(line=dict(width=1, color='white')))
        fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        # Highlight IDR
        idr_row = df_cluster[df_cluster['currency_pair'] == 'IDR']
        if not idr_row.empty:
            fig.add_trace(go.Scatter(
                x=idr_row['corr_dxy'], y=idr_row['corr_cny'],
                mode='markers+text',
                marker=dict(size=idr_row['size'].values[0] + 6, color='#097fe8',
                           line=dict(width=3, color='white')),
                text=idr_row['currency_pair'],
                textposition='middle center',
                name='IDR (fokus)'))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Belum ada data clustering — jalankan POST /api/run-clustering")

with col_right:
    st.subheader("Indeks Kerentanan IDR")
    st.caption("Risiko IDR untuk portofolio" if is_investor else "Seberapa rentan IDR & ambang intervensi")
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=ikr_val,
        number={'suffix': "%", 'font': {'size': 50}},
        delta={'reference': 50, 'increasing': {'color': "#E97366"}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "#097fe8"},
            'steps': [
                {'range': [0, 25], 'color': '#72BC8F'},
                {'range': [25, 45], 'color': '#EAC26B'},
                {'range': [45, 70], 'color': '#DE9255'},
                {'range': [70, 100], 'color': '#E97366'}],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': ikr_val}}))
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # IKR Rank
    if cluster_latest:
        st.caption("**Ranking Kerentanan**")
        ranked = sorted(cluster_latest,
                       key=lambda c: (c.get('cluster_label') == 2, c.get('is_outlier')), reverse=True)
        for idx, c in enumerate(ranked[:6]):
            col_a, col_b = st.columns([1, 1])
            label = f"{idx+1}. {c['currency_pair']}"
            value = c.get('cluster_name') or CLUSTER_NAMES.get(c.get('cluster_label'), '-')
            is_idr = c['currency_pair'] == 'IDR'
            with col_a:
                st.markdown(f"{'**' if is_idr else ''}{label}{'**' if is_idr else ''}")
            with col_b:
                st.markdown(f"{'**' if is_idr else ''}{value}{'**' if is_idr else ''}")

# ─── Trend Chart & Alert Feed ───────────────────────────────
col_tr, col_al = st.columns([7, 5])

with col_tr:
    st.subheader("Tren corr_dxy & Volatilitas IDR")
    st.caption("Timing hedging / early warning saat ketergantungan USD melonjak")
    if features_idr and len(features_idr) >= 2:
        df_f = pd.DataFrame(features_idr)
        if 'ts' in df_f.columns:
            df_f['ts'] = pd.to_datetime(df_f['ts'])
            df_f = df_f.sort_values('ts')
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df_f['ts'], y=df_f['corr_dxy_20d'],
                mode='lines+markers', name='corr_dxy IDR',
                line=dict(color='#097fe8', width=2.5)))
            fig2.add_trace(go.Scatter(
                x=df_f['ts'], y=df_f['volatility_20d'],
                mode='lines+markers', name='volatility_20d IDR',
                line=dict(color='#D9730D', width=2.5, dash='dot')))
            fig2.add_hline(y=0.6, line_dash="dash", line_color="#E97366",
                          annotation_text="zona ambang")
            fig2.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
                              legend=dict(orientation='h', y=-0.2))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Data features IDR tidak memiliki kolom timestamp")
    else:
        st.info("Belum cukup data features IDR (butuh minimal 2 titik)")

with col_al:
    st.subheader("🔔 Alert Feed")
    st.caption("Trigger rebalancing / hedging" if is_investor else "Trigger evaluasi intervensi")
    if notifs:
        for n in notifs[-10:]:
            ntype = n.get('type', 'info')
            icon = {'clustering_done': '◉', 'forex_update': '↗', 'notification': 'ℹ'}.get(ntype, 'ℹ')
            title = n.get('title') or n.get('message') or 'Update'
            ts = n.get('ts', '')
            try:
                t_str = datetime.fromisoformat(ts.replace('Z', '+00:00')).strftime('%H:%M') if ts else '-'
            except:
                t_str = '-'
            with st.container():
                col_i, col_m = st.columns([0.5, 3.5])
                with col_i:
                    st.markdown(f"<span style='font-size:18px'>{icon}</span>",
                              unsafe_allow_html=True)
                with col_m:
                    st.markdown(f"**{title}**")
                    st.caption(f"{ntype} · {t_str}")
                st.divider()
    else:
        st.info("Belum ada notifikasi")

# ─── Outlier Table ──────────────────────────────────────────
st.subheader("Hasil Clustering & Outlier")
st.caption("Mata uang yang harus diwaspadai" if is_investor else "Deteksi tekanan tak normal pada IDR")
if cluster_latest:
    rows = []
    for c in cluster_latest:
        pair = c['currency_pair']
        f = get_features(pair, 1)
        feat = f[-1] if f else {}
        rows.append({
            'Mata uang': pair,
            'Cluster': c.get('cluster_name') or CLUSTER_NAMES.get(c.get('cluster_label'), '-'),
            'corr_dxy': fmt_val(feat.get('corr_dxy_20d')),
            'corr_cny': fmt_val(feat.get('corr_cny_20d')),
            'volatility': fmt_val(feat.get('volatility_20d')),
            'Outlier': '⚠ Ya' if c.get('is_outlier') else '✓ Tidak',
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                 column_config={
                     'Mata uang': st.column_config.TextColumn('Mata uang', width='small'),
                     'Cluster': st.column_config.TextColumn('Cluster', width='medium'),
                     'corr_dxy': st.column_config.TextColumn('corr_dxy', width='small'),
                     'corr_cny': st.column_config.TextColumn('corr_cny', width='small'),
                     'volatility': st.column_config.TextColumn('volatility', width='small'),
                     'Outlier': st.column_config.TextColumn('Status', width='small'),
                 })
else:
    st.info("Belum ada data clustering")

# ─── Auto-refresh ───────────────────────────────────────────
st.caption(f"Data diperbarui otomatis — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
