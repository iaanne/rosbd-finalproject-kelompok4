import socket
import logging
import sys
import json

# Monkey-patch socket
_original_getaddrinfo = socket.getaddrinfo
def _patched_getaddrinfo(host, port, *args, **kwargs):
    if (host == "host.docker.internal" or host in ("localhost", "127.0.0.1", "::1", "localhost.")) and str(port) == "9092":
        host = "100.75.210.119"
    return _original_getaddrinfo(host, port, *args, **kwargs)
socket.getaddrinfo = _patched_getaddrinfo

from kafka import KafkaConsumer

print("Connecting to Kafka consumer...", flush=True)
try:
    consumer = KafkaConsumer(
        "forex-raw",
        bootstrap_servers="100.75.210.119:9092",
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        consumer_timeout_ms=3000
    )
    print("Consumer connected. Waiting for messages...", flush=True)
    count = 0
    for msg in consumer:
        print(f"Partition: {msg.partition} | Key: {msg.key} | TS: {msg.value.get('ts')} | Pair: {msg.value.get('currency_pair')}", flush=True)
        count += 1
        if count >= 30:
            break
except Exception as e:
    import traceback
    traceback.print_exc()
