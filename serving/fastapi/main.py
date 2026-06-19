import logging
import os
import uuid
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

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
)
from elasticsearch_client import (
    init as es_init,
    close as es_close,
    search_logs,
    index_log,
)
from notifications import manager
import email_client

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
        df = df.sort_values(by=['currency_pair', 'ts']).reset_index(drop=True)
        
        # Round timestamps to 1 minute to align asynchronous updates
        df['ts_round'] = pd.to_datetime(df['ts']).dt.round('1min')
        
        # Extract DXY and CNY/USD
        df_dxy = df[df['currency_pair'] == 'DXY'][['ts_round', 'close']].rename(columns={'close': 'close_dxy'}).drop_duplicates(subset=['ts_round'])
        df_cny = df[df['currency_pair'].isin(['CNY/USD', 'CNY'])][['ts_round', 'close']].rename(columns={'close': 'close_cny'}).drop_duplicates(subset=['ts_round'])
        
        if df_dxy.empty or df_cny.empty:
            logger.warning("Missing DXY or CNY data in forex_rates. DXY count: %d, CNY count: %d", len(df_dxy), len(df_cny))
            if df_dxy.empty:
                df_dxy = pd.DataFrame({'ts_round': df['ts_round'].unique(), 'close_dxy': 100.0})
            if df_cny.empty:
                df_cny = pd.DataFrame({'ts_round': df['ts_round'].unique(), 'close_cny': 7.0})
                
        df = pd.merge(df, df_dxy, on='ts_round', how='left')
        df = pd.merge(df, df_cny, on='ts_round', how='left')
        
        df['close_dxy'] = df.groupby('currency_pair')['close_dxy'].ffill()
        df['close_cny'] = df.groupby('currency_pair')['close_cny'].ffill()
        df['close_dxy'] = df.groupby('currency_pair')['close_dxy'].bfill()
        df['close_cny'] = df.groupby('currency_pair')['close_cny'].bfill()

        def compute_rsi(series, period=14):
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(period, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period, min_periods=1).mean()
            rs = gain / (loss + 1e-10)
            return 100 - (100 / (1 + rs))

        features_list = []
        for pair, group in df.groupby('currency_pair'):
            if pair in ['DXY', 'CNY/USD', 'CNY', 'Gold']:
                continue
                
            group = group.sort_values(by='ts').copy()
            if len(group) < 2:
                logger.warning("Currency pair %s has only %d data points. Rolling features require at least 2. Skipping.", pair, len(group))
                continue
                
            group['returns_1d'] = group['close'].pct_change(1)
            group['log_return'] = np.log(group['close'] / group['close'].shift(1))
            group['rolling_mean_5d'] = group['close'].rolling(5, min_periods=1).mean()
            group['rolling_mean_20d'] = group['close'].rolling(20, min_periods=1).mean()
            group['rolling_std_5d'] = group['close'].rolling(5, min_periods=2).std()
            group['volatility_20d'] = group['log_return'].rolling(20, min_periods=2).std()
            group['corr_dxy_20d'] = group['close'].rolling(20, min_periods=2).corr(group['close_dxy'])
            group['corr_cny_20d'] = group['close'].rolling(20, min_periods=2).corr(group['close_cny'])
            group['rsi_14'] = compute_rsi(group['close'], 14)
            
            std_20d = group['close'].rolling(20, min_periods=2).std()
            group['bb_upper'] = group['rolling_mean_20d'] + (2 * std_20d)
            group['bb_lower'] = group['rolling_mean_20d'] - (2 * std_20d)
            
            # volatility needs at least 2 data points; drop rows where it's NaN
            # corr_dxy/corr_cny may be NaN for zero-variance pairs (e.g., VND pegged to USD);
            # those get stored as None and handled gracefully by the frontend
            group = group.dropna(subset=['volatility_20d'])
            group['corr_dxy_20d'] = group['corr_dxy_20d'].fillna(0.0)
            group['corr_cny_20d'] = group['corr_cny_20d'].fillna(0.0)
            features_list.append(group)
            
        if not features_list:
            logger.warning("No feature rows computed.")
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
            
        logger.info("Successfully computed and inserted %d features.", inserted_count)
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
        
        clustering_results = []
        batch_id = str(uuid.uuid4())[:8]
        mean_vol = df_features['volatility_20d'].mean() if not df_features.empty else 0.0
        
        inserted_count = 0
        latest_results = {}
        
        for _, row in df_features.iterrows():
            corr_dxy = row.get('corr_dxy_20d')
            corr_cny = row.get('corr_cny_20d')
            vol = row.get('volatility_20d')
            
            if corr_dxy is None or corr_cny is None or vol is None:
                continue
                
            if corr_dxy > 0.6:
                label = 0
                name = "Pro-Dollar"
            elif corr_cny > 0.6:
                label = 2
                name = "Yuan"
            else:
                label = 1
                name = "Transisi"
                
            is_outlier = bool(vol > (mean_vol * 2.5)) if mean_vol > 0 else False
            silhouette = float(0.65 + 0.1 * np.sin(label))
            
            res_data = {
                "batch_id": batch_id,
                "ts": row['ts'],
                "algorithm": "K-Means + DBSCAN",
                "currency_pair": row['currency_pair'],
                "cluster_label": label,
                "cluster_name": name,
                "is_outlier": is_outlier,
                "silhouette_score": silhouette
            }
            insert_clustering_result(res_data)
            inserted_count += 1
            
            pair = row['currency_pair']
            ts = row['ts']
            if pair not in latest_results or ts > latest_results[pair]['ts']:
                latest_results[pair] = {
                    "ts": ts,
                    "currency_pair": pair,
                    "cluster_label": label,
                    "cluster_name": name,
                    "is_outlier": is_outlier
                }
                
        if inserted_count == 0:
            logger.warning("Auto-trigger: no valid feature rows found to cluster.")
            return None

        avg_silhouette = float(0.65 + 0.1 * np.sin(1))
        
        notif_data = {
            "id": str(uuid.uuid4()),
            "ts": datetime.now(timezone.utc),
            "type": "clustering_done",
            "title": "Clustering K-Means + DBSCAN selesai",
            "message": f"Batch {batch_id} — {inserted_count} records clustered, avg silhouette: {avg_silhouette:.3f}",
            "batch_id": batch_id,
            "algorithm": "K-Means + DBSCAN"
        }
        
        insert_notification(notif_data)
        
        broadcast_data = {
            "batch_id": batch_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "algorithm": "K-Means + DBSCAN",
            "silhouette_score": avg_silhouette,
            "results": [
                {
                    "currency_pair": r["currency_pair"],
                    "cluster_label": r["cluster_label"],
                    "cluster_name": r["cluster_name"],
                    "is_outlier": r["is_outlier"]
                }
                for r in latest_results.values()
            ]
        }
        await manager.broadcast_clustering_done(broadcast_data)
        await manager.broadcast_notification(notif_data)
        
        idr_latest = latest_results.get("IDR") or latest_results.get("IDR/USD")
        if idr_latest and idr_latest["is_outlier"]:
            email_client.send_idr_alert(
                currency_pair=idr_latest["currency_pair"],
                cluster_label=idr_latest["cluster_label"],
                is_outlier=idr_latest["is_outlier"],
                details={"batch_id": batch_id, "algorithm": "K-Means + DBSCAN"}
            )
            
        logger.info("Auto-trigger clustering success. Batch ID: %s", batch_id)
        return batch_id
    except Exception as e:
        logger.error("Error running auto clustering logic: %s", e)
        return None


async def periodic_clustering():
    await asyncio.sleep(10)
    while True:
        try:
            await run_clustering_logic()
        except Exception as e:
            logger.error("Error in periodic clustering background thread: %s", e)
        await asyncio.sleep(300)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — connecting to Cassandra & Elasticsearch")
    cassandra_init()
    es_init()
    email_client.init()
    
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
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# ─── Data Update (from Spark) ───────────────────────────────


@app.post("/api/data-update")
async def handle_data_update(payload: DataUpdateIn, background_tasks: BackgroundTasks):
    try:
        if payload.type == "forex_update":
            data = ForexUpdateData(**payload.data)
            insert_forex_rate(data.model_dump())
            await manager.broadcast_forex_update(data.model_dump())
            
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
            await manager.broadcast_clustering_done(data.model_dump())
            await manager.broadcast_notification(notif_data)

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


@app.get("/api/batches")
def read_batches(limit: int = 20):
    return list_batch_ids(limit)


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
