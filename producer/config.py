import os

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "forex-raw")
FETCH_INTERVAL_SECONDS = int(os.getenv("FETCH_INTERVAL_SECONDS", "60"))

# DXY & CNY WAJIB ada -> input corr_dxy & corr_cny (inti IKR + cluster).
# GOLD (GC=F) dibuang karena di luar scope Investor + Bank Indonesia.
TICKERS = [
    "IDR=X",
    "THB=X",
    "SGD=X",
    "MYR=X",
    "PHP=X",
    "VND=X",
    "DX-Y.NYB",
    "CNY=X",
]

CURRENCY_ALIAS = {
    "IDR=X": "IDR",
    "THB=X": "THB",
    "SGD=X": "SGD",
    "MYR=X": "MYR",
    "PHP=X": "PHP",
    "VND=X": "VND",
    "DX-Y.NYB": "DXY",
    "CNY=X": "CNY",
}