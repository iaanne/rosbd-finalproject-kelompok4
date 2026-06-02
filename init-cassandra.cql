CREATE KEYSPACE IF NOT EXISTS dedolarisasi 
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE dedolarisasi;

-- Tabel 1: forex_rates (OHLCV)
CREATE TABLE IF NOT EXISTS forex_rates (
    currency_pair TEXT,
    timestamp TIMESTAMP,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    PRIMARY KEY ((currency_pair), ts)
) WITH CLUSTERING ORDER BY (ts DESC);

-- Tabel 2: features (lengkap dengan RSI (Relative Strength Index) , Bollinger Bands, dll)
CREATE TABLE IF NOT EXISTS features (
    currency_pair TEXT,
    timestamp TIMESTAMP,
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

-- Tabel 3: clustering_results (untuk 3 algoritma)
CREATE TABLE IF NOT EXISTS clustering_results (
    batch_id TEXT,
    timestamp TIMESTAMP,
    algorithm TEXT,
    currency_pair TEXT,
    cluster_label INT,
    cluster_name TEXT,
    is_outlier BOOLEAN,
    silhouette_score DOUBLE,
    PRIMARY KEY ((batch_id), ts, algorithm, currency_pair)
) WITH CLUSTERING ORDER BY (ts DESC);
