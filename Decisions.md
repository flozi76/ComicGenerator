# Design Decisions

This file records the key design choices made during architecture planning (2026-05-23).

---

## Application Type
**Decision**: Python console application (not a web server or GUI).
**Reason**: Simplest path to a working pipeline; no frontend complexity; easy to run from cron or scripts.

---

## Color Mode
**Decision**: Black & white (greyscale).
**Reason**: Faithful to Dylan Dog's original Italian print aesthetic; also cheaper per image (greyscale = less detail required from the model).
**Implementation**: Image prompts instruct the model to produce B&W; the Pillow compositor converts every panel to greyscale with `.convert("L")` unconditionally — this is the authoritative step regardless of what the model returns.

---

## Panel Count
**Decision**: AI decides (4–12 panels per comic).
**Reason**: Lets the model match panel density to narrative pacing — a simple 4-beat story shouldn't be padded to 8 panels.
**Constraint**: Plot agent validates count is within 4–12; retries once on invalid response.

---

## Panel Layout
**Decision**: AI decides per story using a weighted row system.
**Reason**: Fixed grids are boring; the AI can choose splash panels for dramatic openings, dense rows for action, wide panels for reveals.
**Format**: JSON layout spec with `rows[].height_weight` and `rows[].panels[].weight` — interpreted by the Pillow compositor into pixel geometry.

---

## Text in Panels (Captions / Dialogue)
**Decision**: Text is embedded in the AI image prompt — Python does NOT render text overlays.
**Reason**: Simpler implementation; avoids font licensing and layout complexity.
**Trade-off**: Less reliable — AI image models frequently misplace or misspell text. Accepted for v1; Python text overlay is a future enhancement.
**Mitigation**: The image prompt always includes "No text, no speech bubbles, no captions" to suppress unwanted AI-generated text, while the caption/dialogue is part of the scene description wording.

---

## Final Output Format
**Decision**: Single stitched PNG (one comic page).
**Reason**: Easy to share, view, and iterate on; no PDF dependency.
**Future**: Multi-page PDF and animated GIF are in the backlog.

---

## Text Generation Provider
**Decision**: OpenAI GPT-4o.
**Reason**: Strong instruction-following for structured JSON output; reliable JSON generation with low hallucination rate.

---

## Image Generation Provider
**Decision**: Start with OpenAI DALL-E 3; switch to Black Forest Labs Flux Pro when ready.
**Reason**: DALL-E 3 is already in the OpenAI SDK — zero extra setup. Flux Pro delivers better illustration quality at lower cost (~$0.014–0.04 vs $0.04–0.08 per image) but requires a separate API key and `httpx` integration.
**Implementation**: `src/models/image_client.py` uses an abstract `ImageClient` base class; switching providers is a one-line config change.

---

## Config Format
**Decision**: YAML file (`config.yml`, gitignored) with `config.example.yml` committed.
**Reason**: Human-readable, supports comments, easy to edit; `pyyaml` is widely available.
**Provider slots**: All future providers (Anthropic, Black Forest Labs) have placeholder slots in `config.example.yml` even if unused — reduces friction when switching.

---

## Parallelism Model
**Decision**: `asyncio.gather()` for concurrent scene generation; `asyncio.Semaphore(4)` to cap concurrent image API calls.
**Reason**: Python asyncio fits naturally with the `openai` async client; semaphore prevents hitting DALL-E 3's ~5 req/min rate limit on default API tier.
**Semaphore limit**: Configurable in `config.yml` (`openai.max_concurrent_images`).

---

## Output Folder Naming
**Decision**: `output/<YYYY-MM-DD>/story_<HHmmss>_<slug>_<3randchars>/`
**Reason**: Date prefix gives daily folders; timestamp + slug makes each story human-readable; 3-char random suffix prevents collisions if two runs start in the same second.
