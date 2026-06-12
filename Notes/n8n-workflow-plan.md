# Plan: ComicGenerator as a native n8n workflow

Goal: rebuild the pipeline (idea → plot → scenes → images → music → reel → TikTok
drafts) as a node-by-node n8n workflow, instead of wrapping the Python CLI.

## Key architectural decisions

**Self-hosted n8n is required.** The reel needs ffmpeg, and n8n Cloud disables the
Execute Command node. Run n8n in Docker with ffmpeg baked into the image:

```dockerfile
FROM n8nio/n8n
USER root
RUN apk add --no-cache ffmpeg
USER node
```

**Everything else is plain HTTP.** Anthropic, fal.ai (images + music), and TikTok's
Content Posting API are all REST — they map 1:1 onto HTTP Request nodes. No custom
n8n nodes needed.

**The page compositor is optional.** Since the reel is now built from the per-scene
images directly (fit-width 1080×1920), the Pillow page composite is only a keepsake
artifact. The n8n workflow can skip it entirely — that removes the only other
Python dependency.

**Simplify the layout logic away.** The weighted-row layout only matters for the
printed page. For the reel, ask the plot agent for title/tagline/beats only, and
generate every image at the same aspect (e.g. fal `portrait_4_3` or `square_hd`);
the fit-width frame logic absorbs any aspect.

**TikTok stays in inbox mode** (drafts, `video.upload` scope, no audit). The cached
token from `scripts/tiktok_login.py` is seeded into n8n once; the workflow refreshes
it itself from then on (refresh tokens last ~1 year, access tokens 24h).

## Credentials / setup (once)

| Where | What |
|-------|------|
| n8n Credentials → Header Auth "Anthropic" | `x-api-key: <anthropic key>` |
| n8n Credentials → Header Auth "fal" | `Authorization: Key <fal key>` |
| n8n Variables | `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, style suffix text, `PANEL_SECONDS=3` |
| Workflow static data (seeded by a one-off Code node) | `access_token`, `refresh_token`, `expires_at` from `tiktok_token.json` |

## Workflow, node by node

### Stage 0 — Trigger & input
1. **Schedule Trigger** (e.g. daily) — or **Form/Webhook Trigger** for manual ideas.
2. **Google Sheets** (optional): pull the next unused idea row; mark it used at the
   end. Alternative: a small **HTTP Request** to Anthropic that invents an idea.
3. **Set** node: assemble run config — `idea`, `style`, `panel_seconds`, run id
   (`{{ $now.format('yyyyMMdd-HHmmss') }}`), work dir `/tmp/comic/<runid>`.

### Stage 1 — Plot
4. **HTTP Request "Plot"** → `POST https://api.anthropic.com/v1/messages`
   (claude-sonnet-4-6). System prompt = the existing plot prompt, trimmed of the
   layout part: return JSON `{title, tagline, panel_count (4–12), beats[]}`.
5. **Code "Parse plot"**: `JSON.parse` the model output (strip code fences),
   validate `4 ≤ panel_count ≤ 12`, throw on failure (n8n retries / error workflow
   catches). Output: one item carrying the plot.

### Stage 2 — Scenes (fan out)
6. **Code "Split beats"**: emit one item per beat → `{index, beat, title, tagline}`.
7. **HTTP Request "Scene text"** → Anthropic per item; returns
   `{caption, dialogue, image_prompt}`. Node settings: **Batching = 4 items /
   1s interval** (replaces the asyncio semaphore), **Retry on Fail = 2**.
8. **Code "Append style suffix"**: `image_prompt + "\n\n" + styleSuffix` (the fenced
   block from `Styles/<name>.md`, stored in an n8n Variable or a Set node).

### Stage 3 — Images (fal queue pattern)
9. **HTTP Request "Submit image"** → `POST https://queue.fal.run/<model path>`
   (e.g. `fal-ai/bytedance/seedream/v4/text-to-image`) with
   `{prompt, image_size: "square_hd", enable_safety_checker: false}`.
   Keep `status_url`/`response_url` on the item.
10. **Polling loop** (n8n loop back-edge):
    **Wait 3s** → **HTTP "Poll status"** (`status_url`) → **IF status ≠ COMPLETED**
    → back to Wait (cap via loop counter ~40); else continue.
    *Alternative:* fal supports webhooks (`?fal_webhook=<n8n webhook url>`) — split
    into two workflows and skip polling; start with polling, it's one workflow and
    easier to debug.
