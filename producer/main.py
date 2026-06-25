import time
import threading
import socket

# Monkey-patch socket to resolve host.docker.internal or localhost on port 9092 to Tailscale IP
_original_getaddrinfo = socket.getaddrinfo
def _patched_getaddrinfo(host, port, *args, **kwargs):
    print(f"[DNS RESOLVE] Resolving {host}:{port}", flush=True)
    if (host == "host.docker.internal" or host in ("localhost", "127.0.0.1", "::1", "localhost.")) and str(port) == "9092":
        print(f"[DNS REDIRECT] Redirected {host}:{port} -> 100.75.210.119:9092", flush=True)
        host = "100.75.210.119"
    return _original_getaddrinfo(host, port, *args, **kwargs)
socket.getaddrinfo = _patched_getaddrinfo

from config import FETCH_INTERVAL_SECONDS
from fetcher import start_tiingo_websocket, poll_exchangerate_api
from kafka_producer import get_producer


def main():
    print("=" * 50, flush=True)
    print("LAPTOP 1 - Data Ingestion (Tiingo WebSocket + ExchangeRate-API)", flush=True)
    print(f"REST Polling Interval: {FETCH_INTERVAL_SECONDS}s", flush=True)
    print("Kafka topic: forex-raw", flush=True)
    print("=" * 50, flush=True)

    print(f"[DEBUG] socket.getaddrinfo is: {socket.getaddrinfo}", flush=True)
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
        import os
        os._exit(0)
    finally:
        try:
            producer.flush()
            producer.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
