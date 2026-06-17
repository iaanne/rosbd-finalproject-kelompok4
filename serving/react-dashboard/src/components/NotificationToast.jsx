import { useState, useEffect, useCallback } from 'react';

const TOAST_DURATION = 5000;

export default function NotificationToast({ notification, onDismiss }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!notification) return;
    requestAnimationFrame(() => setVisible(true));
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(() => onDismiss(), 300);
    }, TOAST_DURATION);
    return () => clearTimeout(timer);
  }, [notification, onDismiss]);

  if (!notification) return null;

  const typeColors = {
    clustering_done: '#3b82f6',
    forex_update: '#10b981',
    notification: '#f59e0b',
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 20,
        right: 20,
        zIndex: 9999,
        background: '#1e293b',
        color: '#fff',
        padding: '12px 20px',
        borderRadius: 8,
        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
        maxWidth: 380,
        transform: visible ? 'translateX(0)' : 'translateX(120%)',
        opacity: visible ? 1 : 0,
        transition: 'all 0.3s ease',
        borderLeft: `4px solid ${typeColors[notification.type] || '#6366f1'}`,
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 14 }}>
        {notification.title || notification.type}
      </div>
      <div style={{ fontSize: 13, color: '#cbd5e1' }}>
        {notification.message || JSON.stringify(notification.data || '')}
      </div>
    </div>
  );
}
