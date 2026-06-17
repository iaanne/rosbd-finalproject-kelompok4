from fastapi import WebSocket
from typing import Set
import logging
import json
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

    async def broadcast_forex_update(self, data: dict):
        await self.broadcast({"type": "forex_update", "data": data})

    async def broadcast_feature_update(self, data: dict):
        await self.broadcast({"type": "feature_update", "data": data})

    async def broadcast_clustering_done(self, data: dict):
        await self.broadcast({"type": "clustering_done", "data": data})

    async def broadcast_notification(self, data: dict):
        await self.broadcast({"type": "notification", "data": data})


manager = ConnectionManager()
