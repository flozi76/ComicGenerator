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
from src.models.text_client import get_text_client
from src.publisher import publish_to_instagram
from src.style import STYLES_DIR, load_style


def available_styles() -> list[str]:
    """Discover style names from the styles directory (filenames without .md)."""
    if not STYLES_DIR.exists():
        return []
    return sorted(p.stem for p in STYLES_DIR.glob("*.md"))


def build_output_dir(base: Path, title_slug: str) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H%M%S")
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=3))
    folder = base / date_str / f"story_{time_str}_{title_slug}_{rand}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _confirm_publish() -> bool:
    """Ask whether to publish to Instagram. Non-interactive stdin → no."""
    if not sys.stdin.isatty():
        return False
    try:
        answer = input("\nPublish to Instagram as reel + story? [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


async def run_pipeline(
    idea: str,
    style_name: str,
    cfg_path: Path,
    fun: bool = False,
    panel_count: Optional[int] = None,
    publish: Optional[bool] = None,
) -> None:
    cfg = load_config(cfg_path)
    style_config = load_style(style_name)
    plot_client = get_text_client(cfg.providers.plot_provider, cfg)
    scene_client = get_text_client(cfg.providers.scene_provider, cfg)
    image_client = get_image_client(cfg)

    print(f"\n=== Comic Generator ===")
    print(f"Idea   : {idea}")
    print(f"Style  : {style_name}")
    print(f"Mode   : {'fun' if fun else 'noir'}")
    print(f"Panels : {panel_count if panel_count is not None else 'model decides (4-12)'}")
    print(f"Plot   : {cfg.providers.plot_provider} ({cfg.text_model_name(cfg.providers.plot_provider)})")
    print(f"Scene  : {cfg.providers.scene_provider} ({cfg.text_model_name(cfg.providers.scene_provider)})")
    print(f"Images : {cfg.providers.image_provider} ({cfg.image_model_name(cfg.providers.image_provider)})")
    print()

    # Step 1 — plot
    print("[1/3] Generating plot...")
    plot = await plot_agent.run(
        idea, style_config, plot_client, fun=fun, panel_count=panel_count
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
    semaphore = asyncio.Semaphore(cfg.openai.max_concurrent_images)

    tasks = [
        scene_agent.run(
            beat=beat,
            plot=plot,
            cfg=cfg,
            output_dir=output_dir,
            text_client=scene_client,
            image_client=image_client,
            semaphore=semaphore,
            style_config=style_config,
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

    # Step 4 — optional Instagram publishing
    # `publish` overrides the prompt: True/False from CLI flags, None = ask.
    if publish is None:
        do_publish = cfg.instagram.enabled and _confirm_publish()
    else:
        do_publish = publish

    if do_publish:
        print("\n[4/4] Publishing to Instagram...")
        try:
            publish_to_instagram(plot, comic_paths, output_dir, cfg.instagram)
            print("      Published to Instagram.")
        except Exception as e:
            print(f"      Instagram publishing failed: {e}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a noir/horror comic from a story idea."
    )
    parser.add_argument(
        "--idea",
        required=True,
        help="The story idea or premise for the comic.",
    )
    styles = available_styles()
    parser.add_argument(
        "--style",
        default="dylan-dog",
        choices=styles or None,
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
    publish_group = parser.add_mutually_exclusive_group()
    publish_group.add_argument(
        "--publish",
        dest="publish",
        action="store_true",
        default=None,
        help="Publish to Instagram without prompting (reel + story).",
    )
    publish_group.add_argument(
        "--no-publish",
        dest="publish",
        action="store_false",
        help="Skip Instagram publishing without prompting.",
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
                publish=args.publish,
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
