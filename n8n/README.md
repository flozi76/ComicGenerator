# n8n integration

Phased migration of the pipeline to n8n — see `Notes/n8n-workflow-plan.md` for the
design. This directory holds the Docker setup and the importable workflows:

| File | What |
|------|------|
| `docker-compose.yml` + `Dockerfile` | Self-hosted n8n with ffmpeg + python3 baked in |
| `phase0-workflow.json` | Phase 0: one Execute Command node wrapping the Python CLI |
| `native-workflow.json` | The full node-by-node pipeline (no Python CLI involved) |

## Running n8n (Docker, recommended)

```bash
cd n8n
cp .env.example .env       # fill in the keys (values are in config.yml)
docker compose up -d --build
```

n8n UI → http://localhost:5678 (first visit creates the owner account).
The repo is mounted at **`/project`** inside the container; workflows and run
artifacts survive restarts (`n8n_data` volume, `output/` on the host).

Alternative without Docker: `npm install -g n8n && n8n` — then the native
workflow's `/project/...` paths and `$env.*` keys must exist on the host instead.

## Native workflow (`native-workflow.json`)

The full pipeline as ~25 nodes, reel-only (no comic page composite):

```
Manual/Schedule ─ Init run ─ mkdir ─ Invent idea (Claude) ─ Plot (Claude) ─ Parse plot
                                                                      │
                       ┌─ Split beats → Scene text (Claude, 4× batched) → Build image
                       │  prompt → Image (fal seedream) → Download → Write scene_NN.png
                       │  → Collect ──────────────┐
                       │                          ├─ Merge → Render reel (ffmpeg) →
                       └─ Music (fal stable-audio-3) → Download → music.wav ──┘
                                                                      │
              TikTok token (refresh helper) → init upload → PUT reel.mp4 → Done
```

- **Idea**: Claude invents a fresh noir premise each run (no idea pool to maintain).
- **Style**: all Dylan Dog prompts/constants live in the **Init run** Code node —
  edit there to change style, models (`claude-sonnet-4-6`, seedream, stable-audio-3),
  or pacing (`panelSeconds`).
- **API keys** come from the container environment (`.env` →
  `{{ $env.ANTHROPIC_API_KEY }}` / `FAL_API_KEY` / `TIKTOK_CLIENT_*`) — no n8n
  credentials to configure.
- **TikTok**: `scripts/n8n_tiktok_token.py` reads/refreshes `/project/tiktok_token.json`
  (seeded once by `scripts/tiktok_login.py` on the host), then the workflow does the
  inbox init + binary PUT. The reel lands in **TikTok drafts**; caption/hashtags are
  added by hand in the app (the inbox API ignores captions).
- **Reel**: `scripts/n8n_render_reel.sh` mirrors `build_panel_reel` — every panel
  spans the full 1080px width, vertically padded/cropped to 1920.
- Run artifacts: `output/n8n/run-<timestamp>/` (scene PNGs, music.wav, reel.mp4).

Import → run once manually (takes a few minutes) → toggle **Active** for the
daily 19:00 schedule (`GENERIC_TIMEZONE` in `.env`).

⚠️ While the native workflow's schedule is active, disable any other scheduled
producer (Phase 0 / CLI cron) — two writers would race on the TikTok token refresh.

## Phase 0 workflow (`phase0-workflow.json`)

One Execute Command node runs the existing CLI end-to-end
(`scripts/n8n_generate.sh` → `python3 -m src.main --idea … --publish`).
Good as a fallback while iterating on the native one.

- Running it **inside Docker**: edit the *Pick idea* node and change `projectDir`
  to `/project`. The image already contains python3 + the CLI's deps (the legacy
  instagrapi path is not installed).
- Running it on the **host**: `projectDir` stays the absolute repo path;
  python3/ffmpeg come from brew.

Generation output goes to the usual `output/<date>/story_*/` either way; the
reel lands in TikTok drafts (inbox mode).
