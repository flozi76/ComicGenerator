from abc import ABC, abstractmethod
from openai import AsyncOpenAI
from src.config import Config


class ImageClientError(Exception):
    pass


class ImageClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> bytes:
        """Return raw PNG/JPEG bytes for the given prompt."""


class OpenAIImageClient(ImageClient):
    """Supports dall-e-3 (returns URL) and gpt-image-* models (return base64)."""

    def __init__(self, cfg: Config) -> None:
        self._client = AsyncOpenAI(api_key=cfg.openai.api_key)
        self._model = cfg.openai.image_model
        self._size = cfg.openai.image_size
        self._quality = cfg.openai.image_quality

    async def generate(self, prompt: str) -> bytes:
        import asyncio
        import base64
        import httpx

        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = await self._client.images.generate(
                    model=self._model,
                    prompt=prompt,
                    n=1,
                    size=self._size,
                    quality=self._quality,
                )
            except Exception as e:
                msg = str(e)
                if "rate_limit_exceeded" in msg and attempt < max_retries - 1:
                    wait = 15 * (attempt + 1)
                    print(f"    [image] Rate limit hit — waiting {wait}s before retry {attempt + 2}/{max_retries}...")
                    await asyncio.sleep(wait)
                    continue
                raise ImageClientError(f"Image generation error ({self._model}): {e}") from e

            item = response.data[0]
            # gpt-image-* models return base64; dall-e-3 returns a URL
            if item.b64_json:
                return base64.b64decode(item.b64_json)
            url = item.url
            async with httpx.AsyncClient(timeout=60) as http:
                r = await http.get(url)
                r.raise_for_status()
                return r.content

        raise ImageClientError(f"Image generation failed after {max_retries} attempts (rate limit).")


class FluxClient(ImageClient):
    """Stub for Black Forest Labs Flux Pro. Wire up when switching providers."""

    def __init__(self, cfg: Config) -> None:
        self._api_key = cfg.black_forest_labs.api_key
        self._model = cfg.black_forest_labs.model

    async def generate(self, prompt: str) -> bytes:
        # TODO: implement Flux Pro via httpx POST to https://api.bfl.ai/v1/image
        # Docs: https://docs.bfl.ml/quick_start/
        raise NotImplementedError(
            "Flux client not yet implemented. "
            "Set providers.active_image_provider: dall-e-3 in config.yml."
        )


def get_image_client(cfg: Config) -> ImageClient:
    provider = cfg.providers.active_image_provider
    if provider in ("dall-e-3", "openai"):
        return OpenAIImageClient(cfg)
    if provider == "flux":
        return FluxClient(cfg)
    raise ValueError(f"Unknown image provider: {provider!r}. Choose 'dall-e-3', 'openai', or 'flux'.")
