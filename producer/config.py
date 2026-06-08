KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "forex-raw"
FETCH_INTERVAL_SECONDS = 60

TICKERS = [
    "IDR=X",
    "THB=X",
    "SGD=X",
    "MYR=X",
    "PHP=X",
    "VND=X",
    "DX-Y.NYB",
    "CNY=X",
    "GC=F",
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
    "GC=F": "GOLD",
}
