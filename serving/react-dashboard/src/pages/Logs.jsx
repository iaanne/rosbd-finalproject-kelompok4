import { useEffect, useState } from 'react';
import { api } from '../api';

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [algorithm, setAlgorithm] = useState('');
  const [currencyPair, setCurrencyPair] = useState('');

  useEffect(() => { api.getClusterLogs().then(setLogs); }, []);

  async function search() {
    const params = {};
    if (algorithm) params.algorithm = algorithm;
    if (currencyPair) params.currency_pair = currencyPair;
    const res = await api.getClusterLogs(params);
    setLogs(res);
  }

  return (
    <div>
      <h1>Cluster Logs (Elasticsearch)</h1>

      <div style={{ display: 'flex', gap: 8, margin: '12px 0' }}>
        <input placeholder="Algorithm" value={algorithm} onChange={(e) => setAlgorithm(e.target.value)}
          style={input} />
        <input placeholder="Currency pair" value={currencyPair} onChange={(e) => setCurrencyPair(e.target.value)}
          style={input} />
        <button onClick={search} style={{
          padding: '8px 20px', background: '#2563eb', color: '#fff', border: 'none',
          borderRadius: 6, cursor: 'pointer',
        }}>Search</button>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 8, fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#f8fafc', textAlign: 'left' }}>
              <th style={th}>Timestamp</th>
              <th style={th}>Algorithm</th>
              <th style={th}>Currency Pair</th>
              <th style={th}>Cluster Label</th>
              <th style={th}>Outlier</th>
              <th style={th}>Features</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((r, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #e2e8f0' }}>
                <td style={td}>{r.timestamp}</td>
                <td style={td}>{r.algorithm}</td>
                <td style={td}>{r.currency_pair}</td>
                <td style={td}>{r.cluster_label}</td>
                <td style={td}>{r.is_outlier ? '⚠️' : 'No'}</td>
                <td style={td}>{r.features ? JSON.stringify(r.features) : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const input = {
  padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', flex: 1,
};
const th = { padding: '8px 12px', color: '#64748b' };
const td = { padding: '8px 12px' };
