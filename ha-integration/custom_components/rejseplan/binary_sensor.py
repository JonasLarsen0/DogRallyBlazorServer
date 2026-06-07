"""Binary sensor platform for RejseplanAPI."""
from __future__ import annotations

import re

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_LINE_FILTER, CONF_STOP_NAME, CONF_WALK_TIME, DEFAULT_WALK_TIME, DOMAIN
from .coordinator import RejseplanCoordinator


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RejseplanAPI binary sensors from a config entry."""
    coordinator: RejseplanCoordinator = hass.data[DOMAIN][entry.entry_id]
    stop_name = entry.data.get(CONF_STOP_NAME, coordinator.stop_id)
    line_filter = entry.data.get(CONF_LINE_FILTER, "")
    walk_time = int(
        entry.options.get(CONF_WALK_TIME, entry.data.get(CONF_WALK_TIME, DEFAULT_WALK_TIME))
    )

    async_add_entities(
        [
            GoNowBinarySensor(coordinator, entry, stop_name, line_filter, walk_time),
            CancelledBinarySensor(coordinator, entry, stop_name, line_filter),
        ]
    )


class _RejseplanBinarySensorBase(
    CoordinatorEntity[RejseplanCoordinator], BinarySensorEntity
):
    """Shared base class for all RejseplanAPI binary sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: RejseplanCoordinator,
        entry: ConfigEntry,
        stop_name: str,
        line_filter: str,
        sensor_suffix: str,
    ) -> None:
        """Initialise common attributes."""
        super().__init__(coordinator)
        self._stop_name = stop_name
        self._line_filter = line_filter

        slug_stop = _slugify(stop_name)
        slug_line = _slugify(line_filter) if line_filter else "all"

        self._attr_unique_id = f"{entry.entry_id}_{sensor_suffix}"
        self._attr_name = sensor_suffix.replace("_", " ").title()

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Rejseplan {stop_name}" + (f" {line_filter}" if line_filter else ""),
            manufacturer="Rejseplanen",
            model="RejseplanAPI",
            entry_type=None,
        )


class GoNowBinarySensor(_RejseplanBinarySensorBase):
    """Binary sensor that turns ON when it is time to leave to catch the next departure."""

    _attr_device_class = None
    _attr_icon = "mdi:run-fast"

    def __init__(
        self,
        coordinator: RejseplanCoordinator,
        entry: ConfigEntry,
        stop_name: str,
        line_filter: str,
        walk_time_minutes: int,
    ) -> None:
        super().__init__(coordinator, entry, stop_name, line_filter, "go_now")
        self._walk_time_minutes = walk_time_minutes

    @property
    def is_on(self) -> bool:
        """Return True when it is time to leave."""
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.go_now

    @property
    def extra_state_attributes(self) -> dict:
        """Return walk time, departure time, line and direction."""
        if self.coordinator.data is None:
            return {"walk_time_minutes": self._walk_time_minutes}
        d = self.coordinator.data
        departure_iso = (
            d.next_departure_dt.isoformat() if d.next_departure_dt else None
        )
        return {
            "walk_time_minutes": self._walk_time_minutes,
            "departure_time": departure_iso,
            "line": d.line,
            "direction": d.direction,
        }


class CancelledBinarySensor(_RejseplanBinarySensorBase):
    """Binary sensor that turns ON when the next departure is cancelled."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:cancel"

    def __init__(
        self,
        coordinator: RejseplanCoordinator,
        entry: ConfigEntry,
        stop_name: str,
        line_filter: str,
    ) -> None:
        super().__init__(coordinator, entry, stop_name, line_filter, "cancelled")

    @property
    def is_on(self) -> bool:
        """Return True when the next departure is cancelled."""
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.cancelled
