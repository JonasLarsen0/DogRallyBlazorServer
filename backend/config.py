"""
Application configuration loaded from environment / .env file.
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Rejseplanen API
    rejseplanen_api_key: str = ""

    # Polling
    poll_interval_seconds: int = 30

    # CORS — comma-separated list, or "*"
    cors_origins: str = "*"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Default stop IDs to watch on startup (comma-separated)
    default_stop_ids: str = ""

    # Walk time used for go_now computation (seconds)
    walk_time_seconds: int = 300

    # When True, only train departures are shown (IC, RE, S-tog etc. — no bus/metro/ferry)
    train_only: bool = False

    @field_validator("poll_interval_seconds")
    @classmethod
    def _min_poll_interval(cls, v: int) -> int:
        if v < 5:
            raise ValueError("poll_interval_seconds must be >= 5")
        return v

    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def default_stop_ids_list(self) -> list[str]:
        """Return default stop IDs as a list."""
        return [s.strip() for s in self.default_stop_ids.split(",") if s.strip()]


# Module-level singleton — import and use everywhere.
settings = Settings()
