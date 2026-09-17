---
name: sds-api-design
description: BioEksen API design conventions. Use when designing, reviewing or implementing an HTTP API endpoint, and when writing a call to another service — timeouts, retries, circuit breakers and idempotency.
---

# API Design

Every API contains standard and specialized endpoints.

## Standard API Endpoints

Every app MUST expose these four, with identical paths and schemas:

| Endpoint | Is | Principal |
|----------|-----|-----------|
| `GET /api/health` | Full health report: process status, dependency checks, capacity numbers | Operator |
| `GET /api/health/live` | Liveness probe: is the process alive? Checks no dependency | None |
| `GET /api/health/ready` | Readiness probe: can this instance serve traffic now? What load balancers probe | None |
| `GET /api/admin/logs` | This app's logs, filtered and paginated | Operator |

All four MUST be served with `Cache-Control: no-store`. The principal column is
`sds-auth`'s; the schemas and status codes are in the references below.

- `references/standard-api-endpoints.md` — the conventions and the reasoning
  behind them.
- `references/openapi.yaml` — the normative OpenAPI 3.1 definition, takes precedence over the markdown.
- `references/service-calls.md` — the calling side: deadlines, timeouts, what
  may be retried, circuit breakers and idempotency.

## Specialized Endpoints

App-specific endpoints have no shared schema, but MUST follow the conventions in `references/standard-api-endpoints.md`: the type and unit table, the body `status` vs HTTP status code mapping, and the error envelope.

They are also the versioned half of the estate: every app-specific path is
served under `/api/v{major}/`, and the four standard endpoints above are the
only unversioned ones. The rule, and the 90 day deprecation window a bump
carries, are in the same document.
