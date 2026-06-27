# Real-Time Monitoring Dedolarisasi ASEAN

Dashboard monitoring real-time pergerakan mata uang ASEAN terhadap USD dan CNY, dilengkapi clustering (K-Means, DBSCAN, AHC), notifikasi Telegram, dan deteksi anomali.

**Kelompok 5 — ROSBD 4B**

| Anggota | Peran | Laptop |
|---------|-------|--------|
| Jimly Syahbatin (L0224033) | Data Ingestion (Kafka, Tiingo, ExchangeRate-API) | Laptop 1 |
| Nadhifa Sakha Tri Yasmin (L0224036) | Processing (Spark, Jupyter, Clustering) | Laptop 2 |
| Adrian Farrel Aziz Yatyoga (L0224040) | Serving Layer (API, Dashboard, Telegram) | Laptop 3 |

---

## Arsitektur Pipeline

```
LAPTOP 1                          LAPTOP 2                          LAPTOP 3
Data Ingestion                    Processing                        Serving
┌──────────────────────────┐     ┌──────────────────────┐     ┌──────────────────────────┐
│  Tiingo WebSocket FX     │     │  Jupyter (PySpark)   │     │  Apache Cassandra 5.0    │
│  ExchangeRate-API REST   │─K→  │  Spark Structured    │     │  Elasticsearch 8.14      │
│  Yahoo Finance (backfill)│     │  Streaming           │────→│  FastAPI (REST + WS)     │
│       ↓                  │     │  Feature Engineering │     │  React Dashboard (Vite)  │
│  Apache Kafka 7.6        │     │  K-Means / DBSCAN /  │     │  Telegram Bot            │
│  Zookeeper               │     │  AHC Clustering      │     │  Nginx (reverse proxy)   │
└──────────────────────────┘     └──────────────────────┘     └──────────────────────────┘
         ↕ Tailscale VPN ↕              ↕ Tailscale VPN ↕              ↕ Tailscale VPN ↕
```

### Alur Data
1. **Laptop 1** — Tiingo WebSocket (real-time FX quotes) + ExchangeRate-API (REST fallback tiap 60 detik) → Kafka topic `forex-raw`
2. **Laptop 2** — Spark Structured Streaming via Jupyter notebook baca dari Kafka → preprocessing → feature engineering (rolling correlation, volatility, RSI) → clustering (K-Means/DBSCAN/AHC) → simpan ke Cassandra
3. **Laptop 3** — FastAPI serving REST & WebSocket → React dashboard visualisasi → Telegram notifikasi alert

---

## Tech Stack

| Layer | Teknologi |
|-------|-----------|
| Data Source | Tiingo WebSocket FX, ExchangeRate-API REST, Yahoo Finance (`yfinance` backfill) |
| Message Broker | Apache Kafka 7.6 + Zookeeper |
| Processing | Apache Spark 3.5 (PySpark), scikit-learn, scipy, Jupyter |
| Database | Apache Cassandra 5.0, Elasticsearch 8.14 |
| Backend API | FastAPI (Python 3.10), aiokafka, httpx |
| Frontend | React 18, Vite 5, Tailwind CSS 4, D3.js |
| Notifikasi | Telegram Bot API |
| Networking | Tailscale VPN, proxychains4 |
| Container | Docker, Docker Compose |

---

## Struktur Folder

