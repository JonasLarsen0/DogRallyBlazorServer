"""
WebSocket connection manager.

Keeps track of all active WebSocket clients and broadcasts JSON payloads to
every connected client.  Any client that has disconnected is silently removed.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages a set of active WebSocket connections."""

    def __init__(self) -> None:
        self._active: set[WebSocket] = set()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self, websocket: WebSocket) -> None:
        """Accept the connection and register it."""
        await websocket.accept()
        self._active.add(websocket)
        logger.info(
            "WebSocket client connected — total connections: %d",
            len(self._active),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove the connection from the active set (idempotent)."""
        self._active.discard(websocket)
        logger.info(
            "WebSocket client disconnected — remaining connections: %d",
            len(self._active),
        )

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_json(self, websocket: WebSocket, data: Any) -> None:
        """Send JSON to a single client, disconnect on error."""
        try:
            await websocket.send_json(data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to send to WebSocket client: %s", exc)
            self.disconnect(websocket)

    async def broadcast_json(self, data: Any) -> None:
        """
        Broadcast a JSON-serialisable payload to all connected clients.

        Disconnected / errored clients are removed from the active set.
        """
        if not self._active:
            return

        # Snapshot to avoid mutation during iteration
        clients = list(self._active)
        dead: list[WebSocket] = []

        for ws in clients:
            try:
                await ws.send_json(data)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Broadcast failed for a client (%s) — removing", exc)
                dead.append(ws)

        for ws in dead:
            self._active.discard(ws)

    async def broadcast_departures(self, data: dict[str, Any]) -> None:
        """
        Convenience wrapper — broadcasts a departures payload.

        Expects ``data`` to be a dict with at least a ``"type"`` key.
        """
        await self.broadcast_json(data)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def connection_count(self) -> int:
        """Number of currently active connections."""
        return len(self._active)
