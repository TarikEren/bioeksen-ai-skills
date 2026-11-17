# Log Record

This document is the normative definition of a BioEksen log record: its
fields, its enumerated values, and the rules an emitting app MUST follow,
including how its records reach the project's log aggregator, when it has one,
per **Delivery**.

## Fields

| Field | Type | Rules |
|-------|------|-------|
| `id` | string | The emitting service, app or process. Stable across restarts and deployments. Lowercase, `-` separated, at most 63 characters, e.g. `auth-service` — see **Allocating an id** |
| `timestamp` | string | RFC 3339 with offset and at least millisecond precision, e.g. `2026-09-03T14:05:00.123Z`. MUST be the time the event occurred, not the time it was written or delivered |
| `severity` | enum | See below |
| `type` | enum | See below |
| `code` | string \| null | The error code identifying the failure, per `error-codes.md`. `null` when the record does not describe a failure. REQUIRED when `severity` is `ERROR` or `FATAL` |
| `message` | string | See below |

The same six fields are what an app's own `GET /api/admin/logs` returns — see
`sds-api-design/references/standard-api-endpoints.md`.

These six are the record as *emitted*. A store that keeps records MAY add its
own identifier for the stored row, which is assigned on write and never part
of the record an app emits. Such an identifier is detail, not a dimension —
see below — and MUST NOT be confused with `id`, which names the emitting app.

### Allocating an id

This is the normative rule for the value, which `sds-commit` reuses as the
`{software-id}` half of a change identifier — see
`sds-commit/references/release-notes.md`.

- The id is **supplied** by the user. It is never derived from a repository
  name, a directory name, or anything else at the point of use.
- When it has not been supplied, **ask for it**. An assistant or generator MUST
  NOT invent one, and MUST NOT fall back to a plausible-looking guess.
- An id is stored in one place: the file `.bioeksen/software-id`, holding the
  id and nothing else, in the directory of the service it names; surrounding
  whitespace is ignored.
  - In a repository that holds one service, that directory is the
    repository's root.
  - In a monorepo, each service's directory holds its own, and the root holds
    the monorepo's own id. That id names no service and appears on no log
    record.
  - Everything that needs a path's id reads the nearest such file above the
    path, never looking past the repository's root: the app's logging
    configuration, a hook minting a change identifier, an assistant writing
    a release note. A service's logging refuses the monorepo's own id, the
    root file of a repository that holds service files below it, rather than
    label its records with a name no service has.
  - A project generator asks for the id once, at creation, and writes the
    file.
- An app whose runtime cannot read that file — a bundled, standalone or
  serverless build that ships without the repository — MAY carry the id
  compiled in. The copy is generated from the service's file at build time,
  or committed beside it with a test that fails whenever the two differ, and it
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

One fixed location per service is what lets a tool find the id without being
told, and what keeps a wrong one visible: it is a one-line file whose history
shows who set it and when, rather than a value repeated through configuration
where a typo in one copy goes unnoticed.

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
credential expired user=0b2f6c1e-8a43-4d7e-9c15-6f0e2a7b9d31 request=8c21 attempts=3
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
| `op` | The operation the record belongs to, from a bounded set the app's binding defines |
| `user` | The person concerned, by the principal key their token carries, a lowercase UUID: Entra's `oid`, or Keycloak's `sub`, per `sds-auth/references/credentials.md`. Never a name, an email or a UPN |
| `attempt` | Which attempt of a retried outbound call this is, counting from 1 |
| `error` | A failure's own text where it says more than its code's meaning, written `Name: message`: the error's name, then an exception's message or a driver's error |
| `cause` | The errors beneath that one, outermost first, each written `Name: message` and joined by ` <- ` |

`op` names what the app was doing, so the records of one operation can be
found and counted together. Its set is bounded: a value is built from
templates, never from the values a request carries, so a route is
`POST /api/v1/orders/[id]`, never `POST /api/v1/orders/42`. An identifier in
`op` makes the set unbounded and gives every request an operation of its own.
Each stack skill lists the values its binding sets; a Next.js app's are in
`sds-nextjs-backend/SKILL.md`.

`user` names a person by the principal key alone. The key identifies nobody once the
person's data is erased, per **An app's own users** in
`sds-auth/references/credentials.md`, so every record naming them stays as
written and no longer identifies anyone. A name, an email or a UPN
would be personal data in records that nothing may delete, `AUDIT` records
above all, which are kept forever and never altered, per **The outbox**. An
`AUDIT` record therefore names a person nowhere but under `user`: not in its
prose, and not under another key. The schema enforces the format:
`LogFields` in `sds-api-design/references/openapi.yaml` refuses a record whose
`user=` value is anything but a lowercase UUID, so the app's own check refuses
it as `LOG-4000`.

