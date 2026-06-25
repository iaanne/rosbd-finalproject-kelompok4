#!/bin/bash
# ==========================================
# LAPTOP 3 — Serving Layer
# Cassandra → Elasticsearch → FastAPI → React
# ==========================================

set -euo pipefail

echo "========================================"
echo "  LAPTOP 3 — Serving Layer"
echo "========================================"

# 1. Start all services (Cassandra, ES, FastAPI, React)
echo "[1/4] Starting all Docker services..."
docker compose -f docker-compose-laptop3.yml up -d

# 2. Wait for FastAPI health
echo "[2/4] Waiting for FastAPI to be healthy..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "  FastAPI ready!"
    break
  fi
  echo "  Waiting... ($i/30)"
  sleep 5
done

# 3. Backfill historical data + compute features
echo "[3/4] Running historical backfill & feature computation..."
docker exec fastapi-laptop3 python /app/populate_data.py 2>/dev/null || \
  echo "  (populate_data.py skipped — run manually if needed)"

# 4. Trigger initial clustering
echo "[4/4] Triggering initial clustering..."
curl -sf -X POST http://localhost:8000/api/run-clustering > /dev/null && \
  echo "  Clustering completed!"

echo ""
echo "========================================"
echo "  LAPTOP 3 READY"
echo "  Dashboard    : http://localhost:3000"
echo "  API Docs     : http://localhost:8000/docs"
echo "  FastAPI      : http://localhost:8000"
echo "========================================"
