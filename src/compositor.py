from pathlib import Path
from dataclasses import dataclass
from PIL import Image

from src.agents.plot_agent import PlotResult
from src.agents.scene_agent import SceneResult
from src.config import CompositorConfig


@dataclass
class PanelBounds:
    panel_index: int
    page_num: int
    x: int
    y: int
    width: int
    height: int


def _letterbox(img: Image.Image, panel_w: int, panel_h: int) -> Image.Image:
    """Scale image to fit entirely inside the panel, filling gaps with black.

    Never crops — captions/bubbles at any edge are always preserved.
    Black fill bars are invisible on a dark noir comic background.
    """
    src_w, src_h = img.size
    scale = min(panel_w / src_w, panel_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    panel = Image.new("RGB", (panel_w, panel_h), color=(0, 0, 0))
    x_off = (panel_w - new_w) // 2
    y_off = (panel_h - new_h) // 2
    panel.paste(resized, (x_off, y_off))
    return panel


def _distribute(total: int, weights: list[float], gap: int) -> list[int]:
    """Convert weights to pixel sizes that sum exactly to total."""
    usable = total - gap * (len(weights) - 1)
    total_w = sum(weights)
    sizes = [int(w / total_w * usable) for w in weights]
    # assign leftover pixels to the last slot to absorb rounding error
    sizes[-1] = usable - sum(sizes[:-1])
    return sizes


def calculate_panel_bounds(
    plot: PlotResult,
    cfg: CompositorConfig,
) -> list[PanelBounds]:
    """Calculate pixel bounds for every panel in reading order."""
    canvas_w = cfg.canvas_width
    canvas_h = cfg.canvas_height
    gap = cfg.gap_px
    margin = cfg.margin_px

    bounds: list[PanelBounds] = []
    for page_num, page in enumerate(plot.layout.pages, start=1):
        row_heights = _distribute(
            canvas_h - 2 * margin,
            [r.height_weight for r in page.rows],
            gap,
        )

        y = margin
        for row, row_h in zip(page.rows, row_heights):
            panel_widths = _distribute(
                canvas_w - 2 * margin,
                [p.weight for p in row.panels],
                gap,
            )

            x = margin
            for panel_spec, panel_w in zip(row.panels, panel_widths):
                bounds.append(
                    PanelBounds(
                        panel_index=panel_spec.panel_index,
                        page_num=page_num,
                        x=x,
                        y=y,
                        width=panel_w,
                        height=row_h,
                    )
                )
                x += panel_w + gap

            y += row_h + gap

    return bounds


def compose(
    plot: PlotResult,
    scenes: list[SceneResult],
    output_dir: Path,
    cfg: CompositorConfig,
) -> list[Path]:
    scene_by_index = {s.index: s for s in scenes}
    layout = plot.layout

    canvas_w = cfg.canvas_width
    canvas_h = cfg.canvas_height
    gap = cfg.gap_px
    margin = cfg.margin_px

    out_paths = []
    for page_num, page in enumerate(layout.pages, start=1):
        canvas = Image.new("RGB", (canvas_w, canvas_h), color=(0, 0, 0))

        row_heights = _distribute(
            canvas_h - 2 * margin,
            [r.height_weight for r in page.rows],
            gap,
        )

        y = margin
        for row, row_h in zip(page.rows, row_heights):
            panel_widths = _distribute(
                canvas_w - 2 * margin,
                [p.weight for p in row.panels],
                gap,
            )

            x = margin
            for panel_spec, panel_w in zip(row.panels, panel_widths):
                scene = scene_by_index.get(panel_spec.panel_index)

                if scene and scene.image_path.exists():
                    img = Image.open(scene.image_path).convert("RGB")
                    panel_img = _letterbox(img, panel_w, row_h)
                else:
                    panel_img = Image.new("RGB", (panel_w, row_h), color=(30, 30, 30))

                canvas.paste(panel_img, (x, y))
                x += panel_w + gap

            y += row_h + gap

        out_path = output_dir / f"comic-{page_num:03d}.png"
        canvas.save(out_path, format="PNG", optimize=True)
        out_paths.append(out_path)

    return out_paths
