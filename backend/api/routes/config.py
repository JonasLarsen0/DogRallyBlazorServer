"""
Runtime configuration routes.

GET  /api/config  — retrieve current watched stops & walk time
POST /api/config  — update watched stops & walk time (triggers poller restart)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigResponse(BaseModel):
    stop_ids: list[str]
    walk_time_seconds: int
    poll_interval_seconds: int


class ConfigUpdateRequest(BaseModel):
    stop_ids: list[str] = Field(default_factory=list)
    walk_time_seconds: int = Field(default=300, ge=0)


@router.get("", response_model=ConfigResponse)
async def get_config(request: Request) -> ConfigResponse:
    """Return the current poller configuration."""
    poller = request.app.state.poller
    from backend.config import settings

    return ConfigResponse(
        stop_ids=poller.stop_ids,
        walk_time_seconds=poller.walk_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
    )


@router.post("", response_model=ConfigResponse)
async def update_config(
    body: ConfigUpdateRequest,
    request: Request,
) -> ConfigResponse:
    """
    Update watched stop IDs and/or walk time.

    This triggers an immediate poller restart so the new configuration
    takes effect on the next polling cycle.

    Request body::

        { "stop_ids": ["8600626", "8600868"], "walk_time_seconds": 420 }
    """
    poller = request.app.state.poller
    from backend.config import settings

    await poller.update_config(
        stop_ids=body.stop_ids,
        walk_seconds=body.walk_time_seconds,
    )
    logger.info(
        "Config updated via API — stops=%s, walk_seconds=%d",
        body.stop_ids,
        body.walk_time_seconds,
    )

    return ConfigResponse(
        stop_ids=poller.stop_ids,
        walk_time_seconds=poller.walk_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
    )
