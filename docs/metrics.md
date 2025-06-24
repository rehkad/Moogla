# Metrics

Moogla exposes Prometheus compatible metrics on the `/metrics` endpoint. The
endpoint uses the same authentication and rate limiting settings as the other
API routes.

The following metrics are provided:

- `moogla_requests_total` – count of handled requests labeled by path
- `moogla_request_latency_seconds` – request latency histogram
- `moogla_tokens_generated_total` – total number of tokens produced

Include your API key or JWT token when scraping the endpoint if authentication
is enabled.
