# Log Record

This document is the normative definition of a BioEksen log record: its
fields, its enumerated values, and the rules an emitting app MUST follow. The
aggregator endpoints that carry these records are in `aggregator-api.md`.

## Fields

| Field | Type | Rules |
|-------|------|-------|
| `id` | string | The emitting service, app or process. Stable across restarts and deployments. Lowercase, `-` separated, e.g. `auth-service` |
| `timestamp` | string | RFC 3339 with offset and at least millisecond precision, e.g. `2026-09-03T14:05:00.123Z`. MUST be the time the event occurred, not the time it was submitted |
| `severity` | enum | See below |
| `type` | enum | See below |
| `code` | string \| null | The error code identifying the failure, per `error-codes.md`. `null` when the record does not describe a failure. REQUIRED when `severity` is `ERROR` or `FATAL` |
| `message` | string | See below |

The same six fields are what an app's own `GET /api/admin/logs` returns — see
`sds-api-design/references/standard-api-endpoints.md`.

These six are the record as *emitted*. A store that keeps records MAY add its
own identifier for the stored row, which is assigned on write and never
submitted: the aggregator returns one as `recordId`, per `aggregator-api.md`.
Such an identifier is detail, not a dimension — see below — and MUST NOT be
confused with `id`, which names the emitting app.

### Allocating an id

This is the normative rule for the value, which `sds-commit` reuses as the
`{software-id}` half of a change identifier — see
`sds-commit/references/release-notes.md`.

- The id is **supplied**: by the project itself, or by the id-issuing service
  once one exists. It is never derived from a repository name, a directory
  name, or anything else at the point of use.
- When it has not been supplied, **ask for it**. An assistant or generator MUST
  NOT invent one, and MUST NOT fall back to a plausible-looking guess.
- Format: `[a-z0-9-]`, lowercase, `-` separated, e.g. `auth-service`.
- Once allocated it is permanent. Changing it severs every existing log record
  and release-note entry from the service that produced them.

A guessed id is worse than a missing one. It looks correct, so nothing flags
it, and the records it labels are filed under a service that does not exist —
while the real service's records are split across two names.

`id` bears no relation to an error code prefix. Prefixes name the kind of
failure and are shared across the estate, so every app emits many of them; see
`error-codes.md`.

### Severity

`DEBUG` | `INFO` | `WARNING` | `ERROR` | `FATAL`

Guidance on choosing between them is in `SKILL.md`.

### Type

`APP` | `SECURITY` | `AUDIT` | `ACCESS` | `JOB`

Guidance on choosing between them is in `SKILL.md`.

Both sets are closed. Adding a value is a change to this document and to every
consumer; changing what an existing value *means* is not permitted at all.

### Why millisecond precision is required

Whole-second timestamps cannot be repaired after the fact. Records sharing a
second have no defined order, and nothing downstream can reconstruct one —
which is exactly the situation during an incident, when records cluster. The
precision has to be captured at emission or it is gone permanently.
Milliseconds are the minimum; finer costs nothing and is welcome.

## Message

The message is the only free-text field, which makes it the field most likely
to become unusable. It MUST:

- Begin with the prose fixed by the record's `code`, derived exactly as
  **Derived attributes** in `code-prefixes.md` specifies under *Message prose*
  — that rule is normative for the derivation. A record with no code states what happened in the past
  tense as a fact: `"job completed"`, not `"completing job"`
- Carry all varying values in a structured tail, so the prose prefix stays
  constant and greppable — see below
- Contain no newlines. The rendered form is one line per record
- Not repeat the error code. It has its own field precisely so that filtering
  never depends on parsing free text
- Contain nothing from the forbidden list in `SKILL.md`

## Structured tail

Everything variable goes at the end of the message as `logfmt`: space
separated `key=value` pairs, after the human-readable prose.

```
credential expired user=3f9a request=8c21 attempts=3
upstream timed out request=8c21 target="billing-service" waited_ms=3000
```

Rules:

