import json
import re
from openai import AsyncOpenAI
from src.config import OpenAIConfig


class TextClientError(Exception):
    pass


class TextClient:
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

    async def chat_json(self, system: str, user: str, max_tokens: int = 8000) -> dict:
        raw = await self.chat(system, user, max_tokens)
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        # GPT-4o sometimes emits trailing commas — strip them before parsing
        clean = re.sub(r",\s*([}\]])", r"\1", clean)
        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            raise TextClientError(f"Failed to parse JSON from model response: {e}\nRaw: {raw}") from e
