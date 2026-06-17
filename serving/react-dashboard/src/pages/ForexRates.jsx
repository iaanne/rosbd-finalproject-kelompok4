import { useEffect, useState } from 'react';
import { api } from '../api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

export default function ForexRates() {
  const [pairs, setPairs] = useState([]);
  const [selected, setSelected] = useState('');
  const [data, setData] = useState([]);

  useEffect(() => { api.getCurrencyPairs().then(setPairs); }, []);
  useEffect(() => {
    if (!selected) return;
    api.getForexRates(selected).then(setData);
  }, [selected]);

  const chartData = [...data].reverse();

  return (
    <div>
      <h1>Forex Rates</h1>
      <select value={selected} onChange={(e) => setSelected(e.target.value)}
        style={{ padding: '8px 12px', margin: '12px 0', borderRadius: 6, border: '1px solid #cbd5e1' }}>
        <option value="">-- Select pair --</option>
        {pairs.map((p) => <option key={p} value={p}>{p}</option>)}
      </select>

      {chartData.length > 0 && (
        <div style={{ background: '#fff', borderRadius: 8, padding: 16, marginTop: 12 }}>
          <h3>{selected} — Close Price</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="ts" tick={false} />
              <YAxis domain={['auto', 'auto']} />
              <Tooltip />
              <Line type="monotone" dataKey="close" stroke="#2563eb" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {chartData.length > 0 && (
        <div style={{ overflowX: 'auto', marginTop: 16 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 8 }}>
            <thead>
              <tr style={{ background: '#f8fafc', textAlign: 'left' }}>
                <th style={th}>Timestamp</th>
                <th style={th}>Open</th>
                <th style={th}>High</th>
                <th style={th}>Low</th>
                <th style={th}>Close</th>
                <th style={th}>Volume</th>
              </tr>
            </thead>
            <tbody>
              {chartData.slice(0, 20).map((r, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <td style={td}>{r.ts}</td>
                  <td style={td}>{r.open}</td>
                  <td style={td}>{r.high}</td>
                  <td style={td}>{r.low}</td>
                  <td style={td}>{r.close}</td>
                  <td style={td}>{r.volume}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const th = { padding: '8px 12px', fontSize: 13, color: '#64748b' };
const td = { padding: '8px 12px', fontSize: 13 };
