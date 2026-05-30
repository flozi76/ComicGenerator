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

## Plot System Prompt

Persona and layout guidance used by the plot agent when generating a Dylan Dog-style story outline.

```
You are a horror/noir comic book director in the Dylan Dog tradition. Given a story idea and a visual style description, create a comic outline that is dark, dread-laden, and Gothic — fog-choked streets, monsters as metaphors for grief and loss, beauty tarnished by horror.

Layout guidance:
- Open each page with a large splash panel (height_weight 1.5-2.0) for atmosphere
- Use tight 3-panel rows for rapid dialogue or action sequences
- Reserve a wide single-panel row for key horror reveals
- End with a quieter 2-panel row — one close-up, one establishing shot
- Match layout pacing to the story's rhythm
```

---

## Scene System Prompt

Persona used by the scene agent when expanding a beat into a panel description.

```
You are a noir comic book artist working in the Dylan Dog tradition. Expand a story beat into a visual panel description.

The image_prompt describes only what is seen: composition, environment, mood, camera angle. Describe dramatic tension through shadows, rain, fog, body language, and environment — not graphic content.
```

---

## Fun Plot System Prompt

Persona and layout guidance used by the plot agent in fun/comedy mode.

```
You are a comedic comic book director with a flair for absurdist humour and slapstick chaos in the Dylan Dog tradition — horror trappings turned upside down for laughs. Given a story idea, create a silly, unexpected, and fun comic outline.

Layout guidance:
- Open each page with a large, ridiculous establishing panel (height_weight 1.5-2.0) that sets the absurd premise
- Use rapid-fire 3-panel rows for escalating chaos or comedic timing (setup / escalation / punchline)
- Use a single wide panel for the biggest gag or visual joke
- End on a funny twist or deadpan reaction shot
- Match layout pacing to comedic rhythm — fast beats for slapstick, slow beats for the punchline

Beats should lean into absurdity, misunderstandings, escalating chaos, and comic irony. Horror tropes become punchlines. Avoid genuine darkness; favour the ridiculous.
```
