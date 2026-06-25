#!/bin/bash
# ==========================================
# Init Kafka Topics
# Sesuaikan container name dengan setup
# ==========================================

set -euo pipefail

KAFKA_CONTAINER="${1:-kafka-laptop1}"
KAFKA_BROKER="localhost:9092"

echo "=== Init Kafka Topics ($KAFKA_CONTAINER) ==="
sleep 5

create_topic() {
  local TOPIC=$1
  local PART=${2:-3}
  echo "  Creating '$TOPIC' (partitions=$PART)..."
  docker exec "$KAFKA_CONTAINER" kafka-topics --create \
    --if-not-exists \
    --bootstrap-server "$KAFKA_BROKER" \
    --partitions "$PART" \
    --replication-factor 1 \
    --topic "$TOPIC"
}

create_topic "forex-raw" 3

echo "=== Topics ==="
docker exec "$KAFKA_CONTAINER" kafka-topics --list --bootstrap-server "$KAFKA_BROKER"
echo "=== Done ==="
