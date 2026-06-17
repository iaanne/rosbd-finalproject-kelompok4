import logging
import os
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — connecting to Cassandra & Elasticsearch")
    cassandra_init()
    es_init()
    email_client.init()
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
async def handle_data_update(payload: DataUpdateIn):
    try:
        if payload.type == "forex_update":
            data = ForexUpdateData(**payload.data)
            insert_forex_rate(data.model_dump())
            await manager.broadcast_forex_update(data.model_dump())
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


@app.get("/api/features/{currency_pair}")
def read_features(currency_pair: str, limit: int = 100):
    return get_features(currency_pair, limit)


# ─── Clustering Results ─────────────────────────────────────


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
