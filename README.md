# Real-Time Monitoring Dedolarisasi ASEAN

Dashboard monitoring real-time pergerakan mata uang ASEAN terhadap USD dan CNY, dilengkapi clustering (K-Means, DBSCAN, AHC), notifikasi Telegram, dan deteksi anomali.

**Kelompok 4 — ROSBD 4B**

| Anggota | Peran | Laptop |
|---------|-------|--------|
| Nadhifa Sakha Tri Yasmin (L0224036) | Data Ingestion (Kafka, Yahoo Finance) | Laptop 1 |
| Jimly Syahbatin (L0224033) | Processing (Spark, Clustering) | Laptop 2 |
| Adrian Farrel Aziz Yatyoga (L0224040) | Serving Layer (API, Dashboard) | Laptop 3 |

---

## Arsitektur Pipeline

```
LAPTOP 1                    LAPTOP 2                    LAPTOP 3
Data Ingestion              Processing                  Serving
┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
│  Yahoo Finance     │     │  Apache Spark      │     │  Cassandra         │
│       ↓            │     │       ↓            │     │  Elasticsearch     │
│  Python Producer   │─K→  │  Preprocessing     │     │  FastAPI (Python)  │
│       ↓            │     │       ↓            │     │  React Dashboard   │
│  Apache Kafka      │     │  K-Means, DBSCAN,  │     │  Telegram Bot      │
│  Zookeeper         │     │  AHC               │────→│  Nginx (reverse    │
└────────────────────┘     └────────────────────┘     │  proxy)            │
                                                       └────────────────────┘
```

### Alur Data
1. **Laptop 1** — Yahoo Finance → Python Producer → Kafka topic `forex-raw`
2. **Laptop 2** — Spark Streaming baca dari Kafka → preprocessing → clustering (K-Means/DBSCAN/AHC) → simpan ke Cassandra
3. **Laptop 3** — FastAPI serving REST & WebSocket → React dashboard visualisasi → Telegram notifikasi

---

## Tech Stack

| Layer | Teknologi |
|-------|-----------|
| Data Source | Yahoo Finance API (`yfinance`) |
| Message Broker | Apache Kafka 7.6 + Zookeeper |
| Processing | Apache Spark 3.5, scikit-learn, scipy |
| Database | Apache Cassandra 5, Elasticsearch 8.14 |
| Backend API | FastAPI (Python 3.12) |
| Frontend | React 18, Vite, Tailwind CSS, D3.js |
| Notifikasi | Telegram Bot API (`httpx`) |
| Container | Docker, Docker Compose |

---

## Struktur Folder

```
rosbd-finalproject-kelompok4/
├── producer/                        # Laptop 1 — Data Ingestion
│   ├── config.py                    #   Konfigurasi ticker & Kafka
│   ├── fetcher.py                   #   Fetch OHLCV dari Yahoo Finance
│   ├── kafka_producer.py            #   Kirim ke Kafka topic forex-raw
│   └── main.py                      #   Loop utama (tiap 60 detik)
│
├── processing/                      # Laptop 2 — Spark Processing
│   ├── spark_forex_streaming.py     #   Spark Structured Streaming
│   ├── spark_clustering.py          #   Clustering dengan Spark ML
│   └── populate_data.py             #   Backfill fitur + clustering
│
├── serving/                         # Laptop 3 — Serving Layer
│   ├── fastapi/                     #   Backend API (Python)
│   │   ├── main.py                  #     FastAPI app, WebSocket, endpoints
│   │   ├── cassandra_client.py      #     CRUD ke Cassandra
│   │   ├── clustering.py            #     K-Means, DBSCAN, AHC logic
│   │   ├── telegram_client.py       #     Kirim alert ke Telegram
│   │   ├── kafka_consumer.py        #     Consumer WebSocket broadcast
│   │   ├── backfill_historical.py   #     Backfill Yahoo Finance ke DB
│   │   └── populate_data.py         #     Compute features + cluster
│   │
│   └── react-dashboard/             #   Frontend React
│       ├── src/
│       │   ├── App.jsx              #     Komponen utama dashboard
│       │   └── App.css              #     Styling Tailwind + CSS
│       ├── Dockerfile               #     Multi-stage build (Vite → Nginx)
│       └── nginx.conf               #     Reverse proxy ke FastAPI
│
├── docker-compose-laptop1.yml       # Service Laptop 1 (Kafka)
├── docker-compose-laptop2.yml       # Service Laptop 2 (Spark)
├── docker-compose-laptop3.yml       # Service Laptop 3 (Cassandra, ES, API, React)
│
├── setup-laptop1.sh                 # One-command setup Laptop 1
├── setup-laptop2.sh                 # One-command setup Laptop 2
├── setup-laptop3.sh                 # One-command setup Laptop 3
├── backfill.sh                      # Backfill historical data + clustering
├── create-kafka-topics.sh           # Inisialisasi topic Kafka
│
├── serving/init-cassandra.cql       # Schema Cassandra
└── serving/init-elasticsearch.sh    # Mapping Elasticsearch
```

