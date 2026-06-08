#!/bin/bash
echo "Waiting for Kafka to be ready..."
until kafka-topics --bootstrap-server localhost:9092 --list > /dev/null 2>&1; do
  sleep 2
done

echo "Creating topic: forex-raw"
kafka-topics --bootstrap-server localhost:9092 \
  --create \
  --topic forex-raw \
  --partitions 3 \
  --replication-factor 1 \
  --if-not-exists

echo "Topic created. Verifying..."
kafka-topics --bootstrap-server localhost:9092 --describe --topic forex-raw
