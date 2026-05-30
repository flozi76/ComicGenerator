import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

STYLES_DIR = Path("styles")


@dataclass
class StyleConfig:
    name: str
    image_suffix: str
    plot_persona: str
    scene_persona: str
    fun_plot_persona: str


def _section_block(text: str, heading: str) -> str:
    """Return the first fenced code block under a ## heading, or empty string."""
    heading_match = re.search(rf"(?m)^## {re.escape(heading)}", text)
    if not heading_match:
        return ""
    after = text[heading_match.end():]
    next_heading = re.search(r"(?m)^## ", after)
    section = after[: next_heading.start()] if next_heading else after
    block = re.search(r"```[^\n]*\n(.*?)```", section, re.DOTALL)
    return block.group(1).strip() if block else ""


def _all_blocks(text: str, heading: str) -> list[str]:
    """Return all fenced code blocks under a ## heading."""
    heading_match = re.search(rf"(?m)^## {re.escape(heading)}", text)
    if not heading_match:
        return []
    after = text[heading_match.end():]
    next_heading = re.search(r"(?m)^## ", after)
    section = after[: next_heading.start()] if next_heading else after
    return [b.strip() for b in re.findall(r"```[^\n]*\n(.*?)```", section, re.DOTALL)]


def load_style(style_name: str) -> StyleConfig:
    style_file = STYLES_DIR / f"{style_name}.md"
    if not style_file.exists():
        print(f"Warning: style file {style_file} not found — using empty style.")
        return StyleConfig(
            name=style_name,
            image_suffix="",
            plot_persona="You are a comic book director.",
            scene_persona="You are a comic book artist.",
            fun_plot_persona="You are a comedic comic book director.",
        )

    text = style_file.read_text()

    # Image suffix = all blocks under Image Prompt Suffix joined (suffix + hard constraint)
    image_blocks = _all_blocks(text, "Image Prompt Suffix")
    image_suffix = " ".join(image_blocks)

    plot_persona = _section_block(text, "Plot System Prompt")
    scene_persona = _section_block(text, "Scene System Prompt")
    fun_plot_persona = _section_block(text, "Fun Plot System Prompt")

    return StyleConfig(
        name=style_name,
        image_suffix=image_suffix,
        plot_persona=plot_persona or "You are a comic book director.",
        scene_persona=scene_persona or "You are a comic book artist.",
        fun_plot_persona=fun_plot_persona or plot_persona or "You are a comedic comic book director.",
    )
