# Standard API Endpoints

Every BioEksen web app MUST expose the endpoints in this document with exactly
these paths, schemas and semantics. Endpoint-specific deviations MUST be
documented in the owning app's own API spec.

- All paths below are preceded by the host name of the app in question.
- All requests and responses are `application/json; charset=utf-8`.
- The keywords MUST, SHOULD and MAY are used as in RFC 2119.

A component that runs only inside jobs, such as an AI task's wrapper started
by a CI runner for one run, is not a web app, and serves no endpoints, these
included. Nothing can probe a process that exists for one run, and between
runs there is no process to ask. What these endpoints give a web app it gets
another way:

- **Its health is its job's result.** A run that cannot work fails, and the
  CI service reports the failed job.
- **Its records still go through an outbox**, per **The outbox** in
  `sds-logging/references/log-record.md`, kept on the runner host's volume at
  `LOG_OUTBOX_PATH`. The component delivers it before a run ends, and sends
  whatever is still undelivered at the start of the next run, before its own
  records. With no `GET /api/admin/logs` to read it, an operator reads the
  aggregator, or the outbox on the runner host.

## Conventions

### Versioning

Paths fall into two groups, and only one of them carries a version.

| Endpoints | Path | Versioned |
|-----------|------|-----------|
| The five in this document | `/api/health`, `/api/health/live`, `/api/health/ready`, `/api/admin/logs`, `/api/client-errors` | No |
| Everything else an app serves, including the log aggregator's own endpoints | `/api/v{major}/…` | Yes |

The standard five are unversioned because every app implements them
identically, and because they are configured outside the app that serves them:
in load balancer definitions, orchestrator manifests and monitoring checks. A
version bump there is the hardest kind to roll out, and a probe path that moves
takes healthy instances out of rotation while the configuration catches up. If
one of the five ever has to break, the honest signal is a new path, not a
version negotiation.

For the versioned group:

- The segment carries the **major version only**, as an integer — `/api/v1/`,
  `/api/v2/`. There is no `v0` and no minor component, because a minor version
  by definition adds nothing a caller must be told about.
- It increments only for a change that would carry `!` under
  `sds-commit/SKILL.md`. Additive change never bumps it.
- When it increments, both versions MUST be served for **90 days** from the
  release of the new one. Removing the old version is itself a breaking change
  and is announced as one.
- A request to an unrecognised version is a request to a path that does not
  exist: 404 with `RES-4200`. It is not `VAL-4002` — that code is for a value
  outside an enumeration in a body or query string, and the version is neither.

A deprecation window nobody wrote down is a window that never closes, which is
why the 90 days is stated here rather than agreed per migration.

### Types and units

| Concept | Type | Unit / format |
|---------|------|---------------|
| Memory and disk sizes | number | GB (decimal, e.g. `1.75`) |
| `uptime` | integer | seconds |
| Counts (`page`, `count`, `totalCount`, connection counts) | integer | — |
| Timestamps and dates | string | RFC 3339 with offset, e.g. `2026-09-03T14:05:00Z`. Log record timestamps carry at least millisecond precision |

Numeric fields MUST be JSON numbers, not strings.

### Body `status` vs HTTP status code

The body carries a machine-readable `status` string; the HTTP status line
carries the transport result. Clients MUST treat the HTTP status code as
authoritative and MAY use the body `status` for detail.

| Body `status` | Meaning | HTTP code |
|---------------|---------|-----------|
| `ok` | Up and serving | 200 |
| `not-ready` | Process alive, dependencies not ready yet | 503 |
| `fail` | Up but a required dependency failed | 503 |

A server that is unreachable returns no body at all. Clients MUST treat a
connection failure or timeout as `fail`; no endpoint can report its own
unreachability.

This table describes the health endpoints. Every other successful body carries
`ok` and nothing else, per `app-endpoints.md`.

### Dependency check values

Every check value — the database's `status`, `cache`, and each entry of
`dependencies` — uses: `ok` (working), `fail` (present but broken), `na` (not
applicable to this app). An app without a cache MUST report `"cache": "na"`
rather than omitting the key, and an app with no further dependencies reports
`"dependencies": {}`.

