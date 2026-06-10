"""Publish generated comic pages to Instagram as a reel + story.

Uses the unofficial `instagrapi` library, which logs in with a normal
username/password and uploads local files directly (no public hosting needed).

A Reel must be a video, so the static page PNGs are turned into an MP4
slideshow (a few seconds per page) via ffmpeg. Each page is also padded to
9:16 and pushed as a story frame.

ffmpeg must be installed and on PATH (`brew install ffmpeg`); instagrapi also
relies on it internally for video uploads.
"""
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from PIL import Image

from src.agents.plot_agent import PlotResult
from src.agents.scene_agent import SceneResult
from src.config import InstagramConfig

# Instagram reels/stories are 9:16. 1080x1920 is the standard upload size.
FRAME_W, FRAME_H = 1080, 1920


def _ffmpeg_exe() -> str:
    """Locate an ffmpeg binary: system PATH first, then the one bundled with
    imageio-ffmpeg (a transitive instagrapi dependency)."""
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        raise RuntimeError(
            "ffmpeg is required to build the reel video but was not found.\n"
            "Install it with:  brew install ffmpeg"
        ) from e


def _challenge_code_handler(username: str, choice) -> str:
    """Instagram sent a verification code (email/SMS). Ask the user to type it."""
    where = getattr(choice, "name", str(choice))
    return input(f"Instagram sent a verification code to your {where} for "
                 f"{username}. Enter it: ").strip()


def _two_factor_code() -> str:
    """Account has 2FA — ask for the current authenticator/SMS code."""
    return input("Enter your Instagram 2FA code: ").strip()


def _format_caption(template: str, plot: PlotResult) -> str:
    try:
        return template.format(title=plot.title, tagline=plot.tagline)
    except (KeyError, IndexError):
        # Bad placeholder in the template — fall back to a sane caption.
        return f"{plot.title}\n\n{plot.tagline}"


