import math
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import TICKERS, CURRENCY_ALIAS


def _safe_float(value):
    """Ambil skalar float dari sel yfinance (bisa Series akibat MultiIndex)."""
    if hasattr(value, "iloc"):
        value = value.iloc[0]
    return float(value)


def fetch_ticker(ticker):
    try:
        data = yf.download(
            tickers=ticker,
            period="1d",
            interval="1m",
            progress=False,
            auto_adjust=False,
        )
        if data.empty:
            print(f"[WARN] No data for {ticker} (market closed / empty)")
            return None

        row = data.iloc[-1]
        close = _safe_float(row["Close"])

        # Buang record kosong supaya korelasi/volatilitas tidak jadi NaN
        if close is None or math.isnan(close):
            print(f"[WARN] Skipping {ticker}: close is NaN")
            return None

        volume_raw = row["Volume"]
        if hasattr(volume_raw, "iloc"):
            volume_raw = volume_raw.iloc[0]

        return {
            "currency_pair": CURRENCY_ALIAS.get(ticker, ticker),
            "ts": datetime.now(timezone.utc).isoformat(),  # field "ts" (cocok PK Cassandra)
            "source": "yahoo_finance",
            "open": _safe_float(row["Open"]),
            "high": _safe_float(row["High"]),
            "low": _safe_float(row["Low"]),
            "close": close,
            "volume": int(volume_raw) if pd.notna(volume_raw) else 0,
        }
    except Exception as e:
        print(f"[ERROR] Failed to fetch {ticker}: {e}")
        return None


def fetch_all():
    results = []
    with ThreadPoolExecutor(max_workers=len(TICKERS)) as executor:
        futures = {executor.submit(fetch_ticker, t): t for t in TICKERS}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    return results
