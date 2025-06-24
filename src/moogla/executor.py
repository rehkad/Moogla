from __future__ import annotations

"""Utilities for executing prompts against LLM providers."""

from typing import Optional
import os
from functools import lru_cache

import openai


class LLMExecutor:
    """Simple wrapper around the OpenAI client with optional caching."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        cache_size: Optional[int] = None,
    ) -> None:
        self.model = model
        self.client = openai.OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=api_base,
        )

        if cache_size is None:
            cache_size_env = os.getenv("MOOGLA_CACHE_SIZE")
            cache_size = int(cache_size_env) if cache_size_env else 128

        self._complete_cached = lru_cache(maxsize=cache_size)(self._complete)

    def _complete(self, prompt: str, max_tokens: int) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def complete(self, prompt: str, *, max_tokens: int = 16) -> str:
        """Return a completion for the given prompt."""
        return self._complete_cached(prompt, max_tokens)
