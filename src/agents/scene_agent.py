import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from src.agents.plot_agent import Beat, PlotResult, Row
from src.config import Config
from src.models.image_client import ImageClient, ImageClientError
from src.models.text_client import TextClient, TextClientError

SCENE_SYSTEM_PROMPT = """You are a noir comic book artist. Expand a story beat into a visual panel description.

Respond ONLY with compact JSON, no markdown fences:
{
  "caption": "one short atmospheric narration sentence",
  "dialogue": "one short spoken line, or empty string if none",
  "image_prompt": "visual scene description under 50 words — focus on setting, lighting, character expression, and mood. Avoid explicit violence; convey tension atmospherically."
}

The image_prompt describes only what is seen: composition, environment, mood, camera angle. Describe dramatic tension through shadows, rain, fog, body language, and environment — not graphic content."""



@dataclass
class SceneResult:
    index: int
    caption: str
    dialogue: str
    image_prompt: str
    image_path: Path


def _aspect_hint(beat_index: int, plot: PlotResult) -> str:
    """Prepend a composition hint based on the panel's aspect ratio in the layout."""
    for row in plot.layout.rows:
        for panel in row.panels:
            if panel.panel_index == beat_index:
                total_w = sum(p.weight for p in row.panels)
                panel_w_ratio = panel.weight / total_w
                row_total_h = sum(r.height_weight for r in plot.layout.rows)
                row_h_ratio = row.height_weight / row_total_h
                aspect = panel_w_ratio / row_h_ratio
                if aspect < 0.6:
                    return "Tall vertical composition. "
                if aspect > 1.8:
                    return "Wide horizontal panoramic composition. "
                return ""
    return ""


async def run(
    beat: Beat,
    plot: PlotResult,
    cfg: Config,
    output_dir: Path,
    text_client: TextClient,
    image_client: ImageClient,
    semaphore: asyncio.Semaphore,
    style_suffix: str,
) -> SceneResult:
    print(f"  [scene {beat.index + 1:02d}] Generating text...")

    user_msg = (
        f'Story: "{plot.title}" — {plot.tagline}\n'
        f"Scene {beat.index + 1} of {plot.panel_count}: {beat.beat}"
    )

    scene_data = await text_client.chat_json(SCENE_SYSTEM_PROMPT, user_msg, max_tokens=500)

    caption = scene_data.get("caption", "")
    dialogue = scene_data.get("dialogue", "")
    image_prompt_base = scene_data.get("image_prompt", beat.beat)

    aspect_hint = _aspect_hint(beat.index, plot)

    text_elements = []
    if caption:
        text_elements.append(f'Caption bar at the bottom of the panel with the text: "{caption}"')
    if dialogue:
        text_elements.append(f'A comic speech bubble in the upper area with the text: "{dialogue}"')
    text_instruction = " ".join(text_elements) if text_elements else ""

    full_prompt = f"{aspect_hint}{image_prompt_base}. {style_suffix} {text_instruction}".strip()

    print(f"  [scene {beat.index + 1:02d}] Generating image...")
    async with semaphore:
        image_bytes = await image_client.generate(full_prompt)

    image_path = output_dir / f"scene_{beat.index + 1:02d}.png"
    image_path.write_bytes(image_bytes)
    print(f"  [scene {beat.index + 1:02d}] Done → {image_path.name}")

    return SceneResult(
        index=beat.index,
        caption=caption,
        dialogue=dialogue,
        image_prompt=full_prompt,
        image_path=image_path,
    )
