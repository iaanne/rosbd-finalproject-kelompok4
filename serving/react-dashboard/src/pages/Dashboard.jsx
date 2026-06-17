import { useEffect, useState } from 'react';
import { api } from '../api';

export default function Dashboard() {
  const [pairs, setPairs] = useState([]);
  const [batches, setBatches] = useState([]);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.getCurrencyPairs().then(setPairs).catch(() => {});
    api.getBatches().then(setBatches).catch(() => {});
    api.health().then(setHealth).catch(() => setHealth({ status: 'error' }));
  }, []);

  return (
    <div>
      <h1>Dashboard</h1>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', margin: '16px 0' }}>
        <StatCard label="API Status" value={health?.status ?? '...'} />
        <StatCard label="Currency Pairs" value={pairs.length} />
        <StatCard label="Batch IDs" value={batches.length} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <div style={{ background: '#fff', borderRadius: 8, padding: 16 }}>
          <h3>Currency Pairs</h3>
          {pairs.length === 0 ? <p style={{ color: '#94a3b8' }}>No data yet</p> : (
            <ul>{pairs.map((p) => <li key={p}>{p}</li>)}</ul>
          )}
        </div>
        <div style={{ background: '#fff', borderRadius: 8, padding: 16 }}>
          <h3>Recent Batches</h3>
          {batches.length === 0 ? <p style={{ color: '#94a3b8' }}>No data yet</p> : (
            <ul>{batches.map((b) => <li key={b}>{b}</li>)}</ul>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 8, padding: '16px 24px', minWidth: 150,
      boxShadow: '0 1px 3px rgba(0,0,0,.08)',
    }}>
      <div style={{ color: '#64748b', fontSize: 13 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 700, marginTop: 4 }}>{value}</div>
    </div>
  );
}
