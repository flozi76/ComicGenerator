from pathlib import Path
from PIL import Image, ImageOps

from src.agents.plot_agent import PlotResult
from src.agents.scene_agent import SceneResult
from src.config import CompositorConfig


def compose(
    plot: PlotResult,
    scenes: list[SceneResult],
    output_dir: Path,
    cfg: CompositorConfig,
) -> Path:
    scene_by_index = {s.index: s for s in scenes}
    layout = plot.layout

    canvas_w = cfg.canvas_width
    canvas_h = cfg.canvas_height
    gap = cfg.gap_px
    margin = cfg.margin_px

    canvas = Image.new("L", (canvas_w, canvas_h), color=255)  # white greyscale

    num_rows = len(layout.rows)
    total_h_weight = sum(r.height_weight for r in layout.rows)
    usable_h = canvas_h - 2 * margin - gap * (num_rows - 1)

    y = margin
    for row in layout.rows:
        row_h = int(round((row.height_weight / total_h_weight) * usable_h))
        num_panels = len(row.panels)
        total_w_weight = sum(p.weight for p in row.panels)
        usable_w = canvas_w - 2 * margin - gap * (num_panels - 1)

        x = margin
        for panel_spec in row.panels:
            panel_w = int(round((panel_spec.weight / total_w_weight) * usable_w))
            scene = scene_by_index.get(panel_spec.panel_index)

            if scene and scene.image_path.exists():
                img = Image.open(scene.image_path)
                img = ImageOps.fit(img.convert("L"), (panel_w, row_h), Image.LANCZOS)
            else:
                # placeholder for missing/failed panels
                img = Image.new("L", (panel_w, row_h), color=30)

            canvas.paste(img, (x, y))
            x += panel_w + gap

        y += row_h + gap

    out_path = output_dir / "comic.png"
    canvas.save(out_path, format="PNG", optimize=True)
    return out_path
