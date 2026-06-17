export default function NotificationBadge({ count }) {
  if (count === 0) return null;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#ef4444',
        color: '#fff',
        fontSize: 11,
        fontWeight: 700,
        minWidth: 20,
        height: 20,
        borderRadius: 10,
        padding: '0 6px',
        marginLeft: 8,
      }}
    >
      {count > 99 ? '99+' : count}
    </span>
  );
}
