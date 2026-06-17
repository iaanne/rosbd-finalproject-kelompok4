import { useState, useCallback } from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ForexRates from './pages/ForexRates';
import Features from './pages/Features';
import Clustering from './pages/Clustering';
import Logs from './pages/Logs';
import NotificationsPage from './pages/Notifications';
import useWebSocket from './hooks/useWebSocket';
import NotificationToast from './components/NotificationToast';
import NotificationBadge from './components/NotificationBadge';

const nav = [
  { to: '/', label: 'Dashboard' },
  { to: '/forex-rates', label: 'Forex Rates' },
  { to: '/features', label: 'Features' },
  { to: '/clustering', label: 'Clustering' },
  { to: '/logs', label: 'Cluster Logs' },
  { to: '/notifications', label: 'Notifications' },
];

export default function App() {
  const [latestToast, setLatestToast] = useState(null);
  const [unreadCount, setUnreadCount] = useState(0);

  const handleWsMessage = useCallback((msg) => {
    if (msg.type === 'notification') {
      setLatestToast(msg.data);
      setUnreadCount((c) => c + 1);
    }
  }, []);

  useWebSocket(handleWsMessage, true);

  const dismissToast = useCallback(() => {
    setLatestToast(null);
  }, []);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', margin: 0, fontFamily: 'system-ui, sans-serif' }}>
      <NotificationToast notification={latestToast} onDismiss={dismissToast} />

      <nav style={{ width: 220, background: '#1e293b', color: '#fff', padding: '1.5rem 0' }}>
        <h2 style={{ padding: '0 1rem', fontSize: '1.1rem', marginBottom: 24 }}>
          De-dolarisasi
        </h2>
        {nav.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            onClick={() => to === '/notifications' && setUnreadCount(0)}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              padding: '10px 1rem',
              color: isActive ? '#38bdf8' : '#cbd5e1',
              background: isActive ? '#0f172a' : 'transparent',
              textDecoration: 'none',
              borderRight: isActive ? '3px solid #38bdf8' : '3px solid transparent',
            })}
          >
            {label}
            {to === '/notifications' && <NotificationBadge count={unreadCount} />}
          </NavLink>
        ))}
      </nav>

      <main style={{ flex: 1, padding: '1.5rem 2rem', background: '#f1f5f9' }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/forex-rates" element={<ForexRates />} />
          <Route path="/features" element={<Features />} />
          <Route path="/clustering" element={<Clustering />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/notifications" element={<NotificationsPage />} />
        </Routes>
      </main>
    </div>
  );
}
