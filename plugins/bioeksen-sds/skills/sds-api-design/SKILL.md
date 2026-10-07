---
name: sds-api-design
description: BioEksen API design conventions. Use when designing, reviewing or implementing an API — an HTTP endpoint, or a server-side function an app's own UI calls, such as a server action — and when writing a call to another service — timeouts, retries, circuit breakers and idempotency.
---

# API Design

These conventions govern every API an app exposes, whatever carries it: an
HTTP endpoint, or a server-side function the app's own UI calls through its
framework, such as a server action. The success and error envelopes, the codes
and their `details`, unknown input and lists apply to every one of them.
Status codes, methods, headers and paths apply where the API is HTTP; a server
action's result is the envelope itself.

An API written to them reads the same to every caller, whether that caller is
another service or the app's own page: a failure is a code and its `details`,
never a shape one framework happened to suggest.

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
- `references/app-endpoints.md` — every other endpoint an app serves: paths,
  the success body, lists, methods and unknown input.
- `references/service-calls.md` — the calling side: deadlines, timeouts, what
  may be retried, circuit breakers and idempotency.

Paths such as `sds-logging/references/log-record.md` name a file in another
skill of this plugin, relative to the plugin's skills directory: the parent
of `${CLAUDE_SKILL_DIR}`, which is this skill's own directory.

## Specialized Endpoints

App-specific endpoints have no shared schema, but MUST follow
`references/app-endpoints.md`, and the conventions they share with the
standard endpoints in `references/standard-api-endpoints.md`: the type and unit
table, correlation, the error envelope, rate limiting, and the 405, 413 and 415
responses.

They are also the versioned half of the estate: every app-specific path is
served under `/api/v{major}/`, and the four standard endpoints above are the
only unversioned ones. The rule, and the 90 day deprecation window a bump
carries, are in the same document.

An endpoint is written test-first, per `sds-testing/SKILL.md`: the cases its
tests contain — the envelope, the codes, the correlation header, the list
and method rules — are in `sds-testing/references/contract-tests.md`.
