#!/bin/bash
# ==========================================
# LAPTOP 2 — Processing Layer
# Spark Master → Spark Worker → Jupyter
# ==========================================

set -euo pipefail

echo "========================================"
echo "  LAPTOP 2 — Processing (Spark)"
echo "========================================"

echo "[1/2] Starting Spark cluster..."
docker compose -f docker-compose-laptop2.yml up -d

echo "[2/2] Waiting for Spark Master UI (port 8080)..."
sleep 10

echo ""
echo "========================================"
echo "  LAPTOP 2 READY"
echo "  Spark Master UI : http://localhost:8080"
echo "  Jupyter Lab     : http://localhost:8888"
echo "  Jalankan notebook processing/ di Jupyter"
echo "========================================"
