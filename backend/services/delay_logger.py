"""
Delay logging service for compensation purposes.

Algorithm
---------
1. On every poll, we receive a fresh StopDepartures board.
2. We maintain a dict of "tracked" departures keyed by journey_id.
3. When a departure appears/updates, we upsert its latest delay into the tracker.
   If a pending log task exists for that journey_id (false-positive guard),
   we cancel it — the train is still there.
4. When a departure disappears from the board we check whether its expected
   departure time is plausibly in the past (i.e. the train actually departed,
   not just scrolled out of the 20-result window).  If so we schedule a log
   task after a short confirmation wait.
5. At log time we write to SQLite if delay >= 30 minutes.

Timing rationale
----------------
Rejseplanen removes a departure from the board when the train actually
departs.  Historical delay data is then available for roughly 30 minutes
before it is cleared.  We therefore:

  • Trigger on disappearance from the board (the train has left).
  • Wait CONFIRMATION_SECONDS (90 s = 3 poll cycles) before writing.
    This cancels any task if the departure reappears (transient API gap).
  • 90 s is well within the ~30-minute Rejseplanen history window.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models.departure import StopDepartures

logger = logging.getLogger(__name__)

_UTC = timezone.utc

# Delay thresholds for compensation tiers (minutes)
TIERS = (30, 60, 90)

# Only consider a departure genuinely "gone" if its expected time is within
# this window of the past.  Trains more than 3 hours in the future that
# vanish have merely scrolled out of the 20-result window.
_MAX_LOOKBACK_HOURS = 3

# Wait this many seconds after detecting disappearance before writing to DB.
# 3 poll cycles — long enough to cancel on a false-positive reappearance,
# short enough to stay well within Rejseplanen's ~30-minute history window.
_CONFIRMATION_SECONDS = 90.0

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS delay_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    journey_id       TEXT    NOT NULL,
    stop_id          TEXT    NOT NULL,
    stop_name        TEXT    NOT NULL,
    line             TEXT    NOT NULL,
    direction        TEXT    NOT NULL,
    vehicle_type     TEXT    NOT NULL,
    planned_time     TEXT    NOT NULL,
    actual_time      TEXT    NOT NULL,
    delay_minutes    INTEGER NOT NULL,
    delay_tier       INTEGER NOT NULL,
    logged_at        TEXT    NOT NULL,
    log_date         TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_log_date     ON delay_logs(log_date);
CREATE INDEX IF NOT EXISTS idx_stop_id      ON delay_logs(stop_id);
CREATE INDEX IF NOT EXISTS idx_delay_tier   ON delay_logs(delay_tier);
CREATE INDEX IF NOT EXISTS idx_journey_id   ON delay_logs(journey_id);
"""


@dataclass
class _Tracked:
    journey_id: str
    stop_id: str
    stop_name: str
    line: str
    direction: str
    vehicle_type: str
    planned_time: datetime
    last_expected_time: datetime
    last_delay_minutes: int
    first_seen_at: datetime
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(_UTC))


def _delay_tier(minutes: int) -> int | None:
    """Return the highest compensation tier breached, or None if under 30 min."""
    for tier in reversed(TIERS):
        if minutes >= tier:
            return tier
    return None


