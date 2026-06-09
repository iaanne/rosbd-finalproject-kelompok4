from elasticsearch import Elasticsearch
import os

ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
INDEX = "cluster-logs"

_client = None


def get_client():
    global _client
    if _client is None:
        _client = Elasticsearch(ES_HOST)
    return _client


def search_logs(algorithm: str | None = None, currency_pair: str | None = None, size: int = 50):
    es = get_client()
    must = []
    if algorithm:
        must.append({"term": {"algorithm": algorithm}})
    if currency_pair:
        must.append({"term": {"currency_pair": currency_pair}})

    query = {"bool": {"must": must}} if must else {"match_all": {}}

    resp = es.search(index=INDEX, query=query, size=size, sort=[{"timestamp": "desc"}])
    return [h["_source"] for h in resp["hits"]["hits"]]


def index_log(data: dict):
    es = get_client()
    resp = es.index(index=INDEX, document=data)
    return resp["_id"]