def _fit_width(img: Image.Image, w: int, h: int) -> Image.Image:
    """Scale image so it always spans the full width w, never cropping horizontally.

    If the scaled height exceeds h, center-crop vertically. If it's shorter,
    pad top/bottom with black. The image is never scaled down below width w.
    """
    src_w, src_h = img.size
    new_w = w
    new_h = int(src_h * (w / src_w) + 0.5)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    if new_h >= h:
        y_off = (new_h - h) // 2
        return resized.crop((0, y_off, w, y_off + h))
    canvas = Image.new("RGB", (w, h), color=(0, 0, 0))
    canvas.paste(resized, (0, (h - new_h) // 2))
    return canvas


def _letterbox_to(src: Path, w: int, h: int, dst: Path) -> Path:
    """Scale a page to fit inside w×h on a black background (no cropping)."""
    img = Image.open(src).convert("RGB")
    img.thumbnail((w, h), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), color=(0, 0, 0))
    canvas.paste(img, ((w - img.width) // 2, (h - img.height) // 2))
    dst.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dst, format="JPEG", quality=95)
    return dst


def build_reel(pages: list[Path], output_dir: Path, seconds_per_page: float) -> Path:
    """Render the page PNGs into a 9:16 slideshow reel.mp4 via ffmpeg."""
    ffmpeg = _ffmpeg_exe()

    # concat demuxer: each frame shown for `seconds_per_page`. The last file is
    # repeated because the demuxer ignores the final `duration` directive.
    lines: list[str] = []
    for p in pages:
        lines.append(f"file '{p.resolve().as_posix()}'")
        lines.append(f"duration {seconds_per_page}")
    lines.append(f"file '{pages[-1].resolve().as_posix()}'")

    list_path = output_dir / "reel_frames.txt"
    list_path.write_text("\n".join(lines))

    reel_path = output_dir / "reel.mp4"
    vf = (
        f"scale={FRAME_W}:{FRAME_H}:force_original_aspect_ratio=decrease,"
        f"pad={FRAME_W}:{FRAME_H}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar=1,format=yuv420p"
    )
    cmd = [
        ffmpeg, "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-shortest",
        "-vf", vf,
        "-r", "30",
        "-c:v", "libx264", "-c:a", "aac",
        "-movflags", "+faststart",
        str(reel_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed to build the reel:\n{e.stderr}") from e

    return reel_path


def build_panel_reel(
    scenes: list[SceneResult],
    output_dir: Path,
    seconds_per_panel: float,
    audio_path: Optional[Path] = None,
) -> Path:
    """Render a panel-by-panel 9:16 slideshow panel_reel.mp4 via ffmpeg.

    Each panel's source image is scaled to span the full 1080px frame width
    (never cropped horizontally), with vertical letterboxing/cropping only
    as needed to reach the 1920px frame height.
    """
    if not scenes:
        raise ValueError("No scenes available for panel reel.")

    ffmpeg = _ffmpeg_exe()

    frames_dir = output_dir / "panel_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    frame_paths: list[Path] = []
    for scene in sorted(scenes, key=lambda s: s.index):
        if not scene.image_path.exists():
            continue
        img = Image.open(scene.image_path).convert("RGB")
        frame = _fit_width(img, FRAME_W, FRAME_H)
        frame_path = frames_dir / f"panel_{scene.index:03d}.png"
        frame.save(frame_path, format="PNG", optimize=True)
        frame_paths.append(frame_path)

    if not frame_paths:
        raise ValueError("No panel images available for panel reel.")

    lines: list[str] = []
    for frame_path in frame_paths:
        lines.append(f"file '{frame_path.resolve().as_posix()}'")
        lines.append(f"duration {seconds_per_panel}")
    lines.append(f"file '{frame_paths[-1].resolve().as_posix()}'")

    list_path = output_dir / "panel_reel_frames.txt"
    list_path.write_text("\n".join(lines))

    panel_reel_path = output_dir / "panel_reel.mp4"
    # Frames are already cover-cropped to exactly FRAME_W x FRAME_H above.
    vf = "setsar=1,format=yuv420p"

    total_duration = len(frame_paths) * seconds_per_panel
    fade_start = max(0.0, total_duration - 2.0)

    if audio_path:
        # Loop the audio track so it covers any video length; fade out the last 2s.
        audio_inputs = ["-stream_loop", "-1", "-i", str(audio_path)]
        audio_filter = ["-af", f"afade=t=out:st={fade_start:.2f}:d=2"]
    else:
        audio_inputs = ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
        audio_filter = []

    cmd = [
        ffmpeg, "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        *audio_inputs,
        "-shortest",
        "-vf", vf,
        *audio_filter,
        "-r", "30",
        "-c:v", "libx264", "-c:a", "aac",
        "-movflags", "+faststart",
        str(panel_reel_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed to build the panel reel:\n{e.stderr}") from e

    return panel_reel_path


def login(cfg: InstagramConfig):
    """Log in to Instagram, reusing/refreshing the cached session.

    Handles the new-device verification challenge and 2FA interactively, so the
    first login must be run from a real terminal where the code can be typed.
    Returns a logged-in `instagrapi.Client`.
    """
    if not cfg.username or not cfg.password:
        raise ValueError(
            "instagram.username and instagram.password must be set in config.yml."
        )
    try:
        from instagrapi import Client
        from instagrapi.exceptions import ChallengeRequired, TwoFactorRequired
    except ImportError as e:
        raise RuntimeError(
            "instagrapi is not installed. Run:  pip install instagrapi"
        ) from e

    client = Client()
    # Instagram challenges a login from a new device/IP and texts/emails a code.
    # These handlers prompt for it interactively (also covers TOTP/SMS 2FA).
    client.challenge_code_handler = _challenge_code_handler
    client.change_password_handler = lambda username: None

    session = Path(cfg.session_file) if cfg.session_file else None
    if session and session.exists():
        try:
            client.load_settings(session)
        except Exception:
            pass  # corrupt/old session — fall through to a fresh login

    try:
        client.login(cfg.username, cfg.password)
    except TwoFactorRequired:
        # Account has 2FA enabled — retry with a code from the authenticator/SMS.
        code = _two_factor_code()
        client.login(cfg.username, cfg.password, verification_code=code)
    except ChallengeRequired:
        # New-device verification. login() does not auto-resolve it; kick off the
        # challenge flow, which calls _challenge_code_handler for the emailed/SMS code.
        try:
            resolved = client.challenge_resolve(client.last_json)
        except ChallengeRequired as e:
            raise RuntimeError(
                "Instagram requires manual verification that instagrapi can't automate.\n"
                "Open the Instagram app or instagram.com on this network, log in, approve "
                "the 'Was this you?' prompt, then re-run this login.\n"
                f"(details: {e})"
            ) from e
        if not resolved:
            raise RuntimeError("Instagram challenge was not resolved.")
    if session:
        client.dump_settings(session)
    return client


def publish_to_instagram(
    plot: PlotResult,
    pages: list[Path],
    output_dir: Path,
    cfg: InstagramConfig,
) -> None:
    """Log in and publish the comic pages as a reel and/or story frames."""
    if not pages:
        raise ValueError("No comic pages to publish.")

    caption = _format_caption(cfg.caption, plot)
    client = login(cfg)

    if cfg.publish_reel:
        print("      Building reel video...")
        reel = build_reel(pages, output_dir, cfg.seconds_per_page)
        print("      Uploading reel...")
        client.clip_upload(reel, caption=caption)
        print("      Reel published.")

    if cfg.publish_story:
        for i, page in enumerate(pages, start=1):
            frame = _letterbox_to(page, FRAME_W, FRAME_H, output_dir / f"story_{i:03d}.jpg")
            print(f"      Uploading story {i}/{len(pages)}...")
            client.photo_upload_to_story(frame)
        print("      Story published.")
