"""
Service alert route.

GET /api/alerts
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from backend.models.departure import Alert

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[Alert])
async def get_alerts(request: Request) -> list[Alert]:
    """
    Return currently active HIM (service disruption) messages from Rejseplanen.
    """
    client = request.app.state.rejseplanen_client
    try:
        return await client.get_alerts()
    except Exception as exc:  # noqa: BLE001
        logger.error("get_alerts route error: %s", exc)
        raise HTTPException(status_code=502, detail="Upstream API error") from exc
