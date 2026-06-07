"""
Departure board routes.

GET  /api/departures/{stop_id}          — single stop, live fetch
POST /api/departures/favorites          — multiple stops, live fetch
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.models.departure import StopDepartures

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/departures", tags=["departures"])


class FavoritesRequest(BaseModel):
    stop_ids: list[str]


@router.get("/{stop_id}", response_model=StopDepartures)
async def get_stop_departures(
    stop_id: str,
    request: Request,
) -> StopDepartures:
    """
    Fetch the departure board for a single stop (uncached, real-time request).
    """
    client = request.app.state.rejseplanen_client
    try:
        result = await client.get_departures(stop_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("get_stop_departures route error for %s: %s", stop_id, exc)
        raise HTTPException(status_code=502, detail="Upstream API error") from exc

    return result


@router.post("/favorites", response_model=list[StopDepartures])
async def get_favorite_departures(
    body: FavoritesRequest,
    request: Request,
) -> list[StopDepartures]:
    """
    Fetch departure boards for multiple stops at once.

    Request body::

        { "stop_ids": ["8600626", "8600868"] }
    """
    if not body.stop_ids:
        return []

    client = request.app.state.rejseplanen_client
    try:
        results = await client.get_multi_departures(body.stop_ids)
    except Exception as exc:  # noqa: BLE001
        logger.error("get_favorite_departures route error: %s", exc)
        raise HTTPException(status_code=502, detail="Upstream API error") from exc

    return results
