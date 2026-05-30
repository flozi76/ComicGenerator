#!/usr/bin/env python3
import argparse
import asyncio
import json
import random
import string
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.agents import plot_agent, scene_agent
from src.compositor import compose
from src.config import load_config
from src.models.image_client import get_image_client
from src.models.text_client import TextClient

CONFIG_PATH = Path("config.yml")
STYLES_DIR = Path("Styles")


def load_style(style_name: str) -> str:
    style_file = STYLES_DIR / f"{style_name}.md"
    if not style_file.exists():
        print(f"Warning: style file {style_file} not found — using no style suffix.")
        return ""
    text = style_file.read_text()
    import re
    blocks = re.findall(r"```\n(.*?)```", text, re.DOTALL)
    if blocks:
        # First code block is the style suffix, second is the hard constraint
        return blocks[0].strip()
    return ""


def build_output_dir(base: Path, title_slug: str) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H%M%S")
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=3))
    folder = base / date_str / f"story_{time_str}_{title_slug}_{rand}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


async def run_pipeline(
    idea: str,
    style_name: str,
    cfg_path: Path,
    fun: bool = False,
    panel_count: Optional[int] = None,
) -> None:
    cfg = load_config(cfg_path)
    style_suffix = load_style(style_name)

    print(f"\n=== Comic Generator ===")
    print(f"Idea   : {idea}")
    print(f"Style  : {style_name}")
    print(f"Mode   : {'fun' if fun else 'noir'}")
    print(f"Panels : {panel_count if panel_count is not None else 'model decides (4-12)'}")
    print(f"Text   : {cfg.openai.text_model}")
    print(f"Images : {cfg.providers.active_image_provider}")
    print()

    # Step 1 — plot
    print("[1/3] Generating plot...")
    plot = plot_agent.run(
        idea, style_suffix, cfg, style_name=style_name, fun=fun, panel_count=panel_count
    )
    print(f"      Title     : {plot.title}")
    print(f"      Tagline   : {plot.tagline}")
    print(f"      Panels    : {plot.panel_count}")
    print(f"      Pages     : {len(plot.layout.pages)}")

    output_dir = build_output_dir(cfg.output_base_dir, plot.title_slug)
    print(f"      Output dir: {output_dir}")

    plot_path = output_dir / "plot.json"
    plot_path.write_text(json.dumps(plot.to_dict(), indent=2, ensure_ascii=False))

    # Step 2 — scenes (parallel)
    print(f"\n[2/3] Generating {plot.panel_count} scenes in parallel...")
    text_client = TextClient(cfg.openai)
    image_client = get_image_client(cfg)
    semaphore = asyncio.Semaphore(cfg.openai.max_concurrent_images)

    tasks = [
        scene_agent.run(
            beat=beat,
            plot=plot,
            cfg=cfg,
            output_dir=output_dir,
            text_client=text_client,
            image_client=image_client,
            semaphore=semaphore,
            style_suffix=style_suffix,
        )
        for beat in plot.beats
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    scenes = []
    failed = 0
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"  [scene {i + 1:02d}] FAILED: {result}")
            failed += 1
        else:
            scenes.append(result)

    print(f"      {len(scenes)} scenes generated, {failed} failed")

    # Step 3 — composite
    print(f"\n[3/3] Compositing panels into {len(plot.layout.pages)} page(s)...")
    scenes_sorted = sorted(scenes, key=lambda s: s.index)
    comic_paths = compose(plot, scenes_sorted, output_dir, cfg.compositor)
    for p in comic_paths:
        print(f"      Saved → {p}")

    print(f"\nDone! Output folder: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a noir/horror comic from a story idea."
    )
    parser.add_argument(
        "--idea",
        required=True,
        help="The story idea or premise for the comic.",
    )
    parser.add_argument(
        "--style",
        default="dylan-dog",
        choices=["dylan-dog", "milo-manara", "anime"],
        help="Visual style (default: dylan-dog).",
    )
    parser.add_argument(
        "--panels",
        type=int,
        default=None,
        metavar="N",
        help="Number of panels to generate (4-32). If not set, the model chooses (4-12).",
    )
    parser.add_argument(
        "--config",
        default="config.yml",
        help="Path to config YAML file. Default: config.yml",
    )
    parser.add_argument(
        "--fun",
        action="store_true",
        default=False,
        help="Switch to fun/comedy mode instead of horror/noir.",
    )
    args = parser.parse_args()

    if args.panels is not None and not (4 <= args.panels <= 32):
        print("Error: --panels must be between 4 and 32", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(
            run_pipeline(
                args.idea,
                args.style,
                Path(args.config),
                fun=args.fun,
                panel_count=args.panels,
            )
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)


if __name__ == "__main__":
    main()
