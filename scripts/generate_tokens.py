"""Generate Garmin OAuth tokens locally and output base64 string for GitHub secret.

Usage:
    python scripts/generate_tokens.py

Reads GARMIN_EMAIL and GARMIN_PASSWORD from the environment or .env file,
prompting for any missing credentials.
Prompts for an MFA verification code when Garmin requires one.
Outputs a base64 token string to set as the GARMIN_TOKENS GitHub secret.
"""

import base64
import json
import os
import sys
from getpass import getpass

from dotenv import load_dotenv

load_dotenv()

email = os.getenv("GARMIN_EMAIL") or input("Garmin email: ").strip()
password = os.getenv("GARMIN_PASSWORD") or getpass("Garmin password: ")

if not email or not password:
    print("Error: Garmin email and password are required.")
    sys.exit(1)

from garminconnect import Garmin

garmin = Garmin(
    email, password, prompt_mfa=lambda: input("Garmin MFA code: ").strip()
)
if not hasattr(garmin, "garth"):
    print("Error: This script requires garminconnect>=0.2.19,<0.3 for compatible tokens.")
    sys.exit(1)

print(f"Logging in as {email}...")
garmin.login()
print("Login successful!")

oauth1, oauth2 = json.loads(base64.b64decode(garmin.garth.dumps()))
token_str = base64.b64encode(
    json.dumps({"oauth1": oauth1, "oauth2": oauth2}).encode()
).decode()
print(f"\nToken length: {len(token_str)} chars")
print("\nSet this as your GARMIN_TOKENS GitHub secret:")
print("=" * 60)
print(token_str)
print("=" * 60)
print(f"\nRun: gh secret set GARMIN_TOKENS --repo fly-labs/garmin-to-notion")
print("Then paste the token string above when prompted.")
