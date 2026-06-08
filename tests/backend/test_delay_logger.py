"""
Tests for backend.services.delay_logger.DelayLogger.

All tests use a temporary SQLite DB (via tmp_path) and manipulate the
internal _tracking / _log_tasks state directly to stay fully unit-level.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio

from backend.models.departure import Departure, StopDepartures
from backend.services.delay_logger import DelayLogger, _delay_tier, TIERS

_DK_TZ = ZoneInfo("Europe/Copenhagen")
_UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dt(hour: int, minute: int = 0, offset_minutes: int = 0, day: int = 8) -> datetime:
    """Return a Copenhagen-aware datetime, optionally shifted by offset_minutes."""
    base = datetime(2026, 6, day, hour, minute, tzinfo=_DK_TZ)
    return base + timedelta(minutes=offset_minutes)


def _now_utc() -> datetime:
    return datetime.now(_UTC)


def _make_departure(
    journey_id: str = "IC-1200",
    planned_hour: int = 12,
    delay_minutes: int = 0,
    stop_id: str = "8600626",
    vehicle_type: str = "IC",
) -> Departure:
    planned = _dt(planned_hour)
    expected: datetime | None = None
    if delay_minutes != 0:
        expected = planned + timedelta(minutes=delay_minutes)
    return Departure(
        stop_id=stop_id,
        stop_name="Odense St.",
        line="IC",
        direction="København H",
        planned_time=planned,
        expected_time=expected,
        cancelled=False,
        vehicle_type=vehicle_type,
        track="2",
        journey_id=journey_id,
    )


def _make_board(
    departures: list[Departure],
    stop_id: str = "8600626",
) -> StopDepartures:
    return StopDepartures(
        stop_id=stop_id,
        stop_name="Odense St.",
        departures=departures,
        fetched_at=_now_utc(),
    )


# ---------------------------------------------------------------------------
# _delay_tier
# ---------------------------------------------------------------------------


class TestDelayTier:
    def test_29_minutes_returns_none(self):
        assert _delay_tier(29) is None

    def test_30_minutes_returns_30(self):
        assert _delay_tier(30) == 30

    def test_59_minutes_returns_30(self):
        assert _delay_tier(59) == 30

    def test_60_minutes_returns_60(self):
        assert _delay_tier(60) == 60

    def test_89_minutes_returns_60(self):
        assert _delay_tier(89) == 60

    def test_90_minutes_returns_90(self):
        assert _delay_tier(90) == 90

    def test_120_minutes_returns_90(self):
        assert _delay_tier(120) == 90

    def test_zero_returns_none(self):
        assert _delay_tier(0) is None

    def test_negative_returns_none(self):
        assert _delay_tier(-5) is None


# ---------------------------------------------------------------------------
# DelayLogger.process_board — tracking behaviour
# ---------------------------------------------------------------------------


@pytest.fixture()
def logger(tmp_path: Path) -> DelayLogger:
    return DelayLogger(db_path=tmp_path / "test_delay.db")


class TestProcessBoardTracking:
    def test_new_departure_added_to_tracking(self, logger: DelayLogger):
        dep = _make_departure(journey_id="IC-1")
        board = _make_board([dep])
        logger.process_board(board)
        assert "IC-1" in logger._tracking

    def test_departure_update_refreshes_last_seen(self, logger: DelayLogger):
        dep = _make_departure(journey_id="IC-1", delay_minutes=0)
        board = _make_board([dep])
        logger.process_board(board)
        first_seen = logger._tracking["IC-1"].last_seen_at

        # Second poll with updated delay
        dep2 = _make_departure(journey_id="IC-1", delay_minutes=35)
        board2 = _make_board([dep2])
        logger.process_board(board2)

        tracked = logger._tracking["IC-1"]
        assert tracked.last_delay_minutes == 35
        assert tracked.last_seen_at >= first_seen

    def test_below_threshold_not_logged_on_disappearance(self, logger: DelayLogger):
        """Departure < 30 min delay disappears → no log task scheduled."""
        dep = _make_departure(journey_id="IC-1", delay_minutes=29)
        board = _make_board([dep])
        logger.process_board(board)

        # Disappear — send empty board
        empty = _make_board([])
        logger.process_board(empty)

        # No log task should exist
        assert "IC-1" not in logger._log_tasks

    @pytest.mark.asyncio
    async def test_above_threshold_schedules_log_task_on_disappearance(
        self, logger: DelayLogger
    ):
        """Departure >= 30 min delay disappears → log task scheduled."""
        # Use a past expected_time so the guard allows it
        planned_past = _now_utc().astimezone(_DK_TZ) - timedelta(hours=1)
        expected_past = planned_past + timedelta(minutes=35)
        dep2 = Departure(
            stop_id="8600626",
            stop_name="Odense St.",
            line="IC",
            direction="København H",
            planned_time=planned_past,
            expected_time=expected_past,
            cancelled=False,
            vehicle_type="IC",
            journey_id="IC-1",
        )
        board = _make_board([dep2])
        logger.process_board(board)

        empty = _make_board([])
        logger.process_board(empty)

        assert "IC-1" in logger._log_tasks

        # Cleanup
        task = logger._log_tasks.pop("IC-1")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_reappearance_cancels_pending_log_task(self, logger: DelayLogger):
        """
        Departure disappears (task scheduled), then reappears on next poll
        — the pending task should be cancelled.
        """
        planned_past = _now_utc().astimezone(_DK_TZ) - timedelta(hours=1)
        expected_past = planned_past + timedelta(minutes=35)
        dep = Departure(
            stop_id="8600626",
            stop_name="Odense St.",
            line="IC",
            direction="København H",
            planned_time=planned_past,
            expected_time=expected_past,
            cancelled=False,
            vehicle_type="IC",
            journey_id="IC-REAPPEAR",
        )
        board = _make_board([dep])
        logger.process_board(board)

        # Disappear
        empty = _make_board([])
        logger.process_board(empty)

        assert "IC-REAPPEAR" in logger._log_tasks
        task_ref = logger._log_tasks["IC-REAPPEAR"]
        assert not task_ref.done()

        # Reappear — process_board pops and cancels the task synchronously
        logger.process_board(board)

        # The key assertions are synchronous:
        # 1. Task is immediately removed from _log_tasks inside process_board.
        assert "IC-REAPPEAR" not in logger._log_tasks
        # 2. cancel() was requested — task.cancelling() > 0 before the
        #    CancelledError is processed by the event loop.
        assert task_ref.cancelling() > 0 or task_ref.done()

        # Allow the event loop to process the cancellation so the task
        # completes cleanly and pytest doesn't warn "Task destroyed pending".
        task_ref.cancel()  # idempotent if already cancelling
        await asyncio.sleep(0.05)

    def test_future_departure_ignored_on_disappearance(self, logger: DelayLogger):
        """
        A departure with expected_time in the future (>5 min) that vanishes
        from the board has merely scrolled out of the top-20 window — must
        NOT be scheduled for logging.
        """
        planned_future = _now_utc().astimezone(_DK_TZ) + timedelta(hours=2)
        dep = Departure(
            stop_id="8600626",
            stop_name="Odense St.",
            line="IC",
            direction="København H",
            planned_time=planned_future - timedelta(minutes=35),
            expected_time=planned_future,
            cancelled=False,
            vehicle_type="IC",
            journey_id="IC-FUTURE",
        )
        board = _make_board([dep])
        logger.process_board(board)

        empty = _make_board([])
        logger.process_board(empty)

        # Must NOT be in log_tasks — it scrolled out, didn't depart
        assert "IC-FUTURE" not in logger._log_tasks

    def test_stale_departure_too_old_ignored(self, logger: DelayLogger):
        """
        A departure with expected_time more than _MAX_LOOKBACK_HOURS in the
        past is considered stale data and must not be logged.
        """
        from backend.services.delay_logger import _MAX_LOOKBACK_HOURS

        very_old = _now_utc().astimezone(_DK_TZ) - timedelta(hours=_MAX_LOOKBACK_HOURS + 1)
        dep = Departure(
            stop_id="8600626",
            stop_name="Odense St.",
            line="IC",
            direction="København H",
            planned_time=very_old - timedelta(minutes=35),
            expected_time=very_old,
            cancelled=False,
            vehicle_type="IC",
            journey_id="IC-OLD",
        )
        board = _make_board([dep])
        logger.process_board(board)

        empty = _make_board([])
        logger.process_board(empty)

        assert "IC-OLD" not in logger._log_tasks

    @pytest.mark.asyncio
    async def test_delay_exactly_on_threshold_scheduled(self, logger: DelayLogger):
        """Exactly 30-minute delay should be scheduled for logging."""
        # Make expected a couple minutes in the past to pass the guard
        expected_past = _now_utc().astimezone(_DK_TZ) - timedelta(minutes=2)
        planned = expected_past - timedelta(minutes=30)
        dep = Departure(
            stop_id="8600626",
            stop_name="Odense St.",
            line="IC",
            direction="København H",
            planned_time=planned,
            expected_time=expected_past,
            cancelled=False,
            vehicle_type="IC",
            journey_id="IC-EXACT30",
        )
        board = _make_board([dep])
        logger.process_board(board)
        empty = _make_board([])
        logger.process_board(empty)

        assert "IC-EXACT30" in logger._log_tasks
        task = logger._log_tasks.pop("IC-EXACT30")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def test_two_hour_delayed_train_within_window(self, logger: DelayLogger):
        """
        A train with a 2-hour delay — planned 30 min ago, expected 90 min
        from now — should still trigger logging when it disappears, because
        its expected_time is within the 5-minute future grace window check.

        Actually: expected is in the future → the future-guard WILL skip it
        (correct behaviour: train hasn't departed yet).  This test documents
        that the guard correctly classifies this train as "still in window".
        """
        planned = _now_utc().astimezone(_DK_TZ) - timedelta(minutes=30)
        expected = planned + timedelta(hours=2)  # 90 min from now (future)

        dep = Departure(
            stop_id="8600626",
            stop_name="Odense St.",
            line="IC",
            direction="København H",
            planned_time=planned,
            expected_time=expected,
            cancelled=False,
            vehicle_type="IC",
            journey_id="IC-2H-DELAY",
        )
        board = _make_board([dep])
        logger.process_board(board)
        empty = _make_board([])
        logger.process_board(empty)

        # expected is in the future → guard fires → not logged
        assert "IC-2H-DELAY" not in logger._log_tasks


# ---------------------------------------------------------------------------
# DelayLogger.query_logs
# ---------------------------------------------------------------------------


def _insert_row(db: DelayLogger, **overrides: object) -> None:
    """Insert a row directly into the DB for query testing."""
    from datetime import timezone

    defaults = {
        "journey_id": "IC-QT-1",
        "stop_id": "8600626",
        "stop_name": "Odense St.",
        "line": "IC",
        "direction": "København H",
        "vehicle_type": "IC",
        "planned_time": "2026-06-08T12:00:00+02:00",
        "actual_time": "2026-06-08T12:35:00+02:00",
        "delay_minutes": 35,
        "delay_tier": 30,
        "logged_at": "2026-06-08T10:35:00+00:00",
        "log_date": "2026-06-08",
    }
    defaults.update(overrides)

    import sqlite3

    with sqlite3.connect(db._db_path) as conn:
        conn.execute(
            """
            INSERT INTO delay_logs
                (journey_id, stop_id, stop_name, line, direction, vehicle_type,
                 planned_time, actual_time, delay_minutes, delay_tier, logged_at, log_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                defaults["journey_id"],
                defaults["stop_id"],
                defaults["stop_name"],
                defaults["line"],
                defaults["direction"],
                defaults["vehicle_type"],
                defaults["planned_time"],
                defaults["actual_time"],
                defaults["delay_minutes"],
                defaults["delay_tier"],
                defaults["logged_at"],
                defaults["log_date"],
            ),
        )
        conn.commit()


