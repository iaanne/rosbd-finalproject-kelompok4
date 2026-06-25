import socket
import logging
import sys

# Enable kafka-python logging to stdout
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# Monkey-patch socket
_original_getaddrinfo = socket.getaddrinfo
def _patched_getaddrinfo(host, port, *args, **kwargs):
    print(f"[DNS RESOLVE] Resolving {host}:{port}", flush=True)
    if host == "host.docker.internal":
        print(f"[DNS REDIRECT] Redirected host.docker.internal -> 100.75.210.119", flush=True)
        host = "100.75.210.119"
    return _original_getaddrinfo(host, port, *args, **kwargs)
socket.getaddrinfo = _patched_getaddrinfo

from kafka import KafkaProducer

print("Initializing producer...", flush=True)
try:
    producer = KafkaProducer(
        bootstrap_servers="100.75.210.119:9092",
        request_timeout_ms=5000,
        metadata_max_age_ms=5000
    )
    print("Producer initialized successfully!", flush=True)
    print("Fetching metadata...", flush=True)
    meta = producer.partitions_for("forex-raw")
    print(f"Metadata partitions: {meta}", flush=True)
except Exception as e:
    import traceback
    traceback.print_exc()
