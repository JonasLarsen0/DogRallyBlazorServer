"""
Stop search route.

GET /api/stops/search?q={query}
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from backend.models.stop import Stop

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stops", tags=["stops"])


@router.get("/search", response_model=list[Stop])
async def search_stops(
    request: Request,
    q: str = Query(..., min_length=1, description="Stop name fragment to search for"),
) -> list[Stop]:
    """
    Search for stops and stations by name fragment.

    Returns up to 10 matching stops from Rejseplanen's location search.
    """
    client = request.app.state.rejseplanen_client
    try:
        return await client.search_stops(q)
    except Exception as exc:  # noqa: BLE001
        logger.error("search_stops route error: %s", exc)
        raise HTTPException(status_code=502, detail="Upstream API error") from exc
