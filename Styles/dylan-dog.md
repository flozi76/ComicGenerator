# Dylan Dog — Comic Style Definition

This file defines the visual and narrative style used when generating comic panels in the Dylan Dog aesthetic.
It is loaded at runtime by `src/agents/scene_agent.py` and appended to every image prompt.

---

## Visual Style

Dylan Dog is an Italian horror/noir comic series by Tiziano Sclavi, published since 1986.
The defining visual characteristics:

- **Medium**: Pen and ink, black and white — no color in the interior pages
- **Line work**: Heavy crosshatching, dense hatching in shadow areas, clean confident linework for edges
- **Contrast**: Dramatic chiaroscuro — deep shadow pools, stark highlights; high contrast
- **Atmosphere**: Gothic, melancholic, oppressive; rain and fog are frequent
- **Setting**: Urban London — cobblestone streets, Victorian row houses, bleak alleyways, foggy bridges
- **Faces**: Expressive, detailed, slightly caricature-tending; elongated features
- **Composition**: Cinematic framing; frequent dramatic close-ups of faces and hands; wide establishing shots for atmosphere

## Narrative Tone

- Horror with dark humor; dread mixed with absurdity
- Protagonist: young dark-haired man in casual clothing (jeans, open collar shirt), calm demeanor even in extreme situations
- Secondary character: Groucho Marx lookalike sidekick — mustache, large glasses, wisecracking in the face of horror
- Themes: death, loss, memory, the uncanny, monsters as metaphors

---

## Image Prompt Suffix

The following text is appended to every DALL-E / Flux image prompt when this style is active.

```
Black and white only, absolutely no color. Italian noir comic book style, detailed pen and ink artwork, heavy crosshatching, deep shadow areas, dramatic chiaroscuro lighting, 1980s graphic novel aesthetic. Urban gothic London atmosphere, rain-slicked cobblestones, Victorian architecture, cinematic panel composition, moody and atmospheric.
```

**Hard constraint** (always appended last, never omit):

```
No text, no speech bubbles, no captions, no letters, no words, no numbers visible anywhere in the image.
```

---

## Layout Guidance for Plot Agent

When generating panel layouts for Dylan Dog–style stories:
- Open with a large splash panel (height_weight 1.5–2.0) for atmosphere
- Use tight 3-panel rows for rapid dialogue or action sequences
- Reserve a wide single-panel row for key horror reveals
- End with a quieter 2-panel row — one close-up, one establishing shot
