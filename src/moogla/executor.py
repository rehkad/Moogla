from __future__ import annotations

"""Utilities for executing prompts against LLM providers."""

from typing import Optional
import os

import openai


class LLMExecutor:
    """Simple wrapper around the OpenAI client."""

    def __init__(self, model: str, api_key: Optional[str] = None, api_base: Optional[str] = None) -> None:
        self.model = model
        self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), base_url=api_base)

    def complete(self, prompt: str, *, max_tokens: int = 16) -> str:
        """Return a completion for the given prompt."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
