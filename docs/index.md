# Welcome to Moogla

Moogla is a local-first LLM runtime and orchestration framework. This
site contains user and developer documentation.

## Sections

- [Setup](setup.md)
- [Plugin Development](plugins.md)
- [Authentication](authentication.md)
- [Web UI](web_ui.md)

## Controlling Generation

Requests to ``/v1/completions`` and ``/v1/chat/completions`` may include
``max_tokens``, ``temperature`` and ``top_p`` fields to tweak the response.
