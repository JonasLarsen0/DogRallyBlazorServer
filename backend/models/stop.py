"""
Pydantic model for a transit stop / station.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Stop(BaseModel):
    """A physical stop or station returned by the location search endpoint."""

    id: str
    name: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    stop_type: str = "ST"  # Rejseplanen type string e.g. "ST", "ADR", "POI"
