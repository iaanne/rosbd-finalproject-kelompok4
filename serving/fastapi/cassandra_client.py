from cassandra.cluster import Cluster
from cassandra.query import dict_factory
import os
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

CASSANDRA_HOST = os.getenv("CASSANDRA_HOST", "localhost")
KEYSPACE = "dedolarisasi"

_cluster = None
_session = None

_forex_insert = None
_forex_select = None

_features_select = None

_clustering_insert = None
_clustering_select = None
_batch_select = None

_pairs_select = None

_notification_insert = None
_notification_select = None


def init():
    global _cluster, _session
    global _forex_insert, _forex_select, _features_select
    global _clustering_insert, _clustering_select, _batch_select
    global _pairs_select
    global _notification_insert, _notification_select

    _cluster = Cluster([CASSANDRA_HOST])
    _session = _cluster.connect(KEYSPACE)
    _session.row_factory = dict_factory
    logger.info("Connected to Cassandra keyspace: %s", KEYSPACE)

    _forex_insert = _session.prepare(
        "INSERT INTO forex_rates (currency_pair, ts, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
    _forex_select = _session.prepare(
        "SELECT * FROM forex_rates WHERE currency_pair = ? ORDER BY ts DESC LIMIT ?"
    )

    _features_select = _session.prepare(
        "SELECT * FROM features WHERE currency_pair = ? ORDER BY ts DESC LIMIT ?"
    )

    _clustering_insert = _session.prepare(
        "INSERT INTO clustering_results "
        "(batch_id, ts, algorithm, currency_pair, cluster_label, cluster_name, is_outlier, silhouette_score) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    _clustering_select = _session.prepare(
        "SELECT * FROM clustering_results WHERE batch_id = ? ORDER BY ts DESC"
    )
    _batch_select = _session.prepare(
        "SELECT DISTINCT batch_id FROM clustering_results LIMIT ?"
    )

    _pairs_select = _session.prepare(
        "SELECT DISTINCT currency_pair FROM forex_rates LIMIT ?"
    )

    _notification_insert = _session.prepare(
        "INSERT INTO notifications (bucket, ts, id, type, title, message, batch_id, algorithm) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    _notification_select = _session.prepare(
        "SELECT * FROM notifications WHERE bucket = ? ORDER BY ts DESC LIMIT ?"
    )


def close():
    global _cluster
    if _cluster:
        _cluster.shutdown()
        _cluster = None
        logger.info("Cassandra connection closed")


def get_forex_rates(currency_pair: str, limit: int = 100):
    try:
        rows = _session.execute(_forex_select, (currency_pair, limit))
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error("Error fetching forex rates: %s", e)
        return []


def insert_forex_rate(data: dict):
    try:
        _session.execute(
            _forex_insert,
            (
                data["currency_pair"], data["ts"],
                data["open"], data["high"], data["low"],
                data["close"], data["volume"],
            ),
        )
    except Exception as e:
        logger.error("Error inserting forex rate: %s", e)
        raise


def get_features(currency_pair: str, limit: int = 100):
    try:
        rows = _session.execute(_features_select, (currency_pair, limit))
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error("Error fetching features: %s", e)
        return []


def get_clustering_results(batch_id: str):
    try:
        rows = _session.execute(_clustering_select, (batch_id,))
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error("Error fetching clustering results: %s", e)
        return []


def insert_clustering_result(data: dict):
    try:
        _session.execute(
            _clustering_insert,
            (
                data["batch_id"], data["ts"], data["algorithm"],
                data["currency_pair"], data["cluster_label"],
                data["cluster_name"], data["is_outlier"],
                data["silhouette_score"],
            ),
        )
    except Exception as e:
        logger.error("Error inserting clustering result: %s", e)
        raise


def list_batch_ids(limit: int = 20):
    try:
        rows = _session.execute(_batch_select, (limit,))
        return [r["batch_id"] for r in rows]
    except Exception as e:
        logger.error("Error listing batch ids: %s", e)
        return []


def list_currency_pairs(limit: int = 50):
    try:
        rows = _session.execute(_pairs_select, (limit,))
        return [r["currency_pair"] for r in rows]
    except Exception as e:
        logger.error("Error listing currency pairs: %s", e)
        return []


def insert_notification(notif: dict):
    try:
        bucket = "all"
        notif_id = notif.get("id", uuid.uuid4())
        ts = notif.get("ts", datetime.now(timezone.utc))
        _session.execute(
            _notification_insert,
            (
                bucket, ts, notif_id,
                notif["type"], notif["title"], notif["message"],
                notif.get("batch_id", ""), notif.get("algorithm", ""),
            ),
        )
        return str(notif_id)
    except Exception as e:
        logger.error("Error inserting notification: %s", e)
        raise


def get_notifications(limit: int = 50):
    try:
        rows = _session.execute(_notification_select, ("all", limit))
        notifs = []
        for r in rows:
            d = dict(r)
            d["id"] = str(d["id"])
            notifs.append(d)
        return notifs
    except Exception as e:
        logger.error("Error fetching notifications: %s", e)
        return []
