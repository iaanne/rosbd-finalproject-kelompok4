import os

# Manual .env loader
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
print(f"[CONFIG DEBUG] env_path: {env_path}, exists: {os.path.exists(env_path)}, KAFKA_BROKER: {KAFKA_BROKER}", flush=True)
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "forex-raw")
FETCH_INTERVAL_SECONDS = int(os.getenv("FETCH_INTERVAL_SECONDS", "60"))

TIINGO_API_KEY = os.getenv("TIINGO_API_KEY", "fd9f6e7e0e6f946f194da423beec04e781abe53e")
EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY", "e2b644e44f0221bc559cfab3")

# Tiingo WebSocket Tickers
# ASEAN pairs + DXY components
TIINGO_TICKERS = [
    "usdidr", "usdthb", "usdsgd", "usdmyr", "usdphp", "usdvnd",
    "eurusd", "usdjpy", "gbpusd", "usdcad", "usdsek", "usdchf"
]

# Alias mapping for Kafka/Cassandra compatibility
CURRENCY_ALIAS = {
    "USDIDR": "IDR",
    "USDTHB": "THB",
    "USDSGD": "SGD",
    "USDMYR": "MYR",
    "USDPHP": "PHP",
    "USDVND": "VND",
    "USDCNY": "CNY",
}