# Real-Time Monitoring Tren Dedolarisasi dan Dampaknya terhadap Stabilitas Mata Uang ASEAN

## Kelompok 4
| Anggota | Peran | Laptop |
|---------|-------|--------|
| **Nadhifa Sakha Tri Yasmin** (L0224036) | Data Ingestion | Laptop 1 |
| **Jimly Syahbatin** (L0224033) | Processing (Spark + Clustering) | Laptop 2 |
| **Adrian Farrel Aziz Yatyoga** (L0224040) | Serving Layer (API + Dashboard) | Laptop 3 |

## Arsitektur Sistem
LAPTOP 1                    LAPTOP 2                    LAPTOP 3
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  Yahoo Finance   │       │  Apache Spark    │       │  Cassandra       │
│       ↓          │       │       ↓          │       │  Elasticsearch   │
│  Python Producer │─Kafka→│  Preprocessing   │       │  FastAPI         │
│       ↓          │       │       ↓          │       │  React Dashboard │
│  Apache Kafka    │       │  K-Means, DBSCAN,│       │                  │
│  Zookeeper       │       │  AHC             │──────→│                  │
└──────────────────┘       └──────────────────┘       └──────────────────┘
 Data Ingestion             Processing Layer           Serving Layer

## Tech Stack
- **Data Ingestion**: Apache Kafka, Zookeeper, Python, Yahoo Finance API
- **Processing**: Apache Spark Structured Streaming, PySpark ML, scikit-learn, scipy
- **Storage**: Apache Cassandra, Elasticsearch
- **Serving**: FastAPI, React 18 + TypeScript + Vite + Recharts + D3.js + Tailwind CSS
- **Infrastructure**: Docker, Docker Compose

## Struktur Folder
rosbd-finalproject-kelompok4/
├── docker-compose.yml           # Semua service (Kafka, ZK, Cassandra, ES, API, React)
├── producer/                    # Data Ingestion
│   ├── config.py                #   Konfigurasi ticker, Kafka broker
│   ├── fetcher.py               #   Fetch OHLCV dari Yahoo Finance
│   ├── kafka_producer.py        #   Kirim data ke Kafka
│   └── main.py                  #   Loop utama tiap 60 detik
├── scripts/
│   └── create-kafka-topics.sh   # Inisialisasi topic Kafka
├── init-cassandra.cql           # Schema Cassandra
├── init-elasticsearch.sh        # Mapping Elasticsearch
├── fastapi/                     # Backend API
├── react-dashboard/             # Frontend Dashboard
└── README.md

## Cara Menjalankan
### 1. Start semua service
```bash
docker compose up -d
2. Buat topic Kafka
docker exec kafka-laptop1 kafka-topics --bootstrap-server localhost:9092 \
  --create --topic forex-raw --partitions 3 --replication-factor 1
3. Jalankan Data Ingestion (Laptop 1)
cd producer
pip install kafka-python yfinance pandas
python main.py
4. Setup Database (Laptop 3)
# Cassandra
docker exec -i cassandra-laptop3 cqlsh < init-cassandra.cql
# Elasticsearch
docker exec elasticsearch-laptop3 bash /app/init-elasticsearch.sh