"""
Departure board routes.

GET  /api/departures/{stop_id}          — single stop, live fetch
GET  /api/departures/{stop_id}/next     — single next departure for a stop
POST /api/departures/favorites          — multiple stops, live fetch
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.models.departure import StopDepartures

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/departures", tags=["departures"])

_UTC = timezone.utc


class FavoritesRequest(BaseModel):
    stop_ids: list[str]


@router.get("/{stop_id}/next", summary="Next single departure for a stop")
async def get_next_departure(
    stop_id: str,
    request: Request,
) -> dict:
    """
    Return just the next single departure for a stop.

    Useful for Home Assistant integrations and quick status checks.
    Returns 404 if the stop has no upcoming departures.
    """
    client = request.app.state.rejseplanen_client
    try:
        result = await client.get_departures(stop_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("get_next_departure route error for %s: %s", stop_id, exc)
        raise HTTPException(status_code=502, detail="Upstream API error") from exc

    now = datetime.now(tz=_UTC)

    # Find the next departure that has not yet departed (effective time in the future)
    next_dep = None
    for dep in result.departures:
        effective = dep.expected_time or dep.planned_time
        if effective > now:
            next_dep = dep
            break

    if next_dep is None:
        raise HTTPException(status_code=404, detail="No upcoming departures for this stop")

    effective_time = next_dep.expected_time or next_dep.planned_time
    countdown_seconds = int((effective_time - now).total_seconds())

    return {
        "stop_id": result.stop_id,
        "stop_name": result.stop_name,
        "next_departure": {
            "line": next_dep.line,
            "direction": next_dep.direction,
            "planned_time": next_dep.planned_time.isoformat(),
            "expected_time": next_dep.expected_time.isoformat() if next_dep.expected_time else None,
            "delay_minutes": next_dep.delay_minutes,
            "cancelled": next_dep.cancelled,
            "track": next_dep.track,
            "countdown_seconds": countdown_seconds,
        },
    }


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
