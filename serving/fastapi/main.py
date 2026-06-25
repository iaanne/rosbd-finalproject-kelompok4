import logging
import os
import uuid
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Set

from cassandra_client import (
    init as cassandra_init,
    close as cassandra_close,
    get_forex_rates,
    insert_forex_rate,
    get_features,
    get_clustering_results,
    insert_clustering_result,
    list_batch_ids,
    list_currency_pairs,
    insert_notification,
    get_notifications,
    get_all_forex_rates,
    insert_feature,
    get_all_features,
    get_latest_clustering_summary,
    insert_clustering_metrics,
    get_clustering_metrics,
    get_latest_clustering_metrics,
    insert_batch_index,
)
from elasticsearch_client import (
    init as es_init,
    close as es_close,
    search_logs,
    index_log,
)
from clustering import _map_cluster_names
import email_client
from telegram_client import init as tg_init, send_alert as tg_send

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─── Helper Functions for Background Tasks ──────────────────

def run_compute_features_logic():
    try:
        logger.info("Computing features from raw forex_rates...")
        rates = get_all_forex_rates()
        if not rates:
            logger.warning("No forex rates found in database. Cannot compute features.")
            return 0

        df = pd.DataFrame(rates)
        df['ts'] = pd.to_datetime(df['ts'])
        df = df.sort_values(by=['currency_pair', 'ts']).reset_index(drop=True)

        # Resample intraday 1m → daily: ambil close terakhir tiap hari per pair
        df['date'] = df['ts'].dt.date
        daily = df.groupby(['currency_pair', 'date']).agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum', 'ts': 'last'
        }).reset_index().sort_values(['currency_pair', 'ts'])

        # Extract DXY dan CNY daily close untuk korelasi (merge via date, bukan ts, karena ts berbeda per pair)
        dxy = daily[daily['currency_pair'] == 'DXY'][['date', 'close']].rename(columns={'close': 'close_dxy'})
        cny = daily[daily['currency_pair'].isin(['CNY/USD', 'CNY'])][['date', 'close']].rename(columns={'close': 'close_cny'})

        if dxy.empty:
            dxy = pd.DataFrame({'date': daily['date'].unique(), 'close_dxy': 100.0})
        if cny.empty:
            cny = pd.DataFrame({'date': daily['date'].unique(), 'close_cny': 7.0})

        daily = pd.merge(daily, dxy, on='date', how='left')
        daily = pd.merge(daily, cny, on='date', how='left')
        daily.drop(columns=['date'], inplace=True)

        def compute_rsi(series, period=14):
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(period, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period, min_periods=1).mean()
            rs = gain / (loss + 1e-10)
            return 100 - (100 / (1 + rs))

        features_list = []
        for pair, group in daily.groupby('currency_pair'):
            if pair in ['DXY', 'CNY/USD', 'CNY', 'Gold']:
                continue

            group = group.sort_values('ts').copy()
            if len(group) < 2:
                logger.warning("Currency pair %s has only %d data points. Need daily data >= 2.", pair, len(group))
                continue

            group['returns_1d'] = group['close'].pct_change(1)
            group['log_return'] = np.log(group['close'] / group['close'].shift(1))
            group['rolling_mean_5d'] = group['close'].rolling(5, min_periods=1).mean()
            group['rolling_mean_20d'] = group['close'].rolling(20, min_periods=1).mean()
            group['rolling_std_5d'] = group['close'].rolling(5, min_periods=2).std()
            group['volatility_20d'] = group['log_return'].rolling(20, min_periods=2).std()
            group['corr_dxy_20d'] = group['log_return'].rolling(20, min_periods=2).corr(group['close_dxy'].pct_change().fillna(0))
            group['corr_cny_20d'] = group['log_return'].rolling(20, min_periods=2).corr(group['close_cny'].pct_change().fillna(0))
            group['rsi_14'] = compute_rsi(group['close'], 14)

            std_20d = group['close'].rolling(20, min_periods=2).std()
            group['bb_upper'] = group['rolling_mean_20d'] + (2 * std_20d)
            group['bb_lower'] = group['rolling_mean_20d'] - (2 * std_20d)

            group = group.dropna(subset=['volatility_20d'])
            group['corr_dxy_20d'] = group['corr_dxy_20d'].ffill().clip(-1, 1)
            group['corr_cny_20d'] = group['corr_cny_20d'].ffill().clip(-1, 1)
            features_list.append(group)

        if not features_list:
            logger.warning("No feature rows computed. Ensure backfill_historical.py has been run for daily data.")
            return 0

        df_features = pd.concat(features_list).reset_index(drop=True)
        df_features = df_features.replace([np.inf, -np.inf], np.nan)

        inserted_count = 0
        for _, row in df_features.iterrows():
            insert_feature({
                "currency_pair": row['currency_pair'],
                "ts": row['ts'],
                "returns_1d": float(row['returns_1d']) if not pd.isna(row['returns_1d']) else None,
                "log_return": float(row['log_return']) if not pd.isna(row['log_return']) else None,
                "rolling_mean_5d": float(row['rolling_mean_5d']) if not pd.isna(row['rolling_mean_5d']) else None,
                "rolling_mean_20d": float(row['rolling_mean_20d']) if not pd.isna(row['rolling_mean_20d']) else None,
                "rolling_std_5d": float(row['rolling_std_5d']) if not pd.isna(row['rolling_std_5d']) else None,
                "volatility_20d": float(row['volatility_20d']) if not pd.isna(row['volatility_20d']) else None,
                "corr_dxy_20d": float(row['corr_dxy_20d']) if not pd.isna(row['corr_dxy_20d']) else None,
                "corr_cny_20d": float(row['corr_cny_20d']) if not pd.isna(row['corr_cny_20d']) else None,
                "rsi_14": float(row['rsi_14']) if not pd.isna(row['rsi_14']) else None,
                "bb_upper": float(row['bb_upper']) if not pd.isna(row['bb_upper']) else None,
                "bb_lower": float(row['bb_lower']) if not pd.isna(row['bb_lower']) else None
            })
            inserted_count += 1

        logger.info("Successfully computed and inserted %d features (resampled daily).", inserted_count)
        return inserted_count
    except Exception as e:
        logger.error("Error in run_compute_features_logic: %s", e)
        return 0