`error` and `cause` are where an unhandled failure says what actually broke:
`SYS-5000`'s prose, `unhandled error`, deliberately says nothing.

**An error's name is set, never inferred.** Every error class an app defines
MUST give itself an explicit name, as a string, rather than take it from its
class or its constructor at run time. A production build that minifies its
code renames classes, so an inferred name changes from one build to the next,
and the records of one failure stop reading alike. A binding SHOULD enforce
it, through a base error class that requires the name.

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

## The outbox

An app writes every record first to its **outbox**. The outbox is the app's
own store: what its `GET /api/admin/logs` reads, per
`sds-api-design/references/standard-api-endpoints.md`, what records reach the
project's aggregator from, per **Delivery**, and what an operator falls back
on when the aggregator is unreachable or its records are in doubt.

| Severity | Kept until | Over the bound |
|----------|------------|----------------|
| `DEBUG` | Its window. It never leaves the app | Dropped, oldest first |
| `INFO`, `WARNING` | Its window, and never while pending | Dropped, oldest first, unless the outbox is the archive and keeps it longer than 7 days |
| `ERROR`, `FATAL` | Its window, and never while pending | Never dropped |

A record's window is 7 days from its `timestamp` while the aggregator is the
archive, and its window in **Retention** while the outbox is. An app MAY keep
any record longer, and MUST NOT remove one sooner: the window is what
`GET /api/admin/logs` promises. Under pushed delivery, a record is *pending*
from the moment it is written until the aggregator accepts it, or refuses it
with an answer the app does not retry, per **Delivery**; a pending record is
never removed for its age.

An app has two outboxes, because one kind of record must never be kept apart
from the change it describes:

- **The record outbox** holds every record but `AUDIT`. It is a local
  database on the app's own volume, such as an SQLite file, at the path
  `LOG_OUTBOX_PATH` names, per **Transport** in `SKILL.md`. It is never on a
  shared database server, so it survives the failure it may be recording. A
  component that runs only inside jobs keeps it on its runner host's volume,
  so that what one run could not deliver is still there for the next, per
  `sds-api-design/references/standard-api-endpoints.md`.
- **The audit outbox** holds the `AUDIT` records, in a table in the app's own
  database, written in the same transaction as the change each one describes.
  The change and its record commit or roll back together, so a crash between
  them cannot keep the change and lose its record. When that database is down
  the change fails too, and there is nothing to audit.

An `AUDIT` record is never dropped, never removed and never altered: the audit
outbox keeps every one forever, whether the project has an aggregator or not,
so accountability never depends on a service the project may not have, or may
change. The app's runtime database role SHOULD hold only `INSERT` and `SELECT`
on the table, so that not even a defect in the app can alter a record.

The record outbox is bounded by `LOG_OUTBOX_BOUND`, 100,000 records unless the
app sets another. The bound counts the records the table lets the outbox
drop. When a new record would take that count over the bound, the oldest of
them are dropped, and the app records the drop once, with `dropped=` and the
number dropped in its tail: as `LOG-5500` when records were pending because
the aggregator could not be reached, and otherwise as a `WARNING` record with
no code. An `ERROR` or `FATAL` record is never dropped, so the record outbox
can grow past the bound while the aggregator stays down: an outage's own
failures are the records most needed once it ends.

### Retention

How long the archive keeps a record. The archive is the project's aggregator
when `/.bioeksen/services/log-aggregator.md` says `used` with
`Retention: meets`: the user has confirmed it keeps every record at least this
long. Otherwise the archive is the outbox, which keeps each record for its
window here.

| Type | `DEBUG` | `INFO` | `WARNING` | `ERROR`, `FATAL` |
|------|---------|--------|-----------|------------------|
| `APP`, `JOB`, `ACCESS` | 7 days | 7 days | 7 days | 90 days |
| `SECURITY` | 7 days | 1 year | 1 year | 1 year |
| `AUDIT` | — | Forever | Forever | Forever |

- A window runs from the record's `timestamp`. Forever means never removed,
  never dropped, never sampled and never summarised.
- `DEBUG` never leaves the app, so its 7 days are always the outbox's.
- `AUDIT` is always kept by the audit outbox, per **The outbox**, whatever an
  aggregator keeps of it.