class TestQueryLogs:
    def test_returns_all_rows_no_filters(self, logger: DelayLogger):
        _insert_row(logger, journey_id="j1", delay_tier=30, log_date="2026-06-08")
        _insert_row(logger, journey_id="j2", delay_tier=60, log_date="2026-06-08")
        rows = logger.query_logs()
        assert len(rows) == 2

    def test_filter_by_min_tier_30(self, logger: DelayLogger):
        _insert_row(logger, journey_id="j1", delay_tier=30, delay_minutes=30)
        _insert_row(logger, journey_id="j2", delay_tier=60, delay_minutes=60)
        rows = logger.query_logs(min_tier=30)
        assert len(rows) == 2

    def test_filter_by_min_tier_60_excludes_30(self, logger: DelayLogger):
        _insert_row(logger, journey_id="j1", delay_tier=30, delay_minutes=30)
        _insert_row(logger, journey_id="j2", delay_tier=60, delay_minutes=60)
        rows = logger.query_logs(min_tier=60)
        assert len(rows) == 1
        assert rows[0]["journey_id"] == "j2"

    def test_filter_by_min_tier_90(self, logger: DelayLogger):
        _insert_row(logger, journey_id="j1", delay_tier=30, delay_minutes=30)
        _insert_row(logger, journey_id="j2", delay_tier=60, delay_minutes=60)
        _insert_row(logger, journey_id="j3", delay_tier=90, delay_minutes=90)
        rows = logger.query_logs(min_tier=90)
        assert len(rows) == 1
        assert rows[0]["journey_id"] == "j3"

    def test_filter_by_stop_id(self, logger: DelayLogger):
        _insert_row(logger, journey_id="j1", stop_id="8600626")
        _insert_row(logger, journey_id="j2", stop_id="8600868")
        rows = logger.query_logs(stop_id="8600868")
        assert len(rows) == 1
        assert rows[0]["journey_id"] == "j2"

    def test_filter_by_date_from(self, logger: DelayLogger):
        _insert_row(logger, journey_id="j1", log_date="2026-06-01")
        _insert_row(logger, journey_id="j2", log_date="2026-06-08")
        rows = logger.query_logs(date_from="2026-06-05")
        assert len(rows) == 1
        assert rows[0]["journey_id"] == "j2"

    def test_filter_by_date_to(self, logger: DelayLogger):
        _insert_row(logger, journey_id="j1", log_date="2026-06-01")
        _insert_row(logger, journey_id="j2", log_date="2026-06-08")
        rows = logger.query_logs(date_to="2026-06-05")
        assert len(rows) == 1
        assert rows[0]["journey_id"] == "j1"

    def test_filter_by_date_from_and_to(self, logger: DelayLogger):
        _insert_row(logger, journey_id="j1", log_date="2026-06-01")
        _insert_row(logger, journey_id="j2", log_date="2026-06-05")
        _insert_row(logger, journey_id="j3", log_date="2026-06-10")
        rows = logger.query_logs(date_from="2026-06-02", date_to="2026-06-08")
        assert len(rows) == 1
        assert rows[0]["journey_id"] == "j2"

    def test_filter_by_line(self, logger: DelayLogger):
        _insert_row(logger, journey_id="j1", line="IC")
        _insert_row(logger, journey_id="j2", line="RE")
        rows = logger.query_logs(line="RE")
        assert len(rows) == 1
        assert rows[0]["line"] == "RE"

    def test_limit_and_offset(self, logger: DelayLogger):
        for i in range(5):
            _insert_row(logger, journey_id=f"j{i}", log_date="2026-06-08")
        rows = logger.query_logs(limit=2, offset=0)
        assert len(rows) == 2

        rows_offset = logger.query_logs(limit=2, offset=2)
        assert len(rows_offset) == 2
        # Ensure offset actually changes results
        assert rows[0]["journey_id"] != rows_offset[0]["journey_id"]

    def test_empty_db_returns_empty_list(self, logger: DelayLogger):
        rows = logger.query_logs()
        assert rows == []

    def test_result_row_has_expected_keys(self, logger: DelayLogger):
        _insert_row(logger)
        rows = logger.query_logs()
        assert len(rows) == 1
        row = rows[0]
        expected_keys = {
            "id", "journey_id", "stop_id", "stop_name", "line", "direction",
            "vehicle_type", "planned_time", "actual_time", "delay_minutes",
            "delay_tier", "logged_at", "log_date",
        }
        assert expected_keys.issubset(row.keys())

    def test_combined_filters(self, logger: DelayLogger):
        _insert_row(logger, journey_id="j1", stop_id="8600626", delay_tier=30, log_date="2026-06-08")
        _insert_row(logger, journey_id="j2", stop_id="8600868", delay_tier=60, log_date="2026-06-08")
        _insert_row(logger, journey_id="j3", stop_id="8600626", delay_tier=60, log_date="2026-06-01")

        rows = logger.query_logs(stop_id="8600626", min_tier=60, date_from="2026-06-05")
        # j1: wrong tier (30 < 60), j2: wrong stop, j3: too old → no results
        assert rows == []

        rows2 = logger.query_logs(stop_id="8600626", min_tier=30, date_from="2026-06-05")
        assert len(rows2) == 1
        assert rows2[0]["journey_id"] == "j1"
