# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

A Python console application that generates a single-page noir/horror comic from a text idea. It runs a three-step pipeline:
1. **Plot agent** (sync): GPT-4o generates title, tagline, panel count (4–12), page layout, and scene beats
2. **Scene agents** (async, parallel): one coroutine per scene expands a beat into caption + image prompt, then generates a DALL-E 3 image
3. **Compositor**: Pillow stitches all panel images into one greyscale `comic.png`

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
```

Output is written to `output/<YYYY-MM-DD>/story_<HHmmss>_<slug>_<rand>/` containing `plot.json`, `scene_NN.png` files, and `comic.png`.

## Architecture

### Pipeline flow (`src/main.py`)
```
load_config() → plot_agent.run() → [asyncio.gather(scene_agent.run() × N)] → compositor.compose()
```

### Layout system
The plot agent asks GPT-4o to return a **weighted row layout** — a JSON structure where each row has a `height_weight` and each panel within a row has a `weight`. The compositor translates these weights into pixel dimensions using simple proportional arithmetic. The layout drives which scenes go where and at what aspect ratio.

### Image greyscale enforcement
DALL-E 3 often ignores "black and white" prompts and returns warm/sepia images. The compositor calls `.convert("L")` on every downloaded image unconditionally — this is the authoritative greyscale step, not the prompt.

### Rate limiting
`asyncio.Semaphore(cfg.openai.max_concurrent_images)` caps parallel image calls (default: 4) to stay within DALL-E 3's ~5 req/min limit on default API tiers. Adjust in `config.yml`.

### Switching image providers
`src/models/image_client.py` has an `ImageClient` ABC with `DallE3Client` (active) and `FluxClient` (stub). To switch: set `providers.active_image_provider: flux` in `config.yml` and implement `FluxClient.generate()`.

## Key files

| File | Role |
|------|------|
| `src/main.py` | CLI entry point, asyncio pipeline orchestrator |
| `src/config.py` | Loads `config.yml` into typed dataclasses |
| `src/agents/plot_agent.py` | Step 1 — sync GPT-4o call, returns `PlotResult` with layout |
| `src/agents/scene_agent.py` | Step 2 — async coroutine, text + image per scene |
| `src/compositor.py` | Step 3 — Pillow weighted-row compositor |
| `src/models/text_client.py` | Thin async wrapper over `openai.AsyncOpenAI` with JSON parsing |
| `src/models/image_client.py` | `ImageClient` ABC + `DallE3Client` + `FluxClient` stub |
| `Styles/dylan-dog.md` | Style definition — image prompt suffix loaded at runtime |
| `config.example.yml` | Config template (committed); copy to `config.yml` and add key |
| `Decisions.md` | Design decision log |
| `Backlog.md` | Feature backlog |
| `Notes/image-model-research.md` | Image model comparison research |

## Config structure

```yaml
providers:
  active_image_provider: dall-e-3   # or: flux
openai:
  api_key: ""                        # required
  max_concurrent_images: 4          # semaphore limit for parallel image calls
compositor:
  canvas_width: 2400
  canvas_height: 3200
  gap_px: 8
  margin_px: 24
```

## Adding a new comic style

1. Create `Styles/<name>.md` — include a fenced code block with the image prompt suffix (see `Styles/dylan-dog.md` for the format)
2. Run with `--style <name>`

The style file's first fenced code block is parsed as the style suffix appended to every image prompt.
