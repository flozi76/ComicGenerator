# Manga — Comic Style Definition

This file defines the visual and narrative style used when generating comic panels in the classic Japanese manga print aesthetic.
It is loaded at runtime by `src/agents/scene_agent.py` and appended to every image prompt.

---

## Visual Style

Inspired by the golden era of Japanese manga print: Kentaro Miura (*Berserk*), Takehiko Inoue (*Vagabond*, *Slam Dunk*), Naoki Urasawa (*Monster*, *20th Century Boys*), and Goseki Kojima (*Lone Wolf and Cub*). These artists defined the expressive, cinematic black-and-white manga page — obsessive line craft, stark tonal contrast, and emotion distilled into pure ink.

Defining visual characteristics:

- **Medium**: Black and white pen-and-ink with screentone — the foundational manga print aesthetic; no color, no greys except through dot patterns and crosshatching
- **Line work**: Confident, varying line weight; thick bold outlines for silhouettes, finer interior detail lines; cross-hatching builds shadow and texture with technical precision
- **Shading**: Screentone dot patterns for mid-tones and atmosphere; dense hatching in deep shadow areas; stark solid black fills (*beta nori*) for maximum drama
- **Contrast**: Extreme chiaroscuro — brilliant whites against jet-black shadows; open paper space used as active highlight; high visual impact from stark juxtaposition
- **Composition**: Cinematic and dynamic — low-angle worm's-eye shots for power, high-angle overviews for vulnerability, extreme close-ups for psychological intensity; speed lines radiating from impact points
- **Atmosphere**: Richly detailed environments — feudal battlefields, rain-soaked urban streets, ancient forests; backgrounds rendered with meticulous texture to ground the drama
- **Faces**: Expressive with large, detailed eyes as the primary emotional conveyor; character emotion amplified through shadow under the brow, jaw tension, tear trails, and sweat drops
- **Action**: Speed lines, motion blur, and dynamic impact marks convey kinetic energy; battle sequences flow like water — graceful and instinctive

## Narrative Tone

- Epic and psychological; fate, survival, identity, and the cost of power
- Emotional restraint punctuated by explosive violence or revelation
- Silent panels carry as much weight as dialogue — the pause before and aftermath after
- Characters defined by trauma, obsession, or an unyielding will
- Themes: the burden of strength, loyalty and sacrifice, the line between human and monster, solitude and belonging

---

## Image Prompt Suffix

The following text is appended to every DALL-E / Flux image prompt when this style is active.

```
Black and white only, absolutely no color. Classic Japanese manga print style: precise pen-and-ink linework with bold varying line weights, screentone dot shading for mid-tones, heavy cross-hatching in shadow areas, stark beta-nori black fills. Extreme chiaroscuro contrast, open white paper highlights. Cinematic composition — dynamic angles, speed lines, dramatic close-ups. Expressive character faces with large detailed eyes. Richly detailed backgrounds. Kentaro Miura and Takehiko Inoue aesthetic.
```

**Hard constraint** (always appended last, never omit):

```
No text, no speech bubbles, no captions, no letters, no words, no numbers visible anywhere in the image.
```

---

## Plot System Prompt

Persona and layout guidance used by the plot agent when generating a manga-style story outline.

```
You are an epic manga comic director in the tradition of Kentaro Miura and Naoki Urasawa. Given a story idea and a visual style description, create a comic outline that is psychologically weighty and visually explosive — characters defined by obsession or trauma, driven toward a confrontation that carries existential stakes.

Layout guidance:
- Open with a large establishing splash panel (height_weight 1.5-2.0) that sets scale and dread — a vast landscape, an imposing figure, a city at night
- Use rapid 3-4 panel rows for action sequences, tight cross-cuts between close-ups and wide shots
- Reserve a full-width single panel for the key psychological or physical confrontation moment
- Alternate extreme close-ups (eyes, fists, blade edges) with sweeping environmental panels to control rhythm
- End with a quiet 2-panel row — a face carrying the aftermath, and a wide shot of the world unchanged around it
```

---

## Scene System Prompt

Persona used by the scene agent when expanding a beat into a panel description.

```
You are a manga comic artist in the tradition of Kentaro Miura (Berserk) and Takehiko Inoue (Vagabond). Expand a story beat into a visual panel description.

The image_prompt describes only what is seen: ink linework, screentone shading, extreme camera angles, speed lines, and expressive faces. Convey psychological depth through composition and contrast — the weight of a gaze, the stillness before violence, shadow as a character's inner state. Render action with the flow of water; render quiet moments with vast, heavy space.
```

---

## Fun Plot System Prompt

Persona and layout guidance used by the plot agent in fun/comedy mode.

```
You are a comedic manga director with a taste for genre subversion — overpowered protagonists undone by trivialities, intense training arcs for completely mundane goals, brooding anti-heroes confronting deeply embarrassing situations with the gravity of cosmic warfare. Create a comic outline with escalating absurdity played entirely straight.

Layout guidance:
- Open with an absurdly dramatic establishing splash — enormous visual scale, completely trivial stakes
- Use rapid 3-4 panel rows for comedic escalation: the stoic face, the dawning realization, the catastrophic overreaction
- Reserve a full-width panel for the most ridiculous power-up or catastrophic misunderstanding
- End with a deadpan aftermath — the world technically saved, but the protagonist's dignity destroyed

Beats should mine humour from manga tropes: intense training montages for cooking eggs, flashback trauma over a misplaced item, power levels measured in embarrassment. Play every absurd moment with complete sincerity — the comedy is in the commitment.
```
