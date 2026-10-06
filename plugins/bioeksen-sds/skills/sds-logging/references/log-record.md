# Log Record

This document is the normative definition of a BioEksen log record: its
fields, its enumerated values, and the rules an emitting app MUST follow. The
aggregator endpoints that carry these records are in `aggregator-api.md`.

## Fields

| Field | Type | Rules |
|-------|------|-------|
| `id` | string | The emitting service, app or process. Stable across restarts and deployments. Lowercase, `-` separated, at most 63 characters, e.g. `auth-service` — see **Allocating an id** |
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
- A repository stores its id in one place: the file `.bioeksen/software-id` at
  its root, holding the id and nothing else; surrounding whitespace is
  ignored. Everything that needs the id reads it from there — the app's
  logging configuration, a hook minting a change identifier, an assistant
  writing a release note. A project generator asks for the id once, at
  creation, and writes the file.
- An app whose runtime cannot read that file — a bundled, standalone or
  serverless build that ships without the repository — MAY carry the id
  compiled in. The copy is generated from the file at build time, or
  committed beside it with a test that fails whenever the two differ, and it
  is never edited by hand. The file stays the one place the id is set.
- A missing or empty file means the id has not been supplied, and the rule
  above applies: ask.
- Format: lowercase letters and digits in `-` separated words, at most 63
  characters, e.g. `auth-service`. The enforced form is `SoftwareId` in
  `sds-api-design/references/openapi.yaml`. The length keeps an id usable as a
  DNS label and inside an Application ID URI.
- Once allocated it is permanent. Changing it severs every existing log record
  and release-note entry from the service that produced them.

A guessed id is worse than a missing one. It looks correct, so nothing flags
it, and the records it labels are filed under a service that does not exist —
while the real service's records are split across two names.

One fixed location is what lets a tool find the id without being told, and
what keeps a wrong one visible: it is a one-line file whose history shows who
set it and when, rather than a value repeated through configuration where a
typo in one copy goes unnoticed.

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
- Be at most 8192 characters. A message longer than that is carrying a body or
  a dump, which the forbidden list in `SKILL.md` already rules out
- Not repeat the error code. It has its own field precisely so that filtering
  never depends on parsing free text
- Contain nothing from the forbidden list in `SKILL.md`
- Carry no stack trace, not even one flattened onto a single line

A stack is for the person debugging one instance, not for every operator
filtering the estate: it is unbounded, it names the app's internals, and
flattened into the message it buries the constant prefix records are grouped
by. An app that keeps stacks SHOULD write each to its local error channel,
stderr, as one line carrying the failure's `code` and the same `request=` or
`job=` value as its record, so a person can join the two. A stack never
reaches the aggregator.

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

### Reserved keys

A record that carries one of these values MUST carry it under this key, so a
dashboard or a runbook can rely on the name. Any other key is the app's own.

| Key | Carries |
|-----|---------|
| `request` | The request's identifier, per **Correlation** below |
| `job` | A background run's identifier, in place of `request` |
| `attempt` | Which attempt of a retried outbound call this is, counting from 1 |
| `error` | A failure's own text where it says more than its code's meaning: an exception's message, a driver's error |
| `cause` | The errors beneath that one, outermost first, each written `Name: message` and joined by ` <- ` |

`error` and `cause` are where an unhandled failure says what actually broke:
`SYS-5000`'s prose, `unhandled error`, deliberately says nothing.

Text taken from a library or a driver MUST be redacted before it is written.
A driver quoting its connection string puts a password into `cause`, and the
forbidden list in `SKILL.md` covers the tail as much as the prose.

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
  swallowed. The record still exists in the app's local store, and the failure
  is recorded there and written to stderr — together, the app's local error
  channel.
- Submission MUST NOT block the request path. Emit asynchronously.
- An app that emits more than occasionally SHOULD submit in batches, through
  `POST /api/v1/logs/batch` in `aggregator-api.md`. The response handling below
  is the same for a batch as for a single record.
- Every submission MUST carry an `Idempotency-Key`: the same value on every
  retry of that submission, and a fresh one for any submission whose body
  differs. The same key is what stops a retry after a timeout storing a record
  twice; a fresh key is what stops a corrected resubmission being refused as a
  replay. The aggregator honours the key, per
  `sds-api-design/references/service-calls.md`, but does not require it, so
  this rule is the emitter's to keep.
- A `DEBUG` record MUST NOT be submitted, from any environment. It stays in
  the app's own store, which the app's own `GET /api/admin/logs` reads; the
  aggregator keeps no `DEBUG` record and refuses one with `VAL-4006`, per
  `aggregator-api.md`.
- An `AUDIT` record is never `DEBUG`. The aggregator keeps `AUDIT` forever and
  never sees `DEBUG`, so an `AUDIT` record at `DEBUG` would be an
  accountability record nobody keeps.

### Handling the aggregator's response

What an app does next is decided by the status alone:

| Response | Means | The app |
|----------|-------|---------|
| 201 | Stored | Nothing further |
| 503, or no response | The aggregator or its database is unavailable | SHOULD buffer and retry on the background-class terms in `sds-api-design/references/service-calls.md`, including its circuit breaker, so a down aggregator is not called on every record |
| 429 | Over the app's allowance | Waits the `Retry-After` interval, then retries |
| 401 | The app's credential was refused | Refreshes it once and retries. If the fresh credential is refused too, it MUST NOT retry again |
| 400 | The record is malformed | MUST NOT retry it unchanged; retrying a malformed record loops forever |
| 409 | The idempotency key was already spent on a different body | MUST NOT retry. The app is minting keys wrongly |
| 403, 500, any other 4xx | Refused, or the write failed in a way a retry will not change | MUST NOT retry |

A 500 is not retried because it is outside the range
`sds-api-design/references/service-calls.md` retries: the aggregator answers 500 only when its database rejected the
write, and an unreachable database is a 503.

Whatever the app does not retry stays in its local store only, and the app
records that failure there: `LOG-4000` for a 4xx, `LOG-5000` for a 500, and
`LOG-5500` once retries exhaust their budget or the circuit stays open. The
buffer MUST be bounded and, when full, drop its oldest record that is not
`AUDIT`, rather than growing without limit. An `AUDIT` record is never
dropped: it stays in the app's local store, past that store's own window,
until the aggregator has answered 201 for it. The archive keeps `AUDIT`
forever, and a record lost on its way there defeats that.

Two failures happen before anything is submitted. A record the app's own
check refuses, because it would not match this contract, is `LOG-4000`: the
same malformed record the aggregator would have refused, so the same code. A
record the local store fails to write is that store's own failure, `DB-5001`
for a database and `SYS-5000` for any other store, not a `LOG-` code. Both
are written to stderr, since the store that would have held them is either
not trusted with the record or is the thing that failed. `LOG-5000` stays the
code for a submission the aggregator refused.

The two sets of codes belong to different apps. The aggregator answers a
malformed record with the `VAL-` code the selection procedure gives it, as any
app answers any request. The `LOG-` codes are the emitting app's, for the
records it writes about its own submissions.

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