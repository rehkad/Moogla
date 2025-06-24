from __future__ import annotations

"""Utilities for executing prompts against LLM providers."""

from typing import Optional
from pathlib import Path
import asyncio
import threading
from concurrent.futures import ProcessPoolExecutor

_worker_model = None
_worker_backend = None


def _worker_init(model_path: str, backend: str) -> None:
    """Load the local model inside a worker process."""
    global _worker_model, _worker_backend
    _worker_backend = backend
    if backend == "hf":
        from transformers import pipeline

        _worker_model = pipeline("text-generation", model=model_path)
    else:
        from llama_cpp import Llama

        _worker_model = Llama(model_path=str(model_path))


def _worker_complete(prompt: str, max_tokens: int) -> str:
    if _worker_backend == "hf":
        result = _worker_model(prompt, max_new_tokens=max_tokens)
        return result[0]["generated_text"]
    result = _worker_model(prompt, max_tokens=max_tokens)
    return result["choices"][0]["text"]

import openai


class LLMExecutor:
    """Simple wrapper around the OpenAI client."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        *,
        workers: int = 0,
    ) -> None:
        self.model = model
        self.client = None
        self.async_client = None
        self.generator = None
        self.llama = None
        self.async_llama = None
        self.pool: Optional[ProcessPoolExecutor] = None
        self._backend = None
        self._workers = workers

        key = api_key

        model_path = Path(model)
        if model_path.exists() or "/" in model:
            if model_path.suffix in {".gguf", ".ggml", ".bin"}:
                try:
                    from llama_cpp import Llama
                except Exception as exc:  # pragma: no cover - optional dep
                    raise RuntimeError("llama-cpp-python required for GGUF models") from exc

                try:  # pragma: no cover - optional dep
                    from llama_cpp import AsyncLlama as _AsyncLlama  # type: ignore
                except Exception:
                    _AsyncLlama = None

                if _AsyncLlama and workers == 0:
                    self.async_llama = _AsyncLlama(model_path=str(model_path))
                elif workers:
                    self._backend = "llama"
                    self.pool = ProcessPoolExecutor(
                        max_workers=workers,
                        initializer=_worker_init,
                        initargs=(str(model_path), "llama"),
                    )
                else:
                    self.llama = Llama(model_path=str(model_path))
            else:
                try:
                    from transformers import pipeline
                except Exception as exc:  # pragma: no cover - optional dep
                    raise RuntimeError("transformers required for HuggingFace models") from exc

                if workers:
                    self._backend = "hf"
                    self.pool = ProcessPoolExecutor(
                        max_workers=workers,
                        initializer=_worker_init,
                        initargs=(str(model_path), "hf"),
                    )
                else:
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
        if self.pool:
            return self.pool.submit(_worker_complete, prompt, max_tokens).result()
        if self.generator:
            result = self.generator(prompt, max_new_tokens=max_tokens)
            return result[0]["generated_text"]
        if self.llama:
            result = self.llama(prompt, max_tokens=max_tokens)
            return result["choices"][0]["text"]
        raise RuntimeError("No LLM backend configured")

    def stream(self, prompt: str, *, max_tokens: int = 16):
        """Yield completion tokens for the given prompt."""
        if self.client:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
            return

        if self.pool:
            text = self.pool.submit(_worker_complete, prompt, max_tokens).result()
            for ch in text:
                yield ch
            return

        if self.generator:
            try:
                from transformers import TextIteratorStreamer
                import torch

                streamer = TextIteratorStreamer(
                    self.generator.tokenizer, skip_prompt=True, skip_special_tokens=True
                )
                inputs = self.generator.tokenizer(prompt, return_tensors="pt")
                thread = threading.Thread(
                    target=self.generator.model.generate,
                    kwargs={
                        **inputs,
                        "max_new_tokens": max_tokens,
                        "streamer": streamer,
                    },
                )
                thread.start()
                for text in streamer:
                    yield text
                thread.join()
            except Exception:
                result = self.generator(prompt, max_new_tokens=max_tokens)
                yield result[0]["generated_text"]
            return

        if self.llama:
            result = self.llama(
                prompt, max_tokens=max_tokens, stream=True
            )  # type: ignore[arg-type]
            for chunk in result:
                text = chunk.get("choices", [{}])[0].get("text")
                if text:
                    yield text
            return

        raise RuntimeError("No LLM backend configured")

    async def astream(self, prompt: str, *, max_tokens: int = 16):
        """Asynchronously yield completion tokens for the prompt."""
        if self.async_client:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
            return

        if self.async_llama:
            async for chunk in self.async_llama(
                prompt, max_tokens=max_tokens, stream=True
            ):
                text = chunk.get("choices", [{}])[0].get("text")
                if text:
                    yield text
            return

        if self.pool:
            loop = asyncio.get_running_loop()
            text = await loop.run_in_executor(
                self.pool, _worker_complete, prompt, max_tokens
            )
            for ch in text:
                yield ch
            return

        for token in self.stream(prompt, max_tokens=max_tokens):
            yield token

    async def acomplete(self, prompt: str, *, max_tokens: int = 16) -> str:
        """Asynchronously return a completion for the given prompt."""
        if self.async_client:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

        if self.async_llama:
            result = await self.async_llama(prompt, max_tokens=max_tokens)
            return result["choices"][0]["text"]

        if self.pool:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                self.pool, _worker_complete, prompt, max_tokens
            )

        # ``llama_cpp`` exposes only synchronous APIs so local inference can
        # block the event loop.  Run any non-async backends in a thread.
        if self.llama or self.generator or self.client:
            return await asyncio.to_thread(
                self.complete, prompt, max_tokens=max_tokens
            )

        raise RuntimeError("No LLM backend configured")
