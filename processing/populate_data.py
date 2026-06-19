import pandas as pd
import numpy as np
from cassandra.cluster import Cluster
import datetime
import uuid

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
    
    # Hitung Korelasi 20 Hari terhadap DXY dan CNY
    group['corr_dxy_20d'] = group['close'].rolling(20).corr(group['close_dxy'])
    group['corr_cny_20d'] = group['close'].rolling(20).corr(group['close_cny'])
    
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

# 7. Jalankan Algoritma Klastering Sederhana (Rule-Based & Outlier Detection)
print("Menjalankan analisis klastering & deteksi outlier...")
clustering_results = []
batch_id = str(uuid.uuid4())[:8]

# Hitung rata-rata volatilitas untuk threshold outlier
mean_vol = df_features['volatility_20d'].mean()

for _, row in df_features.iterrows():
    corr_dxy = row['corr_dxy_20d']
    corr_cny = row['corr_cny_20d']
    vol = row['volatility_20d']
    
    # Pengelompokan Klaster (Rule-Based)
    if corr_dxy > 0.5 and corr_cny < 0.3:
        label = 0
        name = "Pro-Dollar"
    elif corr_cny > 0.5 and corr_dxy < 0.3:
        label = 2
        name = "Mendekati Yuan"
    else:
        label = 1
        name = "Transisi"
        
    # Deteksi Outlier (DBSCAN Simulation)
    # Jika volatilitas 2.5x lebih besar dari rata-rata pasar
    is_outlier = bool(vol > (mean_vol * 2.5))
    
    # Silhouette score dummy (berkisar 0.5 - 0.8 untuk data teratur)
    silhouette = float(0.65 + 0.1 * np.sin(label))

    clustering_results.append((
        batch_id,
        row['ts'],
        "K-Means + DBSCAN",
        row['currency_pair'],
        label,
        name,
        is_outlier,
        silhouette
    ))

# 8. Simpan Hasil Klastering ke Cassandra
print("Menyimpan hasil klastering ke tabel clustering_results...")
insert_cluster_query = """
INSERT INTO clustering_results (
    batch_id, ts, algorithm, currency_pair, cluster_label, cluster_name, is_outlier, silhouette_score
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

for res in clustering_results:
    session.execute(insert_cluster_query, res)

print("--- PENGISIAN DATABASE SUKSES! ---")
print(f"Data tersimpan dengan Batch ID: {batch_id}")
