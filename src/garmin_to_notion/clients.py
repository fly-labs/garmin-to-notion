"""Garmin and Notion client initialization."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

from garminconnect import Garmin as GarminClient
from notion_client import Client as NotionClient

from garmin_to_notion.config import Settings

logger = logging.getLogger(__name__)

TOKENSTORE_DIR = Path(os.getenv("GARMIN_TOKENSTORE", "~/.garmin_tokens")).expanduser()


@dataclass
class Clients:
    garmin: GarminClient
    notion: NotionClient


def init_clients(settings: Settings) -> Clients:
    """Initialize and authenticate both Garmin and Notion clients.

    Auth priority:
    1. GARMIN_TOKENS env var (base64 string, set via scripts/generate_tokens.py)
    2. Cached tokens on disk (~/.garmin_tokens)
    3. Fresh credential login with retry + backoff
    """
    logger.info("Authenticating with Garmin Connect...")

    # 1. Try GARMIN_TOKENS env var (base64 string from GitHub secret)
    token_string = os.getenv("GARMIN_TOKENS", "").strip()
    if token_string:
        try:
            garmin = GarminClient(settings.garmin_email, settings.garmin_password)
            garmin.login(tokenstore=token_string)
            logger.info("Garmin authentication successful (GARMIN_TOKENS secret)")
            _save_tokens(garmin)
            return Clients(garmin=garmin, notion=NotionClient(auth=settings.notion_token))
        except Exception as e:
            logger.warning("GARMIN_TOKENS expired or invalid: %s", e)

    # 2. Try cached tokens on disk
    tokenstore = str(TOKENSTORE_DIR) if TOKENSTORE_DIR.exists() else None
    if tokenstore:
        try:
            garmin = GarminClient(settings.garmin_email, settings.garmin_password)
            garmin.login(tokenstore=tokenstore)
            logger.info("Garmin authentication successful (cached tokens)")
            _save_tokens(garmin)
            return Clients(garmin=garmin, notion=NotionClient(auth=settings.notion_token))
        except Exception as e:
            logger.warning("Cached tokens expired or invalid: %s. Trying fresh login...", e)

    # 3. Fresh login with retry + exponential backoff
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            garmin = GarminClient(settings.garmin_email, settings.garmin_password)
            garmin.login()
            logger.info("Garmin authentication successful (fresh login)")
            _save_tokens(garmin)
            return Clients(garmin=garmin, notion=NotionClient(auth=settings.notion_token))
        except Exception as e:
            if attempt < max_retries and "429" in str(e):
                wait = 30 * attempt
                logger.warning("Rate limited (attempt %d/%d), waiting %ds...", attempt, max_retries, wait)
                time.sleep(wait)
            else:
                logger.error("Failed to authenticate with Garmin (attempt %d/%d): %s", attempt, max_retries, e)
                if attempt == max_retries:
                    raise SystemExit(1) from e


def _save_tokens(garmin: GarminClient) -> None:
    """Persist garth tokens to disk for reuse across runs."""
    try:
        TOKENSTORE_DIR.mkdir(parents=True, exist_ok=True)
        garmin.garth.dump(str(TOKENSTORE_DIR))
        logger.info("Garmin tokens saved to %s", TOKENSTORE_DIR)
    except Exception as e:
        logger.warning("Failed to save tokens: %s", e)


def init_notion_only(settings: Settings) -> NotionClient:
    """Initialize only the Notion client (for tools that don't need Garmin)."""
    return NotionClient(auth=settings.notion_token)
