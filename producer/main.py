import time
from config import FETCH_INTERVAL_SECONDS
from fetcher import fetch_all
from kafka_producer import get_producer, send_data


def main():
    print("=" * 50)
    print("LAPTOP 1 - Data Ingestion")
    print(f"Fetching every {FETCH_INTERVAL_SECONDS}s -> Kafka topic: forex-raw")
    print("=" * 50)

    producer = get_producer()

    while True:
        try:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Fetching forex data...")
            records = fetch_all()
            if records:
                send_data(producer, records)
                print(f"[OK] Sent {len(records)} records to Kafka")
            else:
                print("[WARN] No data fetched")
        except Exception as e:
            print(f"[ERROR] {e}")

        time.sleep(FETCH_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
