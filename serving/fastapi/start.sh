#!/bin/sh

echo "Starting tailscaled in userspace mode..."
tailscaled --tun=userspace-networking --socks5-server=127.0.0.1:1055 &

# Wait for tailscaled to start
sleep 2

echo "Connecting to Tailscale..."
if [ -n "$TAILSCALE_AUTHKEY" ]; then
    tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname=render-fastapi
else
    echo "WARNING: TAILSCALE_AUTHKEY is not set."
fi

echo "Starting FastAPI with proxychains..."
exec proxychains4 uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
