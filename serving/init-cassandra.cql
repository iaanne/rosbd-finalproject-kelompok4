CREATE KEYSPACE IF NOT EXISTS dedolarisasi
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE dedolarisasi;

-- Tabel 1: forex_rates (OHLCV)
CREATE TABLE IF NOT EXISTS forex_rates (
    currency_pair TEXT,
    ts TIMESTAMP,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    PRIMARY KEY ((currency_pair), ts)
) WITH CLUSTERING ORDER BY (ts DESC);

-- Tabel 2: features
CREATE TABLE IF NOT EXISTS features (
    currency_pair TEXT,
    ts TIMESTAMP,
    returns_1d DOUBLE,
    log_return DOUBLE,
    rolling_mean_5d DOUBLE,
    rolling_mean_20d DOUBLE,
    rolling_std_5d DOUBLE,
    volatility_20d DOUBLE,
    corr_dxy_20d DOUBLE,
    corr_cny_20d DOUBLE,
    rsi_14 DOUBLE,
    bb_upper DOUBLE,
    bb_lower DOUBLE,
    PRIMARY KEY ((currency_pair), ts)
) WITH CLUSTERING ORDER BY (ts DESC);

-- Tabel 3: clustering_results
CREATE TABLE IF NOT EXISTS clustering_results (
    batch_id TEXT,
    ts TIMESTAMP,
    algorithm TEXT,
    currency_pair TEXT,
    cluster_label INT,
    cluster_name TEXT,
    is_outlier BOOLEAN,
    silhouette_score DOUBLE,
    PRIMARY KEY ((batch_id), ts, algorithm, currency_pair)
) WITH CLUSTERING ORDER BY (ts DESC);

-- Tabel 4A: clustering_metrics (metrik per batch)
CREATE TABLE IF NOT EXISTS clustering_metrics (
  batch_id TEXT PRIMARY KEY,
  ts TIMESTAMP,
  kmeans_k INT,
  kmeans_silhouette DOUBLE,
  dbscan_noise_ratio DOUBLE,
  dbscan_silhouette DOUBLE,
  ahc_silhouette DOUBLE,
  dendrogram_linkage TEXT,
  labels_order TEXT
);

-- Tabel 4B: batch_index (indeks kronologis batch clustering)
CREATE TABLE IF NOT EXISTS batch_index (
    bucket TEXT,
    ts TIMESTAMP,
    batch_id TEXT,
    PRIMARY KEY ((bucket), ts)
) WITH CLUSTERING ORDER BY (ts DESC);

-- Tabel 4C: notifications (untuk real-time notifikasi, termasuk alert)
CREATE TABLE IF NOT EXISTS notifications (
    bucket TEXT,
    ts TIMESTAMP,
    id UUID,
    type TEXT,
    title TEXT,
    message TEXT,
    severity TEXT,
    category TEXT,
    batch_id TEXT,
    algorithm TEXT,
    PRIMARY KEY ((bucket), ts, id)
) WITH CLUSTERING ORDER BY (ts DESC);
