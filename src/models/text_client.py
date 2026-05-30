import json
import re
from abc import ABC, abstractmethod
from openai import AsyncOpenAI
from src.config import OpenAIConfig, AnthropicConfig


class TextClientError(Exception):
    pass


class TextClient(ABC):
    @abstractmethod
    async def chat(self, system: str, user: str, max_tokens: int = 8000) -> str: ...

    async def chat_json(self, system: str, user: str, max_tokens: int = 8000) -> dict:
        raw = await self.chat(system, user, max_tokens)
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        clean = re.sub(r",\s*([}\]])", r"\1", clean)
        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            raise TextClientError(f"Failed to parse JSON from model response: {e}\nRaw: {raw}") from e


class OpenAITextClient(TextClient):
    def __init__(self, cfg: OpenAIConfig) -> None:
        self._model = cfg.text_model
        self._client = AsyncOpenAI(api_key=cfg.api_key)

    async def chat(self, system: str, user: str, max_tokens: int = 8000) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as e:
            raise TextClientError(f"OpenAI text API error: {e}") from e
        return response.choices[0].message.content or ""


class AnthropicTextClient(TextClient):
    def __init__(self, cfg: AnthropicConfig) -> None:
        import anthropic
        self._model = cfg.text_model
        self._client = anthropic.AsyncAnthropic(api_key=cfg.api_key)

    async def chat(self, system: str, user: str, max_tokens: int = 8000) -> str:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as e:
            raise TextClientError(f"Anthropic text API error: {e}") from e
        return response.content[0].text


def get_text_client(provider: str, cfg) -> TextClient:
    if provider == "openai":
        return OpenAITextClient(cfg.openai)
    if provider == "anthropic":
        return AnthropicTextClient(cfg.anthropic)
    raise ValueError(f"Unknown text provider: {provider!r}. Choose 'openai' or 'anthropic'.")
