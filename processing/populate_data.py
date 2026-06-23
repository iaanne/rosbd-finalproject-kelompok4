import pandas as pd
import numpy as np
from cassandra.cluster import Cluster
import datetime
import uuid
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.metrics import silhouette_score

# 1. Inisialisasi Koneksi Cassandra
CASSANDRA_IP = "100.66.223.98"
print(f"Menghubungkan ke Cassandra di {CASSANDRA_IP}...")
cluster = Cluster([CASSANDRA_IP])
session = cluster.connect('dedolarisasi')

# 2. Ambil Data forex_rates
print("Mengambil data dari tabel forex_rates...")
query = "SELECT currency_pair, ts, close, open, high, low, volume FROM forex_rates"
rows = session.execute(query)
df = pd.DataFrame(rows)

if df.empty:
    print("Error: Tabel forex_rates kosong! Pastikan data mentah sudah di-ingest.")
    exit(1)

# Urutkan berdasarkan waktu
df = df.sort_values(by=['currency_pair', 'ts']).reset_index(drop=True)

# 3. Pisahkan Data DXY dan CNY/USD untuk Perhitungan Korelasi
print("Menyiapkan data pembanding DXY dan CNY...")
df_dxy = df[df['currency_pair'] == 'DXY'][['ts', 'close']].rename(columns={'close': 'close_dxy'})
df_cny = df[df['currency_pair'].isin(['CNY/USD', 'CNY'])][['ts', 'close']].rename(columns={'close': 'close_cny'})

# Gabungkan pembanding ke dataframe utama
df = pd.merge(df, df_dxy, on='ts', how='left')
df = pd.merge(df, df_cny, on='ts', how='left')

# Isi nilai kosong (jika ada data time mismatch) dengan forward fill
df['close_dxy'] = df.groupby('currency_pair')['close_dxy'].ffill()
df['close_cny'] = df.groupby('currency_pair')['close_cny'].ffill()

# 4. Fungsi Perhitungan Indikator Teknis (RSI)
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

# 5. Hitung Fitur per Currency Pair
print("Menghitung indikator teknis & korelasi (rolling window 20 hari)...")
features_list = []

for pair, group in df.groupby('currency_pair'):
    # Jangan hitung fitur untuk DXY dan CNY itu sendiri
    if pair in ['DXY', 'CNY/USD', 'Gold']:
        continue
    
    group = group.sort_values(by='ts').copy()
    
    # Hitung Return
    group['returns_1d'] = group['close'].pct_change(1)
    group['log_return'] = np.log(group['close'] / group['close'].shift(1))
    
    # Hitung Rata-rata Bergerak (Rolling Mean)
    group['rolling_mean_5d'] = group['close'].rolling(5).mean()
    group['rolling_mean_20d'] = group['close'].rolling(20).mean()
    
    # Hitung Volatilitas (Standard Deviasi)
    group['rolling_std_5d'] = group['close'].rolling(5).std()
    group['volatility_20d'] = group['log_return'].rolling(20).std()
    
    # Hitung Korelasi 20 Hari terhadap DXY dan CNY (pada return, bukan level)
    group['dxy_return'] = group['close_dxy'].pct_change().fillna(0)
    group['cny_return'] = group['close_cny'].pct_change().fillna(0)
    group['corr_dxy_20d'] = group['log_return'].rolling(20).corr(group['dxy_return'])
    group['corr_cny_20d'] = group['log_return'].rolling(20).corr(group['cny_return'])
    
    # Hitung RSI dan Bollinger Bands
    group['rsi_14'] = compute_rsi(group['close'], 14)
    std_20d = group['close'].rolling(20).std()
    group['bb_upper'] = group['rolling_mean_20d'] + (2 * std_20d)
    group['bb_lower'] = group['rolling_mean_20d'] - (2 * std_20d)
    
    # Buang baris yang memiliki nilai NaN (karena window 20 hari di awal)
    group = group.dropna(subset=['corr_dxy_20d', 'corr_cny_20d', 'volatility_20d'])
    features_list.append(group)

df_features = pd.concat(features_list).reset_index(drop=True)

