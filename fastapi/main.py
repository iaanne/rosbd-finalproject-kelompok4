from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from cassandra_client import (
    get_forex_rates,
    insert_forex_rate,
    get_features,
    get_clustering_results,
    insert_clustering_result,
    list_batch_ids,
    list_currency_pairs,
)
from elasticsearch_client import search_logs, index_log

app = FastAPI(title="De-dollarization Dashboard API")

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


# ─── Utility ────────────────────────────────────────────────


@app.get("/api/currency-pairs")
def read_currency_pairs():
    return list_currency_pairs()


@app.get("/api/health")
def health():
    return {"status": "ok"}
