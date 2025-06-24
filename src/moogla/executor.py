
"""Utilities for executing prompts against LLM providers."""

from __future__ import annotations

from typing import Optional
import os

import openai


class LLMExecutor:
    """Simple wrapper around the OpenAI client."""

    def __init__(self, model: str, api_key: Optional[str] = None, api_base: Optional[str] = None) -> None:
        self.model = model
        key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = openai.OpenAI(api_key=key, base_url=api_base)
        self.async_client = openai.AsyncOpenAI(api_key=key, base_url=api_base)

    def complete(self, prompt: str, *, max_tokens: int = 16) -> str:
        """Return a completion for the given prompt."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        assert content is not None
        return content

    async def acomplete(self, prompt: str, *, max_tokens: int = 16) -> str:
        """Asynchronously return a completion for the given prompt."""
        response = await self.async_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        assert content is not None
        return content
