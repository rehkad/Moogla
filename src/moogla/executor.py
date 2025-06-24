from __future__ import annotations

"""Utilities for executing prompts against LLM providers."""

from typing import Optional
import os
from pathlib import Path
import asyncio

import openai


class LLMExecutor:
    """Simple wrapper around the OpenAI client."""

    def __init__(self, model: str, api_key: Optional[str] = None, api_base: Optional[str] = None) -> None:
        self.model = model
        self.client = None
        self.async_client = None
        self.generator = None
        self.llama = None

        key = api_key or os.getenv("OPENAI_API_KEY")

        model_path = Path(model)
        if model_path.exists() or "/" in model:
            if model_path.suffix in {".gguf", ".ggml", ".bin"}:
                try:
                    from llama_cpp import Llama
                except Exception as exc:  # pragma: no cover - optional dep
                    raise RuntimeError("llama-cpp-python required for GGUF models") from exc

                self.llama = Llama(model_path=str(model_path))
            else:
                try:
                    from transformers import pipeline
                except Exception as exc:  # pragma: no cover - optional dep
                    raise RuntimeError("transformers required for HuggingFace models") from exc

                self.generator = pipeline("text-generation", model=str(model_path))
        else:
            self.client = openai.OpenAI(api_key=key, base_url=api_base)
            self.async_client = openai.AsyncOpenAI(api_key=key, base_url=api_base)

    def complete(self, prompt: str, *, max_tokens: int = 16) -> str:
        """Return a completion for the given prompt."""
        if self.client:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        if self.generator:
            result = self.generator(prompt, max_new_tokens=max_tokens)
            return result[0]["generated_text"]
        if self.llama:
            result = self.llama(prompt, max_tokens=max_tokens)
            return result["choices"][0]["text"]
        raise RuntimeError("No LLM backend configured")

    async def acomplete(self, prompt: str, *, max_tokens: int = 16) -> str:
        """Asynchronously return a completion for the given prompt."""
        if self.async_client:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        # fall back to thread pool for sync models
        return await asyncio.to_thread(self.complete, prompt, max_tokens=max_tokens)
