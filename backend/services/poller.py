"""
Background polling service.

Periodically fetches departures from Rejseplanen for all watched stops and
broadcasts the result to all connected WebSocket clients.

The ``go_now`` flag is computed per departure:
    go_now = True  when  seconds_until_departure <= walk_seconds
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from backend.api.rejseplanen import RejseplaneClient
from backend.api.websocket import ConnectionManager
from backend.config import settings
from backend.models.departure import Alert, StopDepartures
from backend.services.delay_logger import DelayLogger

logger = logging.getLogger(__name__)


def _serialize_departures(
    all_stops: list[StopDepartures],
    alerts: list[Alert],
    walk_seconds: int,
) -> dict[str, Any]:
    """
    Build the JSON payload that is broadcast to WebSocket clients.

    Each departure gains a ``go_now`` and ``seconds_until`` field computed
    from the current wall-clock time.
    """
    now = datetime.now(tz=timezone.utc)

    stops_payload: list[dict[str, Any]] = []
    for stop_deps in all_stops:
        deps_payload: list[dict[str, Any]] = []
        for dep in stop_deps.departures:
            effective_time = dep.expected_time or dep.planned_time
            seconds_until = (effective_time - now).total_seconds()
            go_now = 0 < seconds_until <= walk_seconds

            dep_dict = dep.model_dump(mode="json")
            dep_dict["seconds_until"] = round(seconds_until)
            dep_dict["go_now"] = go_now
            deps_payload.append(dep_dict)

        stop_dict = stop_deps.model_dump(mode="json", exclude={"departures"})
        stop_dict["departures"] = deps_payload
        stops_payload.append(stop_dict)

    return {
        "type": "departures_update",
        "timestamp": now.isoformat(),
        "walk_seconds": walk_seconds,
        "stops": stops_payload,
        "alerts": [a.model_dump(mode="json") for a in alerts],
    }


class DeparturePoller:
    """
    Asyncio background task that polls Rejseplanen on a fixed interval and
    broadcasts updates over WebSocket.

    Usage::

        poller = DeparturePoller(client, manager)
        await poller.start(["8600626", "8600868"])
        # later …
        await poller.stop()
    """

    def __init__(
        self,
        client: RejseplaneClient,
        manager: ConnectionManager,
        delay_logger: DelayLogger,
    ) -> None:
        self._client = client
        self._manager = manager
        self._delay_logger = delay_logger
        self._task: asyncio.Task[None] | None = None

        # Mutable runtime state
        self._stop_ids: list[str] = []
        self._walk_seconds: int = settings.walk_time_seconds

        # Latest snapshot — served to newly connected WS clients
        self._last_payload: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def last_payload(self) -> dict[str, Any] | None:
        """The most recently broadcast payload (or None before first poll)."""
        return self._last_payload

    @property
    def stop_ids(self) -> list[str]:
        return list(self._stop_ids)

    @property
    def walk_seconds(self) -> int:
        return self._walk_seconds

    async def start(
        self,
        stop_ids: list[str],
        walk_seconds: int | None = None,
    ) -> None:
        """
        Start polling for the given stop IDs.

        Calling ``start`` while already running gracefully cancels the old
        task before launching a new one.
        """
        await self.stop()

        self._stop_ids = list(stop_ids)
        if walk_seconds is not None:
            self._walk_seconds = walk_seconds

        self._task = asyncio.create_task(
            self._poll_loop(),
            name="departure_poller",
        )
        logger.info(
            "DeparturePoller started — watching %d stop(s), interval=%ds, walk=%ds",
            len(self._stop_ids),
            settings.poll_interval_seconds,
            self._walk_seconds,
        )

    async def stop(self) -> None:
        """Cancel the background polling task if running."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("DeparturePoller stopped")
        self._task = None

    async def update_config(
        self,
        stop_ids: list[str],
        walk_seconds: int,
    ) -> None:
        """Update watched stops and walk time, restarting the poller."""
        logger.info(
            "DeparturePoller config updated — stops=%s, walk_seconds=%d",
            stop_ids,
            walk_seconds,
        )
        await self.start(stop_ids, walk_seconds)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Core polling loop — runs until cancelled."""
        while True:
            await self._do_poll()
            await asyncio.sleep(settings.poll_interval_seconds)

    async def _do_poll(self) -> None:
        """Perform a single poll cycle: fetch data, broadcast, cache."""
        if not self._stop_ids:
            logger.debug("DeparturePoller: no stop IDs configured, skipping poll")
            return

        logger.debug(
            "DeparturePoller: polling %d stop(s) …", len(self._stop_ids)
        )

        try:
            all_stops, alerts = await asyncio.gather(
                self._client.get_multi_departures(self._stop_ids),
                self._client.get_alerts(),
                return_exceptions=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("DeparturePoller: poll failed — %s", exc)
            return

        # Feed each board into the delay logger BEFORE broadcasting.
        # The logger tracks disappearing departures and schedules log writes.
        for board in all_stops:  # type: ignore[union-attr]
            self._delay_logger.process_board(board)

        payload = _serialize_departures(
            all_stops,  # type: ignore[arg-type]
            alerts,     # type: ignore[arg-type]
            self._walk_seconds,
        )
        self._last_payload = payload

        await self._manager.broadcast_departures(payload)
        logger.debug(
            "DeparturePoller: broadcast complete — %d client(s)",
            self._manager.connection_count,
        )
