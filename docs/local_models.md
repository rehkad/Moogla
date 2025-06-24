# Local Models

Moogla can load GGUF or GGML files through `llama-cpp-python` as well as models
from the Hugging Face hub. Older releases of `llama-cpp-python` expose only
synchronous APIs. In that case `LLMExecutor.acomplete` falls back to
`asyncio.to_thread` to keep the HTTP API responsive.

Recent versions provide an `AsyncLlama` class which Moogla will use
automatically when available. This avoids blocking the event loop when running
local models.

While `asyncio.to_thread` keeps the API asynchronous, heavy inference will still
occupy a worker thread and may reduce overall concurrency. If you rely on high
throughput you should consider an async capable backend such as OpenAI's API.
