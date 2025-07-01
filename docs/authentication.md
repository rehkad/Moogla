# Authentication

Set `MOOGLA_API_KEY` to require a header named `X-API-Key` on requests.

```bash
export MOOGLA_API_KEY=secret
moogla serve
```

The API also provides `/register` and `/login` endpoints for JWT based
authentication. After registration, send the returned token in an
`Authorization: Bearer <token>` header.

Tokens are signed with `MOOGLA_JWT_SECRET`. If this variable is not set the
server generates a random value on startup, meaning issued tokens become
invalid after a restart. **Always set a persistent secret in production**,
especially when `MOOGLA_API_KEY` is configured, otherwise the server will
refuse to start.

`MOOGLA_TOKEN_EXP_MINUTES` configures the token lifetime in minutes. The
default is `30`.
The same value can be set on the command line with `--token-exp-minutes` when
running `moogla serve`.

User records are kept in an in-memory SQLite database by default. Set
`MOOGLA_DB_URL` to use a durable database so accounts survive server restarts.

Authenticated clients can list all users via `/users` and change
passwords using the `/change-password` endpoint. Both require either a
valid API key or JWT token.

Rate limiting can be enabled with `MOOGLA_RATE_LIMIT` and a Redis
connection via `MOOGLA_REDIS_URL`.
Set `MOOGLA_CORS_ORIGINS` to enable CORS for a comma separated list of origins.
