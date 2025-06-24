# Authentication

Set `MOOGLA_API_KEY` to require a header named `X-API-Key` on requests.

```bash
export MOOGLA_API_KEY=secret
moogla serve
```

The API also provides `/register` and `/login` endpoints for JWT based
authentication. After registration, send the returned token in an
`Authorization: Bearer <token>` header.

Rate limiting can be enabled with `MOOGLA_RATE_LIMIT` and a Redis
connection via `MOOGLA_REDIS_URL`.
