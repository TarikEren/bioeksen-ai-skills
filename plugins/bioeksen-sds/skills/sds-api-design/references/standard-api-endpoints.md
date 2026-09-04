# Standard API Endpoints

Every BioEksen web app MUST expose the endpoints in this document with exactly
these paths, schemas and semantics. Endpoint-specific deviations MUST be
documented in the owning app's own API spec.

- All paths below are preceded by the host name of the app in question.
- All requests and responses are `application/json; charset=utf-8`.
- The keywords MUST, SHOULD and MAY are used as in RFC 2119.

## Conventions

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

### Dependency check values

Every entry under `checks` uses: `ok` (working), `fail` (present but broken),
`na` (not applicable to this app). An app without a cache MUST report
`"cache": "na"` rather than omitting the key.

### Error envelope

Any 4xx or 5xx response that has a body MUST use the envelope below, with one
exception: the 503 responses of the three health endpoints in this document. A
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
    "details": "<array of field errors, or null>"
}
```

`code` is the app's stable error code, formatted and allocated per
`sds-logging/references/error-codes.md`. The same code MUST appear in the log
record written for this failure. `message` is written for humans and MAY be
reworded at any time; clients that branch on the error MUST branch on `code`.

`details` MUST be `null` unless the error is a validation error, in which case
it is an array of `{ "field": "<name>", "issue": "<what is wrong>" }`.

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

**Responses:** 200 (`ok`), 401, 403, 503 (`fail` or `not-ready`). The 401 and
403 carry the error envelope; the 200 and 503 carry the health schema below.

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

**Responses:** 200 (`ok`), 503 (`fail`).

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

`status` MUST be `ok` only if every check is `ok` or `na`.

### Schema

```json
{
    "status": "ok|fail|not-ready",
    "uptime": 86400,
    "checks": {
        "db": "ok|fail|na",
        "cache": "ok|fail|na"
    }
}
```

## `GET /api/admin/logs`

Returns this app's logs, filtered and paginated. Log records use the shared
format defined by the log aggregator.

**Authorization:** MUST require an authenticated operator. Unauthenticated
requests return 401; authenticated non-operators return 403.

**Responses:** 200, 400 (invalid query parameter), 401, 403, 500.

### Query parameters

All are optional.

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `startDate` | ISO 8601 | earliest log record | Inclusive lower bound on `timestamp` |
| `endDate` | ISO 8601 | now | Inclusive upper bound on `timestamp` |
| `severity` | enum | all | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` \| `CRITICAL` |
| `type` | enum | all | `APP` \| `SECURITY` \| `AUDIT` \| `ACCESS` \| `JOB` |
| `id` | string | all | Owner ID of the log — the service, app or process that emitted it |
| `code` | string | all | Exact error code, e.g. `DB-5001` |
| `page` | integer | `1` | 1-based |
| `limit` | integer | `50` | Max `200`; values above are rejected with 400 |

An unknown `severity` or `type` value, an unparseable date, `page` < 1, or
`endDate` earlier than `startDate` MUST return 400 with the error envelope.

Results MUST be sorted by `timestamp` descending (newest first), tie-broken by
`id` ascending so paging is stable.

### Response fields

- `status`: `ok` on success.
- `page`: the page returned (1-based).
- `count`: number of records in `logs` for this page.
- `totalCount`: total records matching the filter across all pages.
- `logs`: array of log records; empty array when nothing matches (never `null`).
- `filterParams`: the filters actually applied, after defaults are resolved.

A page beyond the last one is not an error: it returns 200, an empty `logs`
array, and the true `totalCount`.

### Log record

Matches the aggregator's stored log shape, defined normatively in
`sds-logging/references/log-record.md`:

- `id`: owner ID assigned by the emitting app.
- `timestamp`: RFC 3339 time the event occurred, millisecond precision.
- `severity`: `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`
- `type`: `APP` | `SECURITY` | `AUDIT` | `ACCESS` | `JOB`
- `code`: the error code, or `null` when the record is not a failure.
- `message`: additional details regarding the log.

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
        "endDate": "2026-09-03T23:59:59Z"
    }
}
```

## Machine-readable schema

`references/openapi.yaml` is the normative OpenAPI 3.1 definition of these
endpoints. This document is the rationale layer; when the two disagree, the
OpenAPI file wins and this document MUST be corrected.

## Open decisions

These are unresolved and MUST be settled before the first app implements the
spec:

- **Versioning.** Paths are currently unversioned. Decide whether standard
  endpoints get a `/api/v1` prefix, or stay unversioned on the grounds that
  they never break.
- **Log retention.** `startDate` defaults to "the earliest log record", which
  is only meaningful once a retention window is defined.
