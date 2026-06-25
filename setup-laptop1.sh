#!/bin/bash
# ==========================================
# LAPTOP 1 — Data Ingestion Pipeline
# Zookeeper → Kafka → Producer Yahoo Finance
# ==========================================

set -euo pipefail

echo "========================================"
echo "  LAPTOP 1 — Data Ingestion"
echo "========================================"

# 1. Start Zookeeper + Kafka
echo "[1/4] Starting Zookeeper & Kafka..."
docker compose -f docker-compose-laptop1.yml up -d
sleep 10

# 2. Create Kafka topic
echo "[2/4] Creating Kafka topic 'forex-raw'..."
docker exec kafka-laptop1 kafka-topics --create \
  --if-not-exists \
  --bootstrap-server localhost:9092 \
  --partitions 3 --replication-factor 1 \
  --topic forex-raw

echo "[3/4] Verifying topic..."
docker exec kafka-laptop1 kafka-topics --list --bootstrap-server localhost:9092

# 3. Install dependencies
echo "[4/4] Installing Python dependencies..."
pip install -q kafka-python pandas websocket-client requests

echo ""
echo "========================================"
echo "  LAPTOP 1 READY"
echo "  Jalankan producer: cd producer && python main.py"
echo "========================================"