```
rosbd-finalproject-kelompok5/
├── producer/                           # Laptop 1 — Data Ingestion
│   ├── config.py                       #   Konfigurasi ticker, API key, Kafka broker
│   ├── fetcher.py                      #   Tiingo WebSocket + ExchangeRate-API poller
│   ├── kafka_producer.py               #   Kafka producer wrapper
│   └── main.py                         #   Entry point (WS thread + REST poller)
│
├── processing/                         # Laptop 2 — Spark Processing
│   ├── stream_reader.ipynb             #   Jupyter notebook: Spark Streaming + clustering
│   ├── backfill_historical.py          #   Backfill 5 tahun data Yahoo Finance ke Cassandra
│   ├── populate_data.py                #   Compute features + clustering standalone
│   └── checkpoints/                    #   Spark streaming checkpoint state
│
├── serving/                            # Laptop 3 — Serving Layer
│   ├── init-cassandra.cql              #   Schema Cassandra (keyspace + tables)
│   ├── init-elasticsearch.sh           #   Mapping index Elasticsearch
│   │
│   ├── fastapi/                        #   Backend API (Python/FastAPI)
│   │   ├── main.py                     #     FastAPI app, WebSocket, endpoints, periodic clustering
│   │   ├── cassandra_client.py         #     CRUD ke Cassandra
│   │   ├── clustering.py               #     K-Means, DBSCAN, AHC logic
│   │   ├── telegram_client.py          #     Kirim alert ke Telegram
│   │   ├── kafka_consumer.py           #     Async Kafka consumer → WebSocket broadcast
│   │   ├── elasticsearch_client.py     #     Index & search Elasticsearch
│   │   ├── start.sh                    #     Entrypoint container (Tailscale + uvicorn)
│   │   ├── Dockerfile                  #     Python 3.10 + Tailscale
│   │   ├── requirements.txt            #     Python dependencies
│   │   ├── .env.example                #     Template environment variables
│   │   └── notifications.py            #     (deprecated — logic pindah ke main.py)
│   │
│   └── react-dashboard/                #   Frontend React
│       ├── src/
│       │   ├── main.jsx                #     Entry point React
│       │   ├── App.jsx                 #     Semua komponen dashboard inline (~1100 baris)
│       │   └── App.css                 #     Tailwind CSS v4 + custom dark theme
│       ├── Dockerfile                  #     Multi-stage build (Vite → Nginx)
│       ├── nginx.conf                  #     Reverse proxy /api & /ws ke FastAPI
│       ├── vite.config.js              #     Dev server proxy ke FastAPI
│       └── package.json                #     React 18, Vite 5, Tailwind CSS 4
│
├── scripts/                            # Script utilitas
│   ├── check_cassandra.py              #   Diagnostik isi tabel Cassandra
│   ├── create-kafka-topics.sh          #   Init Kafka topic
│   └── update_notebook.py              #   Update cell notebook programmatically
│
├── scratch/                            # Script testing sementara
│   ├── test_consumer.py                #   Test Kafka consumer
│   └── test_dns.py                     #   Test DNS resolution Kafka broker
│
├── docker-compose-laptop1.yml          # Service Laptop 1 (Zookeeper + Kafka)
├── docker-compose-laptop2.yml          # Service Laptop 2 (Jupyter/Spark)
├── docker-compose-laptop3.yml          # Service Laptop 3 (Cassandra, ES, FastAPI, React)
│
├── setup-laptop1.sh                    # One-command setup Laptop 1
├── setup-laptop2.sh                    # One-command setup Laptop 2
├── setup-laptop3.sh                    # One-command setup Laptop 3
├── backfill.sh                         # Backfill historical data + compute features + cluster
├── create-kafka-topics.sh              # Inisialisasi topic Kafka
│
├── .env                                # Telegram bot token & chat ID
└── .gitignore
```

---

## Networking (Tailscale)

Setiap laptop terhubung via **Tailscale VPN** dengan IP statis:

| Laptop | Tailscale IP | Service |
|--------|-------------|---------|
| Laptop 1 | `100.75.210.119` | Kafka broker |
| Laptop 2 | — | Akses ke Kafka Laptop 1 |
| Laptop 3 | `100.66.223.98` | Cassandra, FastAPI |

- Kafka `advertised.listeners` di-set ke Tailscale IP Laptop 1 (`100.75.210.119:9092`)
- Producer menggunakan monkey-patch DNS untuk redirect `localhost:9092` → `100.75.210.119:9092`
- FastAPI container menggunakan Tailscale + proxychains4 untuk routing jaringan