async def run_clustering_logic():
    try:
        logger.info("Auto-trigger: running clustering logic...")
        features = get_all_features()
        if not features:
            logger.warning("Auto-trigger: features table is empty, skipping clustering.")
            return None

        df_features = pd.DataFrame(features)
        now = datetime.now(timezone.utc)
        batch_id = now.strftime('%Y%m%d%H%M%S') + '-' + str(uuid.uuid4()).split('-')[0]
        mean_vol = df_features['volatility_20d'].mean() if not df_features.empty else 0.0

        # Build feature matrix: latest snapshot per currency_pair
        latest_ts = df_features.groupby('currency_pair')['ts'].max().reset_index()
        df_latest = pd.merge(latest_ts, df_features, on=['currency_pair', 'ts'], how='left')
        df_latest = df_latest.dropna(subset=['corr_dxy_20d', 'corr_cny_20d', 'volatility_20d'])

        if df_latest.empty:
            logger.warning("Auto-trigger: no valid feature rows after dedup.")
            return None

        X = df_latest[['corr_dxy_20d', 'corr_cny_20d', 'volatility_20d']].values
        n = len(X)

        # ── 1. K-Means (k=3) ──────────────────────────────────────
        kmeans = KMeans(n_clusters=min(3, n), random_state=42, n_init=10)
        km_labels_raw = kmeans.fit_predict(X)
        km_sil = silhouette_score(X, km_labels_raw) if n >= 4 and len(set(km_labels_raw)) > 1 else 0.0

        # ── 2. DBSCAN (eps=0.3, min_samples=2) ────────────────────
        dbscan = DBSCAN(eps=0.3, min_samples=2)
        db_labels_raw = dbscan.fit_predict(X)
        db_sil = silhouette_score(X, db_labels_raw) if n >= 4 and len(set(db_labels_raw)) > 1 else 0.0

        # ── 3. AHC (ward, k=3) ────────────────────────────────────
        ahc = AgglomerativeClustering(n_clusters=min(3, n))
        ahc_labels_raw = ahc.fit_predict(X)
        ahc_sil = silhouette_score(X, ahc_labels_raw) if n >= 4 and len(set(ahc_labels_raw)) > 1 else 0.0

        # ── Relabel all algorithms using idxmax centroid naming ──
        km_label_map = _map_cluster_names(df_latest, km_labels_raw)
        db_label_map = _map_cluster_names(df_latest, db_labels_raw)
        ahc_label_map = _map_cluster_names(df_latest, ahc_labels_raw)
        km_labels = [km_label_map.get(l, 1) if l != -1 else 1 for l in km_labels_raw]
        db_labels = [db_label_map.get(l, 1) if l != -1 else 1 for l in db_labels_raw]
        ahc_labels = [ahc_label_map.get(l, 1) if l != -1 else 1 for l in ahc_labels_raw]

        name_map = {0: "Pro-Dollar", 1: "Transisi", 2: "Mendekati Yuan"}

        inserted_count = 0
        latest_results = {}
        algorithms = [
            ("K-Means", km_labels, km_sil),
            ("DBSCAN", db_labels, db_sil),
            ("AHC", ahc_labels, ahc_sil),
        ]

        for algo_name, labels, sil_score in algorithms:
            for i, row in df_latest.iterrows():
                pair = row['currency_pair']
                canonical = int(labels[i]) if i < len(labels) else 1
                # DBSCAN noise (-1) already mapped to 1 by relabel_by_centroid; guard anyway
                if canonical not in (0, 1, 2):
                    canonical = 1
                name = name_map.get(canonical, "Transisi")
                is_outlier = bool(row['volatility_20d'] > (mean_vol * 2.5)) if mean_vol > 0 else False

                res_data = {
                    "batch_id": batch_id,
                    "ts": row['ts'],
                    "algorithm": algo_name,
                    "currency_pair": pair,
                    "cluster_label": canonical,
                    "cluster_name": name,
                    "is_outlier": is_outlier,
                    "silhouette_score": float(sil_score),
                }
                insert_clustering_result(res_data)
                inserted_count += 1

                if pair not in latest_results or row['ts'] > latest_results[pair]['ts']:
                    latest_results[pair] = {
                        "ts": row['ts'],
                        "currency_pair": pair,
                        "cluster_label": canonical,
                        "cluster_name": name,
                        "is_outlier": is_outlier,
                    }

        avg_silhouette = float(np.mean([km_sil, db_sil, ahc_sil]))

        db_noise_count = int((db_labels_raw == -1).sum())
        db_noise_ratio = float(db_noise_count / n) if n > 0 else 0.0
        dbscan_k = len(set(db_labels_raw) - {-1})

        metrics_data = {
            "batch_id": batch_id,
            "ts": datetime.now(timezone.utc),
            "kmeans_k": int(kmeans.n_clusters),
            "kmeans_silhouette": float(km_sil),
            "dbscan_noise_ratio": db_noise_ratio,
            "dbscan_silhouette": float(db_sil),
            "ahc_silhouette": float(ahc_sil),
            "dendrogram_linkage": "ward",
            "labels_order": "idxmax-mapping(Pro-Dollar,Transisi,Yuan)",
        }
        insert_clustering_metrics(metrics_data)

        insert_batch_index(batch_id, now)

        notif_data = {
            "id": str(uuid.uuid4()),
            "ts": now,
            "type": "clustering_done",
            "title": "Clustering Selesai (K-Means + DBSCAN + AHC)",
            "message": f"Batch {batch_id} — {inserted_count} records, avg silhouette: {avg_silhouette:.3f}",
            "batch_id": batch_id,
            "algorithm": "K-Means + DBSCAN + AHC",
        }
        insert_notification(notif_data)

        broadcast_data = {
            "batch_id": batch_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "algorithm": "K-Means + DBSCAN + AHC",
            "silhouette_score": avg_silhouette,
            "results": [
                {
                    "currency_pair": r["currency_pair"],
                    "cluster_label": r["cluster_label"],
                    "cluster_name": r["cluster_name"],
                    "is_outlier": r["is_outlier"],
                }
                for r in latest_results.values()
            ],
        }
        outliers = [r for r in latest_results.values() if r["is_outlier"] and r["currency_pair"] not in ("DXY", "CNY")]
        for o in outliers:
            alert_msg = {
                "severity": "high",
                "category": "outlier",
                "title": f"Outlier terdeteksi: {o['currency_pair']}",
                "message": f"{o['currency_pair']} terklasifikasi sebagai outlier — volatility di luar normal.",
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            await emit_alert(alert_msg)
            insert_notification({
                "id": str(uuid.uuid4()),
                "ts": datetime.now(timezone.utc),
                "type": "alert",
                "title": alert_msg["title"],
                "message": alert_msg["message"],
                "severity": alert_msg["severity"],
                "category": alert_msg["category"],
                "batch_id": batch_id,
                "algorithm": "DBSCAN",
            })

        broadcast_data["outliers"] = [r["currency_pair"] for r in outliers]
        await ws_broadcast({"type": "system", **broadcast_data, "message": notif_data["message"]})

        idr_latest = latest_results.get("IDR") or latest_results.get("IDR/USD")
        if idr_latest and idr_latest["is_outlier"]:
            email_client.send_idr_alert(
                currency_pair=idr_latest["currency_pair"],
                cluster_label=idr_latest["cluster_label"],
                is_outlier=idr_latest["is_outlier"],
                details={"batch_id": batch_id, "algorithm": "K-Means + DBSCAN + AHC"},
            )

        logger.info("Auto-trigger clustering success. Batch ID: %s", batch_id)
        return batch_id
    except Exception as e:
        logger.error("Error running auto clustering logic: %s", e)
        return None


async def periodic_clustering():
    await asyncio.sleep(10)
    retry_delay = 300
    while True:
        try:
            result = await run_clustering_logic()
            if result is None:
                logger.info("Periodic clustering: skipped (no data yet), retrying in %ds", retry_delay)
            else:
                logger.info("Periodic clustering: batch %s done, next in %ds", result, retry_delay)
            await asyncio.sleep(retry_delay)
        except asyncio.CancelledError:
            logger.warning("Periodic clustering cancelled.")
            break
        except Exception as e:
            logger.error("Periodic clustering crashed with %s: %s, restarting in 60s", type(e).__name__, e)
            await asyncio.sleep(60)


# ─── WebSocket Manager ──────────────────────────────────────

active_connections: Set[WebSocket] = set()


async def ws_broadcast(message: dict):
    dead = set()
    for ws in active_connections:
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    if dead:
        active_connections.difference_update(dead)
        logger.warning("Removed %d stale WebSocket connections", len(dead))


async def emit_alert(data: dict):
    payload = {
        "type": "alert",
        "severity": data.get("severity", "info"),
        "category": data.get("category", "general"),
        "title": data.get("title", ""),
        "message": data.get("message", ""),
        "ts": data.get("ts", datetime.now(timezone.utc).isoformat()),
    }
    await ws_broadcast(payload)
    asyncio.create_task(tg_send(payload["title"], payload["message"], payload["severity"]))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — connecting to Cassandra & Elasticsearch")
    cassandra_init()
    es_init()
    email_client.init()
    tg_init()
    
    # Start periodic clustering background task
    asyncio.create_task(periodic_clustering())
    
    # Start Kafka consumer background task (dynamic import to avoid circular dependency)
    try:
        from kafka_consumer import start_kafka_consumer
        asyncio.create_task(start_kafka_consumer())
        logger.info("Background Kafka consumer task spawned.")
    except Exception as e:
        logger.error("Failed to start background Kafka consumer: %s", e)
    
    yield
    logger.info("Shutting down — closing connections")
    cassandra_close()
    es_close()


app = FastAPI(title="De-dollarization Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Schemas ────────────────────────────────────────────────


class ForexRateIn(BaseModel):
    currency_pair: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class ClusteringResultIn(BaseModel):
    batch_id: str
    ts: datetime
    algorithm: str
    currency_pair: str
    cluster_label: int
    cluster_name: Optional[str] = ""
    is_outlier: bool = False
    silhouette_score: Optional[float] = 0.0


class ClusterLogIn(BaseModel):
    timestamp: datetime
    algorithm: str
    currency_pair: str
    cluster_label: int
    is_outlier: bool
    features: Optional[dict] = None


class DataUpdateIn(BaseModel):
    type: str
    data: dict


class ForexUpdateData(BaseModel):
    currency_pair: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class ClusterResultItem(BaseModel):
    currency_pair: str
    cluster_label: int
    cluster_name: Optional[str] = ""
    is_outlier: bool = False


class ClusteringDoneData(BaseModel):
    batch_id: str
    ts: datetime
    algorithm: str
    silhouette_score: Optional[float] = 0.0
    results: list[ClusterResultItem]


# ─── WebSocket ──────────────────────────────────────────────


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    logger.info("WebSocket client connected (%d total)", len(active_connections))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.discard(websocket)
        logger.info("WebSocket client disconnected (%d remaining)", len(active_connections))
    except Exception:
        active_connections.discard(websocket)
        logger.info("WebSocket client disconnected (%d remaining)", len(active_connections))


# ─── Data Update (from Spark) ───────────────────────────────


@app.post("/api/data-update")
async def handle_data_update(payload: DataUpdateIn, background_tasks: BackgroundTasks):
    try:
        if payload.type == "forex_update":
            data = ForexUpdateData(**payload.data)
            insert_forex_rate(data.model_dump())
            await ws_broadcast({"type": "price_update", **data.model_dump()})
            
            # Trigger feature calculation in background
            background_tasks.add_task(run_compute_features_logic)
            
            if data.currency_pair.upper() == "IDR":
                spread = data.high - data.low
                volatility = spread / data.close if data.close else 0
                threshold = float(os.getenv("IDR_VOLATILITY_THRESHOLD", "0.005"))
                if volatility >= threshold:
                    email_client.send_idr_alert(
                        currency_pair=data.currency_pair,
                        cluster_label=-1,
                        is_outlier=True,
                        volatility=volatility,
                        details={"open": data.open, "high": data.high,
                                 "low": data.low, "close": data.close,
                                 "volume": data.volume},
                    )

        elif payload.type == "clustering_done":
            data = ClusteringDoneData(**payload.data)
            for res in data.results:
                insert_clustering_result({
                    "batch_id": data.batch_id,
                    "ts": data.ts,
                    "algorithm": data.algorithm,
                    "currency_pair": res.currency_pair,
                    "cluster_label": res.cluster_label,
                    "cluster_name": res.cluster_name,
                    "is_outlier": res.is_outlier,
                    "silhouette_score": data.silhouette_score,
                })
                if res.currency_pair.upper() == "IDR" and res.is_outlier:
                    email_client.send_idr_alert(
                        currency_pair=res.currency_pair,
                        cluster_label=res.cluster_label,
                        is_outlier=res.is_outlier,
                        details={"batch_id": data.batch_id, "algorithm": data.algorithm},
                    )
            notif_data = {
                "id": str(uuid.uuid4()),
                "ts": datetime.now(timezone.utc),
                "type": "clustering_done",
                "title": f"Clustering {data.algorithm} selesai",
                "message": f"Batch {data.batch_id} — {len(data.results)} pairs, "
                           f"silhouette: {data.silhouette_score:.3f}",
                "batch_id": data.batch_id,
                "algorithm": data.algorithm,
            }
            insert_notification(notif_data)
            await ws_broadcast({
                "type": "system",
                "batch_id": data.batch_id,
                "algorithm": data.algorithm,
                "silhouette_score": data.silhouette_score,
                "message": notif_data["message"],
                "ts": notif_data["ts"].isoformat() if hasattr(notif_data["ts"], 'isoformat') else str(notif_data["ts"]),
            })

        else:
            raise HTTPException(status_code=400, detail=f"Unknown type: {payload.type}")

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error handling data update: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ─── Forex Rates ────────────────────────────────────────────


@app.get("/api/forex-rates/{currency_pair}")
def read_forex_rates(currency_pair: str, limit: int = 100):
    return get_forex_rates(currency_pair, limit)


@app.post("/api/forex-rates")
def create_forex_rate(data: ForexRateIn):
    insert_forex_rate(data.model_dump())
    return {"status": "ok"}


# ─── Features ───────────────────────────────────────────────


@app.post("/api/compute-features")
def compute_features_endpoint():
    inserted = run_compute_features_logic()
    if inserted == 0:
        raise HTTPException(
            status_code=400,
            detail="Tidak ada data fitur yang berhasil dihitung. Pastikan data mentah forex_rates tersedia (> 20 periode)."
        )
    return {"status": "ok", "message": f"Successfully computed and inserted {inserted} features"}


@app.get("/api/features/{currency_pair}")
def read_features(currency_pair: str, limit: int = 100):
    return get_features(currency_pair, limit)


# ─── Clustering Results ─────────────────────────────────────


@app.post("/api/run-clustering")
async def run_clustering_endpoint():
    batch_id = await run_clustering_logic()
    if not batch_id:
        raise HTTPException(
            status_code=400,
            detail="Tidak ada hasil clustering yang dibuat. Pastikan data features sudah terisi."
        )
    return {"status": "ok", "batch_id": batch_id, "message": "Successfully executed clustering and saved results"}


@app.get("/api/clustering-results/{batch_id}")
def read_clustering_results(batch_id: str):
    return get_clustering_results(batch_id)


@app.post("/api/clustering-results")
def create_clustering_result(data: ClusteringResultIn):
    insert_clustering_result(data.model_dump())
    return {"status": "ok"}


@app.get("/api/clustering/latest")
def read_latest_clustering():
    return get_latest_clustering_summary()


@app.get("/api/clustering-metrics/latest")
def read_latest_clustering_metrics():
    return get_latest_clustering_metrics()


@app.get("/api/clustering-metrics/{batch_id}")
def read_clustering_metrics(batch_id: str):
    return get_clustering_metrics(batch_id)


@app.get("/api/batches")
def read_batches(limit: int = 20):
    return list_batch_ids(limit)


# ─── IKR Ranking & Corr-Delta ───────────────────────────────


@app.get("/api/ikr-ranking")
def read_ikr_ranking():
    """Return ASEAN currencies ranked oleh vulnerability (Mendekati Yuan first)."""
    batches = list_batch_ids(5)
    if not batches:
        return []
    latest_batch = batches[0]
    raw = get_clustering_results(latest_batch)
    seen = {}
    for r in raw:
        p = r["currency_pair"]
        if p not in seen or r["ts"] > seen[p]["ts"]:
            seen[p] = r
    results = list(seen.values())
    asean = [r for r in results if r["currency_pair"] not in ("DXY", "CNY", "GOLD", "Gold")]
    asean.sort(key=lambda r: (
        -(r.get("cluster_label", 1) == 2),
        -(r.get("is_outlier", False)),
        -(r.get("cluster_label", 1) == 1),
        r["currency_pair"],
    ))
    return [{"rank": i + 1, **r} for i, r in enumerate(asean)]


@app.get("/api/corr-delta/{pair}")
def read_corr_delta(pair: str):
    """Return delta corr_dxy_20d antara dua titik data terakhir."""
    features = get_features(pair, limit=2)
    if len(features) < 2:
        return {"pair": pair, "delta": None, "latest": features[0]["corr_dxy_20d"] if features else None}
    latest = features[0]["corr_dxy_20d"]
    prev = features[1]["corr_dxy_20d"]
    delta = (latest - prev) if (latest is not None and prev is not None) else None
    return {"pair": pair, "delta": delta, "latest": latest, "previous": prev}


# ─── Elasticsearch Logs ─────────────────────────────────────


@app.get("/api/cluster-logs")
def read_cluster_logs(
    algorithm: Optional[str] = None,
    currency_pair: Optional[str] = None,
    size: int = 50,
):
    return search_logs(algorithm, currency_pair, size)


@app.post("/api/cluster-logs")
def create_cluster_log(data: ClusterLogIn):
    _id = index_log(data.model_dump())
    return {"status": "ok", "id": _id}


# ─── Notifications ──────────────────────────────────────────


@app.get("/api/notifications")
def read_notifications(limit: int = 50):
    return get_notifications(limit)


# ─── Utility ────────────────────────────────────────────────


@app.get("/api/currency-pairs")
def read_currency_pairs():
    return list_currency_pairs()


@app.get("/api/health")
def health():
    return {"status": "ok"}
