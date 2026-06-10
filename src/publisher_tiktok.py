"""Publish the generated comic as a video to TikTok via the Content Posting API.

The static comic page(s) are rendered into a 9:16 slideshow MP4 (reusing
`build_reel` from publisher.py) and uploaded directly — TikTok's `FILE_UPLOAD`
source takes the raw bytes, so no public file hosting (Cloudinary) is needed.

Two modes (`tiktok.mode`):
  * **inbox** (default) — uploads to the user's TikTok *drafts/inbox*. Works for
    unaudited apps with only the `video.upload` scope; the user finishes posting
    by tapping in the TikTok app. This is the no-app-review path.
  * **direct** — posts straight to the profile. Needs the `video.publish` scope and
    a TikTok app audit; unaudited apps may only post as SELF_ONLY (private).

Tokens come from `scripts/tiktok_login.py`, cached in `tiktok.token_file`, and are
refreshed automatically when expired. `requests` is imported lazily.

API reference: https://developers.tiktok.com/doc/content-posting-api-get-started
"""
import json
import time
from pathlib import Path
from typing import Optional

from src.agents.plot_agent import PlotResult
from src.config import CompositorConfig, TikTokConfig
from src.publisher import build_panel_reel, _format_caption

API = "https://open.tiktokapis.com/v2"
TOKEN_URL = f"{API}/oauth/token/"


def _load_tokens(cfg: TikTokConfig) -> dict:
    """Read cached tokens from token_file, falling back to the config fields."""
    p = Path(cfg.token_file) if cfg.token_file else None
    if p and p.exists():
        try:
            return json.loads(p.read_text())
        except (ValueError, OSError):
            pass
    if cfg.access_token:
        return {
            "access_token": cfg.access_token,
            "refresh_token": cfg.refresh_token,
            "expires_at": 0,
        }
    raise RuntimeError(
        "No TikTok access token found. Run the one-time login helper:\n"
        "    python3 scripts/tiktok_login.py"
    )


def _refresh_if_needed(cfg: TikTokConfig, tokens: dict) -> dict:
    """Refresh the access token if it's expired (or about to expire)."""
    import requests

    if tokens.get("expires_at", 0) > time.time() + 60:
        return tokens
    refresh_token = tokens.get("refresh_token") or cfg.refresh_token
    if not refresh_token:
        return tokens  # nothing to refresh with; hope the token is still valid

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_key": cfg.client_key,
            "client_secret": cfg.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"TikTok token refresh failed: {data}")
    new = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", refresh_token),
        "expires_at": time.time() + data.get("expires_in", 86400),
    }
    if cfg.token_file:
        Path(cfg.token_file).write_text(json.dumps(new, indent=2))
    return new


def _init(access_token: str, body: dict, endpoint: str) -> dict:
    """POST a publish-init request; return its `data` block (upload_url + publish_id)."""
    import requests

    resp = requests.post(
        f"{API}/post/publish/{endpoint}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json=body,
        timeout=60,
    )
    data = resp.json()
    err = data.get("error") or {}
    if err.get("code") not in (None, "ok"):
        raise RuntimeError(
            f"TikTok init failed: {err.get('code')} — {err.get('message')} "
            f"(log_id {err.get('log_id')})"
        )
    return data["data"]


def _upload_file(upload_url: str, video: Path) -> None:
    """PUT the whole video as a single chunk to the returned upload URL."""
    import requests

    size = video.stat().st_size
    with open(video, "rb") as f:
        body = f.read()
    resp = requests.put(
        upload_url,
        data=body,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{size - 1}/{size}",
            "Content-Length": str(size),
        },
        timeout=600,
    )
    if resp.status_code not in (200, 201, 202):
        raise RuntimeError(f"TikTok upload failed: HTTP {resp.status_code} {resp.text}")


def _source_info(video: Path) -> dict:
    size = video.stat().st_size
    # Single-chunk upload: chunk_size == video_size, one chunk total.
    return {
        "source": "FILE_UPLOAD",
        "video_size": size,
        "chunk_size": size,
        "total_chunk_count": 1,
    }


def _build_caption(cfg: TikTokConfig, plot: PlotResult) -> str:
    """Combine the caption template + hashtags into the full TikTok description."""
    text = _format_caption(cfg.caption, plot)
    if cfg.hashtags:
        tags = " ".join(f"#{t.lstrip('#')}" for t in cfg.hashtags)
        text = f"{text}\n\n{tags}"
    return text[:2200]


def _upload_one(
    access_token: str,
    video: Path,
    label: str,
    cfg: TikTokConfig,
    plot: PlotResult,
) -> None:
    """Init + upload a single video to TikTok (draft or direct)."""
    caption = _build_caption(cfg, plot)
    if cfg.mode == "direct":
        body = {
            "post_info": {
                "title": caption,
                "privacy_level": cfg.privacy_level,
                "disable_comment": False,
                "disable_duet": False,
                "disable_stitch": False,
            },
            "source_info": _source_info(video),
        }
        print(f"      Initializing TikTok direct post ({label})...")
        data = _init(access_token, body, "video/init/")
        print(f"      Uploading {label} to TikTok...")
        _upload_file(data["upload_url"], video)
        print(f"      Direct post submitted (publish_id={data.get('publish_id')}).")
    else:
        body = {
            "post_info": {"title": caption},
            "source_info": _source_info(video),
        }
        print(f"      Initializing TikTok draft upload ({label})...")
        data = _init(access_token, body, "inbox/video/init/")
        print(f"      Uploading {label} to TikTok...")
        _upload_file(data["upload_url"], video)
        print(f"      {label} → TikTok drafts (publish_id={data.get('publish_id')}).")


def publish_to_tiktok(
    plot: PlotResult,
    pages: list[Path],
    output_dir: Path,
    cfg: TikTokConfig,
    compositor_cfg: Optional[CompositorConfig] = None,
    audio_path: Optional[Path] = None,
) -> None:
    """Render the comic panels into a panel-by-panel reel and upload it to TikTok."""
    if not pages:
        raise ValueError("No comic pages to publish.")
    if not (cfg.client_key and cfg.client_secret):
        raise RuntimeError(
            "tiktok.client_key / tiktok.client_secret are not set in config.yml.\n"
            "Create an app at https://developers.tiktok.com/ and fill them in, then run:\n"
            "    python3 scripts/tiktok_login.py"
        )
    if compositor_cfg is None:
        raise RuntimeError("compositor_cfg is required to build the panel reel.")

    tokens = _refresh_if_needed(cfg, _load_tokens(cfg))
    access_token = tokens["access_token"]

    print("      Building panel reel video...")
    panel_video = build_panel_reel(
        pages, plot, output_dir, compositor_cfg, compositor_cfg.panel_seconds,
        audio_path=audio_path,
    )
    _upload_one(access_token, panel_video, "panel_reel.mp4", cfg, plot)

    if cfg.mode == "inbox":
        print("      → Open the TikTok app → Inbox/Notifications → finish & post.")
