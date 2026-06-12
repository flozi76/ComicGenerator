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
import base64
import hashlib
import json
import os
import socket
import sys
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

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
    # Login Kit commonly expects user.info.basic plus the posting permission.
    # Keep ordering stable for easier debugging/comparisons in logs.
    if mode == "direct":
        return "user.info.basic,video.publish"
    return "user.info.basic,video.upload"


def _pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) using S256 method."""
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _extract_code_from_url(redirected: str) -> str:
    """Parse a redirected URL and return the OAuth code or abort with context."""
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(redirected).query)
    if "error" in qs:
        err = (qs.get("error") or [""])[0]
        desc = (qs.get("error_description") or [""])[0]
        err_type = (qs.get("error_type") or [""])[0]
        logid = (qs.get("logid") or qs.get("log_id") or [""])[0]
        state = (qs.get("state") or [""])[0]
        msg = f"Authorization failed: error={err} error_type={err_type} description={desc} state={state} logid={logid}"
        if err == "unauthorized_client" and err_type == "client_key":
            msg += (
                "\nAction needed in TikTok Developer Portal (not local code):\n"
                "  1) Verify client_key/client_secret are from the same app.\n"
                "  2) Enable Login Kit + Content Posting API on that app.\n"
                "  3) Enable scopes user.info.basic and video.upload.\n"
                "  4) Add your TikTok account as Sandbox/Test user.\n"
                "  5) Confirm redirect URI exactly matches this run."
            )
        sys.exit(msg)
    code = (qs.get("code") or [""])[0]
    if not code:
        sys.exit("No ?code= found in the pasted URL.")
    return code


def _preflight_authorize_url(auth_link: str) -> Optional[str]:
    """Check if auth URL immediately bounces with an OAuth error before browser flow."""
    try:
        # Do not follow all redirects to the login page; we only need early param errors.
        resp = requests.get(auth_link, allow_redirects=False, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException as exc:
        return f"Preflight skipped (network error): {exc}"

    location = resp.headers.get("Location", "")
    if not location:
        return None

    # TikTok often returns relative redirects.
    parsed = urllib.parse.urlparse(location)
    qs = urllib.parse.parse_qs(parsed.query)
    err = (qs.get("error") or [""])[0]
    if not err:
        return None

    err_code = (qs.get("errCode") or [""])[0]
    err_type = (qs.get("error_type") or [""])[0]
    msg = f"TikTok auth preflight error: error={err} errCode={err_code} error_type={err_type}"
    if err_type == "code_challenge":
        msg += "\nHint: PKCE parameters are required (script already includes them)."
    if err_type == "client_key" or "client_key" in location:
        msg += (
            "\nHint: client_key rejected by TikTok. Confirm this exact app key is from the same app where "
            "Login Kit + Content Posting API are enabled."
        )
    return msg


def main() -> None:
    ap = argparse.ArgumentParser(description="TikTok OAuth login helper.")
    ap.add_argument("--config", default="config.yml")
    ap.add_argument("--redirect-uri", default=None,
                    help="Must exactly match a Redirect URI registered on your TikTok app. "
                         "Defaults to tiktok.redirect_uri in config, else http://127.0.0.1:8080/callback.")
    ap.add_argument(
        "--wait-timeout",
        type=int,
        default=180,
        help="Seconds to wait for local callback before offering manual URL paste fallback.",
    )
    ap.add_argument(
        "--no-local-server",
        action="store_true",
        help="Skip local callback server and always paste the redirected URL manually.",
    )
    ap.add_argument(
        "--scope",
        default="",
        help="Optional scope override (comma-separated), e.g. 'user.info.basic,video.upload'.",
    )
    ap.add_argument(
        "--preflight-only",
        action="store_true",
        help="Only validate auth URL parameters and app setup hints; do not open browser/login.",
    )
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        sys.exit(f"Config not found: {cfg_path}")
    tt = (yaml.safe_load(cfg_path.read_text()) or {}).get("tiktok", {}) or {}
    client_key = str(tt.get("client_key", "")).strip()
    client_secret = str(tt.get("client_secret", "")).strip()
    token_file = tt.get("token_file", "tiktok_token.json")
    mode = tt.get("mode", "inbox")
    # Redirect URI must EXACTLY match one registered under Login Kit. CLI flag wins,
    # else tiktok.redirect_uri from config, else the localhost default. A non-localhost
    # host (e.g. an https URL) auto-selects the paste-the-URL flow below.
    redirect_uri = (args.redirect_uri or str(tt.get("redirect_uri", "")).strip()
                    or "http://127.0.0.1:8080/callback")
    if not client_key or not client_secret:
        sys.exit("Set tiktok.client_key and tiktok.client_secret in config.yml first.")

    scope = args.scope.strip() or _scope_for_mode(mode)
    state = str(int(time.time()))
    code_verifier, code_challenge = _pkce_pair()
    params = {
        "client_key": client_key,
        "scope": scope,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_link = AUTH_URL + "?" + urllib.parse.urlencode(params)

    preflight = _preflight_authorize_url(auth_link)
    if preflight:
        print(preflight)
        if args.preflight_only:
            return

    redirect = urllib.parse.urlparse(redirect_uri)
    use_server = (
        not args.no_local_server and
        redirect.hostname in ("127.0.0.1", "localhost")
    )

    print(f"\nMode: {mode}  →  requesting scope: {scope}")
    print("\nOpen this URL in your browser to authorize (opening automatically):\n")
    print(auth_link + "\n")

    if args.preflight_only:
        return

    try:
        webbrowser.open(auth_link)
    except Exception:
        pass

    if use_server:
        port = redirect.port or 80
        print(f"Waiting for the TikTok redirect on {redirect_uri} ...")
        print(
            "If nothing happens, authorize in the browser and then paste the full redirected URL "
            f"after {args.wait_timeout}s."
        )
        try:
            server = HTTPServer((redirect.hostname, port), _Handler)
        except OSError as exc:
            if exc.errno == 48:
                print(
                    f"Local callback port {port} is already in use; falling back to manual URL paste mode."
                )
            else:
                print(f"Could not start local callback server ({exc}); falling back to manual URL paste mode.")
            use_server = False
        else:
            server.socket.settimeout(1.0)
            deadline = time.time() + max(args.wait_timeout, 0)
            while "code" not in _captured and "error" not in _captured and time.time() < deadline:
                try:
                    server.handle_request()
                except socket.timeout:
                    continue
            if "code" in _captured:
                if _captured.get("state") != state:
                    sys.exit("State mismatch — aborting (possible CSRF).")
                code = _captured["code"]
            else:
                if _captured.get("error"):
                    err = _captured.get("error")
                    desc = _captured.get("error_description", "")
                    err_type = _captured.get("error_type", "")
                    logid = _captured.get("logid", _captured.get("log_id", ""))
                    msg = f"Authorization failed: error={err} error_type={err_type} description={desc} logid={logid}"
                    if err == "unauthorized_client" and err_type == "client_key":
                        msg += (
                            "\nAction needed in TikTok Developer Portal (not local code):\n"
                            "  1) Verify client_key/client_secret are from the same app.\n"
                            "  2) Enable Login Kit + Content Posting API on that app.\n"
                            "  3) Enable scopes user.info.basic and video.upload.\n"
                            "  4) Add your TikTok account as Sandbox/Test user.\n"
                            "  5) Confirm redirect URI exactly matches this run."
                        )
                    sys.exit(msg)
                use_server = False
                print("No callback received in time. Falling back to manual URL paste mode.")
            server.server_close()

    if not use_server:
        redirected = input(
            "\nAfter authorizing, paste the full redirected URL here\n"
            "(it must include ?code=... in the query):\n> "
        ).strip()
        code = _extract_code_from_url(redirected)

    # TikTok URL-decodes the code param once; decode to be safe.
    code = urllib.parse.unquote(code)

    try:
        resp = requests.post(
            TOKEN_URL,
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        data = resp.json()
    except requests.RequestException as exc:
        sys.exit(f"Token exchange request failed: {exc}")
    except ValueError:
        sys.exit(f"Token exchange returned non-JSON (HTTP {resp.status_code}): {resp.text[:300]}")

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

    # Warn if the required scope for the configured mode is missing.
    granted_scope = tokens["scope"]
    if mode == "direct" and "video.publish" not in granted_scope:
        print(
            "\n⚠️  WARNING: 'video.publish' was NOT granted (got: " + granted_scope + ").\n"
            "   Direct-mode posting will fail. To fix:\n"
            "   1. Go to https://developers.tiktok.com/ → your app → Products.\n"
            "   2. Under Content Posting API, enable the 'video.publish' scope.\n"
            "   3. Re-run this script to re-authorize with the correct scope."
        )
    elif mode == "inbox" and "video.upload" not in granted_scope:
        print(
            "\n⚠️  WARNING: 'video.upload' was NOT granted (got: " + granted_scope + ").\n"
            "   Inbox/draft posting will fail. Enable 'video.upload' scope in your\n"
            "   TikTok app at https://developers.tiktok.com/ and re-run this script."
        )
    else:
        print("   You can now publish with the main app (tiktok.enabled: true).")


if __name__ == "__main__":
    main()
