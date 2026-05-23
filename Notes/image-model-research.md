# Image Generation Model Research
*For Dylan Dog–style noir/horror comic panels (black & white, pen-and-ink aesthetic)*

## Summary Recommendation

**Start with DALL-E 3** (OpenAI) — well-supported SDK, good prompt adherence, easy to integrate.
**Switch to Flux Pro** (Black Forest Labs) for higher quality comic/illustration output once initial pipeline is working.

---

## Model Comparison

### DALL-E 3 (OpenAI)
- **API**: OpenAI Python SDK (`openai>=1.0`), fully async
- **Cost**: ~$0.04–0.08 per image (1024×1024, standard quality)
- **Prompt control**: Good; requires detailed prompts for consistent style; tends to produce sepia/warm tones even when B&W is requested — **mitigate by converting to greyscale in Pillow after download**
- **Comic/B&W quality**: Adequate for prototyping; handles noir atmosphere and high-contrast compositions reasonably well
- **Weaknesses**: Frequently ignores "no text" instruction; sometimes adds watermark-like text artifacts; hand anatomy issues on close-ups
- **Integration effort**: Low — already in OpenAI SDK used for text generation

### Flux Pro (Black Forest Labs)
- **API**: REST API at `api.bfl.ai`; Python via direct `httpx` calls or `bfl` SDK
- **Cost**: ~$0.014–0.04 per image (credit-based); significantly cheaper than DALL-E 3 at comparable quality
- **Prompt control**: Excellent; strong style adherence, handles illustration and line-art styles very well; generation time ~4.5s
- **Comic/B&W quality**: Best API-accessible option for 2026; strong performance on pen-and-ink, crosshatching, detailed illustration styles
- **Weaknesses**: Requires separate API key and slightly more integration work; no native Python SDK (use `httpx`)
- **Integration effort**: Medium — abstraction layer in `image_client.py` isolates this

### Stability AI SD3.5 Large
- **API**: REST API at `platform.stability.ai`; credit-based
- **Cost**: ~$0.065 per image
- **Prompt control**: Moderate
- **Comic/B&W quality**: Solid for ink/line-art styles; supports crosshatching and stipple; less consistent than Flux
- **Weaknesses**: SD3.0 deprecated April 2025; API reliability history spotty; less prompt-precise than Flux or DALL-E 3
- **Integration effort**: Medium

### Midjourney
- **API**: No public REST API as of 2026; enterprise API available to large subscribers only
- **Comic/B&W quality**: Best overall artistic quality and style consistency — but not usable programmatically
- **Verdict**: Not viable for this project

---

## Integration Architecture

The `src/models/image_client.py` module uses an abstract base class `ImageClient` with a factory function `get_image_client(config)`. Switching providers requires only a config change:

```yaml
providers:
  active_image_provider: dall-e-3   # change to: flux
```

---

## Sources
- bfl.ai/pricing (Black Forest Labs pricing, 2026)
- docs.bfl.ml/quick_start/pricing
- stability.ai/api-pricing-update-25
- openai.com/api/pricing
