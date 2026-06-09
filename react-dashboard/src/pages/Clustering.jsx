import { useEffect, useState } from 'react';
import { api } from '../api';

const algorithmColors = {
  kmeans: '#2563eb',
  dbscan: '#7c3aed',
  hierarchical: '#059669',
};

export default function Clustering() {
  const [batches, setBatches] = useState([]);
  const [selected, setSelected] = useState('');
  const [data, setData] = useState([]);

  useEffect(() => { api.getBatches().then(setBatches); }, []);
  useEffect(() => {
    if (!selected) return;
    api.getClusteringResults(selected).then(setData);
  }, [selected]);

  const grouped = {};
  for (const r of data) {
    (grouped[r.algorithm] ??= []).push(r);
  }

  return (
    <div>
      <h1>Clustering Results</h1>
      <select value={selected} onChange={(e) => setSelected(e.target.value)}
        style={{ padding: '8px 12px', margin: '12px 0', borderRadius: 6, border: '1px solid #cbd5e1' }}>
        <option value="">-- Select batch --</option>
        {batches.map((b) => <option key={b} value={b}>{b}</option>)}
      </select>

      {Object.entries(grouped).map(([algo, rows]) => (
        <div key={algo} style={{ margin: '16px 0' }}>
          <h3 style={{ color: algorithmColors[algo] ?? '#333' }}>
            {algo.toUpperCase()}
            <span style={{ marginLeft: 12, fontSize: 13, color: '#64748b' }}>
              silhouette: {rows[0]?.silhouette_score?.toFixed(4)}
            </span>
          </h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 8, fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f8fafc', textAlign: 'left' }}>
                  <th style={th}>Currency Pair</th>
                  <th style={th}>Cluster Label</th>
                  <th style={th}>Cluster Name</th>
                  <th style={th}>Outlier</th>
                  <th style={th}>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #e2e8f0' }}>
                    <td style={td}>{r.currency_pair}</td>
                    <td style={td}>{r.cluster_label}</td>
                    <td style={td}>{r.cluster_name || '-'}</td>
                    <td style={td}>{r.is_outlier ? '⚠️ Yes' : 'No'}</td>
                    <td style={td}>{r.ts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

const th = { padding: '8px 12px', color: '#64748b' };
const td = { padding: '8px 12px' };
