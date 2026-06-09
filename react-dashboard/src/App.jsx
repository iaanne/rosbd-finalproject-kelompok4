import { Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ForexRates from './pages/ForexRates';
import Features from './pages/Features';
import Clustering from './pages/Clustering';
import Logs from './pages/Logs';

const nav = [
  { to: '/', label: 'Dashboard' },
  { to: '/forex-rates', label: 'Forex Rates' },
  { to: '/features', label: 'Features' },
  { to: '/clustering', label: 'Clustering' },
  { to: '/logs', label: 'Cluster Logs' },
];

export default function App() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', margin: 0, fontFamily: 'system-ui, sans-serif' }}>
      <nav style={{ width: 220, background: '#1e293b', color: '#fff', padding: '1.5rem 0' }}>
        <h2 style={{ padding: '0 1rem', fontSize: 1.1, marginBottom: 24 }}>
          📊 De-dolarisasi
        </h2>
        {nav.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              display: 'block',
              padding: '10px 1rem',
              color: isActive ? '#38bdf8' : '#cbd5e1',
              background: isActive ? '#0f172a' : 'transparent',
              textDecoration: 'none',
              borderRight: isActive ? '3px solid #38bdf8' : '3px solid transparent',
            })}
          >
            {label}
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
        </Routes>
      </main>
    </div>
  );
}
