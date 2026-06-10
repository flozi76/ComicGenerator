# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

A Python console application that generates a single-page noir/horror comic from a text idea. It runs a three-step pipeline:
1. **Plot agent** (sync): GPT-4o generates title, tagline, panel count (4–12), page layout, and scene beats
2. **Scene agents** (async, parallel): one coroutine per scene expands a beat into caption + image prompt, then generates a DALL-E 3 image
3. **Compositor**: Pillow stitches all panel images into one `comic.png`
4. **Publisher** (optional): after generation, offers to publish the page(s) as a video. Active target is **TikTok** (Content Posting API — renders the pages into a reel MP4 and uploads it; default `inbox` mode lands in TikTok drafts so no app review is needed). A legacy **Instagram** path (`instagrapi`, disabled by default) remains for reference.

`Idea/noir-comic-generator.jsx` is a React prototype for reference — it is not used by the Python app.

## Running

```bash
# Install dependencies (Python 3.11+)
pip install -r requirements.txt

# Copy and fill in your OpenAI key
cp config.example.yml config.yml
# edit config.yml: set openai.api_key

# Generate a comic (run from project root)
python -m src.main --idea "A vampire detective investigates a murder at a midnight concert"

# With explicit style
python -m src.main --idea "..." --style dylan-dog

# With a different config path
python -m src.main --idea "..." --config /path/to/config.yml

# Auto-publish (skip the prompt) / never publish — target set by config (TikTok)
python -m src.main --idea "..." --publish
python -m src.main --idea "..." --no-publish
```

Publishing needs ffmpeg for the reel video (`brew install ffmpeg`, or it falls back to the binary bundled with `imageio-ffmpeg`) and `requests`. Set `tiktok.enabled: true` to be prompted after generation.

**TikTok (active).** Renders the page(s) into a 9:16 reel MP4 and uploads it via the **Content Posting API** (raw bytes — no public file host needed). Two `tiktok.mode`s:
- `inbox` (default) — uploads to your TikTok **drafts**; you tap *Post* in the app. Works for **unaudited** apps with only the `video.upload` scope. This is the no-review path.
- `direct` — posts to the profile. Needs the `video.publish` scope and a TikTok app audit; unaudited apps can only post `SELF_ONLY` (private).

