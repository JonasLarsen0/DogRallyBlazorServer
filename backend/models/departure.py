"""
Pydantic models for departures and service alerts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, computed_field, model_validator


class Departure(BaseModel):
    """A single departure from a stop."""

    stop_id: str
    stop_name: str
    line: str
    direction: str
    planned_time: datetime
    expected_time: Optional[datetime] = None
    cancelled: bool = False
    vehicle_type: str
    track: Optional[str] = None
    journey_id: str

    @computed_field  # type: ignore[misc]
    @property
    def delay_minutes(self) -> int:
        """
        Positive = late, 0 = on time, negative = early.
        Returns 0 when no real-time information is available.
        """
        if self.expected_time is None:
            return 0
        delta = self.expected_time - self.planned_time
        # Round to nearest full minute
        return int(delta.total_seconds() / 60)


class StopDepartures(BaseModel):
    """All departures collected for a single stop at a point in time."""

    stop_id: str
    stop_name: str
    departures: list[Departure]
    fetched_at: datetime


class Alert(BaseModel):
    """A service disruption / information message."""

    id: str
    summary: str
    affected_lines: list[str] = []
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    severity: str = "unknown"
