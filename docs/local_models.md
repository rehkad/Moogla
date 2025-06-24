# Local Models

Moogla can load GGUF or GGML files through `llama-cpp-python` as well as models from the Hugging Face hub. By default local inference runs in a thread via `asyncio.to_thread` which means heavy workloads block a worker thread.

You can launch additional processes to handle local inference with the `--workers` option or the `MOOGLA_WORKERS` environment variable. Each worker process loads the model independently which may improve throughput on multi-core systems. When an asynchronous API is available from `llama_cpp` it will be used automatically instead of spawning workers.