class DelayLogger:
    """
    Tracks departure delays across polls and persists qualifying events to
    a local SQLite database for later compensation claims.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._tracking: dict[str, _Tracked] = {}
        self._log_tasks: dict[str, asyncio.Task[None]] = {}

        # Initialise schema synchronously — called at startup before the event loop
        # is busy, so a quick blocking call is acceptable here.
        self._init_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_board(self, board: "StopDepartures") -> None:
        """
        Feed the latest departure board into the tracker.

        Call this from the poller on every successful fetch — it is
        deliberately synchronous so it never blocks the event loop.
        """
        now = datetime.now(_UTC)
        current_ids = {d.journey_id for d in board.departures}

        # Upsert currently visible departures
        for dep in board.departures:
            effective = dep.expected_time or dep.planned_time
            tracked = self._tracking.get(dep.journey_id)
            if tracked is None:
                self._tracking[dep.journey_id] = _Tracked(
                    journey_id=dep.journey_id,
                    stop_id=dep.stop_id,
                    stop_name=dep.stop_name,
                    line=dep.line,
                    direction=dep.direction,
                    vehicle_type=dep.vehicle_type,
                    planned_time=dep.planned_time,
                    last_expected_time=effective,
                    last_delay_minutes=dep.delay_minutes,
                    first_seen_at=now,
                    last_seen_at=now,
                )
            else:
                tracked.last_expected_time = effective
                tracked.last_delay_minutes = dep.delay_minutes
                tracked.last_seen_at = now
                # If a log task was pending (false-positive from a transient
                # API gap), cancel it — the train is still on the board.
                pending = self._log_tasks.pop(dep.journey_id, None)
                if pending and not pending.done():
                    pending.cancel()
                    logger.debug(
                        "Cancelled pending log for %s — departure reappeared",
                        dep.journey_id,
                    )

        # Detect departures that have vanished from the board
        for journey_id in list(self._tracking):
            if journey_id in current_ids:
                continue  # still visible
            if journey_id in self._log_tasks:
                continue  # already scheduled

            tracked = self._tracking.pop(journey_id)

            # Guard: only treat as genuinely departed if expected time is
            # plausibly in the past (not just scrolled out of top-20 results).
            cutoff = now - timedelta(hours=_MAX_LOOKBACK_HOURS)
            if tracked.last_expected_time < cutoff:
                logger.debug(
                    "Departure %s ignored — expected time too old (%s)",
                    journey_id,
                    tracked.last_expected_time.isoformat(),
                )
                continue

            if tracked.last_delay_minutes < TIERS[0]:
                logger.debug(
                    "Departure %s: delay %d min < %d min threshold, not logging",
                    journey_id,
                    tracked.last_delay_minutes,
                    TIERS[0],
                )
                continue

            # Departure has left the board — schedule a confirmation write.
            # 90 s = 3 poll cycles: enough to catch a reappearance (transient
            # API gap) while staying within Rejseplanen's ~30-min history window.
            task = asyncio.create_task(
                self._delayed_write(tracked, _CONFIRMATION_SECONDS),
                name=f"delay_log_{journey_id}",
            )
            self._log_tasks[journey_id] = task
            logger.info(
                "Departure gone — logging %s %s (delay=%d min) in %.0f s",
                tracked.line,
                tracked.direction,
                tracked.last_delay_minutes,
                _CONFIRMATION_SECONDS,
            )

    async def close(self) -> None:
        """Cancel pending log tasks on shutdown (data loss is acceptable here)."""
        for task in self._log_tasks.values():
            if not task.done():
                task.cancel()

    # ------------------------------------------------------------------
    # Query helpers (called by the REST endpoint)
    # ------------------------------------------------------------------

    def query_logs(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        stop_id: str | None = None,
        min_tier: int = 30,
        line: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        clauses = ["delay_tier >= ?"]
        params: list = [min_tier]

        if date_from:
            clauses.append("log_date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("log_date <= ?")
            params.append(date_to)
        if stop_id:
            clauses.append("stop_id = ?")
            params.append(stop_id)
        if line:
            clauses.append("line = ?")
            params.append(line)

        where = " AND ".join(clauses)
        sql = (
            f"SELECT * FROM delay_logs WHERE {where} "
            f"ORDER BY planned_time DESC LIMIT ? OFFSET ?"
        )
        params += [limit, offset]

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def summary(self) -> dict:
        """Per-stop, per-tier counts for the last 30 days."""
        sql = """
            SELECT
                stop_name,
                delay_tier,
                COUNT(*) AS count
            FROM delay_logs
            WHERE log_date >= date('now', '-30 days')
            GROUP BY stop_name, delay_tier
            ORDER BY stop_name, delay_tier
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql).fetchall()
            return {"rows": [dict(r) for r in rows]}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_CREATE_TABLE)
            conn.commit()
        logger.info("DelayLogger: database ready at %s", self._db_path)

    async def _delayed_write(self, tracked: _Tracked, wait_seconds: float) -> None:
        try:
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            tier = _delay_tier(tracked.last_delay_minutes)
            if tier is None:
                return  # delay dropped below threshold while we waited

            await asyncio.get_event_loop().run_in_executor(
                None, self._write_sync, tracked, tier
            )
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "DelayLogger: failed to write log for %s: %s",
                tracked.journey_id,
                exc,
            )
        finally:
            self._log_tasks.pop(tracked.journey_id, None)

    def _write_sync(self, tracked: _Tracked, tier: int) -> None:
        now = datetime.now(_UTC)
        log_date = tracked.planned_time.astimezone(_UTC).strftime("%Y-%m-%d")

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO delay_logs
                    (journey_id, stop_id, stop_name, line, direction,
                     vehicle_type, planned_time, actual_time, delay_minutes,
                     delay_tier, logged_at, log_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tracked.journey_id,
                    tracked.stop_id,
                    tracked.stop_name,
                    tracked.line,
                    tracked.direction,
                    tracked.vehicle_type,
                    tracked.planned_time.isoformat(),
                    tracked.last_expected_time.isoformat(),
                    tracked.last_delay_minutes,
                    tier,
                    now.isoformat(),
                    log_date,
                ),
            )
            conn.commit()

        logger.info(
            "DelayLogger: logged %s → %s, delay=%d min (tier %d+)",
            tracked.line,
            tracked.direction,
            tracked.last_delay_minutes,
            tier,
        )
