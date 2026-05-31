#!/usr/bin/env python3
"""One-time TikTok OAuth helper.

Walks the TikTok Login Kit authorization-code flow and caches the resulting
access + refresh tokens to `tiktok.token_file` (default: tiktok_token.json), so
the main app can publish without re-authorizing each run.

Usage (from project root):

    python3 scripts/tiktok_login.py
    python3 scripts/tiktok_login.py --config config.yml

Prerequisites in config.yml under `tiktok`:
    client_key, client_secret      — from your app at developers.tiktok.com
    mode                           — inbox (scope video.upload) | direct (video.publish)

A redirect URI must be registered on your TikTok app. This helper defaults to
http://127.0.0.1:8080/callback and runs a tiny local server to catch the code;
register that exact URL on the app (Login Kit → Redirect URI), or pass
--redirect-uri to match what you registered.
"""
import argparse
import json
import sys
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests
import yaml

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

_captured = {}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/callback"):
            self.send_response(404)
            self.end_headers()
            return
        qs = urllib.parse.parse_qs(parsed.query)
        _captured.update({k: v[0] for k, v in qs.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        msg = ("Authorization received. You can close this tab and return to the terminal."
               if "code" in _captured else
               f"Authorization failed: {_captured.get('error_description', _captured)}")
        self.wfile.write(f"<html><body><h3>{msg}</h3></body></html>".encode())

    def log_message(self, *args):
        pass  # silence the default request logging


def _scope_for_mode(mode: str) -> str:
    # video.upload → drafts/inbox (no audit). video.publish → direct post (needs audit).
    return "video.publish" if mode == "direct" else "video.upload"


def main() -> None:
    ap = argparse.ArgumentParser(description="TikTok OAuth login helper.")
    ap.add_argument("--config", default="config.yml")
    ap.add_argument("--redirect-uri", default="http://127.0.0.1:8080/callback",
                    help="Must exactly match a Redirect URI registered on your TikTok app.")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        sys.exit(f"Config not found: {cfg_path}")
    tt = (yaml.safe_load(cfg_path.read_text()) or {}).get("tiktok", {}) or {}
    client_key = tt.get("client_key", "")
    client_secret = tt.get("client_secret", "")
    token_file = tt.get("token_file", "tiktok_token.json")
    mode = tt.get("mode", "inbox")
    if not client_key or not client_secret:
        sys.exit("Set tiktok.client_key and tiktok.client_secret in config.yml first.")

    scope = _scope_for_mode(mode)
    state = str(int(time.time()))
    params = {
        "client_key": client_key,
        "scope": scope,
        "response_type": "code",
        "redirect_uri": args.redirect_uri,
        "state": state,
    }
    auth_link = AUTH_URL + "?" + urllib.parse.urlencode(params)

    redirect = urllib.parse.urlparse(args.redirect_uri)
    use_server = redirect.hostname in ("127.0.0.1", "localhost")

    print(f"\nMode: {mode}  →  requesting scope: {scope}")
    print("\nOpen this URL in your browser to authorize (opening automatically):\n")
    print(auth_link + "\n")
    try:
        webbrowser.open(auth_link)
    except Exception:
        pass

    if use_server:
        port = redirect.port or 80
        print(f"Waiting for the TikTok redirect on {args.redirect_uri} ...")
        server = HTTPServer((redirect.hostname, port), _Handler)
        while "code" not in _captured and "error" not in _captured:
            server.handle_request()
        if "code" not in _captured:
            sys.exit(f"Authorization failed: {_captured}")
        if _captured.get("state") != state:
            sys.exit("State mismatch — aborting (possible CSRF).")
        code = _captured["code"]
    else:
        redirected = input("\nAfter authorizing, paste the full redirected URL here:\n> ").strip()
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(redirected).query)
        code = (qs.get("code") or [""])[0]
        if not code:
            sys.exit("No ?code= found in the pasted URL.")

    # TikTok URL-decodes the code param once; decode to be safe.
    code = urllib.parse.unquote(code)

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": args.redirect_uri,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    data = resp.json()
    if "access_token" not in data:
        sys.exit(f"Token exchange failed: {json.dumps(data, indent=2)}")

    tokens = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "expires_at": time.time() + data.get("expires_in", 86400),
        "scope": data.get("scope", scope),
        "open_id": data.get("open_id", ""),
    }
    Path(token_file).write_text(json.dumps(tokens, indent=2))
    print(f"\n✅ Saved tokens to {token_file}")
    print(f"   scope: {tokens['scope']}")
    print("   You can now publish with the main app (tiktok.enabled: true).")


if __name__ == "__main__":
    main()