11. **HTTP "Fetch result"** (`response_url`) → **HTTP "Download image"**
    (`images[0].url`, response = binary file).
12. **Write Binary File**: `/tmp/comic/<runid>/scene_{{index, padded}}.png`.

### Stage 4 — Music (parallel branch off the plot, same fal pattern)
13. **HTTP "Submit music"** → `POST https://queue.fal.run/fal-ai/stable-audio-3/medium/text-to-audio`
    with `{prompt: styleMood + title + tagline, duration: panel_count × panel_seconds,
    output_format: "wav"}` (port the `_STYLE_MOODS` map into a Code/Set node).
14. Same **Wait → Poll → IF** loop → **HTTP download** (`audio.url`) →
    **Write Binary File** `/tmp/comic/<runid>/music.wav`.

### Stage 5 — Join & render the reel
15. **Merge** node (wait for both branches; images branch first aggregated with an
    **Aggregate/Code** node so all scenes are present).
16. **Code "ffmpeg args"**: build the concat list file content
    (`file 'scene_01.png' / duration 3 …`, last frame repeated) — write it via
    **Write Binary File** as `frames.txt`.
17. **Execute Command "ffmpeg"** — same recipe as `build_panel_reel`:
    pre-fit isn't available (no Pillow), so do fit-width in ffmpeg directly:
    ```
    ffmpeg -y -f concat -safe 0 -i frames.txt -stream_loop -1 -i music.wav \
      -shortest -vf "scale=1080:-2,crop=1080:'min(ih,1920)':0:'(ih-min(ih,1920))/2',pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,format=yuv420p" \
      -af "afade=t=out:st=<total-2>:d=2" -r 30 -c:v libx264 -c:a aac \
      -movflags +faststart /tmp/comic/<runid>/reel.mp4
    ```
    (scale-to-width then vertical crop/pad = exactly the Python `_fit_width` logic).
18. **Read Binary File**: `reel.mp4`.

### Stage 6 — TikTok upload (inbox/drafts)
19. **Code "Check token"**: read static data; if `expires_at < now + 60s` →
20. **HTTP "Refresh token"** → `POST https://open.tiktokapis.com/v2/oauth/token/`
    (form-encoded, `grant_type=refresh_token`) → **Code "Save tokens"** writes the
    new pair back to static data.
21. **HTTP "Init upload"** → `POST /v2/post/publish/inbox/video/init/` with
    `source_info: {source: FILE_UPLOAD, video_size, chunk_size: video_size,
    total_chunk_count: 1}` (Bearer token). Fail the run on `error.code != "ok"`.
22. **HTTP "PUT video"** → the returned `upload_url`, binary body = `reel.mp4`,
    headers `Content-Type: video/mp4`, `Content-Range: bytes 0-<n-1>/<n>`.

### Stage 7 — Notify & cleanup
23. **Telegram/Slack/Email** node: "Reel in TikTok drafts — open the app to post"
    + title/tagline (caption to paste manually — inbox mode ignores `post_info`).
24. **Execute Command**: `rm -rf /tmp/comic/<runid>` (after success).
25. **Error Trigger workflow** (separate): notify on any failure with node name +
    error; n8n keeps the partial run data for debugging.

## Suggested build order

1. **Phase 0 (1 node):** Execute Command wrapping `python -m src.main --publish` —
   immediate value while building the rest.
2. **Phase 1:** Stages 0–3 (plot → images on disk), verify artifacts.
3. **Phase 2:** Stages 4–5 (music + ffmpeg reel).
4. **Phase 3:** Stage 6–7 (token refresh + upload + notify), seed tokens from
   `tiktok_token.json`, then disable the cron on the CLI path.

## Gotchas

- **Items vs. runs:** keep `runid`/plot on every item (n8n Merge by position is
  fragile); use "Run Once for Each Item" consciously on HTTP nodes.
- **fal polling inside loops** counts toward execution time — set workflow timeout
  ≥ 10 min for 12-panel runs.
- **Binary memory:** 8–12 PNGs + wav + mp4 per run is fine, but set
  `N8N_DEFAULT_BINARY_DATA_MODE=filesystem` to avoid keeping binaries in RAM.
- **TikTok token single-writer:** only this workflow should refresh the token, or
  the CLI and n8n will race and invalidate each other's refresh tokens.
