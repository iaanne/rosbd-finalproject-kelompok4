import { useEffect, useState } from 'react';
import { api } from '../api';

export default function Features() {
  const [pairs, setPairs] = useState([]);
  const [selected, setSelected] = useState('');
  const [data, setData] = useState([]);

  useEffect(() => { api.getCurrencyPairs().then(setPairs); }, []);
  useEffect(() => {
    if (!selected) return;
    api.getFeatures(selected).then(setData);
  }, [selected]);

  return (
    <div>
      <h1>Technical Features</h1>
      <select value={selected} onChange={(e) => setSelected(e.target.value)}
        style={{ padding: '8px 12px', margin: '12px 0', borderRadius: 6, border: '1px solid #cbd5e1' }}>
        <option value="">-- Select pair --</option>
        {pairs.map((p) => <option key={p} value={p}>{p}</option>)}
      </select>

      {data.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 8, fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f8fafc', textAlign: 'left' }}>
                <th style={th}>Timestamp</th>
                <th style={th}>Returns 1d</th>
                <th style={th}>Log Return</th>
                <th style={th}>MA 5d</th>
                <th style={th}>MA 20d</th>
                <th style={th}>Volatility</th>
                <th style={th}>RSI 14</th>
                <th style={th}>BB Upper</th>
                <th style={th}>BB Lower</th>
              </tr>
            </thead>
            <tbody>
              {data.slice(0, 50).map((r, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <td style={td}>{r.ts}</td>
                  <td style={td}>{r.returns_1d?.toFixed(6)}</td>
                  <td style={td}>{r.log_return?.toFixed(6)}</td>
                  <td style={td}>{r.rolling_mean_5d?.toFixed(6)}</td>
                  <td style={td}>{r.rolling_mean_20d?.toFixed(6)}</td>
                  <td style={td}>{r.volatility_20d?.toFixed(6)}</td>
                  <td style={td}>{r.rsi_14?.toFixed(2)}</td>
                  <td style={td}>{r.bb_upper?.toFixed(6)}</td>
                  <td style={td}>{r.bb_lower?.toFixed(6)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const th = { padding: '8px 10px', color: '#64748b', whiteSpace: 'nowrap' };
const td = { padding: '8px 10px', whiteSpace: 'nowrap' };
