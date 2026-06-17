import { useEffect, useRef, useCallback } from 'react';

export default function useWebSocket(onMessage, enabled = true) {
  const ws = useRef(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!enabled) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws`;

    let reconnectTimer = null;

    function connect() {
      if (ws.current?.readyState === WebSocket.OPEN) return;

      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageRef.current?.(data);
        } catch (err) {
          console.error('WebSocket parse error:', err);
        }
      };

      ws.current.onclose = () => {
        console.log('WebSocket disconnected, reconnecting in 3s...');
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.current.onerror = () => {
        ws.current?.close();
      };
    }

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      ws.current?.close();
    };
  }, [enabled]);

  return ws;
}
