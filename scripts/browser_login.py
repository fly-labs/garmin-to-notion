#!/usr/bin/env python3
"""Get Garmin OAuth tokens via real browser login (Playwright).

Bypasses the 429-blocked SSO programmatic endpoint by opening a real
browser window. You log in manually (handles CAPTCHA, MFA, etc.),
and the script captures the OAuth ticket automatically.

Usage:
    python scripts/browser_login.py

After success, run:
    gh secret set GARMIN_TOKENS --repo fly-labs/garmin-to-notion
    (paste the base64 token string)
"""

import base64
import json
import re
import time
from pathlib import Path
from urllib.parse import parse_qs

import requests
from requests_oauthlib import OAuth1Session
from playwright.sync_api import sync_playwright

OAUTH_CONSUMER_URL = "https://thegarth.s3.amazonaws.com/oauth_consumer.json"
ANDROID_UA = "com.garmin.android.apps.connectmobile"


def get_oauth_consumer():
    resp = requests.get(OAUTH_CONSUMER_URL, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_oauth1_token(ticket, consumer):
    sess = OAuth1Session(consumer["consumer_key"], consumer["consumer_secret"])
    url = (
        f"https://connectapi.garmin.com/oauth-service/oauth/"
        f"preauthorized?ticket={ticket}"
        f"&login-url=https://sso.garmin.com/sso/embed"
        f"&accepts-mfa-tokens=true"
    )
    resp = sess.get(url, headers={"User-Agent": ANDROID_UA}, timeout=15)
    resp.raise_for_status()
    parsed = parse_qs(resp.text)
    token = {k: v[0] for k, v in parsed.items()}
    token["domain"] = "garmin.com"
    return token


def exchange_oauth2(oauth1, consumer):
    sess = OAuth1Session(
        consumer["consumer_key"],
        consumer["consumer_secret"],
        resource_owner_key=oauth1["oauth_token"],
        resource_owner_secret=oauth1["oauth_token_secret"],
    )
    url = "https://connectapi.garmin.com/oauth-service/oauth/exchange/user/2.0"
    data = {}
    if oauth1.get("mfa_token"):
        data["mfa_token"] = oauth1["mfa_token"]
    resp = sess.post(
        url,
        headers={"User-Agent": ANDROID_UA, "Content-Type": "application/x-www-form-urlencoded"},
        data=data,
        timeout=15,
    )
    resp.raise_for_status()
    token = resp.json()
    token["expires_at"] = int(time.time() + token["expires_in"])
    token["refresh_token_expires_at"] = int(time.time() + token["refresh_token_expires_in"])
    return token


def browser_login():
    ticket = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_context().new_page()

        sso_url = (
            "https://sso.garmin.com/sso/embed"
            "?id=gauth-widget&embedWidget=true"
            "&gauthHost=https://sso.garmin.com/sso"
            "&clientId=GarminConnect&locale=en_US"
            "&redirectAfterAccountLoginUrl=https://sso.garmin.com/sso/embed"
            "&service=https://sso.garmin.com/sso/embed"
        )
        page.goto(sso_url)
        print()
        print("=" * 50)
        print("  Browser opened. Log in with your Garmin")
        print("  credentials. The window closes automatically.")
        print("=" * 50)
        print()

        start = time.time()
        while time.time() - start < 300:
            try:
                for source in [page.content(), page.url]:
                    m = re.search(r"ticket=(ST-[A-Za-z0-9\-]+)", source)
                    if m:
                        ticket = m.group(1)
                        break
                if ticket:
                    break
            except Exception:
                pass
            page.wait_for_timeout(500)

        browser.close()

    if not ticket:
        print("Timed out (5 min). Try again.")
        raise SystemExit(1)
    return ticket


def main():
    print("Garmin Browser Auth")
    print("=" * 50)

    consumer = get_oauth_consumer()
    print("Launching browser...")
    ticket = browser_login()
    print(f"Got ticket: {ticket[:25]}...")

    print("Exchanging for OAuth1...")
    oauth1 = get_oauth1_token(ticket, consumer)

    print("Exchanging for OAuth2...")
    oauth2 = exchange_oauth2(oauth1, consumer)
    print(f"Access token expires in {oauth2['expires_in']}s")
    print(f"Refresh token expires in {oauth2['refresh_token_expires_in']}s")

    # Verify
    r = requests.get(
        "https://connectapi.garmin.com/userprofile-service/socialProfile",
        headers={"User-Agent": "GCM-iOS-5.7.2.1", "Authorization": f"Bearer {oauth2['access_token']}"},
        timeout=15,
    )
    r.raise_for_status()
    print(f"Authenticated as: {r.json().get('displayName', 'unknown')}")

    # Save garth-compatible tokens
    garth_dir = Path.home() / ".garmin_tokens"
    garth_dir.mkdir(exist_ok=True)
    (garth_dir / "oauth1_token.json").write_text(json.dumps(oauth1, indent=2))
    (garth_dir / "oauth2_token.json").write_text(json.dumps(oauth2, indent=2))

    # Generate base64 for GitHub secret
    bundle = {"oauth1": oauth1, "oauth2": oauth2}
    b64 = base64.b64encode(json.dumps(bundle).encode()).decode()

    print()
    print("=" * 50)
    print("GARMIN_TOKENS for GitHub secret:")
    print("=" * 50)
    print(b64)
    print("=" * 50)
    print(f"\nTokens also saved to {garth_dir}")

    # Save to temp file for easy piping
    Path("/tmp/garmin_tokens_b64.txt").write_text(b64)
    print("Base64 saved to /tmp/garmin_tokens_b64.txt")


if __name__ == "__main__":
    main()
