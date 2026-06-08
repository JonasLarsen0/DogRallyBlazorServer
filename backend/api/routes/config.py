"""
Runtime configuration routes.

GET  /api/config  — retrieve current watched stops & walk time
POST /api/config  — update watched stops & walk time (triggers poller restart)

Validation rules for POST:
  - stop_ids: each must match r'^\\d{6,10}$' (Rejseplanen numeric IDs)
  - stop_ids: max 10 entries
  - walk_time_seconds: 60–3600 (1–60 minutes)

Config is persisted to disk so it survives container restarts.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])

_STOP_ID_RE = re.compile(r"^\d{6,10}$")
_MAX_STOP_IDS = 10
_RUNTIME_CONFIG_PATH = Path(settings.delay_log_path).parent / "runtime_config.json"


def _persist_config(stop_ids: list[str], walk_time_seconds: int) -> None:
    """Write current runtime config to disk for persistence across restarts."""
    try:
        _RUNTIME_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _RUNTIME_CONFIG_PATH.write_text(
            json.dumps({"stop_ids": stop_ids, "walk_time_seconds": walk_time_seconds})
        )
        logger.debug("Runtime config persisted to %s", _RUNTIME_CONFIG_PATH)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not persist runtime config: %s", exc)


class ConfigResponse(BaseModel):
    stop_ids: list[str]
    walk_time_seconds: int
    poll_interval_seconds: int


class ConfigUpdateRequest(BaseModel):
    stop_ids: list[str] = Field(default_factory=list)
    walk_time_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Walk time to station in seconds (60–3600, i.e. 1–60 minutes)",
    )


@router.get("", response_model=ConfigResponse)
async def get_config(request: Request) -> ConfigResponse:
    """Return the current poller configuration."""
    poller = request.app.state.poller

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
    takes effect on the next polling cycle.  The config is persisted to disk
    and will be restored on the next container restart.

    Request body::

        { "stop_ids": ["8600626", "8600868"], "walk_time_seconds": 420 }

    Stop ID rules:
      - Each must be a numeric string of 6–10 digits (Rejseplanen format)
      - Maximum 10 stop IDs
    """
    # --- Validate and normalise stop_ids ---
    cleaned: list[str] = []
    invalid: list[str] = []

    for raw in body.stop_ids:
        sid = raw.strip()
        if not _STOP_ID_RE.match(sid):
            invalid.append(raw)
        else:
            cleaned.append(sid)

    if invalid:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid stop ID(s): {invalid!r}. "
                "Stop IDs must be numeric strings of 6–10 digits "
                "(e.g. '8600626')."
            ),
        )

    if len(cleaned) > _MAX_STOP_IDS:
        raise HTTPException(
            status_code=422,
            detail=f"Too many stop IDs: {len(cleaned)} supplied, maximum is {_MAX_STOP_IDS}.",
        )

    poller = request.app.state.poller

    await poller.update_config(
        stop_ids=cleaned,
        walk_seconds=body.walk_time_seconds,
    )

    _persist_config(cleaned, body.walk_time_seconds)

    logger.info(
        "Config updated via API — stops=%s, walk_seconds=%d",
        cleaned,
        body.walk_time_seconds,
    )

    return ConfigResponse(
        stop_ids=poller.stop_ids,
        walk_time_seconds=poller.walk_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
    )