### Further dependencies

`db` and `cache` are named because nearly every app has them. Anything else an
app depends on — a message queue, an object store, another BioEksen app — is
reported under `checks.dependencies`, keyed by name: the dependency's software
id when it is a BioEksen app, and otherwise a name in the same format, e.g.
`object-store`.

- `GET /api/health` lists every dependency.
- `GET /api/health/ready` lists only those whose failure means this instance
  should not receive traffic.

A dependency the app degrades gracefully without belongs in the first and not
the second. Listed under readiness, its failure takes every instance out of
rotation at once — an outage the app was built to avoid.

### Correlation

Every request carries a correlation identifier in the `X-Request-Id` header,
adopted from the caller or generated when absent, propagated on outbound calls
and echoed on every response including errors. The header, its value format and
the propagation rules are defined normatively in
`sds-logging/references/log-record.md`.

This applies to every endpoint an app serves, not only the standard ones.

### Error envelope

Any 4xx or 5xx response the app produces that has a body MUST use the envelope
below, with one exception: the 503 responses of the three health endpoints in
this document. A
503 from `GET /api/health`, `GET /api/health/live` or `GET /api/health/ready`
carries the body `status` value `fail` or `not-ready` and no `code`, because
the condition being reported is the state of the app itself rather than the
outcome of a request.

The exception covers only that 503. Every other error response from a health
endpoint uses the envelope normally — in particular the 401 and 403 of
`GET /api/health`, which are outcomes of the request and carry a `code` like
any other rejection.

```json
{
    "status": "fail",
    "code": "<error code>",
    "message": "<human readable summary>",
    "details": "<what the code defines, or null>"
}
```

`code` is the app's stable error code, formatted and allocated per
`sds-logging/references/error-codes.md`. The same code MUST appear in the log
record written for this failure. `message` is written for humans and MAY be
reworded at any time; clients that branch on the error MUST branch on `code`.

`details` belongs to the code. A code about fields, `VAL-4001` to `VAL-4007`,
MUST carry an array of `{ "field": "<name>", "issue": "<what is wrong>" }`, one
entry per field at fault. Any other code carries the object its entry in
`sds-logging/references/code-prefixes.md` defines, and MUST carry `null` when
its entry defines none — which, today, is every one of them. A client reads
`details` by the `code` beside it, so the shape is never a guess: the code that
says what went wrong also says what `details` holds.

### Method, size and media type

Any endpoint MAY answer 405 with `RES-4500` for a method it does not serve,
and an endpoint that takes a body MAY answer 415 with `VAL-4600`, and MUST
answer 413 with `VAL-4550` for a body over its limit, below. These hold for
every endpoint in the estate, so no endpoint's response list repeats them.

An endpoint's body limit is **1 MiB** (1,048,576 bytes) unless the app sets
another for that endpoint. A different limit is an empirical value in the
sense of `sds-api-design/references/service-calls.md`: the app MAY set it and
MUST record that it has. One default across the estate lets a caller size a
request without reading each app's code, and it is the aggregator's own batch
limit, so the service every app writes to accepts whatever an app's default
accepts.

The limit is counted on the bytes as they arrive, never taken from
`Content-Length` alone. A chunked body carries no `Content-Length`, and a
sender can understate one, so an app that trusts the header can read an
unbounded body into memory before it ever compares a size.

The envelope rule above governs responses the app produces. A proxy or load
balancer in front of the app may refuse an oversized body with a 413 of its
own before the app ever sees the request, and that response carries no
envelope. A client MUST handle a 413 by its status alone, and MUST NOT assume
it carries a `code`.

### Rate limited responses

A 429 response MUST carry a `Retry-After` header giving whole seconds until the
caller may retry:

```
Retry-After: 30
```

A 429 without it tells a client to back off but not for how long, so each
client picks its own interval and the ones that pick badly sustain the overload
the status code exists to shed. Seconds are used rather than an HTTP date
because the value is a backoff, not a deadline, and a clock-skewed client
cannot misread a duration.

