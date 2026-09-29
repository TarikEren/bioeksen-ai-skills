# Log Aggregator API

The log aggregator collects and serves logs from every BioEksen app. Its host
is denoted `HOST`.

`aggregator-api.yaml` beside this file is the normative OpenAPI 3.1 definition
of these endpoints. This document is the rationale layer; where the two
disagree, the schema wins and this document MUST be corrected — the same
relationship `sds-api-design/references/standard-api-endpoints.md` has with
the schema beside it.

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

All six fields MUST be present; `code` MAY be `null`. Validation rules, every
one of which the schema enforces:

- `severity` and `type` MUST be members of their enumerations
- `id` MUST be in the software id format, and `message` MUST be one line of
  at most 8192 characters — see `log-record.md`
- `timestamp` MUST be RFC 3339 with at least millisecond precision
- `code`, when not null, MUST be a code listed in `code-prefixes.md` — which
  the schema enforces by enumerating them, so an unlisted code fails validation
  rather than being stored
- `code` MUST NOT be null when `severity` is `ERROR` or `FATAL`
- A submission carrying `recordId` MUST be rejected with `VAL-4007`, as any
  field outside the six is. The aggregator assigns it on write; an app that
  believes it chooses record identifiers should find that out at once rather
  than have the value silently dropped

### Responses

| HTTP | When |
|------|------|
| 201 | Stored. Body carries the `recordId`, and `Location` names the stored record |
| 400 | Schema validation failed. `details` lists the offending fields |
| 401 | No app credential, or one that does not validate |
| 403 | Authenticated, but not an app holding `logs.write`, which an operator credential never is — `PERM-4150`; or the record's `id` is not the submitting app's — `PERM-4152` |
| 409 | The `Idempotency-Key` is already spent on a different body — `RES-4301` |
| 429 | Over the caller's allowance — `RATE-4400`, carrying `Retry-After` |
| 500 | Stored nowhere — the database rejected the write, `DB-5001` |
| 503 | The aggregator is not ready to accept records, or its database is unreachable |

A 503 is retryable; a 400, 403, 409 or 500 is not. What an emitting app does
with each is the table under **Handling the aggregator's response** in
`log-record.md`.

## `POST HOST/api/v1/logs/batch`

Validates and stores up to 500 records in one request. An app that emits more
than occasionally SHOULD submit this way: every submission costs an
authenticated round trip, and an `ACCESS` record for every inbound request
would otherwise mean an outbound request for every inbound one.

### Request

```json
{
    "records": [
        {
            "id": "auth-service",
            "timestamp": "2026-09-03T14:05:00.123Z",
            "severity": "ERROR",
            "type": "APP",
            "code": "DB-5001",
            "message": "write failed request=8c21"
        }
    ]
}
```

- `records` holds 1 to 500 records, each validated exactly as a single
  submission is. More than 500 is `VAL-4006`. A body over 1 MiB is refused with
  413 `VAL-4550` before it is parsed.
- Every record's `id` MUST be the submitting app's, as for a single
  submission. One that is not refuses the whole batch with 403 `PERM-4152`.
- The batch is all or nothing: every record is stored, or none is.
- A 400 names each failing record by its position — a `details` entry's
  `field` is `records[3].severity`. The app removes those records and
  resubmits the rest, which is a changed body and so goes under a fresh
  `Idempotency-Key`.

All or nothing keeps one status per response and one meaning per idempotency
key. Partial success would need a status per record, and a retry of a partly
stored batch would have to know which half to send again.

### Responses

| HTTP | When |
|------|------|
| 201 | Every record stored. Body carries their `recordId`s, in submission order |
| 400 | At least one record failed validation, and none was stored. `details` names each by position |
| 401 | No app credential, or one that does not validate |
| 403 | As for a single submission — `PERM-4150` or `PERM-4152` |
| 409 | The `Idempotency-Key` is already spent on a different body — `RES-4301` |
| 429 | Over the caller's allowance — `RATE-4400`, carrying `Retry-After` |
| 500 | Stored nowhere — the database rejected the write, `DB-5001` |
| 503 | The aggregator is not ready to accept records, or its database is unreachable |

An emitting app handles each exactly as it handles the same status from a
single submission.

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

### Responses

| HTTP | When |
|------|------|
| 200 | Matching records, newest first. A page beyond the last returns an empty `logs` array and the true `totalCount` |
| 400 | A query parameter failed validation |
| 401 | No operator credential, or one that does not validate |
| 403 | Authenticated, but not an operator |
| 429 | Over the caller's allowance — `RATE-4400`, carrying `Retry-After` |
| 500 | The query failed |
| 503 | Not ready |

### Retention

The aggregator keeps records for **90 days**. It is the estate's archive: the
90 days is what makes a quarterly incident review possible and what any
"when did this start?" investigation reads.

`startDate` defaults to the start of that window, and a `startDate` earlier
than it is clamped rather than rejected, per the rule in
`sds-api-design/references/standard-api-endpoints.md`. `filterParams` echoes
the clamped value, so a caller asking for a year sees what it actually got.

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
| 401 | No operator credential, or one that does not validate |
| 403 | Authenticated, but not an operator |
| 404 | No record with that `recordId` — `RES-4200` |
| 429 | Over the caller's allowance — `RATE-4400`, carrying `Retry-After` |
| 500 | Query failed |
| 503 | Not ready |

## Authorization

Both submission endpoints MUST require an app credential holding the
`logs.write` role from the registry in `sds-auth/references/credentials.md`,
and the credential MUST be the record's own. Requiring a credential is not enough by itself: any app
holding one could still submit records under another app's `id`, and the
forgery would pass every check that looks only at the credential.

The aggregator therefore resolves the token's `azp` — the client id of the
calling app — to a software id, and refuses a record whose `id` differs with
403 `PERM-4152`. That is step 8 of the selection procedure, so it takes
precedence over any validation fault in the same record. An `azp` that
resolves to no app is refused with `PERM-4150`: it names nothing the estate
knows.

The resolution is the aggregator's configuration today, derivable from the
directory by the Application ID URI convention in
`sds-auth/references/credentials.md`, and a lookup against the id-issuing
service once one exists.

The two read endpoints
MUST require an operator credential — the aggregator holds every app's logs,
which makes it the highest-value read target in the estate.