"""Shared Notion API utilities."""

from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Any

from notion_client import Client as NotionClient

logger = logging.getLogger(__name__)

EXPECTED_DATABASES = {
    "Activities": "activities_db_id",
    "Personal Records": "pr_db_id",
    "Daily Steps": "steps_db_id",
    "Sleep": "sleep_db_id",
    "Workouts": "workouts_db_id",
    "Activity Summary": "summary_db_id",
}


def discover_databases(notion: NotionClient) -> dict[str, str]:
    """Search Notion for databases by name and return {field_name: db_id} mapping."""
    results = notion.search(
        filter={"property": "object", "value": "database"},
    ).get("results", [])

    found: dict[str, str] = {}
    for db in results:
        title_parts = db.get("title", [])
        title = title_parts[0]["plain_text"] if title_parts else ""
        if title in EXPECTED_DATABASES:
            field = EXPECTED_DATABASES[title]
            found[field] = db["id"]
            logger.debug("Discovered database '%s' -> %s", title, db["id"])

    missing = [name for name, field in EXPECTED_DATABASES.items() if field not in found]
    if missing:
        logger.warning(
            "Could not find databases: %s. "
            "Make sure the integration is connected to the Fitness Tracker page.",
            ", ".join(missing),
        )
    return found


def retry_on_rate_limit(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator that retries Notion API calls on rate limit (429) errors."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if "rate" in str(e).lower() and attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning("Rate limited, retrying in %.1fs...", delay)
                        time.sleep(delay)
                    else:
                        raise
        return wrapper
    return decorator


def get_prop(props: dict, name: str, prop_type: str) -> Any:
    """Safely extract a property value from Notion page properties."""
    prop = props.get(name)
    if not prop:
        return None
    if prop_type == "number":
        return prop.get("number")
    if prop_type == "select":
        sel = prop.get("select")
        return sel.get("name") if sel else None
    if prop_type == "title":
        title = prop.get("title", [])
        return title[0]["text"]["content"] if title else ""
    if prop_type == "rich_text":
        rt = prop.get("rich_text", [])
        return rt[0]["text"]["content"] if rt else ""
    if prop_type == "date":
        date = prop.get("date")
        return date.get("start") if date else None
    if prop_type == "checkbox":
        return prop.get("checkbox", False)
    if prop_type == "url":
        return prop.get("url")
    return None


def fetch_all_pages(
    notion: NotionClient,
    database_id: str,
    filter: dict | None = None,
) -> list[dict]:
    """Fetch all pages from a Notion database with automatic pagination."""
    pages: list[dict] = []
    has_more = True
    cursor = None
    while has_more:
        kwargs: dict[str, Any] = {"database_id": database_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        if filter:
            kwargs["filter"] = filter
        resp = notion.databases.query(**kwargs)
        pages.extend(resp["results"])
        has_more = resp.get("has_more", False)
        cursor = resp.get("next_cursor")
    return pages