### Caching

All endpoints in this document MUST be served with `Cache-Control: no-store`.

## `GET /api/health`

Full health report: process status plus every dependency check. Intended for
dashboards and operators, not for load-balancer probes.

**Authorization:** MUST require an operator credential. It exposes disk
capacity, memory and connection-pool internals, so it MUST NOT be publicly
reachable. Restricting it to the internal network is a worthwhile additional
measure, but it is not a substitute for the credential: an internal network is
not a trust boundary, and any service that reaches the endpoint would otherwise
read the app's capacity internals unauthenticated.

**Responses:** 200 (`ok`), 401, 403, 429, 503 (`fail` or `not-ready`). The 401,
403 and 429 carry the error envelope; the 200 and 503 carry the health schema
below.

### Fields

- `status`: overall status, per the table above.
- `uptime`: seconds the server has been up.
- `checks`: dependency checks.
    - `db`: database information.
        - `status`: `ok` | `fail` | `na`
        - `openConnections`: count of open connections.
        - `inUseConnections`: count of in-use connections.
        - `idleConnections`: count of idle connections.
    - `cache`: `ok` | `fail` | `na`
    - `dependencies`: every further dependency, name to `ok` | `fail` | `na`;
      `{}` when there are none.
    - `memory`: memory of the server, in GB.
        - `totalHeap`: total heap allocated to the process.
        - `usedHeap`: heap currently used by the process.
        - `totalMemory`: total physical memory of the server.
        - `usedMemory`: physical memory currently in use.
    - `disk`: disk of the server, in GB.
        - `total`: total capacity.
        - `used`: used space.
        - `free`: available space.

When `db` is `na`, its connection counts MUST be `0`.

A runtime without a managed heap reports its process's resident memory as both
`totalHeap` and `usedHeap`. The fields then keep one meaning on every runtime —
memory this process holds — instead of being zero, or absent, on some.

### Schema

```json
{
    "status": "ok|fail|not-ready",
    "uptime": 86400,
    "checks": {
        "db": {
            "status": "ok|fail|na",
            "openConnections": 10,
            "inUseConnections": 2,
            "idleConnections": 8
        },
        "cache": "ok|fail|na",
        "dependencies": {
            "billing-service": "ok|fail|na"
        },
        "memory": {
            "totalHeap": 2.0,
            "usedHeap": 1.25,
            "totalMemory": 16.0,
            "usedMemory": 9.5
        },
        "disk": {
            "total": 512.0,
            "used": 210.5,
            "free": 301.5
        }
    }
}
```

## `GET /api/health/live`

Liveness probe: is the process alive and able to answer? It MUST NOT check any
dependency, MUST NOT touch the database, and SHOULD respond in under 100 ms.

A `fail` here means the process is unrecoverable and SHOULD be restarted.

**Authorization:** MAY be unauthenticated; it exposes nothing.

**Responses:** 200 (`ok`), 503 (`fail`). No 429: a rate limited probe takes a
healthy instance out of rotation, which is the failure this endpoint exists to
detect rather than cause.

### Fields

- `status`: `ok` if the process is alive and serving, `fail` if it is alive but
  unrecoverable. `not-ready` MUST NOT be returned here — readiness is
  `GET /api/health/ready`.

### Schema

```json
{
    "status": "ok|fail"
}
```

## `GET /api/health/ready`

Readiness probe: can this instance serve traffic right now? Returns the
dependency checks that gate traffic, and nothing else. This is the endpoint
load balancers and orchestrators MUST probe.

It is the trimmed form of `GET /api/health`: same check values, no capacity
numbers, safe to call frequently.

**Authorization:** MAY be unauthenticated; it exposes no capacity detail.

**Responses:** 200 (`ok`), 503 (`fail` or `not-ready`).

### Fields

