import asyncio
import json
import logging
from typing import List, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages active WebSocket client connections and event broadcasting."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return

        payload = json.dumps(message, default=str)
        dead_connections = []
        
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(payload)
                except Exception as e:
                    logger.debug(f"Failed to send to client: {e}")
                    dead_connections.append(connection)

            for dead in dead_connections:
                self.active_connections.discard(dead)

manager = ConnectionManager()
