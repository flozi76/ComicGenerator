from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class OpenAIConfig:
    api_key: str
    text_model: str = "gpt-4o"
    image_model: str = "gpt-image-1"
    image_size: str = "1024x1024"
    image_quality: str = "standard"
    image_moderation: str = "auto"  # gpt-image-* only: "auto" | "low"
    max_concurrent_images: int = 4


@dataclass
class AnthropicConfig:
    api_key: str = ""
    text_model: str = "claude-sonnet-4-6"


@dataclass
class BlackForestLabsConfig:
    api_key: str = ""
    image_model: str = "flux-pro-1.1"


@dataclass
class CompositorConfig:
    canvas_width: int = 2400
    canvas_height: int = 3200
    gap_px: int = 8
    margin_px: int = 24


@dataclass
class ProvidersConfig:
    plot_provider: str = "openai"     # provider used for plot generation
    scene_provider: str = "openai"    # provider used for scene descriptions
    image_provider: str = "openai"    # provider used for image generation


@dataclass
class Config:
    providers: ProvidersConfig
    openai: OpenAIConfig
    anthropic: AnthropicConfig
    black_forest_labs: BlackForestLabsConfig
    compositor: CompositorConfig
    output_base_dir: Path

    def text_model_name(self, provider: str) -> str:
        """Resolve a text provider name to the configured model it will run."""
        if provider == "openai":
            return self.openai.text_model
        if provider == "anthropic":
            return self.anthropic.text_model
        return provider

    def image_model_name(self, provider: str) -> str:
        """Resolve an image provider name to the configured model it will run."""
        if provider == "openai":
            return self.openai.image_model
        if provider == "black_forest_labs":
            return self.black_forest_labs.image_model
        return provider


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
        image_model=raw.get("openai", {}).get("image_model", "gpt-image-1"),
        image_size=raw.get("openai", {}).get("image_size", "1024x1024"),
        image_quality=raw.get("openai", {}).get("image_quality", "standard"),
        image_moderation=raw.get("openai", {}).get("image_moderation", "auto"),
        max_concurrent_images=raw.get("openai", {}).get("max_concurrent_images", 4),
    )

    providers = ProvidersConfig(
        plot_provider=raw.get("providers", {}).get("plot_provider", "openai"),
        scene_provider=raw.get("providers", {}).get("scene_provider", "openai"),
        image_provider=raw.get("providers", {}).get("image_provider", "openai"),
    )
    anthropic = AnthropicConfig(
        api_key=raw.get("anthropic", {}).get("api_key", ""),
        text_model=raw.get("anthropic", {}).get("text_model", "claude-sonnet-4-6"),
    )
    bfl = BlackForestLabsConfig(
        api_key=raw.get("black_forest_labs", {}).get("api_key", ""),
        image_model=raw.get("black_forest_labs", {}).get("image_model", "flux-pro-1.1"),
    )
    compositor = CompositorConfig(
        canvas_width=raw.get("compositor", {}).get("canvas_width", 2400),
        canvas_height=raw.get("compositor", {}).get("canvas_height", 3200),
        gap_px=raw.get("compositor", {}).get("gap_px", 8),
        margin_px=raw.get("compositor", {}).get("margin_px", 24),
    )
    output_base_dir = Path(raw.get("output", {}).get("base_dir", "output"))

    # Validate keys only for providers that are actually used
    text_providers = {providers.plot_provider, providers.scene_provider}
    if "openai" in text_providers or providers.image_provider == "openai":
        if not openai_cfg.api_key:
            raise ValueError("openai.api_key is required when using an OpenAI provider.")
    if "anthropic" in text_providers:
        if not anthropic.api_key:
            raise ValueError("anthropic.api_key is required when using Anthropic as a text provider.")
    if providers.image_provider == "black_forest_labs":
        if not bfl.api_key:
            raise ValueError("black_forest_labs.api_key is required when using the black_forest_labs image provider.")

    return Config(
        providers=providers,
        openai=openai_cfg,
        anthropic=anthropic,
        black_forest_labs=bfl,
        compositor=compositor,
        output_base_dir=output_base_dir,
    )
