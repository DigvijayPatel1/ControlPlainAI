"""Provider-independent OpenAI chat completion adapter."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass(slots=True)
class ProviderResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class OpenAIProvider:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not settings.OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY is not configured.")
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise RuntimeError("OpenAI support is not installed.") from exc
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def generate(
        self,
        *,
        prompt: str,
        context: str | None = None,
        model: str | None = None,
    ) -> ProviderResponse:
        selected_model = model or settings.OPENAI_MODEL
        messages: list[dict[str, str]] = []
        if context:
            messages.append({"role": "system", "content": f"Use this grounding context when answering:\n\n{context}"})
        messages.append({"role": "user", "content": prompt})
        response = await self._get_client().chat.completions.create(
            model=selected_model,
            messages=messages,
        )
        usage = response.usage
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", 0) or prompt_tokens + completion_tokens)
        return ProviderResponse(
            content=response.choices[0].message.content or "",
            model=selected_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )


openai_provider = OpenAIProvider()
