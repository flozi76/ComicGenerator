# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

A Python console application that generates a single-page noir/horror comic from a text idea. It runs a three-step pipeline:
1. **Plot agent** (sync): GPT-4o generates title, tagline, panel count (4–12), page layout, and scene beats
2. **Scene agents** (async, parallel): one coroutine per scene expands a beat into caption + image prompt, then generates a DALL-E 3 image
3. **Compositor**: Pillow stitches all panel images into one greyscale `comic.png`
4. **Publisher** (optional): after generation, offers to publish the page(s) to Instagram as a slideshow **reel** + **story** frames via `instagrapi`

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

# Auto-publish to Instagram (skip the prompt) / never publish
python -m src.main --idea "..." --publish
python -m src.main --idea "..." --no-publish
```

Instagram publishing needs `instagrapi` (in `requirements.txt`) and ffmpeg for the reel video (`brew install ffmpeg`, or it falls back to the binary bundled with `imageio-ffmpeg`). Fill `instagram.username` / `instagram.password` in `config.yml` and set `instagram.enabled: true` to be prompted after generation.

**First login:** Instagram challenges a login from a new device/IP with a verification code (email/SMS). Run the login helper once **from a real terminal** so you can type the code; it caches the session so later runs publish without prompting:

```bash
python3 scripts/instagram_login.py
```

Output is written to `output/<YYYY-MM-DD>/story_<HHmmss>_<slug>_<rand>/` containing `plot.json`, `scene_NN.png` files, and `comic.png`.

## Architecture

### Pipeline flow (`src/main.py`)
```
load_config() → plot_agent.run() → [asyncio.gather(scene_agent.run() × N)] → compositor.compose() → [publisher.publish_to_instagram()]
```

### Instagram publishing (`src/publisher.py`)
Optional final step. After compositing, `main.py` decides whether to publish: the `--publish`/`--no-publish` flags force the choice; otherwise, if `instagram.enabled` is true and stdin is a TTY, it prompts `Publish to Instagram as reel + story? [y/N]`. `publish_to_instagram()` logs in with `instagrapi` (caching the session to `instagram.session_file` to avoid re-login/checkpoints), then: (1) **reel** — `build_reel()` renders the page PNG(s) into a 9:16 `reel.mp4` slideshow via **ffmpeg** (concat demuxer, `seconds_per_page` each, padded on black) and `clip_upload`s it; (2) **story** — each page is letterboxed to 1080×1920 and pushed via `photo_upload_to_story`. `instagrapi` is imported lazily inside the function, so the rest of the app runs without it installed. Publishing failures are caught and printed — they never abort a successful generation.

### Layout system
The plot agent asks GPT-4o to return a **weighted row layout** — a JSON structure where each row has a `height_weight` and each panel within a row has a `weight`. The compositor translates these weights into pixel dimensions using simple proportional arithmetic. The layout drives which scenes go where and at what aspect ratio.

### Image greyscale enforcement
DALL-E 3 often ignores "black and white" prompts and returns warm/sepia images. The compositor calls `.convert("L")` on every downloaded image unconditionally — this is the authoritative greyscale step, not the prompt.

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
| `src/publisher.py` | Step 4 (optional) — Instagram reel + story publishing via `instagrapi` + ffmpeg |
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
instagram:
  enabled: false                  # true = prompt to publish after generation
  username: ""                    # Instagram handle
  password: ""                    # Instagram password
  session_file: instagram_session.json
  seconds_per_page: 3             # reel slideshow duration per page
  publish_reel: true
  publish_story: true
  caption: "{title}\n\n{tagline}" # template; {title} {tagline} substituted
```

## Adding a new comic style

1. Create `Styles/<name>.md` — include a fenced code block with the image prompt suffix (see `Styles/dylan-dog.md` for the format)
2. Run with `--style <name>`

The style file's first fenced code block is parsed as the style suffix appended to every image prompt.