One-time setup is in **`tiktok-setup.md`** (create app at https://developers.tiktok.com/, fill `tiktok.client_key`/`client_secret`, then `python3 scripts/tiktok_login.py` to authorize and cache tokens to `tiktok.token_file`).

**Instagram (legacy, disabled).** `src/publisher.py` still has the `instagrapi` reel+story path; it's only used if `tiktok.enabled` is false and `instagram.enabled` is true. Logs in with `instagram.username`/`password` (run `python3 scripts/instagram_login.py` once for the device challenge). Violates IG ToS; kept for reference, not the recommended path.

Output is written to `output/<YYYY-MM-DD>/story_<HHmmss>_<slug>_<rand>/` containing `plot.json`, `scene_NN.png` files, and `comic.png`.

## Architecture

### Pipeline flow (`src/main.py`)
```
load_config() → plot_agent.run() → [asyncio.gather(scene_agent.run() × N)] → compositor.compose() → [publish_to_tiktok() | publish_to_instagram()]
```

### Publishing (`src/publisher_tiktok.py`, `src/publisher.py`)
Optional final step. After compositing, `main.py` picks a target: if `tiktok.enabled` → TikTok; else if `instagram.enabled` → Instagram; else nothing. The `--publish`/`--no-publish` flags force the choice; otherwise, if stdin is a TTY, it prompts `Publish to <target>? [y/N]`. Publishing failures are caught and printed — they never abort a successful generation. Both modules import their heavy/optional deps (`requests`, `instagrapi`) lazily, so the rest of the app runs without them installed. **TikTok credentials are validated at publish time, not in `load_config`**, so a missing token never blocks generation.

**TikTok (`src/publisher_tiktok.py`, `publish_to_tiktok()`)** — `build_reel()` (imported from `publisher.py`) renders the page PNG(s) into a 9:16 `reel.mp4`; then the **Content Posting API** flow: `_load_tokens` (from `tiktok.token_file`, auto-`_refresh_if_needed` via the OAuth refresh token) → `_init` POSTs a publish-init (`inbox/video/init/` for drafts or `video/init/` for direct) with `source: FILE_UPLOAD` → `_upload_file` PUTs the whole MP4 as one chunk to the returned `upload_url`. `inbox` mode lands in drafts (no audit); `direct` mode includes `post_info` (title from `_format_caption`, `privacy_level`). Tokens are obtained one-time via `scripts/tiktok_login.py` (local-redirect OAuth code flow).

**Instagram (`src/publisher.py`, `publish_to_instagram()`, legacy)** — logs in with `instagrapi` (caching the session to `instagram.session_file`), then: (1) **reel** — `build_reel()` renders a 9:16 `reel.mp4` slideshow via **ffmpeg** (concat demuxer, `seconds_per_page` each, padded on black) and `clip_upload`s it; (2) **story** — each page is letterboxed to 1080×1920 and pushed via `photo_upload_to_story`. `build_reel`/`_format_caption` here are the shared helpers reused by the TikTok module.

### Layout system
The plot agent asks GPT-4o to return a **weighted row layout** — a JSON structure where each row has a `height_weight` and each panel within a row has a `weight`. The compositor translates these weights into pixel dimensions using simple proportional arithmetic. The layout drives which scenes go where and at what aspect ratio.

### Image color handling
Whether images are black-and-white or color is controlled entirely by the style's image prompt suffix. Styles like `dylan-dog` include "Black and white only, absolutely no color." in their suffix; other styles (e.g. `enki-bilal`, `milo-manara`, `hugo-pratt`, `magnus`, `manga`) produce color images. The compositor does not apply any color conversion — it uses `.convert("RGB")` to normalise format only.

### Rate limiting
`asyncio.Semaphore(cfg.openai.max_concurrent_images)` caps parallel image calls (default: 4) to stay within DALL-E 3's ~5 req/min limit on default API tiers. Adjust in `config.yml`.

### Provider / model selection
`providers.{plot,scene,image}_provider` each name a **configured provider block** (`openai`, `anthropic`, `black_forest_labs`, `fal`). The block then supplies the concrete `text_model` / `image_model` that actually runs. So `image_provider: openai` + `openai.image_model: dall-e-3` runs DALL·E 3; `image_provider: black_forest_labs` + `black_forest_labs.image_model: flux-pro-1.1` runs Flux direct; `image_provider: fal` + `fal.image_model: fal-ai/flux/dev` runs Flux-dev (or SD3.5, Recraft, …) through the fal.ai aggregator. `get_text_client` / `get_image_client` map a provider name to the right client class; `Config.text_model_name()` / `Config.image_model_name()` resolve a provider name to its model string (used for the startup printout).

### Switching image providers
`src/models/image_client.py` has an `ImageClient` ABC with `OpenAIImageClient` (supports `dall-e-3` and `gpt-image-*`), `FluxClient` (Black Forest Labs direct REST), and `FalClient` (fal.ai queue REST — active, works). To use fal: set `providers.image_provider: fal` in `config.yml`, fill `fal.api_key`, and set `fal.image_model` to a full fal model path. fal is the least-restrictive / cheapest route (`enable_safety_checker: false` disables the NSFW filter and the blacked-out images it produces); one `FalClient` serves any fal model — just change the path.

## Key files

| File | Role |
|------|------|
| `src/main.py` | CLI entry point, asyncio pipeline orchestrator |
| `src/config.py` | Loads `config.yml` into typed dataclasses |
| `src/agents/plot_agent.py` | Step 1 — sync GPT-4o call, returns `PlotResult` with layout |
| `src/agents/scene_agent.py` | Step 2 — async coroutine, text + image per scene |
| `src/compositor.py` | Step 3 — Pillow weighted-row compositor |
| `src/publisher_tiktok.py` | Step 4 (active) — TikTok reel upload via Content Posting API (inbox draft / direct) |
| `src/publisher.py` | Step 4 (legacy) — Instagram reel + story via `instagrapi`; also exports shared `build_reel`/`_format_caption` |
| `scripts/tiktok_login.py` | One-time TikTok OAuth helper → caches tokens to `tiktok.token_file` |
| `src/models/text_client.py` | Thin async wrapper over `openai.AsyncOpenAI` with JSON parsing |
| `src/models/image_client.py` | `ImageClient` ABC + `OpenAIImageClient` + `FluxClient` + `FalClient` |
| `Styles/dylan-dog.md` | Style definition — image prompt suffix loaded at runtime |
| `config.example.yml` | Config template (committed); copy to `config.yml` and add key |
| `Decisions.md` | Design decision log |
| `Backlog.md` | Feature backlog |
| `Notes/image-model-research.md` | Image model comparison research |

## Config structure

Each `providers.*_provider` selects a provider block; that block owns the model:

```yaml
providers:
  plot_provider: openai             # openai | anthropic
  scene_provider: openai            # openai | anthropic
  image_provider: openai            # openai | black_forest_labs | fal
openai:
  api_key: ""                       # required
  text_model: gpt-4o                # gpt-4o | gpt-4o-mini
  image_model: gpt-image-1          # gpt-image-1 | dall-e-3
  max_concurrent_images: 4          # semaphore limit for parallel image calls
anthropic:
  api_key: ""
  text_model: claude-sonnet-4-6     # claude-opus-4-8 | claude-sonnet-4-6
black_forest_labs:
  api_key: ""
  image_model: flux-pro-1.1         # flux-pro-1.1 | flux-pro | flux-dev
fal:
  api_key: ""
  image_model: fal-ai/flux/dev      # full fal path: fal-ai/flux/schnell | fal-ai/flux-pro/v1.1 | fal-ai/stable-diffusion-v35-large
  image_size: square_hd             # square_hd | portrait_4_3 | landscape_16_9 | ...
  enable_safety_checker: false      # false = no NSFW filter (permissive)
compositor:
  canvas_width: 2400
  canvas_height: 3200
  gap_px: 8
  margin_px: 24
tiktok:                           # active publisher
  enabled: true                   # true = prompt to publish after generation
  mode: inbox                     # inbox (drafts, no app review) | direct (profile, needs audit)
  client_key: ""                  # from developers.tiktok.com
  client_secret: ""
  token_file: tiktok_token.json   # written by scripts/tiktok_login.py
  access_token: ""                # optional; normally left blank (use token_file)
  refresh_token: ""
  seconds_per_page: 3             # reel slideshow duration per page
  privacy_level: SELF_ONLY        # direct mode only
  caption: "{title}\n\n{tagline}" # direct mode only; {title} {tagline} substituted
instagram:                        # legacy, disabled by default
  enabled: false
  username: ""
  password: ""
  session_file: instagram_session.json
  seconds_per_page: 3
  publish_reel: true
  publish_story: true
  caption: "{title}\n\n{tagline}"
```

## Adding a new comic style

1. Create `Styles/<name>.md` — include a fenced code block with the image prompt suffix (see `Styles/dylan-dog.md` for the format)
2. Run with `--style <name>`

The style file's first fenced code block is parsed as the style suffix appended to every image prompt.
