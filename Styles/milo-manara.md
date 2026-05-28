# Milo Manara — Comic Style Definition

This file defines the visual and narrative style used when generating comic panels in the Milo Manara aesthetic.
It is loaded at runtime by `src/agents/scene_agent.py` and appended to every image prompt.

---

## Visual Style

Milo Manara is an Italian comics artist known since the 1970s for his fluid, highly detailed ligne claire–influenced ink work with a painterly, sensual quality. His defining visual characteristics:

- **Medium**: Ink with refined hatching, often supplemented by watercolor-style washes; clean yet richly detailed linework
- **Line work**: Graceful, confident lines — thin and expressive, with subtle hatching rather than dense crosshatching; emphasis on contour and form
- **Contrast**: Softer than noir — luminous highlights, gentle shadow gradients rather than stark black pools; warm, balanced tones
- **Atmosphere**: Mediterranean warmth, dream-like and fantastical; sun-drenched piazzas, lush interiors, mythological or historical settings
- **Setting**: Italy, ancient Rome, Mediterranean coasts, fantastical dreamscapes, occasionally dystopian futures
- **Faces**: Elegant and idealised; fine features, expressive eyes, cinematic emotional range
- **Composition**: Cinematic and theatrical — wide establishing shots with strong perspective, intimate close-ups on faces, dynamic diagonal compositions; inspired by film storyboarding

## Narrative Tone

- Surreal and literary; adventure, fantasy, and mythology woven together
- Stories feel like illustrated novels: rich with cultural references, irony, and beauty
- Characters move through history, myth, and dream with elegance
- Themes: freedom, desire, power, fate, the boundary between myth and reality

---

## Image Prompt Suffix

The following text is appended to every DALL-E / Flux image prompt when this style is active.

```
Italian comics art in the style of Milo Manara: fluid confident ink linework with fine hatching, luminous warm tones, elegant and detailed figures, cinematic panel composition. Mediterranean and mythological atmosphere, rich architectural detail, dream-like quality. Graphic novel illustration, refined and expressive draughtsmanship, 1980s Italian fumetti aesthetic.
```

**Hard constraint** (always appended last, never omit):

```
No text, no speech bubbles, no captions, no letters, no words, no numbers visible anywhere in the image.
```

---

## Layout Guidance for Plot Agent

When generating panel layouts for Milo Manara–style stories:
- Open with a large cinematic establishing shot (height_weight 1.5–2.0) — architecture or landscape sets the mood
- Use wide single-panel rows for key dramatic or mythological reveals
- Alternate between intimate close-up rows and expansive environment rows
- End with a contemplative 1- or 2-panel row — a face, a horizon, or a symbolic image
