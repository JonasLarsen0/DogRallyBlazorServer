"""
REST route modules.

Explicit re-exports so that ``from backend.api.routes import alerts`` (etc.)
works even in environments where implicit namespace packages are restricted.
"""

from backend.api.routes import alerts, config, delays, departures, stops

__all__ = ["alerts", "config", "delays", "departures", "stops"]
