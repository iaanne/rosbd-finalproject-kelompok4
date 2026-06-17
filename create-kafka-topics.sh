#!/bin/bash

# Script untuk inisialisasi Kafka Topics
# Menggunakan docker exec untuk menjalankan perintah di dalam container Kafka

KAFKA_CONTAINER="kafka"
# Sesuaikan dengan port broker di dalam container (misal: localhost:9092)
KAFKA_BROKER="localhost:9092"

echo "Menunggu Kafka siap..."
# Berikan waktu sejenak agar Kafka broker sepenuhnya berjalan
sleep 5

# Fungsi untuk membuat Kafka Topic
create_topic() {
  local TOPIC_NAME=$1
  local PARTITIONS=${2:-3}
  local REPLICATION_FACTOR=${3:-1}

  echo "Membuat topic: $TOPIC_NAME ..."
  docker exec $KAFKA_CONTAINER \
    kafka-topics.sh --create \
    --if-not-exists \
    --bootstrap-server $KAFKA_BROKER \
    --partitions $PARTITIONS \
    --replication-factor $REPLICATION_FACTOR \
    --topic $TOPIC_NAME
}

echo "=== Memulai Pembuatan Kafka Topics ==="

# 1. Topic untuk Raw Data dari Yahoo Finance
# Menyimpan data kurs mata uang ASEAN terhadap USD
create_topic "forex_data" 3 1

# Menyimpan data US Dollar Index (DXY)
create_topic "dxy_data" 1 1

# Menyimpan data Harga Emas (Gold)
create_topic "gold_data" 1 1

# 2. (Opsional) Topic untuk data hasil Preprocessing / Feature Engineering dari Spark
create_topic "processed_features" 3 1

# 3. (Opsional) Topic untuk hasil clustering (K-Means, DBSCAN, AHC) 
create_topic "clustering_results" 3 1

echo "=== Selesai Membuat Topics ==="
echo "Daftar topic yang tersedia saat ini:"
docker exec $KAFKA_CONTAINER kafka-topics.sh --list --bootstrap-server $KAFKA_BROKER
