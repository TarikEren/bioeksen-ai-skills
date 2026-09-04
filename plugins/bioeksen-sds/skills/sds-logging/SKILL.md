---
name: sds-logging
description: BioEksen logging and error code conventions. Use when adding log statements, choosing a severity or log type, defining or returning an error code, or wiring an app to the log aggregator.
---

# Logging and Error Codes

Every BioEksen app emits logs to the shared log aggregator and identifies its
failures with error codes. Both are cross-service contracts: an operator
filtering the aggregator, and a client handling an API error, depend on every
app behaving identically.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

- `references/log-record.md` — the record contract: fields, enumerations and
  emission rules. Normative.
- `references/error-codes.md` — error code format, ranges and HTTP mapping.
- `references/code-prefixes.md` — the closed list of every prefix and code.
  Codes are taken from here verbatim, never invented.
- `references/aggregator-api.md` — the aggregator's own endpoints.

## What to log

Log an event when it would help answer "what happened?" after the fact:

- Every request that fails (4xx and 5xx), with its error code
- Every state change to durable data (create, update, delete)
- Every authentication and authorization decision — as `SECURITY`
- Every scheduled job start, finish and failure — as `JOB`
- Startup, shutdown, and dependency status transitions

Do not log successful reads, per-iteration progress inside a loop, or anything
already visible in the `ACCESS` log.

## What MUST NOT be logged

The aggregator is shared across apps and retained. A secret written to it is
leaked to every operator and every backup.

- Passwords, tokens, API keys, session IDs, or `Authorization` header contents
- Full payment or identity numbers
- Request or response bodies in full — log the fields you actually need
- Personal data beyond the identifier needed to correlate the event

If a value must be referenced but not exposed, log a stable hash or the last
four characters, never the value.

## Choosing a severity

The severity set is defined in `references/log-record.md`. This table adds
selection guidance:

| Severity | Use when | Wakes someone |
|----------|----------|---------------|
| `DEBUG` | Detail useful only while diagnosing. MUST be disabled in production by default | No |
| `INFO` | A normal, noteworthy event: startup, job completed, resource created | No |
| `WARNING` | Degraded but handled: retry succeeded, fell back to a default, approaching a limit | No |
| `ERROR` | One operation failed and a user or job is affected. The app keeps running | Not immediately |
| `CRITICAL` | The app cannot serve traffic, or data integrity is at risk | Yes |

Rules:

- A handled, expected condition is not an `ERROR`. A rejected 400 request is
  `WARNING` at most; it means the client misbehaved, not the app.
- A 5xx response MUST be logged at `ERROR` or higher.
- `CRITICAL` MUST correspond to something a person should act on now. If
  nothing can be done about it, it is an `ERROR`.

## Choosing a type

| Type | Use for |
|------|---------|
| `APP` | General application behavior; the default when nothing else fits |
| `SECURITY` | Authentication, authorization, credential changes, suspected abuse |
| `AUDIT` | Deliberate record of who changed what, kept for accountability |
| `ACCESS` | Request-level records: method, path, status, duration |
| `JOB` | Scheduled and background work |

`SECURITY` and `AUDIT` overlap: use `SECURITY` when the interesting fact is
*whether access was granted*, and `AUDIT` when it is *what was changed*. A
failed login is `SECURITY`; a successful role change is both, and SHOULD be
logged twice rather than compromising on one.

## Correlation

- The `id` field is the emitting service, app or process. It MUST be stable
  across restarts and deployments, and MUST match the prefix used by that
  app's error codes — see `references/error-codes.md`.
- Every record produced while handling one request MUST carry the same
  `request=<id>` value in its structured tail, so a failure can be traced end
  to end — see `references/log-record.md`.
- When a request fails, the `code` in the API error response and the `code`
  field of the log record MUST be the same value.

Correlation identifiers and timestamp precision are the two things that cannot
be added to a record after it is written. Emit both from the first version.

## Transport

Apps emit to the log aggregator and to nothing else. An app MUST NOT write
directly to a log store, a hosted logging service, or any other backend.

The aggregator is the single integration point. It can change storage, gain a
forwarder, or grow a query layer without any app, in any language, changing a
line. An app that bypasses it converts one integration point into one per app
— the duplication this repository exists to prevent.

## Bindings

Library choice, logger configuration, error class hierarchies and framework
middleware are language-specific and are not defined here. Whatever the
language, the binding MUST:

- Emit records matching `references/log-record.md`
- Never let a logging failure fail the operation being logged
- Never block the request path on the aggregator being reachable

Split this section into `sds-<language>` skills once a second language is in
use; the contract above stays here.
