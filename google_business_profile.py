#!/usr/bin/env python3
"""Google Business Profile integration for The Driver Man.

Usage:
  # First run (authenticate):
  python google_business_profile.py --auth

  # After auth:
  python google_business_profile.py --list
  python google_business_profile.py --update
  python google_business_profile.py --post "New driver profiles for RTX 5060 series!"
  python google_business_profile.py --status

Requirements:
  pip install google-api-python-client google-auth-oauthlib google-auth-httplib2

Setup:
  1. Go to https://console.cloud.google.com/ → Create Project
  2. Enable "My Business Business Information API" and "My Business API"
  3. Create OAuth 2.0 credentials → Desktop application → Download client_secret.json
  4. Place client_secret.json in this directory or ~/.config/google/client_secret.json
  5. Run with --auth to authenticate
"""

import argparse
import json
import os
import sys
from pathlib import Path

CREDENTIALS_DIR = Path.home() / ".config" / "google"
CLIENT_SECRET_PATH = CREDENTIALS_DIR / "client_secret.json"
TOKEN_PATH = Path.home() / ".gbp_token.json"
SCOPES = ["https://www.googleapis.com/auth/business.manage"]

BUSINESS_NAME = "The Driver Man"
BUSINESS_DESCRIPTION = (
    "Professional NVIDIA driver optimization and GPU performance tuning. "
    "Custom NV Profile Inspector configurations for gaming, AI inference, "
    "and production workloads. Latency reduction, VRAM management, "
    "and per-title profiling."
)
BUSINESS_WEBSITE = "https://lilith-systems.github.io/the-driverman"
BUSINESS_PHONE = "[YOUR PHONE NUMBER]"
BUSINESS_ADDRESS = "[YOUR STREET ADDRESS]"
BUSINESS_HOURS = {
    "monday": [{"open": "09:00", "close": "18:00"}],
    "tuesday": [{"open": "09:00", "close": "18:00"}],
    "wednesday": [{"open": "09:00", "close": "18:00"}],
    "thursday": [{"open": "09:00", "close": "18:00"}],
    "friday": [{"open": "09:00", "close": "18:00"}],
    "saturday": [{"open": "10:00", "close": "16:00"}],
}
SERVICE_CATEGORIES = [
    "NVIDIA driver optimization",
    "GPU performance tuning",
    "NV Profile Inspector configuration",
    "Game-specific driver profiles",
    "AI inference GPU tuning",
    "VRAM optimization",
]


def find_credentials():
    paths = [
        CLIENT_SECRET_PATH,
        Path("client_secret.json"),
        Path.home() / "Downloads" / "client_secret.json",
        Path.home() / "Desktop" / "client_secret.json",
    ]
    for p in paths:
        if p.exists():
            return p
    return None


def authenticate():
    from google_auth_oauthlib.flow import InstalledAppFlow

    cred_path = find_credentials()
    if not cred_path:
        print("=" * 60)
        print("  Google OAuth client_secret.json not found!")
        print("=" * 60)
        print()
        print("To set up Google Business Profile integration:")
        print()
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project (or select existing)")
        print("3. Enable these APIs:")
        print("   - My Business Business Information API")
        print("   - My Business API")
        print("4. Go to APIs & Services → Credentials")
        print("5. Create OAuth 2.0 Client ID → Desktop application")
        print("6. Download the JSON file")
        print(f"7. Save it to: {CLIENT_SECRET_PATH}")
        print()
        print("Then run again with --auth")
        print()
        return None

    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    print(f"Authenticated. Token saved to {TOKEN_PATH}")
    return creds


def get_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not TOKEN_PATH.exists():
        print("No token found. Run with --auth first.")
        return None

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    if not creds or not creds.valid:
        print("Token invalid. Run with --auth to re-authenticate.")
        return None

    return build("mybusiness", "v4", credentials=creds)


def list_accounts(service):
    accounts = service.accounts().list().execute()
    if "accounts" not in accounts:
        print("No business accounts found.")
        return []
    for acct in accounts["accounts"]:
        print(f"  Account: {acct.get('accountName', 'N/A')} ({acct['name']})")
    return accounts["accounts"]


def list_locations(service, account_name):
    locations = service.accounts().locations().list(parent=account_name).execute()
    if "locations" not in locations:
        print(f"No locations found for {account_name}")
        return []
    for loc in locations.get("locations", []):
        print(f"  Location: {loc.get('locationName', 'N/A')}")
        print(f"    Address: {loc.get('address', {}).get('addressLines', ['N/A'])[0]}")
        print(f"    Phone: {loc.get('primaryPhone', 'N/A')}")
        print(f"    Website: {loc.get('websiteUrl', 'N/A')}")
    return locations.get("locations", [])


def update_business(service, account_name, location_name):
    body = {
        "locationName": BUSINESS_NAME,
        "websiteUrl": BUSINESS_WEBSITE,
        "primaryPhone": BUSINESS_PHONE,
        "regularHours": {
            "periods": [
                {"openDay": day.upper(), "openTime": h["open"], "closeDay": day.upper(), "closeTime": h["close"]}
                for day, hours in BUSINESS_HOURS.items()
                for h in hours
            ]
        },
        "categories": [{"displayName": cat} for cat in SERVICE_CATEGORIES],
    }
    try:
        result = service.accounts().locations().patch(
            name=location_name, body=body, updateMask="locationName,websiteUrl,primaryPhone,regularHours,categories"
        ).execute()
        print(f"Updated {location_name}")
        return result
    except Exception as e:
        print(f"Update failed: {e}")
        return None


def create_post(service, location_name, text):
    body = {
        "summary": {"text": text},
        "callToAction": {"actionType": "LEARN_MORE", "url": BUSINESS_WEBSITE},
    }
    try:
        result = service.accounts().locations().localPosts().create(parent=location_name, body=body).execute()
        print(f"Post created: {result.get('name', 'N/A')}")
        return result
    except Exception as e:
        print(f"Post failed: {e}")
        return None


def show_status(service):
    accounts = list_accounts(service)
    if not accounts:
        return
    for acct in accounts:
        locations = list_locations(service, acct["name"])


def main():
    parser = argparse.ArgumentParser(description="Google Business Profile — The Driver Man")
    parser.add_argument("--auth", action="store_true", help="Authenticate with Google")
    parser.add_argument("--list", action="store_true", help="List accounts and locations")
    parser.add_argument("--update", action="store_true", help="Update business info")
    parser.add_argument("--post", type=str, help="Create a post with the given text")
    parser.add_argument("--status", action="store_true", help="Show full status")
    args = parser.parse_args()

    if args.auth:
        authenticate()
        return

    service = get_service()
    if not service:
        return

    if args.list:
        accounts = list_accounts(service)
        if accounts:
            for acct in accounts:
                locations = list_locations(service, acct["name"])

    if args.status:
        show_status(service)

    if args.update:
        accounts = list_accounts(service)
        if accounts:
            print(f"Updating {BUSINESS_NAME} on account {accounts[0]['name']}...")
            locations = list_locations(service, accounts[0]["name"])
            if locations:
                update_business(service, accounts[0]["name"], locations[0]["name"])

    if args.post:
        accounts = list_accounts(service)
        if accounts:
            locations = list_locations(service, accounts[0]["name"])
            if locations:
                create_post(service, locations[0]["name"], args.post)

    if not any(vars(args).values()):
        parser.print_help()


if __name__ == "__main__":
    main()
