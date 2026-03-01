"""Transform the Activities database into the Workouts database.

Reads from the Activities database and creates/updates entries in the
Workouts database with modality classification and intensity mapping.

Runs AFTER the activities sync.
"""

from __future__ import annotations

import logging

from notion_client import Client as NotionClient

from garmin_to_notion.config import Settings
from garmin_to_notion.mappings import (
    INTENSITY_FLOOR,
    INTENSITY_MAP,
    MODALITY_MAP,
    NAME_OVERRIDE_MAP,
    SKIP_TYPES,
)
from garmin_to_notion.notion_helpers import fetch_all_pages, get_prop

logger = logging.getLogger(__name__)

GARMIN_ACTIVITY_URL = "https://connect.garmin.com/modern/activity/"


def _get_modality(
    activity_type: str,
    subactivity_type: str,
    activity_name: str = "",
) -> str:
    """Determine workout modality. Name override > Subtype > Type."""
    if activity_name and activity_name in NAME_OVERRIDE_MAP:
        return NAME_OVERRIDE_MAP[activity_name]
    if subactivity_type and subactivity_type in MODALITY_MAP:
        return MODALITY_MAP[subactivity_type]
    if activity_type and activity_type in MODALITY_MAP:
        return MODALITY_MAP[activity_type]
    return "Other"


def _get_intensity(aerobic_effect_rich: str) -> str:
    """Map aerobic effect rich text to intensity level.

    Parses labels like "3.2 - Highly Impacting" to extract "Highly Impacting".
    """
    label = aerobic_effect_rich
    if " - " in aerobic_effect_rich:
        label = aerobic_effect_rich.split(" - ", 1)[1]
    return INTENSITY_MAP.get(label, "Moderate")


def _apply_intensity_floor(modality: str, intensity: str) -> str:
    """Override intensity if below the minimum for certain modalities."""
    floor = INTENSITY_FLOOR.get(modality)
    if not floor:
        return intensity
    rank = {"Easy": 0, "Moderate": 1, "Hard": 2, "Maximum": 3}
    if rank.get(intensity, 1) < rank.get(floor, 1):
        return floor
    return intensity


def _get_title(modality: str) -> str:
    """Always use modality as the workout title.

    This makes Board/Calendar views clean and consistent.
    Raw activity names are preserved in the Activities database.
    """
    return modality


def _workout_exists(
    notion: NotionClient,
    db_id: str,
    garmin_id: int | None,
    date_str: str | None,
    modality: str,
) -> dict | None:
    """Check if a workout already exists by Garmin ID or date+modality."""
    if garmin_id:
        query = notion.databases.query(
            database_id=db_id,
            filter={"property": "Garmin ID", "number": {"equals": garmin_id}},
        )
        if query["results"]:
            return query["results"][0]

    # Fallback: legacy records matched by date + modality
    if date_str:
        date_only = date_str[:10]
        query2 = notion.databases.query(
            database_id=db_id,
            filter={
                "and": [
                    {"property": "Date", "date": {"equals": date_only}},
                    {"property": "Modality", "select": {"equals": modality}},
                ]
            },
        )
        if query2["results"]:
            return query2["results"][0]

    return None


def _build_properties(activity_page: dict) -> tuple[dict, str, str, str | None, int | None]:
    """Build Workouts properties from an Activities page.

    Returns (properties_dict, title, modality, date_start, garmin_id).
    """
    props = activity_page["properties"]

    activity_type = get_prop(props, "Type", "select") or ""
    subactivity_type = get_prop(props, "SubType", "select") or ""
    activity_name = get_prop(props, "Name", "title") or ""
    date_start = get_prop(props, "Date", "date")
    duration = get_prop(props, "Duration", "rich_text") or ""
    calories = get_prop(props, "Calories", "number")
    distance = get_prop(props, "Distance (km)", "number")
    avg_pace = get_prop(props, "Avg Pace", "rich_text") or ""
    avg_hr = get_prop(props, "Avg HR", "number")
    aerobic_effect = get_prop(props, "Aerobic Effect", "rich_text") or "Unknown"
    garmin_id = get_prop(props, "Garmin ID", "number")

    modality = _get_modality(activity_type, subactivity_type, activity_name)
    intensity = _get_intensity(aerobic_effect)
    intensity = _apply_intensity_floor(modality, intensity)
    title = _get_title(modality)

    workout_props: dict = {
        "Workout": {"title": [{"text": {"content": title}}]},
        "Modality": {"select": {"name": modality}},
        "Intensity": {"select": {"name": intensity}},
    }

    if date_start:
        workout_props["Date"] = {"date": {"start": date_start}}
    if duration and duration.strip():
        workout_props["Duration"] = {
            "rich_text": [{"text": {"content": duration}}]
        }
    if distance and distance > 0:
        workout_props["Distance (km)"] = {"number": round(distance, 2)}
    if calories and calories > 0:
        workout_props["Calories"] = {"number": round(calories)}
    if avg_pace and avg_pace.strip():
        workout_props["Avg Pace"] = {
            "rich_text": [{"text": {"content": avg_pace}}]
        }
    if avg_hr and avg_hr > 0:
        workout_props["Avg HR"] = {"number": round(avg_hr)}

    return workout_props, title, modality, date_start, garmin_id


def sync_workouts(notion: NotionClient, settings: Settings) -> None:
    """Sync Activities database entries to the Workouts database."""
    if not settings.workouts_db_id:
        logger.info("No workouts database configured, skipping")
        return

    logger.info("Fetching activities from Activities database...")
    activities = fetch_all_pages(notion, settings.activities_db_id)
    logger.info("Found %d activities", len(activities))

    created, updated, skipped = 0, 0, 0

    for activity in activities:
        props = activity["properties"]
        activity_type = get_prop(props, "Type", "select") or ""
        subactivity_type = get_prop(props, "SubType", "select") or ""

        if activity_type in SKIP_TYPES or subactivity_type in SKIP_TYPES:
            skipped += 1
            continue

        workout_props, title, modality, date_start, garmin_id = _build_properties(activity)
        existing = _workout_exists(
            notion, settings.workouts_db_id, garmin_id, date_start, modality
        )

        if existing:
            notion.pages.update(page_id=existing["id"], properties=workout_props)
            updated += 1
        else:
            if garmin_id:
                workout_props["Source"] = {
                    "url": f"{GARMIN_ACTIVITY_URL}{garmin_id}"
                }
                workout_props["Garmin ID"] = {"number": garmin_id}
            notion.pages.create(
                parent={"database_id": settings.workouts_db_id},
                properties=workout_props,
            )
            created += 1

    logger.info(
        "Workouts sync complete: %d created, %d updated, %d skipped",
        created, updated, skipped,
    )
