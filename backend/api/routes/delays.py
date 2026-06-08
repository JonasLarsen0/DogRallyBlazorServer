"""
REST endpoints for querying the delay log.

Intended use: look up past delays for compensation claims.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/delays", tags=["delays"])


class DelayLogEntry(BaseModel):
    id: int
    journey_id: str
    stop_id: str
    stop_name: str
    line: str
    direction: str
    vehicle_type: str
    planned_time: str
    actual_time: str
    delay_minutes: int
    delay_tier: int
    logged_at: str
    log_date: str


class DelayLogsResponse(BaseModel):
    total: int
    offset: int
    limit: int
    results: list[DelayLogEntry]


@router.get("", response_model=DelayLogsResponse, summary="List logged delays")
async def list_delays(
    request: Request,
    date_from: str | None = Query(
        None,
        description="Filter from date (YYYY-MM-DD, inclusive)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    date_to: str | None = Query(
        None,
        description="Filter to date (YYYY-MM-DD, inclusive)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    stop_id: str | None = Query(None, description="Filter by stop ID"),
    min_tier: int = Query(30, ge=30, le=90, description="Minimum delay tier (30, 60, or 90)"),
    line: str | None = Query(None, description="Filter by line (e.g. 'IC')"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> DelayLogsResponse:
    """
    Query the delay log.  Returns delays >= ``min_tier`` minutes.

    Use ``date_from`` / ``date_to`` to narrow the search for a specific
    journey you want to claim compensation for.
    """
    delay_logger = request.app.state.delay_logger
    rows = delay_logger.query_logs(
        date_from=date_from,
        date_to=date_to,
        stop_id=stop_id,
        min_tier=min_tier,
        line=line,
        limit=limit,
        offset=offset,
    )
    return DelayLogsResponse(
        total=len(rows),
        offset=offset,
        limit=limit,
        results=[DelayLogEntry(**r) for r in rows],
    )


@router.get("/summary", summary="Delay summary last 30 days")
async def delay_summary(request: Request) -> dict:
    """
    Per-stop breakdown of delay events in the last 30 days,
    grouped by delay tier (30/60/90 minutes).
    """
    return request.app.state.delay_logger.summary()
