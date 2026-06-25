import yfinance as yf
import pandas as pd
import numpy as np
from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args
from datetime import datetime, timezone
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

import os
CASSANDRA_HOST = os.getenv("CASSANDRA_HOST", "100.66.223.98")
KEYSPACE = "dedolarisasi"

TICKERS = {
    "IDR=X": "IDR",
    "THB=X": "THB",
    "SGD=X": "SGD",
    "MYR=X": "MYR",
    "PHP=X": "PHP",
    "VND=X": "VND",
    "DX-Y.NYB": "DXY",
    "CNY=X": "CNY",
}

logger.info("Connecting to Cassandra at %s ...", CASSANDRA_HOST)
cluster = Cluster([CASSANDRA_HOST])
session = cluster.connect(KEYSPACE)
session.execute("TRUNCATE forex_rates;")
logger.info("forex_rates truncated.")

insert_stmt = session.prepare(
    "INSERT INTO forex_rates (currency_pair, ts, open, high, low, close, volume) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)"
)

total_inserted = 0
for yf_ticker, pair_name in TICKERS.items():
    logger.info("Fetching 5y daily data for %s (%s) ...", yf_ticker, pair_name)
    try:
        ticker = yf.Ticker(yf_ticker)
        hist = ticker.history(period="5y", interval="1d")
        if hist.empty:
            logger.warning("No data for %s, skipping.", yf_ticker)
            continue
        hist = hist.reset_index()
        params = []
        for _, row in hist.iterrows():
            ts = row["Date"]
            if isinstance(ts, pd.Timestamp):
                ts = ts.to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)
            open_p = float(row["Open"]) if not pd.isna(row["Open"]) else 0.0
            high_p = float(row["High"]) if not pd.isna(row["High"]) else 0.0
            low_p = float(row["Low"]) if not pd.isna(row["Low"]) else 0.0
            close_p = float(row["Close"]) if not pd.isna(row["Close"]) else 0.0
            volume = int(row["Volume"]) if not pd.isna(row["Volume"]) else 0
            params.append((pair_name, ts, open_p, high_p, low_p, close_p, volume))
        
        results = execute_concurrent_with_args(session, insert_stmt, params)
        count = len(results)
        total_inserted += count
        logger.info("Inserted %d rows for %s", count, pair_name)
    except Exception as e:
        logger.error("Failed fetching/inserting %s: %s", yf_ticker, e)

logger.info("Backfill selesai! Total: %d rows inserted.", total_inserted)
cluster.shutdown()