- `status`: overall readiness, per the table above.
- `uptime`: seconds the server has been up.
- `checks`: dependency checks that gate traffic.
    - `db`: `ok` | `fail` | `na`
    - `cache`: `ok` | `fail` | `na`
    - `dependencies`: the further dependencies that gate traffic, name to
      `ok` | `fail` | `na`; `{}` when there are none.

`status` MUST be `ok` only if every check is `ok` or `na`, including every
entry of `dependencies`.

### Schema

```json
{
    "status": "ok|fail|not-ready",
    "uptime": 86400,
    "checks": {
        "db": "ok|fail|na",
        "cache": "ok|fail|na",
        "dependencies": {
            "billing-service": "ok|fail|na"
        }
    }
}
```

## `GET /api/admin/logs`

Returns this app's logs, filtered and paginated. Log records use the shared
format defined by the log aggregator.

**Authorization:** MUST require an authenticated operator. Unauthenticated
requests return 401; authenticated non-operators return 403.

**Responses:** 200, 400 (invalid query parameter), 401, 403, 429, 500, 503 (not
yet ready to serve — `SYS-5500`, carrying the error envelope like any other
rejection).

### Query parameters

All are optional.

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `startDate` | RFC 3339 | start of the retention window | Inclusive lower bound on `timestamp`. Clamped — see below |
| `endDate` | RFC 3339 | now | Inclusive upper bound on `timestamp` |
| `severity` | enum | all | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` \| `FATAL` |
| `type` | enum | all | `APP` \| `SECURITY` \| `AUDIT` \| `ACCESS` \| `JOB` |
| `id` | string | all | Owner ID of the log — the service, app or process that emitted it |
| `code` | string | all | Exact error code, e.g. `DB-5001` |
| `page` | integer | `1` | 1-based |
| `limit` | integer | `50` | `1` to `200`; values outside are rejected with 400 |

An unknown `severity` or `type` value, an unparseable date, `page` < 1,
`limit` outside 1 to 200, or `endDate` earlier than `startDate` MUST return 400
with the error envelope.

### Retention

An app MUST keep its own records for at least **7 days**, in its two
outboxes, per **The outbox** in `sds-logging/references/log-record.md`. This
endpoint reads both. That is a working week: long enough to debug an app
directly when the aggregator is unreachable or when its records are in doubt.

The archive is the aggregator, which keeps each record for as long as its
type and severity call for, from 14 days to forever — the **Retention** table
in `sds-logging/references/aggregator-api.md`. The two windows are
deliberately different, and an operator comparing them will find records here
that the aggregator no longer holds, and far more there than here. Neither gap
is loss.

This store is also the only one that keeps `DEBUG` records, which never reach
the aggregator. And an `AUDIT`, `ERROR` or `FATAL` record the aggregator has
not yet stored stays here past the window until it has, per the same
document.

A `startDate` earlier than the window MUST be clamped to the start of it rather
than rejected, and `filterParams` MUST echo the clamped value. A 400 would make
a caller guess a boundary it was never told, and the guess goes stale the next
time the window changes.

Results MUST be sorted by `timestamp` descending (newest first), tie-broken by
the store's own record identifier ascending so paging is stable.

The tie-break MUST NOT be the record's `id` field: `id` names the emitting app,
which is the same value for every record this endpoint returns, so ordering by
it breaks no ties at all and leaves records sharing a timestamp free to swap
places between two requests for adjacent pages. The identifier used instead is
whatever the log store assigns per row; it need not be exposed in the response,
but it MUST give a total order.

### Response fields

- `status`: `ok` on success.
- `page`: the page returned (1-based).
- `count`: number of records in `logs` for this page.
- `totalCount`: total records matching the filter across all pages.
- `logs`: array of log records; empty array when nothing matches (never `null`).
- `filterParams`: the filters actually applied, after defaults are resolved,
  including the `page` and `limit` the server used. Echoing the resolved
  pagination is what lets a caller that sent neither know how much of the
  result it is looking at.

A page beyond the last one is not an error: it returns 200, an empty `logs`
array, and the true `totalCount`.

### Log record

Each entry in `logs` is a record in the shape defined normatively by
`sds-logging/references/log-record.md`: the six emitted fields `id`,
`timestamp`, `severity`, `type`, `code` and `message`, carrying the
enumerations and rules that document sets — including how `id` is allocated,
which is not something an app decides for itself.

The store's own row identifier is not one of the six. It provides the tie-break
above and need not be returned.

### Schema

```json
{
    "status": "ok",
    "page": 1,
    "count": 2,
    "totalCount": 137,
    "logs": [
        {
            "id": "auth-service",
            "timestamp": "2026-09-03T14:05:00.123Z",
            "severity": "ERROR",
            "type": "APP",
            "code": "DB-5001",
            "message": "write failed request=8c21"
        }
    ],
    "filterParams": {
        "id": "auth-service",
        "severity": "ERROR",
        "type": "APP",
        "code": "DB-5001",
        "startDate": "2026-09-01T00:00:00Z",
        "endDate": "2026-09-03T23:59:59Z",
        "page": 1,
        "limit": 50
    }
}
```

## `POST /api/client-errors`

Takes a report of an error that happened in one of the app's own pages, in the
browser, and logs it. The SDK's browser error reporter sends it, so an app
does not write its own.

**Authorization:** none. A page fails before its user signs in as often as
after, so the endpoint takes no credential. Three rules keep it the app's own:

- **The `Origin` MUST be the app's own.** A request from another site, or one
  carrying no `Origin`, is refused with 403 `PERM-4153`, step 7 of the
  selection procedure in `sds-logging/references/code-prefixes.md`.
- **It is rate limited per source**, to 10 reports a minute unless the app
  records another value, an empirical value in the sense of
  `service-calls.md`. The next report is answered 429 `RATE-4400`, with
  `Retry-After`. Without the limit, a page caught in an error loop fills the
  app's outbox and the aggregator.
- **The body is at most 16 KiB**, not the 1 MiB default of **Method, size and
  media type**: a report is an error and its causes, never a page's state. A
  larger one is 413 `VAL-4550`.

**Request:** `ClientErrorReport` in `openapi.yaml`.

```json
{
    "route": "/orders/[id]",
    "error": "TypeError: Cannot read properties of undefined (reading 'total')",
    "cause": "FetchError: request failed <- AbortError: aborted"
}
```

- `route` is the page's route template, which MUST be one the app serves. Any
  other route is 400 `VAL-4006`: the report did not come from one of the app's
  pages, and a template, unlike the path a user visited, carries no
  identifier.
- `error` is the error as `Name: message`, and `cause`, when there is one, the
  errors beneath it, outermost first, joined by ` <- `: the forms of the
  reserved tail keys in `sds-logging/references/log-record.md`.
- A field the report does not define is 400 `VAL-4007`, so a reporter cannot
  add a user's name or a page's data to a report.

**Responses:** 200 with `{"status": "ok"}` once the report is logged; 400,
403, 413, 415, 429 and 503 with the error envelope.

**What the app logs.** Each report becomes one record:

| Field | Value |
|-------|-------|
| `severity`, `type`, `code` | `ERROR`, `APP`, `SYS-5000` |
| `message` | `unhandled error`, then the tail: `op="client {route}"`, `error=`, `cause=`, `request=`, and `user=` with the person's principal key when the request carries the app's session |

- `error=` and `cause=` are redacted, as any text from a library is, and
  written on one line, per `sds-logging/references/log-record.md`. When the
  record would be longer than 8192 characters, the app shortens `cause`, then
  `error`, from their ends.
- Nothing else about the user is recorded: no address, no user agent, and no
  page state.
- Reports are grouped like any failure, per **Groups** in
  `sds-logging/references/aggregator-api.md`, so a page that fails for every
  user is one group, not a record per user. Noise from browser extensions and
  old browsers is closed as `close:external`.

## Machine-readable schema

`openapi.yaml`, beside this file, is the normative OpenAPI 3.1 definition of
these endpoints. This document is the rationale layer; when the two disagree, the
OpenAPI file wins and this document MUST be corrected.
