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
| `code` | string \| null | The error code identifying the failure, per `error-codes.md`. `null` when the record does not describe a failure. REQUIRED when `severity` is `ERROR` or `CRITICAL` |
| `message` | string | See below |

The same six fields are what an app's own `GET /api/admin/logs` returns — see
`sds-api-design/references/standard-api-endpoints.md`.

### Severity

`DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`

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

- Begin with the prose fixed by the record's `code` — the Meaning text in
  `code-prefixes.md` with only its first character lowercased, otherwise
  unchanged, so identifiers keep their casing (`endDate earlier than
  startDate`, never `enddate earlier than startdate`). The prose is never
  reworded per occurrence, and a record with no code states what happened in
  the past tense as a fact: `"job completed"`, not `"completing job"`
- Carry all varying values in a structured tail, so the prose prefix stays
  constant and greppable — see below
- Contain no newlines. The rendered form is one line per record
- Contain nothing from the forbidden list in `SKILL.md`

The error code MUST NOT be repeated in the message. It has its own field
precisely so that filtering never depends on parsing free text.

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
- The identifier is generated at the edge if the incoming request does not
  already carry one, and propagated onward.
- Background work uses `job=<run id>` in place of `request=`.
- When a request fails, the `code` in the API error response and the `code`
  field of the log record MUST be the same value.

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
  records and retry with exponential backoff. It MUST bound the buffer and
  drop oldest-first when full, rather than growing without limit.
- When the aggregator returns 400, the record is malformed. It MUST NOT be
  retried unchanged; retrying a malformed record loops forever.
- `DEBUG` records MUST NOT be submitted from production by default.

## Rendering

The aggregator renders a stored record as:

```
[timestamp] [severity] [type] [id] [code]: [message]
```

`[code]` is rendered as `-` when the record has no code. Emitting apps submit
the structured JSON form, not this string; the rendered form exists for
reading, not for parsing.