Each window answers the question its records are read for, for as long as it
is asked. `INFO` and `WARNING` answer "what happened before this failed",
which is asked within days. `ERROR` and `FATAL` are the evidence a fix is
written from, and a quarter outlasts the fix. `SECURITY` is kept a year at
every severity, because an intrusion is often found months after it began.
`AUDIT` is kept forever, because who changed what is asked years later.

- **When an aggregator is added**, records written from then on are
  delivered, and so are the `AUDIT` records already kept, oldest first, so it
  holds every one; nothing else written before is.
- **When it is removed**, or recorded as `Retention: short`, the outbox is
  the archive, and keeps every record still held as this table says.

## Delivery

When the project has an aggregator, the `Delivery` its
`/.bioeksen/services/log-aggregator.md` records says how records reach it.
The record is the same either way: the JSON form this document defines.

| Delivery | The app |
|----------|---------|
| `collected` | Writes each record but `DEBUG` to stdout, as one line of its JSON form, for a collector the aggregator runs, such as Grafana Alloy, to read |
| `pushed` | Sends each record but `DEBUG` from its outbox to the aggregator, as the service's `Interface` documents |

**Collected.** Stdout carries records and nothing else, so a collector never
has to guess what a line is: an app SHOULD send its framework's own output to
stderr. A record is written to stdout once it is in its outbox, and an
`AUDIT` record once the transaction that wrote it commits, read back from the
audit outbox and marked written, so it reaches stdout exactly once. A
collector that is down is the aggregator's failure, not the app's: the
outbox still holds every record.

A collector turns some fields into labels, and only the dimensions above may
become one: `id`, `type`, `severity` and `code`. A label from the tail, such
as `request` or `user`, makes the label set unbounded, per **Dimensions and
detail**.

**Pushed.** A background sender delivers the pending records of both
outboxes, in batches where the aggregator takes them, and marks each one
accepted or refused by the answer. Where the aggregator accepts an
idempotency key, every delivery carries one: the same value on every retry of
it, and a fresh one for any delivery whose body differs.

| Answer | The app |
|--------|---------|
| 2xx | Accepted: the records are no longer pending |
| 503, 502, 504, or no response | Keeps the records pending, and SHOULD retry on the background-class terms in `sds-api-design/references/service-calls.md`, including its circuit breaker |
| 429 | Waits the `Retry-After` interval, then retries |
| 401 | Refreshes its credential once and retries. If the fresh one is refused too, it MUST NOT retry again |
| 400 | Refused as malformed: MUST NOT retry it unchanged, which would loop forever. Recorded as `LOG-4000` |
| 500, or any other status | Refused, in a way a retry will not change: MUST NOT retry. Recorded as `LOG-5000` |

Once retries exhaust their budget or the circuit stays open, the app records
`LOG-5500`, and the records stay pending. A refused record stays in the
outbox only, for its window, and never reaches the archive. A dropped record
is kept nowhere: dropping is a real loss, not a deferral, which is why the
outbox table keeps it to the severities nobody is paged for.

Two failures happen before anything is delivered. A record the app's own
check refuses, because it would not match this contract, is `LOG-4000`: the
same malformed record an aggregator would refuse, so the same code. A record
the outbox fails to write is that outbox's own failure, `DB-5001`, not a
`LOG-` code. Both are written to stderr, since the outbox that would have
held them is either not trusted with the record or is the thing that failed.
The `LOG-` codes are the emitting app's, for the records it writes about its
own delivery; an aggregator answers with its own.

## Emission rules

- Logging MUST NOT fail the operation being logged, with one exception: an
  `AUDIT` record is written in the transaction of the change it describes, so
  the change fails if its record cannot be written (**The outbox**). A failed
  delivery is swallowed: the record is still in the outbox, and the failure is
  recorded there and written to stderr, together the app's local error
  channel.
- Delivery MUST NOT block the request path.
- A `DEBUG` record MUST NOT leave the app, from any environment: it is never
  delivered, and under collected delivery never written to stdout. It stays
  in the record outbox, which the app's own `GET /api/admin/logs` reads.
- An `AUDIT` record is never `DEBUG`. `DEBUG` is off in production and kept 7
  days, so an `AUDIT` record at `DEBUG` would be an accountability record
  nobody keeps.
- Outside collected delivery, an app MAY write its records to stdout or
  stderr, in their JSON form or rendered, for a container runtime or a
  developer to read. Nothing in the project may depend on that output.

## Rendering

A record rendered for a person to read, on stderr or in a viewer, is:

```
[timestamp] [severity] [type] [id] [code]: [message]
```

`[code]` is rendered as `-` when the record has no code. The rendered form
exists for reading, not for parsing: what is delivered is the JSON form.