- Keys MUST be lowercase `[a-z0-9_]`, and unique within one record
- A value containing a space, `=` or `"` MUST be wrapped in double quotes,
  with `"` and `\` backslash-escaped inside
- An empty value is written `key=""`
- Pairs MUST come last; no prose after the first pair

The point of the format is that the constant part of every occurrence is
identical, so records group by prefix, and the variable part is machine
readable without writing a regex per message. Any log tooling that can parse
`logfmt` or key-value pairs — which is most of it — gets the fields for free.

## Correlation

- Every record emitted while handling one request MUST carry `request=<id>` in
  the structured tail, using the same value for the whole request, including
  in calls to other BioEksen services.
- The identifier travels between services in the `X-Request-Id` header.
- Background work uses `job=<run id>` in place of `request=`.
- A record describing a retried outbound call carries `attempt=<n>`, counting
  from 1, so the attempts of one logical call are distinguishable while sharing
  a `request=` value. See `sds-api-design/references/service-calls.md`.
- When a request fails, the `code` in the API error response and the `code`
  field of the log record MUST be the same value.

### `X-Request-Id`

```
X-Request-Id: 8c21f3a94e7b1d05
```

- A service receiving a request with `X-Request-Id` MUST adopt that value as
  its `request=` value. Absent or malformed, it MUST generate one.
- Every outbound call to another BioEksen service MUST carry the value it
  adopted, so one identifier spans the whole call tree.
- Every response MUST echo `X-Request-Id`, including error responses. Without
  the echo, a caller reporting a failure cannot name the request an operator
  needs to search for.
- The value is opaque: `[A-Za-z0-9_-]`, 1 to 128 characters. It SHOULD carry at
  least 64 bits of entropy — a UUID or 16 hex characters. Examples throughout
  these documents shorten it for readability.
- It MUST NOT be trusted as input: it is echoed and logged, never used to
  authorize, address a resource, or build a query. Reject a malformed value by
  generating a fresh one rather than by failing the request.

The header is named here rather than in `sds-api-design` because propagation
is what makes a record traceable, and a name agreed by only one side of a call
is not a convention. Anything that generates the id at the edge — a load
balancer or ingress — sets the same header.

Like timestamp precision, this cannot be added retroactively: a record written
without a correlation identifier can never be tied to the request that caused
it. Emit it from the first version.

> **Open decision.** `request` lives in the structured tail rather than being
> a field of its own. Promoting it would make lookup by request cheap, at the
> cost of an unbounded-cardinality column. Recommendation: leave it in the
> tail until indexed lookup by request is actually needed.

## Dimensions and detail

Record fields divide into two kinds, and the split governs what any log store
can index efficiently:

| Kind | Fields | Property |
|------|--------|----------|
| Dimensions | `id`, `severity`, `type`, `code` | Bounded, enumerated sets. Used to group and filter |
| Detail | `request`, `user`, counts, everything in the structured tail | Unbounded. Read, not grouped |

- A value with unbounded range MUST NOT become a dimension. Request and user
  identifiers belong in the structured tail.
- A new dimension MUST NOT be introduced without a bounded set of values,
  either enumerated in this document (`severity`, `type`) or registered per
  app (`code`, per `error-codes.md`).

Log stores index these two kinds differently — as labels, keyword fields, or
tags versus free text — and an unbounded dimension degrades or breaks that
indexing in every one of them. Keeping the split explicit means the question
is already answered whenever storage or tooling changes.

## Emission rules

- Logging MUST NOT fail the operation being logged. A failed submission is
  swallowed and reported through the app's own local error channel.
- Submission MUST NOT block the request path. Emit asynchronously.
- When the aggregator returns 503, or is unreachable, the app SHOULD buffer
  records and retry on the background-class terms in
  `sds-api-design/references/service-calls.md` — including its circuit breaker,
  so a down aggregator is not called on every record. It MUST bound the buffer
  and drop oldest-first when full, rather than growing without limit.
- When the aggregator returns 400, the record is malformed. It MUST NOT be
  retried unchanged; retrying a malformed record loops forever.
- `DEBUG` records MUST NOT be submitted from production by default.

A record dropped from a full buffer, or rejected as malformed, never reaches
the archive. It exists only in the app's own store, and only for that store's
retention window — see
`sds-api-design/references/standard-api-endpoints.md`. Dropping is therefore a
real loss, not a deferral, which is what the bound on the buffer is trading
against.

## Rendering

The aggregator renders a stored record as:

```
[timestamp] [severity] [type] [id] [code]: [message]
```

`[code]` is rendered as `-` when the record has no code. Emitting apps submit
the structured JSON form, not this string; the rendered form exists for
reading, not for parsing.