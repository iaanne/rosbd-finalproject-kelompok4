from cassandra.cluster import Cluster
from cassandra.query import dict_factory
import os

CASSANDRA_HOST = os.getenv("CASSANDRA_HOST", "localhost")
KEYSPACE = "dedolarisasi"


def get_session():
    cluster = Cluster([CASSANDRA_HOST])
    session = cluster.connect(KEYSPACE)
    session.row_factory = dict_factory
    return session


def get_forex_rates(currency_pair: str, limit: int = 100):
    session = get_session()
    rows = session.execute(
        "SELECT * FROM forex_rates WHERE currency_pair = %s ORDER BY ts DESC LIMIT %s",
        (currency_pair, limit),
    )
    return [dict(r) for r in rows]


def insert_forex_rate(data: dict):
    session = get_session()
    session.execute(
        """
        INSERT INTO forex_rates (currency_pair, ts, open, high, low, close, volume)
        VALUES (%(currency_pair)s, %(ts)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
        """,
        data,
    )


def get_features(currency_pair: str, limit: int = 100):
    session = get_session()
    rows = session.execute(
        "SELECT * FROM features WHERE currency_pair = %s ORDER BY ts DESC LIMIT %s",
        (currency_pair, limit),
    )
    return [dict(r) for r in rows]


def get_clustering_results(batch_id: str):
    session = get_session()
    rows = session.execute(
        "SELECT * FROM clustering_results WHERE batch_id = %s ORDER BY ts DESC",
        (batch_id,),
    )
    return [dict(r) for r in rows]


def insert_clustering_result(data: dict):
    session = get_session()
    session.execute(
        """
        INSERT INTO clustering_results
            (batch_id, ts, algorithm, currency_pair, cluster_label, cluster_name, is_outlier, silhouette_score)
        VALUES (%(batch_id)s, %(ts)s, %(algorithm)s, %(currency_pair)s, %(cluster_label)s, %(cluster_name)s, %(is_outlier)s, %(silhouette_score)s)
        """,
        data,
    )


def list_batch_ids(limit: int = 20):
    session = get_session()
    rows = session.execute(
        "SELECT DISTINCT batch_id FROM clustering_results LIMIT %s", (limit,)
    )
    return [r["batch_id"] for r in rows]


def list_currency_pairs():
    session = get_session()
    rows = session.execute("SELECT DISTINCT currency_pair FROM forex_rates LIMIT 50")
    return [r["currency_pair"] for r in rows]
