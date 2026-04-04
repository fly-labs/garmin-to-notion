"""Generate Garmin OAuth tokens locally and output base64 string for GitHub secret.

Usage:
    python scripts/generate_tokens.py

Reads GARMIN_EMAIL and GARMIN_PASSWORD from .env file.
Outputs a base64 token string to set as the GARMIN_TOKENS GitHub secret.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")

if not email or not password:
    print("Error: Set GARMIN_EMAIL and GARMIN_PASSWORD in .env")
    sys.exit(1)

from garminconnect import Garmin

print(f"Logging in as {email}...")
garmin = Garmin(email, password)
garmin.login()
print("Login successful!")

token_str = garmin.garth.dumps()
print(f"\nToken length: {len(token_str)} chars")
print("\nSet this as your GARMIN_TOKENS GitHub secret:")
print("=" * 60)
print(token_str)
print("=" * 60)
print(f"\nRun: gh secret set GARMIN_TOKENS --repo fly-labs/garmin-to-notion")
print("Then paste the token string above when prompted.")
