import json
from dataclasses import dataclass
from typing import Optional
from src.style import StyleConfig
from src.models.text_client import TextClient


LAYOUT_SCHEMA_EXAMPLE = """
{
  "type": "pages",
  "pages": [
    {
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
  ]
}
"""

_LAYOUT_SCHEMA_DESCRIPTION = f"""
LAYOUT SCHEMA — the weighted multi-page system:
- layout.type is always "pages"
- layout.pages is an ordered list of comic pages
- Each page has a "rows" list — ordered top-to-bottom rows on that page
- Each row has height_weight (float, proportional row height on its page — 1.0 = equal share)
- Each row has panels: a left-to-right list of panels
- Each panel has panel_index (0-based integer, globally unique across all pages) and weight (float, proportional width in the row)
- panel_index values must cover exactly 0 to panel_count-1 with no duplicates or gaps
- Use multiple pages only when panel_count exceeds 10; keep 4–10 panels per page

Layout example for 4 panels on a single page (splash + 3-grid):
{LAYOUT_SCHEMA_EXAMPLE}"""

_PLOT_SYSTEM_STRUCTURE = """
Respond ONLY with a single compact JSON object — no markdown fences, no explanation.

The JSON must have exactly these fields:
{{
  "title": "short punchy story title",
  "tagline": "one sentence — the hook",
  "panel_count": <integer — see instruction in user message>,
  "layout": <layout object — see schema below>,
  "beats": [
    {{"index": 0, "beat": "one short sentence describing what happens in this scene"}},
    ...
  ]
}}

{layout_schema}

beats must have exactly panel_count items, indexed 0 to panel_count-1.
Each beat is ONE short sentence.
"""


def _build_plot_system_prompt(persona: str) -> str:
    return f"{persona}\n{_PLOT_SYSTEM_STRUCTURE.format(layout_schema=_LAYOUT_SCHEMA_DESCRIPTION)}"


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
class Page:
    rows: list[Row]


@dataclass
class Layout:
    type: str
    pages: list[Page]


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
                "pages": [
                    {
                        "rows": [
                            {
                                "height_weight": row.height_weight,
                                "panels": [
                                    {"panel_index": p.panel_index, "weight": p.weight}
                                    for p in row.panels
                                ],
                            }
                            for row in page.rows
                        ]
                    }
                    for page in self.layout.pages
                ],
            },
            "beats": [{"index": b.index, "beat": b.beat} for b in self.beats],
        }


def _parse_and_validate(data: dict, style: str, forced_panel_count: Optional[int] = None) -> PlotResult:
    from slugify import slugify

    panel_count = int(data["panel_count"])
    if forced_panel_count is not None:
        if panel_count != forced_panel_count:
            raise ValueError(
                f"Model returned panel_count={panel_count} but --panels={forced_panel_count} was requested"
            )
    else:
        if not (4 <= panel_count <= 12):
            raise ValueError(f"panel_count {panel_count} is outside 4-12 range")

    layout_data = data["layout"]

    # Accept both new pages format and legacy rows-only format
    if "pages" in layout_data:
        pages_data = layout_data["pages"]
    elif "rows" in layout_data:
        pages_data = [{"rows": layout_data["rows"]}]
    else:
        raise ValueError("layout must have either 'pages' or 'rows'")

    pages = []
    all_indices = []
    for page_data in pages_data:
        rows = []
        for row_data in page_data["rows"]:
            panels = [
                Panel(panel_index=p["panel_index"], weight=float(p["weight"]))
                for p in row_data["panels"]
            ]
            rows.append(Row(height_weight=float(row_data["height_weight"]), panels=panels))
            all_indices.extend(p.panel_index for p in panels)
        pages.append(Page(rows=rows))

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
    layout = Layout(type="pages", pages=pages)

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


async def run(
    idea: str,
    style_config: StyleConfig,
    text_client: TextClient,
    fun: bool = False,
    panel_count: Optional[int] = None,
) -> PlotResult:
    import re
    persona = style_config.fun_plot_persona if fun else style_config.plot_persona
    system_prompt = _build_plot_system_prompt(persona)

    if panel_count is not None:
        approx_pages = max(1, (panel_count + 7) // 8)
        if approx_pages == 1:
            panel_instruction = f"\nGenerate EXACTLY {panel_count} panels on a single page."
        else:
            panel_instruction = (
                f"\nGenerate EXACTLY {panel_count} panels distributed across {approx_pages} pages "
                f"(4–10 panels per page). Each page should have a complete visual composition."
            )
    else:
        panel_instruction = "\nChoose panel_count as an integer between 4 and 12 to best fit the story pacing. Use a single page."

    user_msg = f"Story idea:\n{idea}{panel_instruction}"

    last_error = None
    for attempt in range(2):
        try:
            raw = await text_client.chat(system_prompt, user_msg, max_tokens=2000)
            clean = re.sub(r"```(?:json)?|```", "", raw).strip()
            data = json.loads(clean)
            return _parse_and_validate(data, style=style_config.name, forced_panel_count=panel_count)
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            last_error = e
            print(f"  [plot_agent] Attempt {attempt + 1} failed: {e} — retrying...")

    raise RuntimeError(f"Plot generation failed after 2 attempts. Last error: {last_error}")
