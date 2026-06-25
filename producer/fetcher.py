import json
import time
import requests
import websocket
import threading
from datetime import datetime, timezone

from config import TIINGO_API_KEY, EXCHANGE_RATE_API_KEY, CURRENCY_ALIAS
from kafka_producer import send_data

# Global cache to keep track of latest rates and calculate DXY
latest_rates = {
    "EURUSD": None,
    "USDJPY": None,
    "GBPUSD": None,
    "USDCAD": None,
    "USDSEK": None,
    "USDCHF": None,
    "IDR": None,
    "THB": None,
    "SGD": None,
    "MYR": None,
    "PHP": None,
    "VND": None,
    "CNY": None,
    "DXY": None,
}

cache_lock = threading.Lock()
last_sent_time = {}
RATE_LIMIT_SECONDS = 10.0


def should_send(pair):
    now = time.time()
    if pair not in last_sent_time or (now - last_sent_time[pair]) >= RATE_LIMIT_SECONDS:
        last_sent_time[pair] = now
        return True
    return False


def create_record(pair_name, price, source):
    return {
        "currency_pair": pair_name,
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "open": float(price),
        "high": float(price),
        "low": float(price),
        "close": float(price),
        "volume": 0,
    }


def process_tiingo_quote(ticker, price, producer):
    ticker = ticker.upper()
    with cache_lock:
        if ticker in latest_rates:
            # DXY component
            latest_rates[ticker] = price
            recalculate_and_send_dxy(producer)
        elif ticker in CURRENCY_ALIAS:
            # ASEAN pair
            pair_name = CURRENCY_ALIAS[ticker]
            latest_rates[pair_name] = price
            if should_send(pair_name):
                record = create_record(pair_name, price, "tiingo_websocket")
                send_data(producer, [record])


def recalculate_and_send_dxy(producer):
    components = ["EURUSD", "USDJPY", "GBPUSD", "USDCAD", "USDSEK", "USDCHF"]
    if any(latest_rates[c] is None for c in components):
        return

    eurusd = latest_rates["EURUSD"]
    usdjpy = latest_rates["USDJPY"]
    gbpusd = latest_rates["GBPUSD"]
    usdcad = latest_rates["USDCAD"]
    usdsek = latest_rates["USDSEK"]
    usdchf = latest_rates["USDCHF"]

    dxy = (
        50.14348112
        * (eurusd**-0.576)
        * (usdjpy**0.136)
        * (gbpusd**-0.119)
        * (usdcad**0.091)
        * (usdsek**0.042)
        * (usdchf**0.036)
    )
    latest_rates["DXY"] = dxy

    if should_send("DXY"):
        record = create_record("DXY", dxy, "calculated_tiingo")
        send_data(producer, [record])


def poll_exchangerate_api(producer, interval):
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_RATE_API_KEY}/latest/USD"
    while True:
        try:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Polling ExchangeRate-API...")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("result") == "success":
                    rates = data.get("conversion_rates", {})
                    records_to_send = []

                    # 1. Update CNY
                    cny_rate = rates.get("CNY")
                    if cny_rate:
                        records_to_send.append(create_record("CNY", cny_rate, "exchangerate_api"))
                        with cache_lock:
                            latest_rates["CNY"] = cny_rate

                    # 2. Update DXY components in cache (for DXY calculation fallback)
                    with cache_lock:
                        eur = rates.get("EUR")
                        gbp = rates.get("GBP")
                        jpy = rates.get("JPY")
                        cad = rates.get("CAD")
                        sek = rates.get("SEK")
                        chf = rates.get("CHF")

                        if eur:
                            latest_rates["EURUSD"] = 1.0 / eur
                        if gbp:
                            latest_rates["GBPUSD"] = 1.0 / gbp
                        if jpy:
                            latest_rates["USDJPY"] = jpy
                        if cad:
                            latest_rates["USDCAD"] = cad
                        if sek:
                            latest_rates["USDSEK"] = sek
                        if chf:
                            latest_rates["USDCHF"] = chf

                        if all(
                            latest_rates[c] is not None
                            for c in [
                                "EURUSD",
                                "USDJPY",
                                "GBPUSD",
                                "USDCAD",
                                "USDSEK",
                                "USDCHF",
                            ]
                        ):
                            dxy = (
                                50.14348112
                                * (latest_rates["EURUSD"] ** -0.576)
                                * (latest_rates["USDJPY"] ** 0.136)
                                * (latest_rates["GBPUSD"] ** -0.119)
                                * (latest_rates["USDCAD"] ** 0.091)
                                * (latest_rates["USDSEK"] ** 0.042)
                                * (latest_rates["USDCHF"] ** 0.036)
                            )
                            latest_rates["DXY"] = dxy
                            if should_send("DXY"):
                                records_to_send.append(
                                    create_record(
                                        "DXY", dxy, "calculated_exchangerate_api"
                                    )
                                )

                    # 3. Fallback for ASEAN pairs if websocket is down
                    for currency_code in ["IDR", "THB", "SGD", "MYR", "PHP", "VND"]:
                        rate = rates.get(currency_code)
                        if rate:
                            if should_send(currency_code):
                                records_to_send.append(
                                    create_record(
                                        currency_code, rate, "exchangerate_api_fallback"
                                    )
                                )
                                with cache_lock:
                                    latest_rates[currency_code] = rate

                    if records_to_send:
                        send_data(producer, records_to_send)
                        print(f"[REST] Sent {len(records_to_send)} records to Kafka")
                else:
                    print(f"[REST ERROR] ExchangeRate-API failed: {data.get('error-type')}")
            else:
                print(f"[REST ERROR] HTTP {response.status_code}")
        except Exception as e:
            print(f"[REST ERROR] Failed to poll ExchangeRate-API: {e}")

        time.sleep(interval)


def start_tiingo_websocket(producer):
    def on_message(ws, message):
        try:
            msg = json.loads(message)
            msg_type = msg.get("messageType")
            if msg_type == "H":
                return
            elif msg_type == "A" and "data" in msg:
                data = msg["data"]
                if not data:
                    return

                def process_row(row):
                    if len(row) >= 7 and row[0] == "Q":
                        ticker = row[1]
                        mid = row[5]
                        bid = row[4]
                        ask = row[6]
                        price = mid if (mid is not None) else (bid + ask) / 2.0
                        process_tiingo_quote(ticker, price, producer)

                if isinstance(data[0], list):
                    for row in data:
                        process_row(row)
                else:
                    process_row(data)
        except Exception as e:
            print(f"[WS ERROR] Failed to parse message: {e}")

    def on_error(ws, error):
        print(f"[WS ERROR] {error}")

    def on_close(ws, close_status_code, close_msg):
        print(f"[WS CLOSE] Connection closed: {close_status_code} - {close_msg}")

    def on_open(ws):
        print("[WS OPEN] Connection opened. Subscribing to Tiingo FX...")
        subscribe_msg = {
            "eventName": "subscribe",
            "eventData": {"authToken": TIINGO_API_KEY},
        }
        ws.send(json.dumps(subscribe_msg))

    ws_url = "wss://api.tiingo.com/fx"

    while True:
        try:
            print(f"[WS] Connecting to {ws_url} ...")
            ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
            )
            ws.run_forever()
        except Exception as e:
            print(f"[WS ERROR] WebSocket crashed: {e}")
        print("[WS] Reconnecting in 5 seconds...")
        time.sleep(5)
