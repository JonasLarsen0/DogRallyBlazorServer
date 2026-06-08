"""
Async HTTP client for Rejseplanen API 2.0.

All public methods return empty collections on any HTTP / parse error so the
rest of the application can keep running uninterrupted.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from backend.models.departure import Alert, Departure, StopDepartures
from backend.models.stop import Stop

logger = logging.getLogger(__name__)

# Denmark is always CET/CEST — Rejseplanen times are local.
_DK_TZ = ZoneInfo("Europe/Copenhagen")

_BASE_URL = "https://xmlopen.rejseplanen.dk/bin/rest.exe"
_COMMON_PARAMS: dict[str, str] = {"format": "json", "usePuR": "1"}

# Vehicle type values that count as "train" in Rejseplanen responses
_TRAIN_TYPES: frozenset[str] = frozenset(
    {"IC", "ICE", "LYN", "RE", "REG", "TOG", "S", "RSX", "EC", "EN"}
)

# API params to suppress non-train departures server-side
_TRAIN_ONLY_PARAMS: dict[str, str] = {
    "useBus": "0",
    "useMetro": "0",
    "useFerry": "0",
    "useTog": "1",
    "useSTog": "1",
    "useIC": "1",
    "useICE": "1",
}


def _parse_dk_datetime(date_str: str, time_str: str) -> datetime:
    """
    Convert Rejseplanen date/time strings to an aware datetime (Copenhagen TZ).

    date_str format: DD.MM.YY  (e.g. "07.06.26")
    time_str format: HH:MM     (e.g. "14:35")

    Times can roll past midnight (e.g. "24:05"), which Python's strptime
    cannot handle directly, so we normalize them.
    """
    day, month, year_short = date_str.split(".")
    year = 2000 + int(year_short)
    hour, minute = [int(p) for p in time_str.split(":")]

    # Normalize hours >= 24 (next-day service)
    extra_days, hour = divmod(hour, 24)

    naive = datetime(year, int(month), int(day), hour, minute)
    if extra_days:
        from datetime import timedelta

        naive += timedelta(days=extra_days)

    return naive.replace(tzinfo=_DK_TZ)


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class RejseplaneClient(httpx.AsyncClient):
    """
    Thin async wrapper around the Rejseplanen REST API.

    Usage::

        async with RejseplaneClient(api_key="...") as client:
            stops = await client.search_stops("Nørreport")
    """

    def __init__(self, api_key: str, train_only: bool = False, **kwargs: Any) -> None:
        super().__init__(
            base_url=_BASE_URL,
            timeout=httpx.Timeout(15.0),
            **kwargs,
        )
        self._api_key = api_key
        self._train_only = train_only

    def _params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build query params dict with mandatory keys pre-filled."""
        p: dict[str, Any] = {"accessId": self._api_key, **_COMMON_PARAMS}
        if self._train_only:
            p.update(_TRAIN_ONLY_PARAMS)
        if extra:
            p.update(extra)
        return p

    # ------------------------------------------------------------------
    # Stop search
    # ------------------------------------------------------------------

    async def search_stops(self, query: str) -> list[Stop]:
        """
        Search for stops/stations by name fragment.

        Endpoint: GET /location.name
        """
        if not query.strip():
            return []

        try:
            resp = await self.get(
                "/location.name",
                params={"input": query.strip(), "accessId": self._api_key, "format": "json"},
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("search_stops HTTP error for %r: %s", query, exc)
            return []
        except Exception as exc:  # noqa: BLE001
            logger.error("search_stops unexpected error for %r: %s", query, exc)
            return []

        stops: list[Stop] = []
        try:
            location_list = data.get("LocationList", {})
            # The API may return either a list or a single dict under "StopLocation"
            raw = location_list.get("StopLocation", [])
            if isinstance(raw, dict):
                raw = [raw]
            for loc in raw:
                stops.append(
                    Stop(
                        id=str(loc.get("id", "")),
                        name=loc.get("name", ""),
                        lat=_safe_float(loc.get("y")) / 1_000_000
                        if loc.get("y")
                        else None,
                        lon=_safe_float(loc.get("x")) / 1_000_000
                        if loc.get("x")
                        else None,
                        stop_type=loc.get("type", "ST"),
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("search_stops parse error for %r: %s", query, exc)

        return stops

    # ------------------------------------------------------------------
    # Single departure board
    # ------------------------------------------------------------------

    async def get_departures(
        self,
        stop_id: str,
        max_journeys: int = 20,
    ) -> StopDepartures:
        """
        Fetch the departure board for a single stop.

        Endpoint: GET /departureBoard
        """
        fetched_at = datetime.now(tz=timezone.utc)

        try:
            resp = await self.get(
                "/departureBoard",
                params=self._params({"id": stop_id, "maxJourneys": max_journeys}),
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("get_departures HTTP error for stop %s: %s", stop_id, exc)
            return StopDepartures(
                stop_id=stop_id,
                stop_name=stop_id,
                departures=[],
                fetched_at=fetched_at,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("get_departures unexpected error for stop %s: %s", stop_id, exc)
            return StopDepartures(
                stop_id=stop_id,
                stop_name=stop_id,
                departures=[],
                fetched_at=fetched_at,
            )

        return self._parse_departure_board(stop_id, data, fetched_at)

    # ------------------------------------------------------------------
    # Multi-stop departure board
    # ------------------------------------------------------------------

    async def get_multi_departures(
        self,
        stop_ids: list[str],
    ) -> list[StopDepartures]:
        """
        Fetch departure boards for multiple stops in one request.

        Endpoint: GET /multiDepartureBoard  (repeated &id= params)

        Falls back to individual requests if multi-board is unavailable.
        """
        if not stop_ids:
            return []

        fetched_at = datetime.now(tz=timezone.utc)

        # Build URL with repeated id params manually because httpx merges dicts
        # and would deduplicate the repeated &id= parameters.
        base_params_dict = {"accessId": self._api_key, "format": "json", "usePuR": "1"}
        if self._train_only:
            base_params_dict.update(_TRAIN_ONLY_PARAMS)
        base_params = "&".join(f"{k}={v}" for k, v in base_params_dict.items())
        id_params = "&".join(f"id={sid}" for sid in stop_ids)
        url = f"/multiDepartureBoard?{base_params}&{id_params}"

        try:
            resp = await self.get(url)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            # 400 / 404 → fall back to individual requests
            logger.warning(
                "multiDepartureBoard returned %s, falling back to individual requests",
                exc.response.status_code,
            )
            return await self._fetch_individual(stop_ids)
        except httpx.HTTPError as exc:
            logger.error("get_multi_departures HTTP error: %s", exc)
            return await self._fetch_individual(stop_ids)
        except Exception as exc:  # noqa: BLE001
            logger.error("get_multi_departures unexpected error: %s", exc)
            return []

        # The multi-board response nests per-stop boards under numeric keys or
        # returns a flat DepartureBoard — handle both shapes.
        results: list[StopDepartures] = []
        try:
            # If the API returned a single DepartureBoard (one stop effectively)
            if "DepartureBoard" in data:
                board_data = data
                # Determine stop id from first departure
                first_dep = (
                    board_data.get("DepartureBoard", {}).get("Departure") or []
                )
                if isinstance(first_dep, dict):
                    first_dep = [first_dep]
                detected_stop = (
                    str(first_dep[0].get("stopExtId", stop_ids[0]))
                    if first_dep
                    else stop_ids[0]
                )
                results.append(self._parse_departure_board(detected_stop, board_data, fetched_at))
            else:
                # Multi-board: keys are "1", "2", ... each containing a DepartureBoard
                for key in sorted(data.keys()):
                    board_wrapper = data[key]
                    if "DepartureBoard" not in board_wrapper:
                        continue
                    deps = board_wrapper["DepartureBoard"].get("Departure", [])
                    if isinstance(deps, dict):
                        deps = [deps]
                    stop_id = (
                        str(deps[0].get("stopExtId", "")) if deps else ""
                    ) or stop_ids[int(key) - 1] if int(key) - 1 < len(stop_ids) else ""
                    results.append(
                        self._parse_departure_board(stop_id, board_wrapper, fetched_at)
                    )
        except Exception as exc:  # noqa: BLE001
            logger.error("get_multi_departures parse error: %s", exc)

        return results

    async def _fetch_individual(self, stop_ids: list[str]) -> list[StopDepartures]:
        """Fallback: fetch each stop individually."""
        import asyncio

        tasks = [self.get_departures(sid) for sid in stop_ids]
        return list(await asyncio.gather(*tasks))

    # ------------------------------------------------------------------
    # Service alerts
    # ------------------------------------------------------------------

    async def get_alerts(self) -> list[Alert]:
        """
        Fetch active service messages / HIM alerts.

        Endpoint: GET /himSearch
        """
        try:
            resp = await self.get(
                "/himSearch",
                params={"accessId": self._api_key, "format": "json"},
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("get_alerts HTTP error: %s", exc)
            return []
        except Exception as exc:  # noqa: BLE001
            logger.error("get_alerts unexpected error: %s", exc)
            return []

        alerts: list[Alert] = []
        try:
            him_list = data.get("HimSearch", {}).get("Message", [])
            if isinstance(him_list, dict):
                him_list = [him_list]

            for msg in him_list:
                head = msg.get("head", "") or msg.get("Header", "")
                text = msg.get("text", "") or msg.get("Text", "")
                summary = head or text or "No summary"

                affected: list[str] = []
                for aff in msg.get("affectedProduct", []) or []:
                    if isinstance(aff, dict):
                        name = aff.get("name") or aff.get("num") or ""
                        if name:
                            affected.append(name)

                valid_from: datetime | None = None
                valid_to: datetime | None = None
                try:
                    fd = msg.get("fromDate", "") or msg.get("sDate", "")
                    ft = msg.get("fromTime", "") or msg.get("sTime", "")
                    if fd and ft:
                        valid_from = _parse_dk_datetime(fd, ft)
                except Exception:  # noqa: BLE001
                    pass
                try:
                    td = msg.get("toDate", "") or msg.get("eDate", "")
                    tt = msg.get("toTime", "") or msg.get("eTime", "")
                    if td and tt:
                        valid_to = _parse_dk_datetime(td, tt)
                except Exception:  # noqa: BLE001
                    pass

                alerts.append(
                    Alert(
                        id=str(msg.get("id", "") or msg.get("hid", "")),
                        summary=summary,
                        affected_lines=affected,
                        valid_from=valid_from,
                        valid_to=valid_to,
                        severity=str(msg.get("priority", "unknown")),
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("get_alerts parse error: %s", exc)

        return alerts

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_departure_board(
        self,
        stop_id: str,
        data: dict[str, Any],
        fetched_at: datetime,
    ) -> StopDepartures:
        """
        Convert a raw DepartureBoard JSON response into a StopDepartures model.
        """
        board = data.get("DepartureBoard", {})
        stop_name: str = board.get("name", stop_id)

        raw_deps = board.get("Departure", [])
        if isinstance(raw_deps, dict):
            # Single departure is returned as a dict, not a list
            raw_deps = [raw_deps]

        departures: list[Departure] = []
        for dep in raw_deps:
            try:
                departure = self._parse_single_departure(dep, stop_id)
                if self._train_only and departure.vehicle_type.upper() not in _TRAIN_TYPES:
                    continue
                departures.append(departure)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Skipping unparseable departure: %s — %s", dep, exc)

        return StopDepartures(
            stop_id=stop_id,
            stop_name=stop_name,
            departures=departures,
            fetched_at=fetched_at,
        )

    def _parse_single_departure(
        self,
        dep: dict[str, Any],
        fallback_stop_id: str,
    ) -> Departure:
        """Parse a single departure dict from the API into a Departure model."""
        planned_date: str = dep.get("date", "")
        planned_time_str: str = dep.get("time", "")
        planned_dt = _parse_dk_datetime(planned_date, planned_time_str)

        # Real-time fields are optional
        rt_time_str: str | None = dep.get("rtTime")
        rt_date_str: str | None = dep.get("rtDate")
        expected_dt: datetime | None = None

        if rt_time_str:
            # Use rtDate if present, else fall back to planned date
            rt_date = rt_date_str if rt_date_str else planned_date
            try:
                expected_dt = _parse_dk_datetime(rt_date, rt_time_str)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Could not parse rtTime %r/%r: %s", rt_date, rt_time_str, exc)

        # cancelled may arrive as bool or string "true"/"false"
        raw_cancelled = dep.get("cancelled", False)
        if isinstance(raw_cancelled, str):
            cancelled = raw_cancelled.lower() == "true"
        else:
            cancelled = bool(raw_cancelled)

        stop_name: str = dep.get("stop", "")
        stop_ext_id: str = str(dep.get("stopExtId", fallback_stop_id))

        return Departure(
            stop_id=stop_ext_id,
            stop_name=stop_name,
            line=dep.get("line", dep.get("name", "")),
            direction=dep.get("direction", ""),
            planned_time=planned_dt,
            expected_time=expected_dt,
            cancelled=cancelled,
            vehicle_type=dep.get("type", ""),
            track=dep.get("track") or None,
            journey_id=dep.get("id", ""),
        )
