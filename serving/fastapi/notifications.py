from fastapi import WebSocket
from typing import Set
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket client connected (%d total)", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info("WebSocket client disconnected (%d remaining)", len(self.active_connections))

    async def broadcast(self, message: dict):
        dead = set()
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        if dead:
            self.active_connections -= dead
            logger.warning("Removed %d stale WebSocket connections", len(dead))

    async def broadcast_price_update(self, data: dict):
        await self.broadcast({"type": "price_update", **data})

    async def broadcast_alert(self, data: dict):
        payload = {
            "type": "alert",
            "severity": data.get("severity", "info"),
            "category": data.get("category", "general"),
            "title": data.get("title", ""),
            "message": data.get("message", ""),
            "ts": data.get("ts", datetime.now(timezone.utc).isoformat()),
        }
        await self.broadcast(payload)

    async def broadcast_system(self, data: dict):
        await self.broadcast({"type": "system", **data})


manager = ConnectionManager()
