# Local Models

Moogla can load GGUF or GGML files through `llama-cpp-python` as well as models from the Hugging Face hub. The `llama-cpp-python` package only exposes synchronous APIs. When the server runs with a local model, calls to `LLMExecutor.acomplete` are executed in a thread using `asyncio.to_thread`.

While this keeps the HTTP API asynchronous, heavy inference will still occupy a worker thread and may reduce overall concurrency. If you rely on high throughput you should consider an async capable backend such as OpenAI's API.
