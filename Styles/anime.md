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

## Layout Guidance for Plot Agent

When generating panel layouts for anime–style stories:
- Open with a large cinematic worm's-eye or aerial splash panel (height_weight 1.5–2.0) establishing the scale of the world
- Use a rapid 3–4 panel row for action sequences with tight close-ups and impact beats
- Reserve a full-width single panel for the key dramatic reveal or transformation
- Use extreme close-up panels (eyes, hands, machinery) alongside wide environmental shots to build rhythm
- End with a quiet 2-panel row — a contemplative face and a wide city/landscape shot
