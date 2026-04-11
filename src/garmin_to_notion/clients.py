"""Garmin and Notion client initialization."""

from __future__ import annotations

import base64
import json
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


def _load_tokens_from_env() -> dict | None:
    """Load OAuth tokens from GARMIN_TOKENS env var (base64 JSON bundle)."""
    raw = os.getenv("GARMIN_TOKENS", "").strip()
    if not raw:
        return None
    try:
        data = json.loads(base64.b64decode(raw))
        if "oauth1" in data and "oauth2" in data:
            return data
    except Exception as e:
        logger.warning("Failed to decode GARMIN_TOKENS: %s", e)
    return None


def _load_tokens_from_disk() -> dict | None:
    """Load OAuth tokens from disk (saved by browser_login.py or previous runs)."""
    oauth1_path = TOKENSTORE_DIR / "oauth1_token.json"
    oauth2_path = TOKENSTORE_DIR / "oauth2_token.json"
    if not oauth1_path.exists() or not oauth2_path.exists():
        return None
    try:
        oauth1 = json.loads(oauth1_path.read_text())
        oauth2 = json.loads(oauth2_path.read_text())
        return {"oauth1": oauth1, "oauth2": oauth2}
    except Exception as e:
        logger.warning("Failed to load tokens from disk: %s", e)
    return None


def _save_tokens_to_disk(tokens: dict) -> None:
    """Save OAuth tokens to disk for reuse across runs."""
    try:
        TOKENSTORE_DIR.mkdir(parents=True, exist_ok=True)
        (TOKENSTORE_DIR / "oauth1_token.json").write_text(json.dumps(tokens["oauth1"], indent=2))
        (TOKENSTORE_DIR / "oauth2_token.json").write_text(json.dumps(tokens["oauth2"], indent=2))
        logger.info("Tokens saved to %s", TOKENSTORE_DIR)
    except Exception as e:
        logger.warning("Failed to save tokens: %s", e)


def _init_garmin_with_tokens(tokens: dict) -> GarminClient:
    """Initialize GarminClient using pre-obtained OAuth tokens (no SSO login)."""
    import garth

    # Use __init__ so all class-level URL attributes are set
    garmin = GarminClient()
    garmin.garth = garth.Client(domain=tokens["oauth1"].get("domain", "garmin.com"))

    # Load OAuth1 token
    oauth1 = tokens["oauth1"]
    garmin.garth.oauth1_token = garth.sso.OAuth1Token(
        oauth_token=oauth1["oauth_token"],
        oauth_token_secret=oauth1["oauth_token_secret"],
        mfa_token=oauth1.get("mfa_token"),
        mfa_expiration_timestamp=oauth1.get("mfa_expiration_timestamp"),
        domain=oauth1.get("domain", "garmin.com"),
    )

    # Load OAuth2 token
    oauth2 = tokens["oauth2"]
    garmin.garth.oauth2_token = garth.sso.OAuth2Token(
        **{k: v for k, v in oauth2.items() if k in garth.sso.OAuth2Token.__dataclass_fields__}
    )

    # Load profile (socialProfile works with OAuth2 bearer tokens)
    try:
        profile = garmin.garth.connectapi("/userprofile-service/socialProfile")
        if profile and isinstance(profile, dict):
            garmin.display_name = profile.get("displayName")
            garmin.full_name = profile.get("fullName", profile.get("displayName"))
    except Exception:
        garmin.display_name = None
        garmin.full_name = None

    # Load settings
    try:
        settings = garmin.garth.connectapi("/userprofile-service/usersettings")
        if settings and isinstance(settings, dict) and "userData" in settings:
            garmin.unit_system = settings["userData"].get("measurementSystem")
        else:
            garmin.unit_system = None
    except Exception:
        garmin.unit_system = None

    return garmin


def init_clients(settings: Settings) -> Clients:
    """Initialize and authenticate both Garmin and Notion clients.

    Auth priority:
    1. GARMIN_TOKENS env var (base64 JSON bundle from browser_login.py)
    2. Cached tokens on disk (~/.garmin_tokens)
    3. Fresh credential login with retry + backoff (last resort)
    """
    logger.info("Authenticating with Garmin Connect...")

    # 1. Try GARMIN_TOKENS env var
    tokens = _load_tokens_from_env()
    if tokens:
        try:
            garmin = _init_garmin_with_tokens(tokens)
            logger.info("Garmin auth successful (GARMIN_TOKENS secret, user: %s)", garmin.display_name)
            _save_tokens_to_disk(tokens)
            return Clients(garmin=garmin, notion=NotionClient(auth=settings.notion_token))
        except Exception as e:
            logger.warning("GARMIN_TOKENS failed: %s", e)

    # 2. Try cached tokens on disk
    tokens = _load_tokens_from_disk()
    if tokens:
        try:
            garmin = _init_garmin_with_tokens(tokens)
            logger.info("Garmin auth successful (cached tokens, user: %s)", garmin.display_name)
            _save_tokens_to_disk(tokens)
            return Clients(garmin=garmin, notion=NotionClient(auth=settings.notion_token))
        except Exception as e:
            logger.warning("Cached tokens failed: %s", e)

    # 3. Fresh login with retry (last resort)
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            garmin = GarminClient(settings.garmin_email, settings.garmin_password)
            garmin.login()
            logger.info("Garmin auth successful (fresh login)")
            # Save garth tokens for next time
            try:
                TOKENSTORE_DIR.mkdir(parents=True, exist_ok=True)
                garmin.garth.dump(str(TOKENSTORE_DIR))
            except Exception:
                pass
            return Clients(garmin=garmin, notion=NotionClient(auth=settings.notion_token))
        except Exception as e:
            if attempt < max_retries and "429" in str(e):
                wait = 30 * attempt
                logger.warning("Rate limited (attempt %d/%d), waiting %ds...", attempt, max_retries, wait)
                time.sleep(wait)
            else:
                logger.error("Failed to authenticate (attempt %d/%d): %s", attempt, max_retries, e)
                if attempt == max_retries:
                    raise SystemExit(1) from e


def init_notion_only(settings: Settings) -> NotionClient:
    """Initialize only the Notion client (for tools that don't need Garmin)."""
    return NotionClient(auth=settings.notion_token)
