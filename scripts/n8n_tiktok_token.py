#!/usr/bin/env python3
"""Print a valid TikTok access token, refreshing the token file if needed.

Standalone helper for the native n8n workflow (no repo imports). Reads
TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET from the environment (set in
n8n/docker-compose.yml) and the token file path from argv.

    python3 scripts/n8n_tiktok_token.py [tiktok_token.json]
"""
import json
import os
import sys
import time

import requests

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"


def main() -> None:
    token_file = sys.argv[1] if len(sys.argv) > 1 else "tiktok_token.json"
    try:
        tokens = json.load(open(token_file))
    except (OSError, ValueError) as e:
        sys.exit(f"Cannot read {token_file}: {e} — run scripts/tiktok_login.py once.")

    if tokens.get("expires_at", 0) <= time.time() + 60:
        client_key = os.environ.get("TIKTOK_CLIENT_KEY", "")
        client_secret = os.environ.get("TIKTOK_CLIENT_SECRET", "")
        if not (client_key and client_secret):
            sys.exit("Token expired and TIKTOK_CLIENT_KEY/TIKTOK_CLIENT_SECRET are not set.")
        refresh_token = tokens.get("refresh_token", "")
        if not refresh_token:
            sys.exit(f"Token expired and {token_file} has no refresh_token.")

        resp = requests.post(
            TOKEN_URL,
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        data = resp.json()
        if "access_token" not in data:
            sys.exit(f"TikTok token refresh failed: {data}")
        tokens = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", refresh_token),
            "expires_at": time.time() + data.get("expires_in", 86400),
        }
        with open(token_file, "w") as f:
            json.dump(tokens, f, indent=2)

    print(tokens["access_token"])


if __name__ == "__main__":
    main()
