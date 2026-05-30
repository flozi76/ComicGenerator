# Anime — Comic Style Definition

This file defines the visual and narrative style used when generating comic panels in the classic 80s–90s anime aesthetic.
It is loaded at runtime by `src/agents/scene_agent.py` and appended to every image prompt.

---

## Visual Style

Inspired by the golden era of Japanese animation and manga: Katsuhiro Otomo (*Akira*, 1988), Masamune Shirow (*Ghost in the Shell*, 1989), and Yoshiaki Kawajiri (*Ninja Scroll*, 1993). This era defined cinematic anime — hyper-detailed environments, precise ink linework, and cel-shaded color applied with a painter's eye.

Defining visual characteristics:

- **Medium**: Cel animation aesthetic — clean, confident ink outlines with varying line weight; precise hatching in shadow areas
- **Color**: Flat cel-shaded base colors with hard shadow boundaries; vivid limited palette — deep indigos, electric blues, neon oranges and magentas against near-black environments
- **Contrast**: High — dark atmospheric backgrounds with brilliant foreground color pops; neon reflections on wet surfaces
- **Atmosphere**: Urban dystopia and mythic Japan coexisting — rain-drenched megacity streets, paper lanterns, crumbling concrete, neon kanji signage, steam vents
- **Setting**: Futuristic-feudal hybrid environments; cyberpunk cityscapes, ancient temples with technological intrusions, rooftops at night, underground tunnels
- **Faces**: Anime proportions but grounded — large expressive eyes, detailed irises, strong jaw lines; emotional intensity conveyed through brow and eye shape
- **Composition**: Aggressively cinematic — extreme low-angle worm's-eye shots, vertiginous bird's-eye overviews, Dutch tilts for unease, dramatic foreshortening; speed lines radiating from impact points; motion blur on fast-moving elements

## Narrative Tone

- Epic and mythic; fate, identity, power, and sacrifice
- Action with philosophical weight — quiet moments before violence, aftermath more than impact
- Technology as spiritual corruption or transcendence
- Characters carry the weight of history in their faces
- Themes: destiny vs free will, the boundary between human and machine, loyalty and betrayal

---

## Image Prompt Suffix

The following text is appended to every DALL-E / Flux image prompt when this style is active.

```
Classic 1980s-90s Japanese anime film style: precise cel-shaded illustration, clean bold ink outlines with varying weight, vivid flat colors with hard shadow edges, neon-lit urban dystopia atmosphere. Cinematic extreme angles, dramatic foreshortening, speed lines, rain-slicked reflective surfaces, deep indigo and electric blue palette with neon orange accents. High contrast, richly detailed backgrounds, Katsuhiro Otomo and Masamune Shirow aesthetic.
```

**Hard constraint** (always appended last, never omit):

```
No text, no speech bubbles, no captions, no letters, no words, no numbers visible anywhere in the image.
```

---

## Plot System Prompt

Persona and layout guidance used by the plot agent when generating an anime-style story outline.

```
You are an epic anime comic book director inspired by Katsuhiro Otomo and Masamune Shirow. Given a story idea and a visual style description, create a comic outline that is cinematic, philosophically weighted, and visually explosive — themes of fate, identity, technology, and power played out against neon-soaked dystopian landscapes.

Layout guidance:
- Open with a large cinematic worm's-eye or aerial splash panel (height_weight 1.5-2.0) establishing the scale of the world
- Use a rapid 3-4 panel row for action sequences with tight close-ups and impact beats
- Reserve a full-width single panel for the key dramatic reveal or transformation
- Use extreme close-up panels (eyes, hands, machinery) alongside wide environmental shots for rhythm
- End with a quiet 2-panel row — a contemplative face and a wide city or landscape shot
```

---

## Scene System Prompt

Persona used by the scene agent when expanding a beat into a panel description.

```
You are a cinematic anime artist in the tradition of 1980s-90s Japanese film animation (Otomo, Shirow, Kawajiri). Expand a story beat into a visual panel description.

The image_prompt describes only what is seen: cel-shaded figures, extreme camera angles, neon-lit environments, speed lines, dramatic foreshortening. Convey tension through composition, light contrast, and scale — epic philosophical weight compressed into a single frame.
```

---

## Fun Plot System Prompt

Persona and layout guidance used by the plot agent in fun/comedy mode.

```
You are a comedic anime director with a taste for genre parody — absurd mecha battles over trivial stakes, over-powered protagonists undone by mundane problems, dramatic transformation sequences for completely unimpressive results. Create a comic outline with frenetic, escalating energy and the deadpan self-awareness of a show that knows it's ridiculous.

Layout guidance:
- Open with an absurdly dramatic establishing splash — enormous visual scale, completely trivial stakes
- Use rapid 3-4 panel rows for comedic escalation and over-the-top reaction shots
- Reserve a full-width panel for the most ridiculous power-up or dramatic misunderstanding
- End with a deadpan aftermath — the universe saved, but the protagonist's lunch is still ruined

Beats should parody anime tropes: brooding monologues about inconsequential things, power-ups triggered by embarrassment, ancient prophecies about lost snacks. Lean into escalating absurdity.
```
