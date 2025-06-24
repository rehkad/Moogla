from __future__ import annotations

"""Utilities for executing prompts against LLM providers."""

import asyncio
import threading
from pathlib import Path
from typing import Optional

import openai


class LLMExecutor:
    """Simple wrapper around the OpenAI client."""

    def __init__(
        self, model: str, api_key: Optional[str] = None, api_base: Optional[str] = None
    ) -> None:
        self.model = model
        self.client = None
        self.async_client = None
        self.generator = None
        self.llama = None
        self.async_llama = None

        key = api_key

        model_path = Path(model)
        if model_path.exists() or "/" in model:
            if model_path.suffix in {".gguf", ".ggml", ".bin"}:
                try:
                    import llama_cpp  # type: ignore
                except Exception as exc:  # pragma: no cover - optional dep
                    raise RuntimeError(
                        "llama-cpp-python required for GGUF models"
                    ) from exc

                AsyncLlama = getattr(llama_cpp, "AsyncLlama", None)
                Llama = getattr(llama_cpp, "Llama", None)
                if AsyncLlama is not None:
                    self.async_llama = AsyncLlama(model_path=str(model_path))
                else:
                    if Llama is None:
                        raise RuntimeError("llama-cpp-python required for GGUF models")
                    self.llama = Llama(model_path=str(model_path))
            else:
                try:
                    from transformers import pipeline
                except Exception as exc:  # pragma: no cover - optional dep
                    raise RuntimeError(
                        "transformers required for HuggingFace models"
                    ) from exc

                self.generator = pipeline("text-generation", model=str(model_path))
        else:
            self.client = openai.OpenAI(api_key=key, base_url=api_base)
            self.async_client = openai.AsyncOpenAI(api_key=key, base_url=api_base)

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        """Return a completion for the given prompt."""
        if max_tokens is None:
            max_tokens = 16
        if temperature is None:
            temperature = 1.0
        if top_p is None:
            top_p = 1.0
        if self.client:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            return response.choices[0].message.content
        if self.generator:
            result = self.generator(prompt, max_new_tokens=max_tokens)
            return result[0]["generated_text"]
        if self.llama:
            result = self.llama(prompt, max_tokens=max_tokens)
            return result["choices"][0]["text"]
        raise RuntimeError("No LLM backend configured")

    def stream(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ):
        """Yield completion tokens for the given prompt."""
        if max_tokens is None:
            max_tokens = 16
        if temperature is None:
            temperature = 1.0
        if top_p is None:
            top_p = 1.0
        if self.client:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
            return

        if self.generator:
            try:
                from transformers import TextIteratorStreamer

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

    async def astream(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ):
        """Asynchronously yield completion tokens for the prompt."""
        if max_tokens is None:
            max_tokens = 16
        if temperature is None:
            temperature = 1.0
        if top_p is None:
            top_p = 1.0
        if self.async_client:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
            return

        if self.async_llama:
            result = await self.async_llama(
                prompt, max_tokens=max_tokens, stream=True
            )
            async for chunk in result:
                text = chunk.get("choices", [{}])[0].get("text")
                if text:
                    yield text
            return

        for token in self.stream(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        ):
            yield token

    async def acomplete(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        """Asynchronously return a completion for the given prompt."""
        if max_tokens is None:
            max_tokens = 16
        if temperature is None:
            temperature = 1.0
        if top_p is None:
            top_p = 1.0
        if self.async_client:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            return response.choices[0].message.content

        if self.async_llama:
            result = await self.async_llama(
                prompt, max_tokens=max_tokens
            )
            return result["choices"][0]["text"]

        # Some backends expose only synchronous APIs so local inference can
        # block the event loop. Run them in a thread.
        if self.llama or self.generator or self.client:
            return await asyncio.to_thread(
                self.complete,
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )

        raise RuntimeError("No LLM backend configured")
