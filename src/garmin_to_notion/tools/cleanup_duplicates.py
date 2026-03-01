"""Remove duplicate entries from the Workouts database.

Groups all records by (date, title, modality), keeps the oldest record
(first created), and archives the rest via Notion API (soft delete,
recoverable from Trash).
"""

from __future__ import annotations

import logging
from collections import defaultdict

from notion_client import Client as NotionClient

from garmin_to_notion.config import Settings
from garmin_to_notion.notion_helpers import fetch_all_pages, get_prop

logger = logging.getLogger(__name__)


def _make_group_key(
    title: str | None,
    date_str: str | None,
    modality: str | None,
) -> tuple[str, str, str]:
    """Create a grouping key for deduplication."""
    date_part = (date_str or "unknown")[:10]
    return (date_part, title or "untitled", modality or "Other")


def cleanup_duplicates(
    notion: NotionClient,
    settings: Settings,
    dry_run: bool = True,
) -> None:
    """Find and archive duplicate workout entries."""
    if not settings.workouts_db_id:
        logger.error("No workouts database configured (NOTION_WORKOUTS_DB_ID)")
        return

    prefix = "[DRY RUN] " if dry_run else ""
    logger.info("%sFetching all workout records...", prefix)

    pages = fetch_all_pages(notion, settings.workouts_db_id)
    logger.info("Total records: %d", len(pages))

    # Group by (date, title, modality)
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for page in pages:
        props = page["properties"]
        title = get_prop(props, "Workout", "title") or ""
        date_str = get_prop(props, "Date", "date") or ""
        modality = get_prop(props, "Modality", "select") or ""
        key = _make_group_key(title, date_str, modality)
        groups[key].append(page)

    to_archive: list[dict] = []
    groups_with_dupes = 0

    for key, group in groups.items():
        if len(group) <= 1:
            continue

        groups_with_dupes += 1
        date_part, title, modality = key

        # Keep the oldest (first created)
        group_sorted = sorted(group, key=lambda p: p.get("created_time", ""))
        keep = group_sorted[0]
        discard = group_sorted[1:]

        logger.info(
            "  Group: [%s] %s (%s) - %d records", date_part, title, modality, len(group)
        )
        logger.info(
            "    KEEP:    %s (created %s)",
            keep["id"],
            keep.get("created_time", "unknown")[:19],
        )
        for p in discard:
            logger.info(
                "    ARCHIVE: %s (created %s)",
                p["id"],
                p.get("created_time", "unknown")[:19],
            )
            to_archive.append(p)

    logger.info("Groups with duplicates: %d", groups_with_dupes)
    logger.info("Total records to archive: %d", len(to_archive))

    if not to_archive:
        logger.info("No duplicates found. Nothing to do.")
        return

    if dry_run:
        logger.info("[DRY RUN] No changes made. Use --execute to archive duplicates.")
        return

    logger.info("Archiving duplicates...")
    archived, errors = 0, 0

    for page in to_archive:
        try:
            notion.pages.update(page_id=page["id"], archived=True)
            archived += 1
        except Exception as e:
            errors += 1
            logger.error("Error archiving %s: %s", page["id"], e)

    logger.info(
        "Done: %d archived, %d errors. Records are in Notion Trash.",
        archived, errors,
    )