# 6. Simpan Fitur ke Cassandra
print("Menyimpan hasil perhitungan ke tabel features...")
insert_feature_query = """
INSERT INTO features (
    currency_pair, ts, returns_1d, log_return, rolling_mean_5d, rolling_mean_20d, 
    rolling_std_5d, volatility_20d, corr_dxy_20d, corr_cny_20d, rsi_14, bb_upper, bb_lower
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

for _, row in df_features.iterrows():
    session.execute(insert_feature_query, (
        row['currency_pair'],
        row['ts'],
        float(row['returns_1d']) if not pd.isna(row['returns_1d']) else None,
        float(row['log_return']) if not pd.isna(row['log_return']) else None,
        float(row['rolling_mean_5d']) if not pd.isna(row['rolling_mean_5d']) else None,
        float(row['rolling_mean_20d']) if not pd.isna(row['rolling_mean_20d']) else None,
        float(row['rolling_std_5d']) if not pd.isna(row['rolling_std_5d']) else None,
        float(row['volatility_20d']) if not pd.isna(row['volatility_20d']) else None,
        float(row['corr_dxy_20d']) if not pd.isna(row['corr_dxy_20d']) else None,
        float(row['corr_cny_20d']) if not pd.isna(row['corr_cny_20d']) else None,
        float(row['rsi_14']) if not pd.isna(row['rsi_14']) else None,
        float(row['bb_upper']) if not pd.isna(row['bb_upper']) else None,
        float(row['bb_lower']) if not pd.isna(row['bb_lower']) else None
    ))

# 7. Jalankan Klastering dengan K-Means + DBSCAN + AHC
print("Menjalankan K-Means + DBSCAN + AHC clustering...")
batch_id = str(uuid.uuid4())[:8]

# Ambil data unik per currency_pair (snapshot terbaru)
latest_ts = df_features.groupby('currency_pair')['ts'].max().reset_index()
df_latest = pd.merge(latest_ts, df_features, on=['currency_pair', 'ts'], how='left')
df_latest = df_latest.dropna(subset=['corr_dxy_20d', 'corr_cny_20d', 'volatility_20d'])

X = df_latest[['corr_dxy_20d', 'corr_cny_20d', 'volatility_20d']].values
n = len(X)

print(f"Running clustering on {n} currency pairs...")

# ── 1. K-Means (k=3) ────────────────────────────────
kmeans = KMeans(n_clusters=min(3, n), random_state=42, n_init=10)
km_labels_raw = kmeans.fit_predict(X)
km_sil = silhouette_score(X, km_labels_raw) if n >= 4 and len(set(km_labels_raw)) > 1 else 0.0

# ── 2. DBSCAN ────────────────────────────────────────
dbscan = DBSCAN(eps=0.3, min_samples=2)
db_labels_raw = dbscan.fit_predict(X)
db_sil = silhouette_score(X, db_labels_raw) if n >= 4 and len(set(db_labels_raw)) > 1 else 0.0

# ── 3. AHC ───────────────────────────────────────────
ahc = AgglomerativeClustering(n_clusters=min(3, n))
ahc_labels_raw = ahc.fit_predict(X)
ahc_sil = silhouette_score(X, ahc_labels_raw) if n >= 4 and len(set(ahc_labels_raw)) > 1 else 0.0

# ── Helper: relabel arbitrary cluster IDs to canonical 0/1/2 ──
def relabel_by_centroid(labels_raw):
    unique = sorted(set(labels_raw) - {-1})
    if len(unique) < 2:
        return [1] * len(labels_raw)
    centroids_ = np.array([
        [X[labels_raw == c, 0].mean(), X[labels_raw == c, 1].mean()]
        for c in unique
    ])
    order = sorted(range(len(unique)), key=lambda i: (centroids_[i, 0], centroids_[i, 1]))
    c0 = unique[order[0]]
    c2 = unique[order[-1]]
    c1 = unique[order[1]] if len(order) >= 3 else unique[0]
    mapping = {c0: 0, c1: 1, c2: 2}
    return [mapping.get(l, 1) if l != -1 else 1 for l in labels_raw]

# ── Relabel K-Means ──────────────────────────────────
centroids = kmeans.cluster_centers_
k = len(centroids)
centroid_order = sorted(range(k), key=lambda i: (centroids[i, 0], centroids[i, 1]))
km_label_map = {}
if k >= 1: km_label_map[centroid_order[0]] = 0
if k >= 2: km_label_map[centroid_order[1]] = 1
if k >= 3: km_label_map[centroid_order[2]] = 2
km_labels = [km_label_map.get(l, 1) for l in km_labels_raw]

db_labels = relabel_by_centroid(db_labels_raw)
ahc_labels = relabel_by_centroid(ahc_labels_raw)

name_map = {0: "Pro-Dollar", 1: "Transisi", 2: "Yuan"}
mean_vol = df_latest['volatility_20d'].mean()

clustering_results = []
for algo_name, labels, sil_score in [
    ("K-Means", km_labels, km_sil),
    ("DBSCAN", db_labels, db_sil),
    ("AHC", ahc_labels, ahc_sil),
]:
    for i, row in df_latest.iterrows():
        canonical = int(labels[i]) if i < len(labels) else 1
        if canonical not in (0, 1, 2):
            canonical = 1
        name = name_map.get(canonical, "Transisi")
        is_outlier = bool(row['volatility_20d'] > (mean_vol * 2.5)) if mean_vol > 0 else False

        clustering_results.append((
            batch_id,
            row['ts'],
            algo_name,
            row['currency_pair'],
            canonical,
            name,
            is_outlier,
            float(sil_score),
        ))

avg_sil = (km_sil + db_sil + ahc_sil) / 3
print(f"Clustering selesai — Silhouette: K-Means={km_sil:.3f}, DBSCAN={db_sil:.3f}, AHC={ahc_sil:.3f}, Rata-rata={avg_sil:.3f}")

# 8. Simpan Hasil Klastering ke Cassandra
print(f"Menyimpan {len(clustering_results)} hasil klastering ke tabel clustering_results (batch {batch_id})...")
insert_cluster_query = """
INSERT INTO clustering_results (
    batch_id, ts, algorithm, currency_pair, cluster_label, cluster_name, is_outlier, silhouette_score
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

for res in clustering_results:
    session.execute(insert_cluster_query, res)

print("--- PENGISIAN DATABASE SUKSES! ---")
print(f"Data tersimpan dengan Batch ID: {batch_id}")
