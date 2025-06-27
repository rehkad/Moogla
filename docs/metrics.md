# Metrics

Set `MOOGLA_METRICS=1` to expose a Prometheus compatible `/metrics` endpoint.
The server records request counts and latency for each route. Example:

```bash
export MOOGLA_METRICS=1
moogla serve
```

Query metrics with:

```bash
curl http://localhost:11434/metrics
```