---

## Cara Menjalankan (Quick Start dengan .sh)

### Prasyarat
- Docker & Docker Compose terinstall di semua laptop
- Network antar laptop terhubung (Kafka via `host.docker.internal`)

### Laptop 1 — Data Ingestion
```bash
chmod +x setup-laptop1.sh
./setup-laptop1.sh

# Setelah selesai, jalankan producer:
cd producer
pip install kafka-python yfinance pandas
python main.py
```

### Laptop 2 — Processing
```bash
chmod +x setup-laptop2.sh
./setup-laptop2.sh

# Buka Jupyter Lab di http://localhost:8888
# Jalankan notebook processing/ secara berurutan
```

### Laptop 3 — Serving Layer
```bash
chmod +x setup-laptop3.sh backfill.sh
./setup-laptop3.sh

# Backfill historical data (tunggu ~5 menit):
./backfill.sh

# Dashboard: http://localhost:3000
# API Docs:   http://localhost:8000/docs
```

---

## Cara Menjalankan (Manual Step-by-Step)

### Laptop 1 — Zookeeper + Kafka + Producer

```bash
# 1. Start Zookeeper & Kafka
docker compose -f docker-compose-laptop1.yml up -d

# 2. Buat Kafka topic
docker exec kafka-laptop1 kafka-topics --create \
  --if-not-exists \
  --bootstrap-server localhost:9092 \
  --partitions 3 --replication-factor 1 \
  --topic forex-raw

# 3. Jalankan producer
cd producer
pip install kafka-python yfinance pandas
python main.py
```

### Laptop 2 — Spark Cluster

```bash
# 1. Start Spark
docker compose -f docker-compose-laptop2.yml up -d

# 2. Akses Jupyter Lab di http://localhost:8888
#    Jalankan file .ipynb di folder processing/ secara berurutan
```

### Laptop 3 — Cassandra + Elasticsearch + FastAPI + React

```bash
# 1. Start semua service (Cassandra, ES, FastAPI, React)
docker compose -f docker-compose-laptop3.yml up -d

# 2. Tunggu sampai semua container healthy
docker compose -f docker-compose-laptop3.yml ps

# 3. (Opsional) Backfill historical data Yahoo Finance
docker exec fastapi-laptop3 python /app/backfill_historical.py

# 4. Compute features (rolling correlation, volatility, dll)
curl -X POST http://localhost:8000/api/compute-features

# 5. Jalankan clustering
curl -X POST http://localhost:8000/api/run-clustering

# 6. Verifikasi
curl http://localhost:8000/api/health
curl http://localhost:8000/api/batches?limit=3
```

---

## Endpoint API

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/health` | Health check |
| GET | `/api/forex-rates/{pair}?limit=N` | Data OHLCV historis |
| GET | `/api/features/{pair}?limit=N` | Fitur teknis (rolling corr, vol, RSI) |
| POST | `/api/compute-features` | Compute ulang fitur dari forex_rates |
| GET | `/api/batches?limit=N` | Daftar batch clustering |
| GET | `/api/clustering/latest` | Hasil clustering terbaru |
| GET | `/api/clustering-results/{batch_id}` | Hasil clustering per batch |
| GET | `/api/clustering-metrics/latest` | Silhouette score terbaru |
| POST | `/api/run-clustering` | Jalankan clustering (K-Means + DBSCAN + AHC) |
| GET | `/api/ikr-ranking` | Ranking kerentanan mata uang ASEAN |
| GET | `/api/corr-delta/{pair}` | Delta korelasi DXY |
| GET | `/api/notifications?limit=N` | Riwayat notifikasi |
| WS | `/ws` | WebSocket real-time price + alert |

---

## Notifikasi Telegram

1. Buat bot via `@BotFather` di Telegram, dapatkan token
2. Tambahkan bot ke supergroup, dapatkan chat ID
3. Set di `.env` root project:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID_INVESTOR=-1001234567890
   ```
4. Restart FastAPI: `docker compose -f docker-compose-laptop3.yml up -d fastapi`

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Kafka tidak connect | Pastikan Laptop 1 nyala dan IP sesuai di `KAFKA_BOOTSTRAP_SERVERS` |
| Cassandra timeout | `docker compose -f docker-compose-laptop3.yml restart cassandra` |
| Dashboard blank | `docker compose -f docker-compose-laptop3.yml build react && docker compose -f docker-compose-laptop3.yml up -d react` |
| Data clustering kosong | Jalankan `curl -X POST http://localhost:8000/api/run-clustering` |
| Ingin reset data | `docker compose -f docker-compose-laptop3.yml down -v && docker compose -f docker-compose-laptop3.yml up -d` |
