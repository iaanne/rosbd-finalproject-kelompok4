const BASE = '/api';

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed`);
  return res.json();
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed`);
  return res.json();
}

export const api = {
  getForexRates: (pair, limit = 100) => get(`/forex-rates/${pair}?limit=${limit}`),
  getFeatures: (pair, limit = 100) => get(`/features/${pair}?limit=${limit}`),
  getClusteringResults: (batchId) => get(`/clustering-results/${batchId}`),
  getBatches: (limit = 20) => get(`/batches?limit=${limit}`),
  getCurrencyPairs: () => get('/currency-pairs'),
  getClusterLogs: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return get(`/cluster-logs${q ? '?' + q : ''}`);
  },
  getNotifications: (limit = 50) => get(`/notifications?limit=${limit}`),
  postDataUpdate: (type, data) => post('/data-update', { type, data }),
  health: () => get('/health'),
};
