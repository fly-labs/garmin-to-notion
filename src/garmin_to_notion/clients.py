"""Garmin and Notion client initialization."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from garminconnect import Garmin as GarminClient
from notion_client import Client as NotionClient

from garmin_to_notion.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class Clients:
    garmin: GarminClient
    notion: NotionClient


def init_clients(settings: Settings) -> Clients:
    """Initialize and authenticate both Garmin and Notion clients."""
    logger.info("Authenticating with Garmin Connect...")
    garmin = GarminClient(settings.garmin_email, settings.garmin_password)
    try:
        garmin.login()
    except Exception as e:
        logger.error("Failed to authenticate with Garmin: %s", e)
        raise SystemExit(1) from e

    logger.info("Garmin authentication successful")
    notion = NotionClient(auth=settings.notion_token)
    return Clients(garmin=garmin, notion=notion)


def init_notion_only(settings: Settings) -> NotionClient:
    """Initialize only the Notion client (for tools that don't need Garmin)."""
    return NotionClient(auth=settings.notion_token)
