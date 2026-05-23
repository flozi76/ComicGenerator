import json
from dataclasses import dataclass
from openai import OpenAI
from src.config import Config


LAYOUT_SCHEMA_EXAMPLE = """
{
  "type": "rows",
  "rows": [
    {
      "height_weight": 2.0,
      "panels": [{"panel_index": 0, "weight": 1.0}]
    },
    {
      "height_weight": 1.0,
      "panels": [
        {"panel_index": 1, "weight": 1.0},
        {"panel_index": 2, "weight": 1.5},
        {"panel_index": 3, "weight": 1.0}
      ]
    }
  ]
}
"""

PLOT_SYSTEM_PROMPT = f"""You are a horror/noir comic book director. Given a story idea and a visual style description, create a single-page comic outline.

Respond ONLY with a single compact JSON object — no markdown fences, no explanation.

The JSON must have exactly these fields:
{{
  "title": "short punchy story title",
  "tagline": "one dark sentence — the hook",
  "panel_count": <integer between 4 and 12>,
  "layout": <layout object — see schema below>,
  "beats": [
    {{"index": 0, "beat": "one short sentence describing what happens in this scene"}},
    ...
  ]
}}

LAYOUT SCHEMA — the weighted row system:
- layout.type is always "rows"
- layout.rows is an ordered top-to-bottom list of rows
- Each row has height_weight (float, proportional row height — 1.0 = equal share with others)
- Each row has panels: a left-to-right list of panels in that row
- Each panel has panel_index (0-based integer) and weight (float, proportional width in this row)
- panel_index values must cover exactly 0 to panel_count-1 with no duplicates or gaps

Layout example for 4 panels (splash + 3-grid):
{LAYOUT_SCHEMA_EXAMPLE}

Layout guidance:
- Open with a large splash panel (height_weight 1.5-2.0) for atmosphere
- Use tight 3-panel rows for action or rapid events
- Use a single wide panel for key horror reveals
- End on a quieter 2-panel close-up + establishing shot
- Match layout pacing to the story's rhythm

beats must have exactly panel_count items, indexed 0 to panel_count-1.
Each beat is ONE short sentence. Be concise and dark.
"""

FUN_PLOT_SYSTEM_PROMPT = f"""You are a comedic comic book director with a flair for absurdist humour and slapstick chaos. Given a story idea and a visual style description, create a single-page comic outline that is silly, unexpected, and fun.

Respond ONLY with a single compact JSON object — no markdown fences, no explanation.

The JSON must have exactly these fields:
{{
  "title": "short punchy comedic title",
  "tagline": "one ridiculous sentence — the joke hook",
  "panel_count": <integer between 4 and 12>,
  "layout": <layout object — see schema below>,
  "beats": [
    {{"index": 0, "beat": "one short sentence describing what happens in this scene"}},
    ...
  ]
}}

LAYOUT SCHEMA — the weighted row system:
- layout.type is always "rows"
- layout.rows is an ordered top-to-bottom list of rows
- Each row has height_weight (float, proportional row height — 1.0 = equal share with others)
- Each row has panels: a left-to-right list of panels in that row
- Each panel has panel_index (0-based integer) and weight (float, proportional width in this row)
- panel_index values must cover exactly 0 to panel_count-1 with no duplicates or gaps

Layout example for 4 panels (splash + 3-grid):
{LAYOUT_SCHEMA_EXAMPLE}

Layout guidance:
- Open with a large, ridiculous establishing panel (height_weight 1.5-2.0) that sets the absurd premise
- Use rapid-fire 3-panel rows for escalating chaos or comedic timing (setup / escalation / punchline)
- Use a single wide panel for the biggest gag or visual joke
- End on a funny twist or deadpan reaction shot
- Match layout pacing to comedic rhythm — fast beats for slapstick, slow beats for the punchline

beats must have exactly panel_count items, indexed 0 to panel_count-1.
Each beat is ONE short sentence. Lean into absurdity, misunderstandings, escalating chaos, and comic irony.
Avoid darkness; favour the ridiculous.
"""


@dataclass
class Beat:
    index: int
    beat: str


@dataclass
class Panel:
    panel_index: int
    weight: float


@dataclass
class Row:
    height_weight: float
    panels: list[Panel]


@dataclass
class Layout:
    type: str
    rows: list[Row]


@dataclass
class PlotResult:
    title: str
    title_slug: str
    tagline: str
    panel_count: int
    layout: Layout
    beats: list[Beat]
    style: str

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "title_slug": self.title_slug,
            "tagline": self.tagline,
            "panel_count": self.panel_count,
            "style": self.style,
            "layout": {
                "type": self.layout.type,
                "rows": [
                    {
                        "height_weight": row.height_weight,
                        "panels": [
                            {"panel_index": p.panel_index, "weight": p.weight}
                            for p in row.panels
                        ],
                    }
                    for row in self.layout.rows
                ],
            },
            "beats": [{"index": b.index, "beat": b.beat} for b in self.beats],
        }


def _parse_and_validate(data: dict, style: str) -> PlotResult:
    import re
    from slugify import slugify

    panel_count = int(data["panel_count"])
    if not (4 <= panel_count <= 12):
        raise ValueError(f"panel_count {panel_count} is outside 4-12 range")

    layout_data = data["layout"]
    rows = []
    all_indices = []
    for row_data in layout_data["rows"]:
        panels = [
            Panel(panel_index=p["panel_index"], weight=float(p["weight"]))
            for p in row_data["panels"]
        ]
        rows.append(Row(height_weight=float(row_data["height_weight"]), panels=panels))
        all_indices.extend(p.panel_index for p in panels)

    expected = set(range(panel_count))
    actual = set(all_indices)
    if actual != expected:
        raise ValueError(
            f"Layout panel indices {sorted(actual)} do not match expected {sorted(expected)}"
        )
    if len(all_indices) != panel_count:
        raise ValueError(f"Layout has {len(all_indices)} panels but panel_count is {panel_count}")

    beats_data = data["beats"]
    if len(beats_data) != panel_count:
        raise ValueError(f"beats count {len(beats_data)} != panel_count {panel_count}")

    beats = [Beat(index=b["index"], beat=b["beat"]) for b in beats_data]
    layout = Layout(type=layout_data.get("type", "rows"), rows=rows)

    title = data["title"]
    return PlotResult(
        title=title,
        title_slug=slugify(title, allow_unicode=False),
        tagline=data["tagline"],
        panel_count=panel_count,
        layout=layout,
        beats=beats,
        style=style,
    )


def run(idea: str, style_prompt: str, cfg: Config, style_name: str = "dylan-dog", fun: bool = False) -> PlotResult:
    import re
    client = OpenAI(api_key=cfg.openai.api_key)
    user_msg = f"Style:\n{style_prompt}\n\nStory idea:\n{idea}"
    system_prompt = FUN_PLOT_SYSTEM_PROMPT if fun else PLOT_SYSTEM_PROMPT

    last_error = None
    for attempt in range(2):
        response = client.chat.completions.create(
            model=cfg.openai.text_model,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = response.choices[0].message.content or ""
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        try:
            data = json.loads(clean)
            return _parse_and_validate(data, style=style_name)
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            last_error = e
            print(f"  [plot_agent] Attempt {attempt + 1} failed: {e} — retrying...")

    raise RuntimeError(f"Plot generation failed after 2 attempts. Last error: {last_error}")
