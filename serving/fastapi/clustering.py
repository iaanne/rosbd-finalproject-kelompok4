import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from scipy.cluster.hierarchy import linkage
import logging

logger = logging.getLogger(__name__)


def _map_cluster_names(df_latest, labels):
    """
    Map arbitrary cluster labels to canonical 0/1/2 using idxmax approach:
    - Cluster containing currency with highest corr_dxy_20d -> Pro-Dollar (0)
    - Cluster containing currency with highest corr_cny_20d -> Mendekati Yuan (2)
    - Remaining -> Transisi (1)
    """
    df = df_latest.copy()
    df['cluster_id'] = labels

    valid = df.dropna(subset=['corr_dxy_20d', 'corr_cny_20d'])
    if valid.empty:
        return {c: 1 for c in sorted(set(labels) - {-1})}

    top_dxy = valid.loc[valid['corr_dxy_20d'].idxmax(), 'cluster_id']
    top_cny = valid.loc[valid['corr_cny_20d'].idxmax(), 'cluster_id']

    unique = sorted(set(labels) - {-1})
    label_map = {}
    for c in unique:
        if c == top_dxy:
            label_map[c] = 0
        elif c == top_cny:
            label_map[c] = 2
        else:
            label_map[c] = 1

    if top_dxy == top_cny and len(unique) >= 2:
        second = [c for c in unique if c != top_dxy][0]
        if len(unique) == 2:
            label_map[second] = 1
        elif len(unique) >= 3:
            third = [c for c in unique if c not in (top_dxy, second)][0]
            label_map[second] = 1
            label_map[third] = 2

    return label_map


def _run_algorithm(X, n, algorithm='K-Means', n_clusters=3, eps=0.3, min_samples=2):
    if algorithm == 'K-Means':
        k = min(n_clusters, n)
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels_raw = model.fit_predict(X)
    elif algorithm == 'DBSCAN':
        model = DBSCAN(eps=eps, min_samples=min_samples)
        labels_raw = model.fit_predict(X)
    elif algorithm == 'AHC':
        k = min(n_clusters, n)
        model = AgglomerativeClustering(n_clusters=k)
        labels_raw = model.fit_predict(X)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    n_unique = len(set(labels_raw) - {-1})
    sil = silhouette_score(X, labels_raw) if n >= 4 and n_unique > 1 else 0.0
    return labels_raw, sil


def compute_clustering(features_df, algorithm='K-Means', n_clusters=3, eps=0.3, min_samples=2):
    """
    Run a single clustering algorithm and return (df_latest, labels, sil_score).
    Returns None if insufficient data.
    """
    df_latest = features_df.groupby('currency_pair').last().reset_index()
    df_latest = df_latest.dropna(subset=['corr_dxy_20d', 'corr_cny_20d', 'volatility_20d'])

    if df_latest.empty:
        return None

    X = df_latest[['corr_dxy_20d', 'corr_cny_20d', 'volatility_20d']].values
    n = len(X)

    labels_raw, sil = _run_algorithm(X, n, algorithm, n_clusters, eps, min_samples)
    label_map = _map_cluster_names(df_latest, labels_raw)
    labels = [label_map.get(l, 1) if l != -1 else 1 for l in labels_raw]

    return df_latest, labels, sil


def compute_dendrogram(features_df):
    """Compute linkage matrix for dendrogram."""
    latest = features_df.groupby('currency_pair').last().reset_index()
    latest = latest.dropna(subset=['corr_dxy_20d', 'corr_cny_20d'])
    if len(latest) < 2:
        return None
    X = latest[['corr_dxy_20d', 'corr_cny_20d']].values
    return linkage(X, method='ward')
