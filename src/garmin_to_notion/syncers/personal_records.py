"""Sync Garmin personal records to the Notion Personal Records database."""

from __future__ import annotations

import logging

from garminconnect import Garmin as GarminClient
from notion_client import Client as NotionClient

from garmin_to_notion.config import Settings
from garmin_to_notion.formatters import format_garmin_record_value, gmt_to_local
from garmin_to_notion.mappings import (
    DEFAULT_COVER,
    RECORD_COVERS,
    RECORD_ICONS,
    RECORD_TYPE_NAMES,
)

logger = logging.getLogger(__name__)


def _format_activity_type(activity_type: str | None) -> str:
    """Format a Garmin activity type for personal records."""
    if activity_type is None:
        return "Walking"
    return activity_type.replace("_", " ").title()


def _get_icon(name: str) -> str:
    return RECORD_ICONS.get(name, RECORD_ICONS["Other"])


def _get_cover(name: str) -> str:
    return RECORD_COVERS.get(name, DEFAULT_COVER)


def _format_record_text(value: str, pace: str) -> str:
    """Combine value and pace into a single record string."""
    if value and pace and value != pace:
        return f"{value} ({pace})"
    if value:
        return value
    return ""


def _get_existing_record(
    notion: NotionClient,
    database_id: str,
    activity_name: str,
) -> dict | None:
    """Find an existing PR record by name."""
    query = notion.databases.query(
        database_id=database_id,
        filter={"property": "Name", "title": {"equals": activity_name}},
    )
    return query["results"][0] if query["results"] else None


def _get_record_by_date_and_name(
    notion: NotionClient,
    database_id: str,
    activity_date: str,
    activity_name: str,
) -> dict | None:
    """Find a record by exact date and name."""
    query = notion.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Name", "title": {"equals": activity_name}},
                {"property": "Date", "date": {"equals": activity_date}},
            ]
        },
    )
    return query["results"][0] if query["results"] else None


def _build_record_properties(
    activity_date: str,
    activity_type: str,
    activity_name: str,
    value: str,
    pace: str,
) -> dict:
    """Build Notion properties for a personal record."""
    return {
        "Name": {"title": [{"text": {"content": activity_name}}]},
        "Date": {"date": {"start": activity_date}},
        "Activity": {
            "rich_text": [{"text": {"content": activity_type}}]
        },
        "Record": {
            "rich_text": [
                {"text": {"content": _format_record_text(value, pace)}}
            ]
        },
        "Icon": {
            "rich_text": [{"text": {"content": _get_icon(activity_name)}}]
        },
    }


def _update_record(
    notion: NotionClient,
    page_id: str,
    activity_date: str,
    value: str | None,
    pace: str | None,
    activity_name: str,
) -> None:
    """Update an existing record in Notion."""
    properties: dict = {
        "Date": {"date": {"start": activity_date}},
    }
    if value or pace:
        properties["Record"] = {
            "rich_text": [
                {"text": {"content": _format_record_text(value or "", pace or "")}}
            ]
        }

    try:
        notion.pages.update(
            page_id=page_id,
            properties=properties,
            icon={"emoji": _get_icon(activity_name)},
            cover={"type": "external", "external": {"url": _get_cover(activity_name)}},
        )
    except Exception as e:
        logger.error("Error updating record %s: %s", activity_name, e)


def _create_record(
    notion: NotionClient,
    database_id: str,
    activity_date: str,
    activity_type: str,
    activity_name: str,
    value: str,
    pace: str,
) -> None:
    """Create a new record in Notion."""
    properties = _build_record_properties(
        activity_date, activity_type, activity_name, value, pace
    )
    try:
        notion.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            icon={"emoji": _get_icon(activity_name)},
            cover={"type": "external", "external": {"url": _get_cover(activity_name)}},
        )
    except Exception as e:
        logger.error("Error creating record %s: %s", activity_name, e)


def sync_personal_records(
    garmin: GarminClient,
    notion: NotionClient,
    settings: Settings,
) -> None:
    """Sync all Garmin personal records to the Notion Personal Records database."""
    if not settings.pr_db_id:
        logger.info("No PR database configured, skipping")
        return

    records = garmin.get_personal_record()
    filtered = [r for r in records if r.get("typeId") != 16]
    logger.info("Fetched %d personal records from Garmin", len(filtered))

    created, updated, skipped = 0, 0, 0

    for record in filtered:
        raw_date = record.get("prStartTimeGmtFormatted", "")
        if len(raw_date) > 10:
            # Full datetime in GMT → convert to local timezone, keep date only
            activity_date = gmt_to_local(raw_date, settings.timezone).date().isoformat()
        else:
            activity_date = raw_date
        activity_type = _format_activity_type(record.get("activityType"))
        type_id = record.get("typeId", 0)
        activity_name = RECORD_TYPE_NAMES.get(type_id, "Other")
        value, pace = format_garmin_record_value(
            record.get("value", 0), activity_type, type_id
        )

        existing = _get_existing_record(notion, settings.pr_db_id, activity_name)
        existing_date = _get_record_by_date_and_name(
            notion, settings.pr_db_id, activity_date, activity_name
        )

        if existing_date:
            _update_record(
                notion, existing_date["id"], activity_date, value, pace,
                activity_name,
            )
            updated += 1
        elif existing:
            try:
                date_prop = existing["properties"]["Date"]
                if (
                    date_prop
                    and date_prop.get("date")
                    and date_prop["date"].get("start")
                ):
                    existing_date_str = date_prop["date"]["start"]
                    if activity_date > existing_date_str:
                        _update_record(
                            notion, existing["id"], existing_date_str,
                            None, None, activity_name,
                        )
                        _create_record(
                            notion, settings.pr_db_id, activity_date,
                            activity_type, activity_name, value, pace,
                        )
                        created += 1
                    else:
                        skipped += 1
                else:
                    _update_record(
                        notion, existing["id"], activity_date, value, pace,
                        activity_name,
                    )
                    updated += 1
            except (KeyError, TypeError) as e:
                logger.warning("Error processing record %s: %s", activity_name, e)
                _create_record(
                    notion, settings.pr_db_id, activity_date,
                    activity_type, activity_name, value, pace,
                )
                created += 1
        else:
            _create_record(
                notion, settings.pr_db_id, activity_date,
                activity_type, activity_name, value, pace,
            )
            created += 1

    logger.info(
        "Personal records sync complete: %d created, %d updated, %d unchanged",
        created, updated, skipped,
    )
