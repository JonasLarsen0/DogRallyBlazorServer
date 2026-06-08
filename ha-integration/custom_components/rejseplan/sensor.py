"""Sensor platform for RejseplanAPI."""
from __future__ import annotations

import logging
import re
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_LINE_FILTER, CONF_STOP_NAME, DOMAIN
from .coordinator import RejseplanCoordinator

_LOGGER = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RejseplanAPI sensors from a config entry."""
    coordinator: RejseplanCoordinator = hass.data[DOMAIN][entry.entry_id]
    stop_name = entry.data.get(CONF_STOP_NAME, coordinator.stop_id)
    line_filter = entry.data.get(CONF_LINE_FILTER, "")

    async_add_entities(
        [
            NextDepartureSensor(coordinator, entry, stop_name, line_filter),
            DelayMinutesSensor(coordinator, entry, stop_name, line_filter),
            MinutesUntilSensor(coordinator, entry, stop_name, line_filter),
        ]
    )


class _RejseplanSensorBase(CoordinatorEntity[RejseplanCoordinator], SensorEntity):
    """Shared base class for all RejseplanAPI sensors."""

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

        # Stable unique_id — never changes even if stop name display changes
        self._attr_unique_id = f"{entry.entry_id}_{sensor_suffix}"

        # entity_id friendly name (HA derives the entity_id from this + domain)
        self._attr_name = sensor_suffix.replace("_", " ").title()

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Rejseplan {stop_name}" + (f" {line_filter}" if line_filter else ""),
            manufacturer="Rejseplanen",
            model="RejseplanAPI",
            entry_type=DeviceEntryType.SERVICE,
        )

        # Build a human-readable entity name prefix used by HA
        self._entity_prefix = f"rejseplan_{slug_stop}_{slug_line}"


class NextDepartureSensor(_RejseplanSensorBase):
    """Sensor showing the ISO datetime of the next departure."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    # TIMESTAMP device class must NOT have a state_class set (HA 2024.x requirement)
    _attr_state_class = None

    def __init__(
        self,
        coordinator: RejseplanCoordinator,
        entry: ConfigEntry,
        stop_name: str,
        line_filter: str,
    ) -> None:
        super().__init__(coordinator, entry, stop_name, line_filter, "next_departure")
        self._attr_icon = "mdi:train"

    @property
    def native_value(self) -> datetime | None:
        """Return the next departure datetime."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.next_departure_dt

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        if self.coordinator.data is None:
            return {}
        d = self.coordinator.data
        return {
            "line": d.line,
            "direction": d.direction,
            "delay_minutes": d.delay_minutes,
            "track": d.track,
            "vehicle_type": d.vehicle_type,
        }


class DelayMinutesSensor(_RejseplanSensorBase):
    """Sensor showing the current delay in minutes (0 if on time)."""

    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = "mdi:clock-alert"

    def __init__(
        self,
        coordinator: RejseplanCoordinator,
        entry: ConfigEntry,
        stop_name: str,
        line_filter: str,
    ) -> None:
        super().__init__(coordinator, entry, stop_name, line_filter, "delay_minutes")

    @property
    def native_value(self) -> int:
        """Return delay in minutes."""
        if self.coordinator.data is None:
            return 0
        return self.coordinator.data.delay_minutes


class MinutesUntilSensor(_RejseplanSensorBase):
    """Sensor showing minutes until the expected departure."""

    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_icon = "mdi:timer"

    def __init__(
        self,
        coordinator: RejseplanCoordinator,
        entry: ConfigEntry,
        stop_name: str,
        line_filter: str,
    ) -> None:
        super().__init__(coordinator, entry, stop_name, line_filter, "minutes_until")

    @property
    def native_value(self) -> float | None:
        """Return minutes until departure."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.minutes_until
