"""Settings and environment variable validation."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    garmin_email: str
    garmin_password: str
    notion_token: str
    activities_db_id: str | None
    pr_db_id: str | None
    steps_db_id: str | None
    sleep_db_id: str | None
    workouts_db_id: str | None
    summary_db_id: str | None
    timezone: ZoneInfo
    fetch_limit: int
    days_back: int

    @property
    def has_all_db_ids(self) -> bool:
        """Check if all database IDs are configured."""
        return all([
            self.activities_db_id,
            self.pr_db_id,
            self.steps_db_id,
            self.sleep_db_id,
            self.workouts_db_id,
            self.summary_db_id,
        ])

    def with_discovered_ids(self, discovered: dict[str, str]) -> Settings:
        """Return a new Settings with missing DB IDs filled from discovered mapping."""
        overrides = {}
        for field in (
            "activities_db_id", "pr_db_id", "steps_db_id",
            "sleep_db_id", "workouts_db_id", "summary_db_id",
        ):
            current = getattr(self, field)
            if not current and field in discovered:
                overrides[field] = discovered[field]
        if not overrides:
            return self
        from dataclasses import replace
        return replace(self, **overrides)


def load_settings(require_garmin: bool = True) -> Settings:
    """Load and validate all configuration from environment variables."""
    required = ["NOTION_TOKEN"]
    if require_garmin:
        required += ["GARMIN_EMAIL", "GARMIN_PASSWORD"]

    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your values.")
        sys.exit(1)

    tz_name = os.getenv("TIMEZONE", "UTC")
    try:
        timezone = ZoneInfo(tz_name)
    except (KeyError, ValueError):
        print(f"Error: Invalid timezone '{tz_name}'. Use IANA format (e.g. America/Sao_Paulo).")
        sys.exit(1)

    return Settings(
        garmin_email=os.getenv("GARMIN_EMAIL", ""),
        garmin_password=os.getenv("GARMIN_PASSWORD", ""),
        notion_token=os.environ["NOTION_TOKEN"],
        activities_db_id=os.getenv("NOTION_DB_ID"),
        pr_db_id=os.getenv("NOTION_PR_DB_ID"),
        steps_db_id=os.getenv("NOTION_STEPS_DB_ID"),
        sleep_db_id=os.getenv("NOTION_SLEEP_DB_ID"),
        workouts_db_id=os.getenv("NOTION_WORKOUTS_DB_ID"),
        summary_db_id=os.getenv("NOTION_SUMMARY_DB_ID"),
        timezone=timezone,
        fetch_limit=int(os.getenv("GARMIN_ACTIVITIES_FETCH_LIMIT", "1000")),
        days_back=int(os.getenv("GARMIN_DAYS_BACK", "30")),
    )
