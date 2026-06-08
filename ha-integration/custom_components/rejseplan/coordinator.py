"""DataUpdateCoordinator for RejseplanAPI."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_PATH_DEPARTURES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class RejseplanDepartureData:
    """Parsed departure data exposed to platform entities."""

    next_departure_dt: datetime | None
    delay_minutes: int
    minutes_until: float | None
    go_now: bool
    cancelled: bool
    line: str
    direction: str
    track: str
    vehicle_type: str


class RejseplanCoordinator(DataUpdateCoordinator[RejseplanDepartureData]):
    """Coordinator that fetches live departure data from RejseplanAPI."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_url: str,
        stop_id: str,
        stop_name: str,
        line_filter: str | None,
        walk_time_minutes: int,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialise the coordinator."""
        self.api_url = api_url.rstrip("/")
        self.stop_id = stop_id
        self.stop_name = stop_name
        self.line_filter = line_filter or ""
        self.walk_time_minutes = walk_time_minutes
        self._session = session

        from datetime import timedelta

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{stop_id}_{self.line_filter}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> RejseplanDepartureData:
        """Fetch data from the API and return parsed departure data."""
        url = self.api_url + API_PATH_DEPARTURES.format(stop_id=self.stop_id)
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    raise UpdateFailed(
                        f"API returned HTTP {resp.status} for stop {self.stop_id}"
                    )
                payload: dict[str, Any] = await resp.json()
        except aiohttp.ClientError as err:
            _LOGGER.warning(
                "Connection error fetching departures for stop %s: %s",
                self.stop_id,
                err,
            )
            # Return previous data so entities keep their last value
            if self.data is not None:
                return self.data
            raise UpdateFailed(f"Cannot reach RejseplanAPI: {err}") from err

        # API returns {"stop_id": ..., "departures": [...], ...}
        departures: list[dict[str, Any]] = (
            payload.get("departures", []) if isinstance(payload, dict) else payload
        )
        return self._parse(departures)

    def _parse(self, departures: list[dict[str, Any]]) -> RejseplanDepartureData:
        """Find the first relevant, non-cancelled departure and build data object."""
        now = dt_util.utcnow()

        for dep in departures:
            line = dep.get("line", "")
            # Apply line filter (case-insensitive, partial match)
            if self.line_filter and self.line_filter.upper() not in line.upper():
                continue

            cancelled = bool(dep.get("cancelled", False))

            # Parse expected departure time — prefer "expected_time", fall back to "planned_time"
            raw_time = dep.get("expected_time") or dep.get("planned_time") or dep.get("time")
            if not raw_time:
                continue

            departure_dt = _parse_dt(raw_time)
            if departure_dt is None:
                continue

            # Skip departures that have already passed by more than 60 s
            minutes_until: float | None = None
            if departure_dt:
                diff_seconds = (departure_dt - now).total_seconds()
                if diff_seconds < -60:
                    continue
                minutes_until = diff_seconds / 60.0

            planned_raw = dep.get("planned_time") or dep.get("time")
            planned_dt = _parse_dt(planned_raw) if planned_raw else None
            delay_minutes = 0
            if planned_dt and departure_dt:
                delay_seconds = (departure_dt - planned_dt).total_seconds()
                delay_minutes = max(0, int(round(delay_seconds / 60)))

            go_now = (
                minutes_until is not None
                and minutes_until <= self.walk_time_minutes
                and not cancelled
            )

            return RejseplanDepartureData(
                next_departure_dt=departure_dt,
                delay_minutes=delay_minutes,
                minutes_until=round(minutes_until, 1) if minutes_until is not None else None,
                go_now=go_now,
                cancelled=cancelled,
                line=line,
                direction=dep.get("direction", ""),
                track=dep.get("track", ""),
                vehicle_type=dep.get("vehicle_type", dep.get("type", "")),
            )

        # No matching departure found — return a neutral state
        return RejseplanDepartureData(
            next_departure_dt=None,
            delay_minutes=0,
            minutes_until=None,
            go_now=False,
            cancelled=False,
            line=self.line_filter,
            direction="",
            track="",
            vehicle_type="",
        )


def _parse_dt(raw: str | None) -> datetime | None:
    """Parse an ISO-8601 string (with or without timezone) to an aware datetime."""
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            # Assume UTC if no timezone info present
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        _LOGGER.debug("Could not parse datetime string: %r", raw)
        return None
