# Log Aggregator API

The log aggregator collects and serves logs from every BioEksen app. Its host
is denoted `HOST`.

The aggregator is itself a BioEksen app: it follows
`sds-api-design/references/standard-api-endpoints.md`, including the string
`status` values, the HTTP status mapping, and the error envelope. It therefore
also exposes the standard health endpoints.

Record fields and their rules are defined in `log-record.md`. The aggregator
adds one value of its own: `recordId`, the identifier it assigns to a stored row
on write. It is not part of a submitted record, and it is not the record's `id`
field, which names the emitting app. It is returned by every endpoint below and
is what `GET HOST/api/logs/:id` takes.

## `POST HOST/api/logs`

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
- `code`, when not null, MUST match `^[A-Z][A-Z0-9]{1,7}-[45][0-9]{3}$` and
  MUST be a code listed in `code-prefixes.md`
- `code` MUST NOT be null when `severity` is `ERROR` or `CRITICAL`

### Responses

| HTTP | When |
|------|------|
| 201 | Stored. Body carries the `recordId` |
| 400 | Schema validation failed. `details` lists the offending fields |
| 500 | Stored nowhere — the database rejected the write or was unreachable |
| 503 | The aggregator is not ready to accept records |

A 400 means the record is malformed and MUST NOT be retried unchanged. A 500
or 503 is retryable — see the emission rules in `log-record.md`.

## `GET HOST/api/logs`

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

## `GET HOST/api/logs/:id`

Returns a single stored record. The path parameter is the `recordId` defined at
the top of this document, not the record's `id` field.

| HTTP | When |
|------|------|
| 200 | Found; body is the record |
| 404 | No record with that id |
| 500 | Query failed |
| 503 | Not ready |

## Authorization

`POST /api/logs` MUST require an app credential; any app that can reach it can
otherwise forge records attributed to another `id`. The two read endpoints
MUST require an operator credential — the aggregator holds every app's logs,
which makes it the highest-value read target in the estate.