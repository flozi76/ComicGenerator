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
        self._moderation = cfg.openai.image_moderation

    async def generate(self, prompt: str) -> bytes:
        import asyncio
        import base64
        import httpx

        # `moderation` is a gpt-image-* parameter; older models don't accept it.
        extra = {}
        if self._model.startswith("gpt-image"):
            extra["moderation"] = self._moderation

        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = await self._client.images.generate(
                    model=self._model,
                    prompt=prompt,
                    n=1,
                    size=self._size,
                    quality=self._quality,
                    **extra,
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
    """Black Forest Labs Flux via the BFL REST API (async poll pattern)."""

    _BASE = "https://api.bfl.ai/v1"

    def __init__(self, cfg: Config) -> None:
        self._api_key = cfg.black_forest_labs.api_key
        self._model = cfg.black_forest_labs.image_model  # e.g. "flux-pro-1.1"

    async def generate(self, prompt: str) -> bytes:
        import asyncio
        import httpx

        headers = {
            "x-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as http:
            # Submit generation task
            resp = await http.post(
                f"{self._BASE}/{self._model}",
                headers=headers,
                json={"prompt": prompt, "width": 1024, "height": 1024},
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                if resp.status_code == 429:
                    raise ImageClientError(f"Flux rate limit hit on submit — reduce max_concurrent_images in config.yml") from e
                raise ImageClientError(f"Flux submit error ({self._model}): {e}") from e

            submit_data = resp.json()
            polling_url = submit_data["polling_url"]

            # Poll until ready (max ~2 minutes)
            for _ in range(60):
                await asyncio.sleep(2)
                poll = await http.get(
                    polling_url,
                    headers=headers,
                )
                poll.raise_for_status()
                data = poll.json()
                status = data.get("status", "")

                if status == "Ready":
                    image_url = data["result"]["sample"]
                    img = await http.get(image_url, timeout=60)
                    img.raise_for_status()
                    return img.content

                if status in ("Error", "Failed", "Content Moderated", "Request Moderated"):
                    raise ImageClientError(f"Flux generation blocked/failed: status={status!r}")

        raise ImageClientError("Flux generation timed out after 120 seconds.")


class FalClient(ImageClient):
    """fal.ai aggregator via the queue REST API (async submit + poll).

    `image_model` is the full fal model path, e.g. 'fal-ai/flux/dev',
    'fal-ai/flux-pro/v1.1', or 'fal-ai/stable-diffusion-v35-large'. One client
    serves any of them — just change the path in config.
    """

    _BASE = "https://queue.fal.run"

    def __init__(self, cfg: Config) -> None:
        self._api_key = cfg.fal.api_key
        self._model = cfg.fal.image_model
        self._image_size = cfg.fal.image_size
        self._safety = cfg.fal.enable_safety_checker

    async def generate(self, prompt: str) -> bytes:
        import asyncio
        import httpx

        headers = {
            "Authorization": f"Key {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": prompt,
            "image_size": self._image_size,
            "num_images": 1,
            "enable_safety_checker": self._safety,
        }

        async with httpx.AsyncClient(timeout=120) as http:
            # Submit to the queue
            resp = await http.post(
                f"{self._BASE}/{self._model}",
                headers=headers,
                json=payload,
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                if resp.status_code == 429:
                    raise ImageClientError(
                        "fal rate limit hit on submit — reduce max_concurrent_images in config.yml"
                    ) from e
                raise ImageClientError(f"fal submit error ({self._model}): {e} — {resp.text}") from e

            submit = resp.json()
            status_url = submit["status_url"]
            response_url = submit["response_url"]

            # Poll status until COMPLETED (max ~2 minutes)
            for _ in range(60):
                await asyncio.sleep(2)
                poll = await http.get(status_url, headers=headers)
                poll.raise_for_status()
                status = poll.json().get("status", "")

                if status == "COMPLETED":
                    result = await http.get(response_url, headers=headers)
                    result.raise_for_status()
                    data = result.json()
                    images = data.get("images") or []
                    if not images:
                        raise ImageClientError(f"fal returned no images: {data}")
                    image_url = images[0]["url"]
                    img = await http.get(image_url, timeout=60)
                    img.raise_for_status()
                    return img.content

                if status not in ("IN_QUEUE", "IN_PROGRESS"):
                    raise ImageClientError(f"fal generation failed: status={status!r} — {poll.text}")

        raise ImageClientError("fal generation timed out after 120 seconds.")


def get_image_client(cfg: Config) -> ImageClient:
    provider = cfg.providers.image_provider
    if provider == "openai":
        return OpenAIImageClient(cfg)
    if provider == "black_forest_labs":
        return FluxClient(cfg)
    if provider == "fal":
        return FalClient(cfg)
    raise ValueError(
        f"Unknown image provider: {provider!r}. Choose 'openai', 'black_forest_labs', or 'fal'."
    )
