from __future__ import annotations

"""Utilities for executing prompts against LLM providers."""

from typing import Optional
import os
import time
import logging

import openai
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# Prometheus metrics
completion_timer = Histogram(
    "openai_completion_seconds",
    "Time spent calling the OpenAI API",
)
completion_errors = Counter(
    "openai_errors_total",
    "Total OpenAI API errors",
)


class LLMExecutor:
    """Simple wrapper around the OpenAI client."""

    def __init__(self, model: str, api_key: Optional[str] = None, api_base: Optional[str] = None) -> None:
        self.model = model
        self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"), base_url=api_base)

    def complete(self, prompt: str, *, max_tokens: int = 16) -> str:
        """Return a completion for the given prompt."""
        start = time.perf_counter()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception:
            completion_errors.inc()
            logger.exception("OpenAI call failed")
            raise
        finally:
            duration = time.perf_counter() - start
            completion_timer.observe(duration)
