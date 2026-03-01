"""CLI entry point for garmin-to-notion.

Usage:
    python -m garmin_to_notion              # Run all syncs
    python -m garmin_to_notion activities   # Sync only activities
    python -m garmin_to_notion records      # Sync only personal records
    python -m garmin_to_notion steps        # Sync only daily steps
    python -m garmin_to_notion sleep        # Sync only sleep data
    python -m garmin_to_notion workouts     # Sync only workouts
    python -m garmin_to_notion summary      # Sync only summary aggregations
    python -m garmin_to_notion cleanup      # Deduplicate workouts (dry run)
    python -m garmin_to_notion cleanup --execute  # Actually remove duplicates
"""

from __future__ import annotations

import argparse
import logging
import sys

from garmin_to_notion.config import load_settings
from garmin_to_notion.log import setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync Garmin fitness data to Notion databases",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=["all", "activities", "records", "steps", "sleep", "workouts", "summary", "cleanup"],
        help="Which sync to run (default: all)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="For cleanup: actually archive duplicates (default is dry run)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger(__name__)

    # Cleanup and summary only need Notion, not Garmin
    require_garmin = args.command not in ("cleanup", "summary")
    settings = load_settings(require_garmin=require_garmin)

    # Auto-discover database IDs from Notion if any are missing
    if not settings.has_all_db_ids:
        from notion_client import Client as NotionClient
        from garmin_to_notion.notion_helpers import discover_databases

        logger.info("Some database IDs missing, running auto-discovery...")
        notion = NotionClient(auth=settings.notion_token)
        discovered = discover_databases(notion)
        settings = settings.with_discovered_ids(discovered)
        if discovered:
            logger.info("Auto-discovered %d database(s)", len(discovered))

    if args.command == "cleanup":
        from garmin_to_notion.clients import init_notion_only
        from garmin_to_notion.tools.cleanup_duplicates import cleanup_duplicates

        notion = init_notion_only(settings)
        cleanup_duplicates(notion, settings, dry_run=not args.execute)
        return

    if args.command == "summary":
        from garmin_to_notion.clients import init_notion_only
        from garmin_to_notion.syncers.summary import sync_summary

        notion = init_notion_only(settings)
        sync_summary(notion, settings)
        return

    from garmin_to_notion.clients import init_clients
    from garmin_to_notion.syncers.activities import sync_activities
    from garmin_to_notion.syncers.daily_steps import sync_daily_steps
    from garmin_to_notion.syncers.personal_records import sync_personal_records
    from garmin_to_notion.syncers.sleep import sync_sleep
    from garmin_to_notion.syncers.summary import sync_summary
    from garmin_to_notion.syncers.workouts import sync_workouts

    clients = init_clients(settings)

    sync_map = {
        "activities": lambda: sync_activities(clients.garmin, clients.notion, settings),
        "records": lambda: sync_personal_records(clients.garmin, clients.notion, settings),
        "steps": lambda: sync_daily_steps(clients.garmin, clients.notion, settings),
        "sleep": lambda: sync_sleep(clients.garmin, clients.notion, settings),
        "workouts": lambda: sync_workouts(clients.notion, settings),
        "summary": lambda: sync_summary(clients.notion, settings),
    }

    # Database ID required for each syncer
    db_check = {
        "activities": settings.activities_db_id,
        "records": settings.pr_db_id,
        "steps": settings.steps_db_id,
        "sleep": settings.sleep_db_id,
        "workouts": settings.workouts_db_id,
        "summary": settings.summary_db_id,
    }

    commands = list(sync_map.keys()) if args.command == "all" else [args.command]

    for cmd in commands:
        if not db_check.get(cmd):
            logger.info("Skipping %s (no database ID configured)", cmd)
            continue
        try:
            logger.info("Starting %s sync...", cmd)
            sync_map[cmd]()
        except Exception as e:
            logger.error("Error during %s sync: %s", cmd, e, exc_info=args.verbose)
            if args.command != "all":
                sys.exit(1)


if __name__ == "__main__":
    main()
