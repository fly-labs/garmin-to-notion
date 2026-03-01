"""Sync Garmin sleep data to the Notion Sleep database."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from garminconnect import Garmin as GarminClient
from notion_client import Client as NotionClient

from garmin_to_notion.config import Settings
from garmin_to_notion.formatters import format_duration
from garmin_to_notion.notion_helpers import fetch_all_pages, get_prop

logger = logging.getLogger(__name__)


def _compute_sleep_score(
    deep_sec: int, light_sec: int, rem_sec: int, awake_sec: int
) -> int:
    """Compute a 0-100 sleep quality score from sleep stage data.

    Scoring (inspired by WHOOP/Oura methodology):
    - Duration score (40%): optimal 7-9h total sleep
    - Deep % score (25%): optimal ~20% of total sleep
    - REM % score (25%): optimal ~22% of total sleep
    - Awake penalty (10%): less awake time = better

    Returns minimum 1 for valid data (avoids zero in charts).
    """
    total_sleep = deep_sec + light_sec + rem_sec
    if total_sleep == 0:
        return 0

    total_hours = total_sleep / 3600

    # Duration: 100 if 7-9h, linear ramp from 4h->7h and 9h->11h
    if 7 <= total_hours <= 9:
        dur_score = 100
    elif total_hours < 7:
        dur_score = max(0, (total_hours - 4) / 3 * 100)
    else:
        dur_score = max(0, (11 - total_hours) / 2 * 100)

    # Deep %: optimal ~20%, score drops linearly away from target
    deep_pct = deep_sec / total_sleep * 100
    deep_score = max(0, 100 - abs(deep_pct - 20) * 4)

    # REM %: optimal ~22%, score drops linearly away from target
    rem_pct = rem_sec / total_sleep * 100
    rem_score = max(0, 100 - abs(rem_pct - 22) * 4)

    # Awake penalty: 0 min = 100, 30+ min = 0
    awake_min = awake_sec / 60
    awake_score = max(0, 100 - awake_min * (100 / 30))

    score = dur_score * 0.40 + deep_score * 0.25 + rem_score * 0.25 + awake_score * 0.10
    return round(min(100, max(1, score)))


def _get_existing_sleep_dates(
    notion: NotionClient, database_id: str
) -> dict[str, dict]:
    """Fetch all existing sleep entries and return {date_str: page} mapping."""
    pages = fetch_all_pages(notion, database_id)
    result: dict[str, dict] = {}
    for page in pages:
        date_str = get_prop(page["properties"], "Date", "date")
        if date_str:
            result[date_str[:10]] = page
    return result


def _get_sleep_range(
    garmin: GarminClient,
    days_back: int,
    tz: ZoneInfo,
    existing_dates: set[str],
) -> list[dict]:
    """Fetch sleep data for the last *days_back* days, skipping known dates."""
    today = datetime.now(tz=tz).date()
    results = []
    skipped = 0
    for i in range(days_back):
        d = today - timedelta(days=i)
        date_str = d.isoformat()
        if date_str in existing_dates:
            skipped += 1
            continue
        try:
            data = garmin.get_sleep_data(date_str)
            if data and data.get("dailySleepDTO"):
                results.append(data)
        except Exception:
            logger.debug("No sleep data for %s", date_str)
        if (i + 1) % 100 == 0:
            logger.info(
                "Sleep fetch progress: %d/%d days checked (%d skipped)",
                i + 1, days_back, skipped,
            )
    if skipped:
        logger.info("Skipped %d days already in Notion", skipped)
    return results


def _build_properties(sleep_data: dict, settings: Settings) -> dict | None:
    """Build Notion properties from Garmin sleep data. Returns None if no data."""
    daily_sleep = sleep_data.get("dailySleepDTO", {})
    if not daily_sleep:
        return None

    sleep_date = daily_sleep.get("calendarDate", "Unknown Date")
    total_sleep = sum(
        (daily_sleep.get(k, 0) or 0)
        for k in ("deepSleepSeconds", "lightSleepSeconds", "remSleepSeconds")
    )

    if total_sleep == 0:
        logger.info("Skipping sleep data for %s (total sleep is 0)", sleep_date)
        return None

    score = _compute_sleep_score(
        daily_sleep.get("deepSleepSeconds", 0) or 0,
        daily_sleep.get("lightSleepSeconds", 0) or 0,
        daily_sleep.get("remSleepSeconds", 0) or 0,
        daily_sleep.get("awakeSleepSeconds", 0) or 0,
    )

    return {
        "Name": {
            "title": [{"text": {"content": format_duration(total_sleep)}}]
        },
        "Date": {"date": {"start": sleep_date}},
        "Duration": {
            "rich_text": [{"text": {"content": format_duration(total_sleep)}}]
        },
        "Deep": {
            "rich_text": [
                {
                    "text": {
                        "content": format_duration(
                            daily_sleep.get("deepSleepSeconds", 0)
                        )
                    }
                }
            ]
        },
        "Light": {
            "rich_text": [
                {
                    "text": {
                        "content": format_duration(
                            daily_sleep.get("lightSleepSeconds", 0)
                        )
                    }
                }
            ]
        },
        "REM": {
            "rich_text": [
                {
                    "text": {
                        "content": format_duration(
                            daily_sleep.get("remSleepSeconds", 0)
                        )
                    }
                }
            ]
        },
        "Awake": {
            "rich_text": [
                {
                    "text": {
                        "content": format_duration(
                            daily_sleep.get("awakeSleepSeconds", 0)
                        )
                    }
                }
            ]
        },
        "Resting HR": {"number": sleep_data.get("restingHeartRate", 0)},
        "Score": {"number": score},
    }


def sync_sleep(
    garmin: GarminClient,
    notion: NotionClient,
    settings: Settings,
) -> None:
    """Sync historical sleep data to the Notion Sleep database."""
    if not settings.sleep_db_id:
        logger.info("No sleep database configured, skipping")
        return

    # Bulk-fetch existing entries (1 Notion query instead of N)
    logger.info("Fetching existing sleep entries from Notion...")
    existing_map = _get_existing_sleep_dates(notion, settings.sleep_db_id)
    logger.info("Found %d existing sleep entries in Notion", len(existing_map))

    # Fetch only missing days from Garmin
    sleep_entries = _get_sleep_range(
        garmin, settings.days_back, settings.timezone, set(existing_map.keys())
    )
    logger.info("Fetched %d new sleep entries from Garmin", len(sleep_entries))

    created = 0

    for data in sleep_entries:
        sleep_date = data.get("dailySleepDTO", {}).get("calendarDate")
        if not sleep_date:
            continue

        properties = _build_properties(data, settings)
        if not properties:
            continue

        notion.pages.create(
            parent={"database_id": settings.sleep_db_id},
            properties=properties,
        )
        created += 1

    # Repair entries with missing/zero scores
    repaired = 0
    for date_str, page in existing_map.items():
        props = page["properties"]
        current_score = get_prop(props, "Score", "number")
        if current_score and current_score > 0:
            continue

        # Fetch fresh data from Garmin to recompute score
        try:
            data = garmin.get_sleep_data(date_str)
            if not data or not data.get("dailySleepDTO"):
                continue
        except Exception:
            continue

        new_props = _build_properties(data, settings)
        if not new_props:
            continue

        new_score = new_props["Score"]["number"]
        if new_score and new_score > 0:
            notion.pages.update(
                page_id=page["id"],
                properties={"Score": {"number": new_score}},
            )
            repaired += 1

    logger.info(
        "Sleep sync complete: %d created, %d already existed, %d scores repaired",
        created, len(existing_map), repaired,
    )
