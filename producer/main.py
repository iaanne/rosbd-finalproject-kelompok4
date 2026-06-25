import time
import threading
from config import FETCH_INTERVAL_SECONDS
from fetcher import start_tiingo_websocket, poll_exchangerate_api
from kafka_producer import get_producer


def main():
    print("=" * 50)
    print("LAPTOP 1 - Data Ingestion (Tiingo WebSocket + ExchangeRate-API)")
    print(f"REST Polling Interval: {FETCH_INTERVAL_SECONDS}s")
    print("Kafka topic: forex-raw")
    print("=" * 50)

    producer = get_producer()

    # 1. Start Tiingo WebSocket in a background thread
    ws_thread = threading.Thread(
        target=start_tiingo_websocket, args=(producer,), daemon=True
    )
    ws_thread.start()
    print("[INIT] Tiingo WebSocket thread started.")

    # 2. Run ExchangeRate-API Poller in the main thread
    try:
        poll_exchangerate_api(producer, FETCH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[STOP] Shutting down producer...")
    finally:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    main()
