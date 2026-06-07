"""
WebSocket endpoint.

WS /ws

On connection:
  1. The latest cached departures snapshot is sent immediately (if available).
  2. The client remains connected and receives broadcast updates from the poller.

The connection is kept alive until the client disconnects or a send error
occurs.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle a WebSocket client connection."""
    manager = websocket.app.state.connection_manager
    poller = websocket.app.state.poller

    await manager.connect(websocket)

    # Immediately push the latest cached snapshot so the client doesn't have
    # to wait until the next polling cycle.
    last_payload = poller.last_payload
    if last_payload is not None:
        try:
            await websocket.send_json(last_payload)
            logger.debug("Sent cached snapshot to new WebSocket client")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not send initial snapshot: %s", exc)
            manager.disconnect(websocket)
            return

    # Keep the connection open — wait for the client to close it or for a
    # network error.  We do not process any inbound messages, but we must
    # call receive() so that disconnect events propagate.
    try:
        while True:
            # Blocks until the client sends something or disconnects.
            # We discard the message content — clients are read-only consumers.
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected normally")
    except Exception as exc:  # noqa: BLE001
        logger.warning("WebSocket connection error: %s", exc)
    finally:
        manager.disconnect(websocket)
