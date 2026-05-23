# Comic Generator — Backlog

## Done

- [x] Proof-of-concept React prototype (`Idea/noir-comic-generator.jsx`)
- [x] Architecture planning and design decisions
- [x] Image model research (`Notes/image-model-research.md`)
- [x] Dylan Dog style definition (`Styles/dylan-dog.md`)
- [x] Python project skeleton (config, models, agents, compositor, CLI)

## Active

- [ ] **Test end-to-end with real OpenAI API key** — run `python src/main.py --idea "..."` and verify output folder, panel images, and stitched `comic.png`
- [ ] **Tune Dylan Dog style prompt** — iterate on `Styles/dylan-dog.md` style suffix based on actual DALL-E 3 output quality

## Next Up

- [ ] **Switch image provider to Flux Pro** — wire up `FluxClient` in `src/models/image_client.py`; update `config.yml` to `active_image_provider: flux`; compare output quality against DALL-E 3
- [ ] **Improve layout variety** — expand the plot agent prompt with more example layouts; add L-shaped panels or pinwheel layouts
- [ ] **Add a second comic style** — e.g. `Styles/marvelmanga.md` or `Styles/tintin.md` for comparison

## Future / Animated

- [ ] **Panel animation** — animate each scene (e.g. slow Ken Burns zoom) and stitch into a video or animated GIF
- [ ] **Web viewer** — serve the generated comic from the React prototype (`Idea/`) with the new Python backend
- [ ] **Multi-page comics** — extend the pipeline to generate 6–8 pages rather than a single-page story
- [ ] **Character consistency** — investigate ControlNet or reference-image chaining to keep the protagonist's appearance consistent across panels
- [ ] **Local model support** — run Stable Diffusion locally (via `diffusers`) to avoid per-image API costs
