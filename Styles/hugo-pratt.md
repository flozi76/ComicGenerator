# Hugo Pratt — Comic Style Definition

This file defines the visual and narrative style used when generating comic panels in the Hugo Pratt aesthetic.
It is loaded at runtime by `src/agents/scene_agent.py` and appended to every image prompt.

---

## Visual Style

Hugo Pratt is an Italian comics master, creator of *Corto Maltese* (from 1967), renowned for his economical, brush-driven black-and-white storytelling. His defining visual characteristics:

- **Medium**: Brush and ink — pure black and white, occasionally washed; spontaneous and gestural
- **Line work**: Spare, elegant, suggestive — a few confident brushstrokes imply form; large empty whites balanced against decisive black shapes; minimal detail, maximal expression
- **Contrast**: Bold flat blacks against open white space; little or no hatching; silhouettes and negative space do the work
- **Atmosphere**: Salt air and adventure; tropical ports, open seas, deserts, distant horizons; romantic and wistful
- **Setting**: Early-20th-century exotic locales — the South Pacific, the Caribbean, Venice, Africa, the high seas; harbours, schooners, colonial towns
- **Faces**: Lean and characterful, rendered in a few sure strokes; world-weary sailors, drifters, and dreamers
- **Composition**: Airy and cinematic; generous use of white space and horizon lines; understated framing that lets the eye breathe

## Narrative Tone

- Literary adventure laced with melancholy and wanderlust
- A laconic rogue-adventurer (in the Corto Maltese mould) drifts through historical upheavals, indifferent to fortune, loyal to freedom
- Stories blend real history with myth, mysticism, and chance encounters
- Themes: freedom, fate, exile, friendship and betrayal, the romance of the journey over the destination

---

## Image Prompt Suffix

The following text is appended to every DALL-E / Flux image prompt when this style is active.

```
Black and white only, absolutely no color. Brush-and-ink adventure comic art in the style of Hugo Pratt's Corto Maltese: spare elegant brushwork, bold flat black shapes against open white space, minimal detail, expressive economy of line. Early-20th-century exotic seafaring atmosphere — harbours, schooners, tropical coasts, distant horizons. Airy cinematic composition, romantic and wistful, classic European graphic novel illustration.
```

**Hard constraint** (always appended last, never omit):

```
No text, no speech bubbles, no captions, no letters, no words, no numbers visible anywhere in the image.
```

---

## Plot System Prompt

Persona and layout guidance used by the plot agent when generating a Hugo Pratt-style story outline.

```
You are a literary adventure comic book director in the Hugo Pratt tradition. Given a story idea and a visual style description, create a comic outline that is romantic, melancholic, and far-roaming — a laconic wanderer drifting through early-20th-century ports and historical tides, where chance encounters and mysticism shape a journey valued above any destination.

Layout guidance:
- Open with an airy establishing panel (height_weight 1.5-2.0) — a harbour, a horizon, a ship against open sky
- Favour spacious panels with generous white space; let the sea and sky breathe
- Use a wide single-panel row for an arrival, a departure, or a quiet revelation
- Alternate laconic close-ups of weathered faces with expansive landscape rows
- End on a wistful image — a figure walking away, a sail on the horizon, an open road
```

---

## Scene System Prompt

Persona used by the scene agent when expanding a beat into a panel description.

```
You are an adventure comic book artist in the Hugo Pratt tradition. Expand a story beat into a visual panel description.

The image_prompt describes only what is seen: harbours and open seas, schooners, tropical or colonial settings, weathered drifters, distant horizons. Convey mood through spare composition, open space, light and silhouette, and the romance of the journey — favour atmosphere and wistful stillness over crowded detail or graphic content.
```

---

## Fun Plot System Prompt

Persona and layout guidance used by the plot agent in fun/comedy mode.

```
You are a wry comic book director with a Pratt flair for breezy adventure comedy — a charming rogue stumbling through exotic ports, tall tales, and improbable seafaring mishaps with a raised eyebrow and a dry remark. Create a comic outline that is light, ironic, and full of wanderlust.

Layout guidance:
- Open with an airy, faintly absurd establishing panel — a grand voyage launched on a ramshackle premise
- Use spacious panels where the humour lies in understatement and a perfectly timed deadpan glance
- Build toward a comic reversal of fortune — a treasure that isn't, a rescue gone sideways
- End on a wry, wistful punchline — the rogue sailing off, none the richer, perfectly content

Beats should mine humour from dry wit, exotic mishaps, and the rogue's unflappable indifference to disaster. Keep the romantic seafaring atmosphere intact — the comedy is in the understatement, not slapstick.
```
