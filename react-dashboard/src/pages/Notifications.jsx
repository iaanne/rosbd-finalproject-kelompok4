import { useState, useEffect } from 'react';
import { api } from '../api';

export default function Notifications() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getNotifications().then((data) => {
      setNotifications(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const typeBadge = (type) => {
    const colors = {
      clustering_done: { bg: '#dbeafe', color: '#1e40af', label: 'Clustering' },
      forex_update: { bg: '#d1fae5', color: '#065f46', label: 'Forex' },
      notification: { bg: '#fef3c7', color: '#92400e', label: 'Info' },
    };
    const c = colors[type] || { bg: '#e2e8f0', color: '#475569', label: type };
    return (
      <span style={{
        background: c.bg, color: c.color,
        padding: '2px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600,
      }}>
        {c.label}
      </span>
    );
  };

  if (loading) return <div style={{ padding: 20 }}>Loading...</div>;

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Notifications</h2>
      {notifications.length === 0 && <p style={{ color: '#64748b' }}>No notifications yet.</p>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {notifications.map((n) => (
          <div
            key={n.id}
            style={{
              background: '#fff',
              padding: '12px 16px',
              borderRadius: 8,
              border: '1px solid #e2e8f0',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {typeBadge(n.type)}
                <strong>{n.title}</strong>
              </div>
              <span style={{ fontSize: 12, color: '#94a3b8' }}>
                {n.ts ? new Date(n.ts).toLocaleString() : ''}
              </span>
            </div>
            <div style={{ color: '#64748b', fontSize: 14 }}>{n.message}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
