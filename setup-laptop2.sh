#!/bin/bash
# ==========================================
# LAPTOP 2 — Processing Layer
# Jupyter (Spark Local Mode)
# ==========================================

set -euo pipefail

echo "========================================"
echo "  LAPTOP 2 — Processing (Spark)"
echo "========================================"

echo "[1/1] Starting Jupyter Notebook..."
docker compose -f docker-compose-laptop2.yml up -d

echo "Waiting for service to initialize..."
sleep 5

echo ""
echo "========================================"
echo "  LAPTOP 2 READY"
echo "  Jupyter Lab     : http://localhost:8888"
echo "  Jalankan notebook processing/ di Jupyter"
echo "========================================"
