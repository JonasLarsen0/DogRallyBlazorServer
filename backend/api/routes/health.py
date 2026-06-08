"""
Health and stats routes.

GET /api/health  — rich operational health check (liveness + status)
GET /api/stats   — lightweight stats for dashboard status bar / about panel
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from backend.config import settings

router = APIRouter(prefix="/api", tags=["meta"])

_UTC = timezone.utc


@router.get("/health", summary="Operational health check")
async def health(request: Request) -> dict:
    """
    Return rich operational data about the running backend.

    Does **not** make a live probe to Rejseplanen — reports the result of the
    most recent background poll so the endpoint stays fast.
    """
    now = datetime.now(_UTC)

    # --- uptime ---
    startup_ts: datetime | None = getattr(request.app.state, "startup_time", None)
    uptime_seconds = int((now - startup_ts).total_seconds()) if startup_ts else 0

    # --- poller ---
    poller = request.app.state.poller
    polls_completed: int = getattr(poller, "polls_completed", 0)
    last_poll_at: datetime | None = getattr(poller, "last_poll_at", None)
    last_poll_error: str | None = getattr(poller, "last_poll_error", None)
    poller_running: bool = getattr(poller, "_task", None) is not None and not (
        getattr(poller, "_task").done()
        if getattr(poller, "_task", None)
        else True
    )

    rejseplanen_reachable: bool = last_poll_error is None and polls_completed > 0
    last_successful_poll: str | None = (
        last_poll_at.isoformat() if last_poll_at and last_poll_error is None else None
    )

    # --- websocket ---
    manager = request.app.state.connection_manager
    active_connections: int = manager.connection_count

    # --- delay log ---
    delay_stats = _delay_log_stats(settings.delay_log_path)

    return {
        "status": "ok",
        "version": "1.0.0",
        "uptime_seconds": uptime_seconds,
        "rejseplanen_api": {
            "reachable": rejseplanen_reachable,
            "last_successful_poll": last_successful_poll,
            "last_poll_error": last_poll_error,
        },
        "poller": {
            "running": poller_running,
            "watched_stops": poller.stop_ids,
            "poll_interval_seconds": settings.poll_interval_seconds,
            "polls_completed": polls_completed,
            "last_poll_at": last_poll_at.isoformat() if last_poll_at else None,
        },
        "websocket": {
            "active_connections": active_connections,
        },
        "delay_log": delay_stats,
    }


@router.get("/stats", summary="Lightweight dashboard stats")
async def stats(request: Request) -> dict:
    """
    Lightweight stats intended for the dashboard status bar / about panel.

    Returns today's and this week's delay counts, the most delayed line today,
    active WebSocket connections, and the timestamp of the last poller update.
    """
    manager = request.app.state.connection_manager
    poller = request.app.state.poller
    last_poll_at: datetime | None = getattr(poller, "last_poll_at", None)

    db_stats = _stats_query(settings.delay_log_path)

    return {
        "delays_logged_today": db_stats["today"],
        "delays_logged_this_week": db_stats["this_week"],
        "most_delayed_line_today": db_stats["most_delayed_line_today"],
        "active_connections": manager.connection_count,
        "last_update": last_poll_at.isoformat() if last_poll_at else None,
    }


# ---------------------------------------------------------------------------
# Internal helpers — synchronous SQLite queries (fast, single-file DB)
# ---------------------------------------------------------------------------


def _delay_log_stats(db_path: str) -> dict:
    """Return aggregate counts and file size for the delay log."""
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN delay_tier >= 30 THEN 1 ELSE 0 END) AS t30,
                    SUM(CASE WHEN delay_tier >= 60 THEN 1 ELSE 0 END) AS t60,
                    SUM(CASE WHEN delay_tier >= 90 THEN 1 ELSE 0 END) AS t90
                FROM delay_logs
                """
            ).fetchone()
        total, t30, t60, t90 = (int(v or 0) for v in row)
    except Exception:
        total = t30 = t60 = t90 = 0

    try:
        db_size = os.path.getsize(db_path)
    except OSError:
        db_size = 0

    return {
        "total_entries": total,
        "entries_30min": t30,
        "entries_60min": t60,
        "entries_90min": t90,
        "db_size_bytes": db_size,
    }


def _stats_query(db_path: str) -> dict:
    """Return today/week counts and most-delayed line today."""
    today_count = 0
    week_count = 0
    most_delayed_line: str | None = None

    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN log_date = date('now') THEN 1 ELSE 0 END),
                    SUM(CASE WHEN log_date >= date('now', '-6 days') THEN 1 ELSE 0 END)
                FROM delay_logs
                """
            ).fetchone()
            today_count = int(row[0] or 0)
            week_count = int(row[1] or 0)

            line_row = conn.execute(
                """
                SELECT line
                FROM delay_logs
                WHERE log_date = date('now')
                GROUP BY line
                ORDER BY COUNT(*) DESC
                LIMIT 1
                """
            ).fetchone()
            most_delayed_line = line_row[0] if line_row else None
    except Exception:
        pass

    return {
        "today": today_count,
        "this_week": week_count,
        "most_delayed_line_today": most_delayed_line,
    }
