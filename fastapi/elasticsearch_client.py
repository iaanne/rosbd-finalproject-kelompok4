from elasticsearch import Elasticsearch
import os
import logging

logger = logging.getLogger(__name__)

ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
INDEX = "cluster-logs"

_client = None


def init():
    global _client
    _client = Elasticsearch(
        hosts=[ES_HOST],
        request_timeout=30,
        max_retries=3,
        retry_on_timeout=True,
    )
    logger.info("Connected to Elasticsearch at %s", ES_HOST)


def close():
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("Elasticsearch connection closed")


def search_logs(algorithm: str | None = None, currency_pair: str | None = None, size: int = 50):
    if not _client:
        return []
    try:
        must = []
        if algorithm:
            must.append({"term": {"algorithm": algorithm}})
        if currency_pair:
            must.append({"term": {"currency_pair": currency_pair}})

        query = {"bool": {"must": must}} if must else {"match_all": {}}

        resp = _client.search(
            index=INDEX, query=query, size=size, sort=[{"timestamp": "desc"}]
        )
        return [h["_source"] for h in resp["hits"]["hits"]]
    except Exception as e:
        logger.error("Error searching logs: %s", e)
        return []


def index_log(data: dict):
    if not _client:
        return None
    try:
        resp = _client.index(index=INDEX, document=data)
        return resp["_id"]
    except Exception as e:
        logger.error("Error indexing log: %s", e)
        return None