---

## Cara Menjalankan (Quick Start)

### Prasyarat
- Docker & Docker Compose terinstall di semua laptop
- Tailscale terinstall dan terautentikasi di semua laptop
- Network antar laptop terhubung via Tailscale

### Laptop 1 — Data Ingestion
```bash
chmod +x setup-laptop1.sh
./setup-laptop1.sh

# Setelah selesai, jalankan producer:
cd producer
pip install kafka-python pandas websocket-client requests
python main.py
```

### Laptop 2 — Processing
```bash
chmod +x setup-laptop2.sh
./setup-laptop2.sh

# Buka Jupyter Lab di http://localhost:8888
# Jalankan notebook processing/stream_reader.ipynb
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
pip install kafka-python pandas websocket-client requests
python main.py
```

### Laptop 2 — Jupyter/Spark

```bash
# 1. Start Jupyter with PySpark
docker compose -f docker-compose-laptop2.yml up -d

# 2. Akses Jupyter Lab di http://localhost:8888
#    Jalankan notebook processing/stream_reader.ipynb
```

### Laptop 3 — Cassandra + Elasticsearch + FastAPI + React

```bash
# 1. Start semua service
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
| POST | `/api/forex-rates` | Insert forex rate baru |
| GET | `/api/features/{pair}?limit=N` | Fitur teknis (rolling corr, vol, RSI) |
| POST | `/api/compute-features` | Compute ulang fitur dari forex_rates |
| GET | `/api/batches?limit=N` | Daftar batch clustering |
| GET | `/api/clustering/latest` | Hasil clustering terbaru |
| GET | `/api/clustering-results/{batch_id}` | Hasil clustering per batch |
| POST | `/api/clustering-results` | Insert hasil clustering |
| GET | `/api/clustering-metrics/latest` | Silhouette score terbaru |
| GET | `/api/clustering-metrics/{batch_id}` | Metrics per batch |
| POST | `/api/run-clustering` | Jalankan clustering (K-Means + DBSCAN + AHC) |
| GET | `/api/ikr-ranking` | Ranking kerentanan mata uang ASEAN |
| GET | `/api/corr-delta/{pair}` | Delta korelasi DXY |
| GET | `/api/cluster-logs` | Cari log clustering dari Elasticsearch |
| POST | `/api/cluster-logs` | Insert log clustering ke Elasticsearch |
| GET | `/api/notifications?limit=N` | Riwayat notifikasi |
| GET | `/api/currency-pairs` | Daftar currency pair unik |
| GET | `/api/test-alert` | Test notifikasi Telegram |
| POST | `/api/data-update` | Ingest data dari Spark |
| WS | `/ws` | WebSocket real-time price + alert |

---

## Notifikasi Telegram

1. Buat bot via `@BotFather` di Telegram, dapatkan token
2. Tambahkan bot ke supergroup, dapatkan chat ID
3. Set di `.env` root project:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=-1001234567890
   ```
4. Restart FastAPI: `docker compose -f docker-compose-laptop3.yml up -d fastapi`

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Kafka tidak connect | Pastikan Laptop 1 nyala dan Tailscale IP sesuai di `KAFKA_BOOTSTRAP_SERVERS` |
| Cassandra timeout | `docker compose -f docker-compose-laptop3.yml restart cassandra` |
| Dashboard blank | `docker compose -f docker-compose-laptop3.yml build react && docker compose -f docker-compose-laptop3.yml up -d react` |
| Data clustering kosong | Jalankan `curl -X POST http://localhost:8000/api/run-clustering` |
| Ingin reset data | `docker compose -f docker-compose-laptop3.yml down -v && docker compose -f docker-compose-laptop3.yml up -d` |
| WebSocket tidak connect | Pastikan port 8000 terbuka dan Tailscale aktif di Laptop 3 |
