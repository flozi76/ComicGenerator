from dataclasses import dataclass, field
from typing import List
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
class FalConfig:
    api_key: str = ""
    image_model: str = "fal-ai/flux/dev"   # full fal model path
    image_size: str = "square_hd"          # square_hd | square | portrait_4_3 | landscape_4_3 | ...
    enable_safety_checker: bool = False    # False = no NSFW filter (permissive); avoids blacked-out images
    music_enabled: bool = False            # True = generate background music for the panel reel
    music_model: str = "fal-ai/stable-audio-3/medium/text-to-audio"  # fal model for music generation


@dataclass
class InstagramConfig:
    enabled: bool = False                       # True = offer to publish after generation
    username: str = ""                          # Instagram handle
    password: str = ""                          # Instagram password
    session_file: str = "instagram_session.json"  # cached login session (avoids re-login/checkpoints)
    seconds_per_page: float = 3.0               # how long each page is shown in the reel
    publish_reel: bool = True                   # publish a slideshow reel of the pages
    publish_story: bool = True                  # publish each page as a story frame
    caption: str = "{title}\n\n{tagline}"       # caption template; {title} {tagline} are substituted


@dataclass
class TikTokConfig:
    """TikTok Content Posting API. Default 'inbox' mode uploads the reel to your
    TikTok drafts (no app review needed); you tap 'Post' in the app to publish."""
    enabled: bool = False
    client_key: str = ""                        # from developers.tiktok.com app
    client_secret: str = ""
    access_token: str = ""                       # filled by scripts/tiktok_login.py (or token_file)
    refresh_token: str = ""
    token_file: str = "tiktok_token.json"        # cached access/refresh token (preferred over the fields above)
    mode: str = "inbox"                          # inbox (draft, no review) | direct (public/SELF_ONLY, needs audit)
    seconds_per_page: float = 3.0                # how long each page is shown in the reel
    privacy_level: str = "SELF_ONLY"             # direct mode only: SELF_ONLY | PUBLIC_TO_EVERYONE | MUTUAL_FOLLOW_FRIENDS
    caption: str = "{title}\n\n{tagline}"        # caption template; {title} and {tagline} are substituted
    hashtags: List[str] = field(default_factory=list)  # appended to caption as #tag1 #tag2 …


@dataclass
class CompositorConfig:
    canvas_width: int = 2400
    canvas_height: int = 3200
    gap_px: int = 8
    margin_px: int = 24
    panel_seconds: float = 3.0


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
    fal: FalConfig
    compositor: CompositorConfig
    instagram: InstagramConfig
    tiktok: TikTokConfig
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
        if provider == "fal":
            return self.fal.image_model
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
    fal = FalConfig(
        api_key=raw.get("fal", {}).get("api_key", ""),
        image_model=raw.get("fal", {}).get("image_model", "fal-ai/flux/dev"),
        image_size=raw.get("fal", {}).get("image_size", "square_hd"),
        enable_safety_checker=raw.get("fal", {}).get("enable_safety_checker", False),
        music_enabled=raw.get("fal", {}).get("music_enabled", False),
        music_model=raw.get("fal", {}).get("music_model", "fal-ai/stable-audio-3/medium/text-to-audio"),
    )
    compositor = CompositorConfig(
        canvas_width=raw.get("compositor", {}).get("canvas_width", 2400),
        canvas_height=raw.get("compositor", {}).get("canvas_height", 3200),
        gap_px=raw.get("compositor", {}).get("gap_px", 8),
        margin_px=raw.get("compositor", {}).get("margin_px", 24),
        panel_seconds=raw.get("compositor", {}).get("panel_seconds", 3.0),
    )
    ig_raw = raw.get("instagram", {}) or {}
    instagram = InstagramConfig(
        enabled=ig_raw.get("enabled", False),
        username=ig_raw.get("username", ""),
        password=ig_raw.get("password", ""),
        session_file=ig_raw.get("session_file", "instagram_session.json"),
        seconds_per_page=ig_raw.get("seconds_per_page", 3.0),
        publish_reel=ig_raw.get("publish_reel", True),
        publish_story=ig_raw.get("publish_story", True),
        caption=ig_raw.get("caption", "{title}\n\n{tagline}"),
    )
    tt_raw = raw.get("tiktok", {}) or {}
    tiktok = TikTokConfig(
        enabled=tt_raw.get("enabled", False),
        client_key=tt_raw.get("client_key", ""),
        client_secret=tt_raw.get("client_secret", ""),
        access_token=tt_raw.get("access_token", ""),
        refresh_token=tt_raw.get("refresh_token", ""),
        token_file=tt_raw.get("token_file", "tiktok_token.json"),
        mode=tt_raw.get("mode", "inbox"),
        seconds_per_page=tt_raw.get("seconds_per_page", 3.0),
        privacy_level=tt_raw.get("privacy_level", "SELF_ONLY"),
        caption=tt_raw.get("caption", "{title}\n\n{tagline}"),
        hashtags=tt_raw.get("hashtags", []) or [],
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
    if providers.image_provider == "fal":
        if not fal.api_key:
            raise ValueError("fal.api_key is required when using the fal image provider.")

    # Note: TikTok credential checks happen at publish time (in publisher_tiktok),
    # not here — a missing token must never block comic generation.

    return Config(
        providers=providers,
        openai=openai_cfg,
        anthropic=anthropic,
        black_forest_labs=bfl,
        fal=fal,
        compositor=compositor,
        instagram=instagram,
        tiktok=tiktok,
        output_base_dir=output_base_dir,
    )
