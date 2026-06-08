import yfinance as yf
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import TICKERS, CURRENCY_ALIAS


def fetch_ticker(ticker):
    try:
        data = yf.download(
            tickers=ticker,
            period="1d",
            interval="1m",
            progress=False,
        )
        if data.empty:
            return None

        row = data.iloc[-1]
        return {
            "currency_pair": CURRENCY_ALIAS.get(ticker, ticker),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "open": float(row["Open"].iloc[0]),
            "high": float(row["High"].iloc[0]),
            "low": float(row["Low"].iloc[0]),
            "close": float(row["Close"].iloc[0]),
            "volume": int(row["Volume"].iloc[0]) if pd.notna(row["Volume"].iloc[0]) else 0,
        }
    except Exception as e:
        print(f"[ERROR] Failed to fetch {ticker}: {e}")
        return None


def fetch_all():
    results = []
    with ThreadPoolExecutor(max_workers=9) as executor:
        futures = {executor.submit(fetch_ticker, t): t for t in TICKERS}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    return results
