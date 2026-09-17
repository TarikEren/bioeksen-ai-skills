# Log Aggregator API

The log aggregator collects and serves logs from every BioEksen app. Its host
is denoted `HOST`.

`aggregator-api.yaml` beside this file is the normative OpenAPI 3.1 definition
of these endpoints. This document is the rationale layer; where the two
disagree, the schema wins and this document MUST be corrected — the same
relationship `standard-api-endpoints.md` has with `openapi.yaml`.

The aggregator is itself a BioEksen app: it follows
`sds-api-design/references/standard-api-endpoints.md`, including the string
`status` values, the HTTP status mapping, and the error envelope. It therefore
also exposes the standard health endpoints, unversioned like every app's.

Its own log endpoints are app-specific, so they carry a version — they are
below at `/api/v1/`, on the terms that document sets, including the 90 day
window during which a superseded version stays served.

Record fields and their rules are defined in `log-record.md`. The aggregator
adds one value of its own: `recordId`, the identifier it assigns to a stored row
on write. It is not part of a submitted record, and it is not the record's `id`
field, which names the emitting app. It is returned by every endpoint below and
is what `GET HOST/api/v1/logs/:recordId` takes.

## `POST HOST/api/v1/logs`

Validates an incoming record and stores it.

### Request

```json
{
    "id": "auth-service",
    "timestamp": "2026-09-03T14:05:00.123Z",
    "severity": "ERROR",
    "type": "APP",
    "code": "DB-5001",
    "message": "write failed request=8c21"
}
```

All six fields MUST be present; `code` MAY be `null`. Validation rules:

- `severity` and `type` MUST be members of their enumerations
- `timestamp` MUST be RFC 3339 with at least millisecond precision
- `code`, when not null, MUST be a code listed in `code-prefixes.md` — which
  the schema enforces by enumerating them, so an unlisted code fails validation
  rather than being stored
- `code` MUST NOT be null when `severity` is `ERROR` or `CRITICAL`
- A submission carrying `recordId` MUST be rejected. The aggregator assigns it
  on write; an app that believes it chooses record identifiers should find that
  out at once rather than have the value silently dropped

### Responses

| HTTP | When |
|------|------|
| 201 | Stored. Body carries the `recordId` |
| 400 | Schema validation failed. `details` lists the offending fields |
| 500 | Stored nowhere — the database rejected the write or was unreachable |
| 503 | The aggregator is not ready to accept records |

A 400 means the record is malformed and MUST NOT be retried unchanged. A 500
or 503 is retryable — see the emission rules in `log-record.md`.

## `GET HOST/api/v1/logs`

Returns stored logs across all apps, filtered and paginated.

The query parameters, their defaults, the pagination rules, the response fields
and the error envelope are the ones defined for an app's own
`GET /api/admin/logs` in
`sds-api-design/references/standard-api-endpoints.md`, which is normative for
them. One parameter differs:

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `id` | string | all | The emitting service, app or process. On an app's own endpoint every record has the same value; here it selects between apps |

Results MUST be sorted by `timestamp` descending, tie-broken by `recordId`
ascending so paging is stable — `recordId` being the store-assigned identifier
that endpoint's tie-break rule calls for. Every record in the response carries
it, so a listing can be followed to a single record.

### Retention

The aggregator keeps records for **90 days**. It is the estate's archive: the
90 days is what makes a quarterly incident review possible and what any
"when did this start?" investigation reads.

`startDate` defaults to the start of that window, and a `startDate` earlier
than it is clamped rather than rejected, per the rule in
`standard-api-endpoints.md`. `filterParams` echoes the clamped value, so a
caller asking for a year sees what it actually got.

Records older than the window are removed. Nothing in these specs promises an
archival tier beyond it, so a record that must outlive 90 days — an `AUDIT`
record kept for a compliance obligation, say — needs somewhere else to live,
and that is a decision for whoever has the obligation.

An app's own `GET /api/admin/logs` reads a different store with a shorter
window. The two disagreeing is expected, not data loss.

### Response

```json
{
    "status": "ok",
    "page": 1,
    "count": 1,
    "totalCount": 137,
    "logs": [
        {
            "recordId": "01J9Z4K7XQ2M8N",
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
        "startDate": "2026-09-01T00:00:00.000Z",
        "endDate": "2026-09-03T23:59:59.999Z",
        "page": 1,
        "limit": 50
    }
}
```

A page beyond the last one returns 200 with an empty `logs` array and the true
`totalCount`.

## `GET HOST/api/v1/logs/:recordId`

Returns a single stored record. The path parameter is the `recordId` defined at
the top of this document, not the record's `id` field.

| HTTP | When |
|------|------|
| 200 | Found; body is the record |
| 404 | No record with that `recordId` — `RES-4200` |
| 500 | Query failed |
| 503 | Not ready |

## Authorization

`POST /api/v1/logs` MUST require an app credential; any app that can reach it can
otherwise forge records attributed to another `id`. The two read endpoints
MUST require an operator credential — the aggregator holds every app's logs,
which makes it the highest-value read target in the estate.