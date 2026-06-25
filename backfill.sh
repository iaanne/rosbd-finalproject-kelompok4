#!/bin/bash
# ==========================================
# Backfill Historical Data + Feature + Cluster
# Jalankan setelah setup-laptop3.sh
# ==========================================

set -euo pipefail

echo "========================================"
echo "  Backfill Historical Data"
echo "========================================"

# 1. Backfill forex_rates from Yahoo Finance
echo "[1/4] Running backfill_historical.py..."
docker exec fastapi-laptop3 python /app/backfill_historical.py

# 2. Compute features (rolling correlation, volatility, etc.)
echo "[2/4] Computing features..."
curl -sf -X POST http://localhost:8000/api/compute-features | python3 -m json.tool

# 3. Run clustering (K-Means + DBSCAN + AHC)
echo "[3/4] Running clustering..."
curl -sf -X POST http://localhost:8000/api/run-clustering | python3 -m json.tool

# 4. Verify
echo "[4/4] Verifying..."
curl -s http://localhost:8000/api/health
echo ""
curl -s http://localhost:8000/api/clustering/latest | python3 -c "
import sys, json
d = json.load(sys.stdin)
pairs = sorted(set(r['currency_pair'] for r in d.get('results', [])))
print(f'Clustering pairs ({len(pairs)}): {pairs}')
"

echo ""
echo "========================================"
echo "  BACKFILL COMPLETE"
echo "========================================"
