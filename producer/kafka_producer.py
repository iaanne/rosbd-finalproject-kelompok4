import json
from kafka import KafkaProducer

from config import KAFKA_BROKER, KAFKA_TOPIC


def get_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),  # key = currency_pair
        acks="all",                                   # jaminan terkirim
        retries=5,
        linger_ms=10,
    )


def send_data(producer, records):
    for record in records:
        pair = record["currency_pair"]
        # key=pair -> 1 mata uang konsisten di 1 partisi (urutan waktu terjaga)
        future = producer.send(KAFKA_TOPIC, key=pair, value=record)
        future.add_callback(lambda m, p=pair: print(f"[SENT] {p} -> partition {m.partition}"))
        future.add_errback(lambda e, p=pair: print(f"[ERROR] {p}: {e}"))
    producer.flush()
