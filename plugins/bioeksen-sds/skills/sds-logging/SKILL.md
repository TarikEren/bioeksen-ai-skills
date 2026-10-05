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

Paths such as `sds-logging/references/log-record.md` name a file in another
skill of this plugin, relative to the plugin's skills directory: the parent
of `${CLAUDE_SKILL_DIR}`, which is this skill's own directory.

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
| `FATAL` | The app cannot serve traffic, or data integrity is at risk | Yes |

Rules:

- A handled, expected condition is not an `ERROR`. A rejected 400 request is
  `WARNING`, which its code fixes per **Derived attributes** in
  `references/code-prefixes.md`; it means the client misbehaved, not the app.
- A 5xx response MUST be logged at `ERROR` or higher.
- `FATAL` MUST correspond to something a person should act on now. If
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

`references/log-record.md` defines the mechanics: the `id` field naming the
emitting app, the `request=` value every record of one request shares, and the
`X-Request-Id` header that carries it between services. Three rules are
repeated here because they are the ones that get missed:

- The `id` is allocated, never guessed — supplied by the project or by the
  id-issuing service, and asked for when it has not been.
- `id` has nothing to do with the prefix of an error code. Prefixes name the
  *kind* of failure and are shared by every app, so one app emits several of
  them — see `references/error-codes.md`.
- When a request fails, the `code` in the API error response and the `code`
  field of the log record MUST be the same value.

Correlation identifiers and timestamp precision are the two things that cannot
be added to a record after it is written. Emit both from the first version.

## Transport

The aggregator is the only remote destination for an app's log records. An
app MUST NOT write to a shared log store, a hosted logging service, or any
other remote backend.

Two local destinations sit beside it, and neither is an integration point:

- An app MUST keep its own records in a local store for its retention window.
  That store is what `GET /api/admin/logs` reads, per
  `sds-api-design/references/standard-api-endpoints.md`, and what an operator
  falls back on when the aggregator is unreachable or its records are in doubt.
- An app MAY also write its records to stdout or stderr, as the JSON record or
  in the rendered form `references/log-record.md` defines, for a container
  runtime or a developer to read. Nothing in the estate consumes that output,
  and no alert or dashboard may depend on it.

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
- Map `FATAL` to a call that logs and returns, never to one that ends the
  process

`FATAL` means a person must act now while the app is still running — a pool
exhausted for over a minute, an app past its startup budget. Several libraries
give their fatal level a different meaning: in Go, `log.Fatal`,
`logrus.Fatal` and `zap`'s `Fatal` log and then call `os.Exit(1)`. Bound to
one of those, the severity that should page someone instead kills the process
that was about to recover, and turns a degraded app into a restart loop.

What a binding's own tests assert — no secret in any record, a code on every
failure record, a request unharmed by a down aggregator — is the Logging table
in `sds-testing/references/contract-tests.md`, written before the binding.

Split this section into `sds-<language>` skills once a second language is in
use; the contract above stays here.
