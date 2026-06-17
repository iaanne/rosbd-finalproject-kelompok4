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

-- Tabel 4: notifications (untuk real-time notifikasi)
CREATE TABLE IF NOT EXISTS notifications (
    bucket TEXT,
    ts TIMESTAMP,
    id UUID,
    type TEXT,
    title TEXT,
    message TEXT,
    batch_id TEXT,
    algorithm TEXT,
    PRIMARY KEY ((bucket), ts, id)
) WITH CLUSTERING ORDER BY (ts DESC);
