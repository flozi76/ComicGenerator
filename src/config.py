from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class OpenAIConfig:
    api_key: str
    text_model: str = "gpt-4o"
    image_model: str = "dall-e-3"
    image_size: str = "1024x1024"
    image_quality: str = "standard"
    max_concurrent_images: int = 4


@dataclass
class AnthropicConfig:
    api_key: str = ""


@dataclass
class BlackForestLabsConfig:
    api_key: str = ""
    model: str = "flux-pro"


@dataclass
class CompositorConfig:
    canvas_width: int = 2400
    canvas_height: int = 3200
    gap_px: int = 8
    margin_px: int = 24


@dataclass
class ProvidersConfig:
    active_text_provider: str = "openai"
    active_image_provider: str = "dall-e-3"


@dataclass
class Config:
    providers: ProvidersConfig
    openai: OpenAIConfig
    anthropic: AnthropicConfig
    black_forest_labs: BlackForestLabsConfig
    compositor: CompositorConfig
    output_base_dir: Path


def load_config(path: Path = Path("config.yml")) -> Config:
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            f"Copy config.example.yml to config.yml and fill in your API key."
        )
    with open(path) as f:
        raw = yaml.safe_load(f)

    openai_cfg = OpenAIConfig(
        api_key=raw.get("openai", {}).get("api_key", ""),
        text_model=raw.get("openai", {}).get("text_model", "gpt-4o"),
        image_model=raw.get("openai", {}).get("image_model", "dall-e-3"),
        image_size=raw.get("openai", {}).get("image_size", "1024x1024"),
        image_quality=raw.get("openai", {}).get("image_quality", "standard"),
        max_concurrent_images=raw.get("openai", {}).get("max_concurrent_images", 4),
    )
    if not openai_cfg.api_key:
        raise ValueError(
            "openai.api_key is empty in config.yml. "
            "Add your OpenAI API key to continue."
        )

    providers = ProvidersConfig(
        active_text_provider=raw.get("providers", {}).get("active_text_provider", "openai"),
        active_image_provider=raw.get("providers", {}).get("active_image_provider", "dall-e-3"),
    )
    anthropic = AnthropicConfig(api_key=raw.get("anthropic", {}).get("api_key", ""))
    bfl = BlackForestLabsConfig(
        api_key=raw.get("black_forest_labs", {}).get("api_key", ""),
        model=raw.get("black_forest_labs", {}).get("model", "flux-pro"),
    )
    compositor = CompositorConfig(
        canvas_width=raw.get("compositor", {}).get("canvas_width", 2400),
        canvas_height=raw.get("compositor", {}).get("canvas_height", 3200),
        gap_px=raw.get("compositor", {}).get("gap_px", 8),
        margin_px=raw.get("compositor", {}).get("margin_px", 24),
    )
    output_base_dir = Path(raw.get("output", {}).get("base_dir", "output"))

    return Config(
        providers=providers,
        openai=openai_cfg,
        anthropic=anthropic,
        black_forest_labs=bfl,
        compositor=compositor,
        output_base_dir=output_base_dir,
    )
