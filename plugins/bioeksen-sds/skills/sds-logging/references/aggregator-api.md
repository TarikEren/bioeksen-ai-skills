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
adds two values of its own. `recordId` is the identifier it assigns to a stored
row on write. It is not part of a submitted record, and it is not the record's
`id` field, which names the emitting app. It is returned by every endpoint
below and is what `GET HOST/api/v1/logs/:recordId` takes. `group` is the
`groupId` of the error group an `ERROR` or `FATAL` record belongs to, per
**Groups**, and `null` on every other record. `chain` is an `AUDIT` record's
place in its day's hash chain, per **Audit records**, and `null` on every
other record.

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
  at most 8192 characters, whose `user=` value, if it carries one, is a
  lowercase principal key — see `log-record.md`
- `timestamp` MUST be RFC 3339 with at least millisecond precision
- `code`, when not null, MUST be a code listed in `code-prefixes.md` — which
  the schema enforces by enumerating them, so an unlisted code fails validation
  rather than being stored
- `code` MUST NOT be null when `severity` is `ERROR` or `FATAL`
- `severity` MUST NOT be `DEBUG`: a `DEBUG` record never leaves the app that
  wrote it, per `log-record.md`, so one submitted is refused with `VAL-4006`
- A submission carrying `recordId`, `group` or `chain` MUST be rejected with
  `VAL-4007`, as any field outside the six is. The aggregator assigns both; an
  app that believes it chooses them should find that out at once rather than
  have the value silently dropped

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
them. Two parameters differ:

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `id` | string | all | The emitting service, app or process. On an app's own endpoint every record has the same value; here it selects between apps |
| `startDate` | RFC 3339 | 90 days before now | Inclusive lower bound on `timestamp`. Never clamped — see **Retention** |

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
            "message": "write failed request=8c21",
            "group": "01J9Z4K7XQ2M8N3P5R6S7T8V9W",
            "chain": null
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
the top of this document, not the record's `id` field. Besides an operator, the
git service's integration calls it, to find the group of a record a
`Fixes-Log:` trailer names (**Authorization**).

| HTTP | When |
|------|------|
| 200 | Found; body is the record |
| 401 | No credential, or one that does not validate |
| 403 | Authenticated, but neither an operator nor an app holding `logs.resolve` |
| 404 | No record with that `recordId`: none was stored, or it was deleted when its window ended or when its group's cap counted it — `RES-4200` |
| 429 | Over the caller's allowance — `RATE-4400`, carrying `Retry-After` |
| 500 | Query failed |
| 503 | Not ready |

## `GET HOST/api/v1/codes`

Returns every error code this aggregator accepts: the registry in
`code-prefixes.md` of the `bioeksen-sds` release it was built from.

The aggregator refuses a record whose code it does not list with 400
`VAL-4002`, and a refused record never reaches the archive. An app's release
can carry a code its own registry gained after the running aggregator was
built, so release verification reads this endpoint, and refuses a release
whose build carries a code missing from it, per `sds-ci/SKILL.md`. The
aggregator is then always deployed first, and a new code is never refused.

The codes are checked against the code format, never against the `ErrorCode`
enumeration: the list exists to compare two registries, so a reader built from
an older release must still read one that holds a newer code.

### Response

```json
{
    "status": "ok",
    "codes": ["AUTH-4100", "AUTH-4101", "AUTH-4102"]
}
```

`codes` holds every code accepted, each once, in ascending order.

### Responses

| HTTP | When |
|------|------|
| 200 | The codes this aggregator accepts |
| 401 | No credential, or one that does not validate |
| 403 | Authenticated, but neither an app holding `logs.write` nor an operator |
| 429 | Over the caller's allowance — `RATE-4400`, carrying `Retry-After` |
| 503 | Not ready |

## Groups

The aggregator assigns every `ERROR` and `FATAL` record to an error **group**
when it stores the record, except an `AUDIT` record, which is never grouped. A
group is one failure, however often it happens:

```
group     = (id, code, op, signature)
signature = the first 16 hex digits of sha256(normalize(error) + " <- " + normalize(cause))
```

- `op`, `error` and `cause` are the record's reserved tail keys, per
  `log-record.md`. A key the record does not carry counts as empty, and a
  record without `op` is in a group whose `op` is null.
- Normalisation keeps error names, and replaces numbers, UUIDs, hex strings
  and quoted strings with placeholders, so two occurrences of one failure that
  differ only in the values they name share a signature. That is why every
  error class sets its name explicitly, per `log-record.md`.
- The aggregator computes the signature, and an app sends no hash. One
  implementation means the normalisation can be improved without redeploying
  any app.
- One `(id, code, op)` holds at most 20 signatures. Every further signature
  joins that triple's `overflow` group, so a failure whose text varies in a way
  the normalisation misses cannot create groups without limit.
- A group's `groupId` is a ULID, assigned when its first record arrives, and
  every record of the group carries it as `group`.

### States

| State | Entered when |
|-------|--------------|
| `open` | The group's first record arrives. The aggregator alerts its operators |
| `linked` | An issue naming the group opens, or reopens |
| `fix_merged` | A pull request merges, bringing a commit whose `Fixes-Log:` trailer names a record of the group |
| `resolved` | A release carrying that commit's Change-Id is deployed |
| `closed` | The issue closes without a merged fix, with exactly one closure label |

An issue links to a group, never to single records: every record of the
group carries the link, those already stored and those still to come. An issue
names its group with a `Group: {groupId}` line, written when the issue is
opened from the group.

The aggregator enters `open` itself. Every other state comes from the git
service, through `PUT HOST/api/v1/groups/:groupId/issue`.

### Closure labels

| Label | Means |
|-------|-------|
| `close:external` | Caused outside BioEksen's code and configuration: an upstream or third-party service, the host, the network or power, or the user's browser environment |
| `close:wont-fix` | Our defect, deliberately not fixed. The closing comment states its impact and why |
| `close:obsolete` | The code no longer exists. The closing comment names the Change-Id that removed it |
| `close:not-reproducible` | It cannot be reproduced, and has not recurred |

An issue closed without exactly one of these is not a closure: the git
service's integration reopens it with a comment, and the group stays as it
was. The label is required because a closed failure that comes back means
something different for each: an outside cause recurs while our code is
right, but an obsolete or unreproducible failure that recurs proves the
closure wrong.

Three failures are never closed this way, because they are ours to fix:

- A caller's bad input is not an `ERROR` at all. It is a `WARNING` with a
  4xxx code, per `SKILL.md`.
- A caller's input that produces an `ERROR` means validation is missing. It
  is fixed and resolved, never `close:external`.
- An expected condition logged as `ERROR` is a logging defect, and is fixed
  too.

### Recurrence

| The group is | A new record of it arrives | Then |
|--------------|----------------------------|------|
| `open` or `linked` | At any time | It is stored, and nothing changes |
| `fix_merged` | Before the fix's release is deployed | It belongs to the fix, and nothing changes |
| `resolved` | After the fix's release was deployed | **A regression.** The group returns to `linked`, its issue is reopened, and the aggregator alerts its operators |
| `closed` with `close:not-reproducible` or `close:obsolete` | At any time | The group returns to `linked`, and its issue is reopened |
| `closed` with `close:external` or `close:wont-fix` | At any time | It is stored, and nothing changes |

A group that returns to `linked` loses its Change-Id and its label. Its issue
keeps the history.

### Cap and counts

A group keeps whole its first 100 records and its latest 100. Every record is
stored when it arrives, so a 201 is always true. When a record leaves the
latest 100, and is not one of the first 100, it is deleted and counted instead:

- in an hourly count entry, `{start, count, firstSeen, lastSeen}`, kept for 7
  days;
- then merged into a daily count entry of the same form, kept as long as the
  group. A day begins at midnight UTC+03:00.

A group's first count entry makes the aggregator alert its operators: the
failure is repeating beyond its cap. `GET HOST/api/v1/groups/:groupId/occurrences`
serves the entries, and a view of the logs shows them inline, as
`48,213 more DB-5001 (op="POST /api/v1/orders/[id]") 14:00–15:00`.

The first 100 are the failure as it began, which a fix is written from. The
latest 100 are the failure as it is now, which shows whether it changed.
Between them, a failure repeating a million times is the same record a million
times, so it costs a count, not a copy.

## `PUT HOST/api/v1/groups/:groupId/issue`

Moves a group to the state its issue is in, per **States**. The aggregator is
connected to the project's git provider, whose integration calls this endpoint as
an app holding `logs.resolve`:

| When, in the git service | Body |
|--------------------------|------|
| An issue naming the group by its `Group:` line opens, or reopens | `{"state": "linked", "issue": "<the issue>"}` |
| A pull request merges, bringing a commit whose `Fixes-Log:` trailer names a record of the group | `{"state": "fix_merged", "issue": "<the issue>", "changeId": "<that commit's Change-Id>"}` |
| A release carrying that Change-Id is deployed | `{"state": "resolved", "issue": "<the issue>", "changeId": "<the same Change-Id>"}` |
| The issue closes without a merged fix, with one closure label | `{"state": "closed", "issue": "<the issue>", "label": "<the label>"}` |

- `issue` names the issue as the git service does, by its URL or its key. For
  a fix no issue tracked, it names the pull request.
- The integration finds the group of a record a `Fixes-Log:` trailer names
  with `GET HOST/api/v1/logs/:recordId`. The trailer SHOULD name one of the
  group's first 100 records, which stay while the group is unresolved; one of
  the latest 100 can be counted away before the fix merges, and then names
  nothing.
- `changeId` is the Change-Id of the commit whose trailer named the record,
  per `sds-commit/SKILL.md`. It is present exactly in `fix_merged` and
  `resolved`, and ties the group to the change that fixed it, as that change's
  release-note entry ties it to its commit.
- `resolved` is entered only from `fix_merged`, with the same Change-Id.
  Anything else is refused with 409 `RES-4302`: a group is resolved by
  deploying the fix merged for it, and by nothing else.
- A group a fix has reached stays on the fix's path. The git service closes an
  issue when its fixing pull request merges, so a `closed` for a group in
  `fix_merged` or `resolved` leaves it unchanged, and is answered 200 with the
  group as it is.
- When a group's state changes, the aggregator stamps it with `changedAt`.
  Nothing else about its records changes: their six fields and their
  `recordId` are fixed when they are written.

### Request

```json
{
    "state": "fix_merged",
    "issue": "https://github.com/bioeksen/bio-inventory/issues/42",
    "changeId": "bio-inventory-20261007T101500-a3f9"
}
```

### Responses

| HTTP | When |
|------|------|
| 200 | The group, in the state it is now in |
| 400 | The link failed validation; `details` names the field |
| 401 | No app credential, or one that does not validate |
| 403 | Authenticated, but not an app holding `logs.resolve` — `PERM-4150`, which an operator credential never is |
| 404 | No group with that `groupId` — `RES-4200` |
| 409 | `resolved` for a group not in `fix_merged` by the same Change-Id — `RES-4302` |
| 429 | Over the caller's allowance — `RATE-4400`, carrying `Retry-After` |
| 500 | The write failed — `DB-5001` |
| 503 | Not ready |

## `GET HOST/api/v1/groups/:groupId/occurrences`

Returns a group's count entries, per **Cap and counts**: `hourly` for the last
7 days and `daily` for every earlier day, each oldest first, and each an empty
array when no record left the cap in that span.

### Response

```json
{
    "status": "ok",
    "groupId": "01J9Z4K7XQ2M8N3P5R6S7T8V9W",
    "hourly": [
        {
            "start": "2026-10-09T14:00:00.000+03:00",
            "count": 48213,
            "firstSeen": "2026-10-09T14:00:00.004+03:00",
            "lastSeen": "2026-10-09T14:59:59.870+03:00"
        }
    ],
    "daily": []
}
```

### Responses

| HTTP | When |
|------|------|
| 200 | The group's count entries |
| 401 | No operator credential, or one that does not validate |
| 403 | Authenticated, but not an operator |
| 404 | No group with that `groupId` — `RES-4200` |
| 429 | Over the caller's allowance — `RATE-4400`, carrying `Retry-After` |
| 500 | The query failed |
| 503 | Not ready |

## Retention

The aggregator is the estate's archive, and how long it keeps a record depends
on what the record is:

| Type | `INFO` | `WARNING` | `ERROR`, `FATAL` |
|------|--------|-----------|------------------|
| `APP`, `JOB` | 30 days | 90 days | As its group keeps it, per **Grouped records** |
| `ACCESS` | 14 days | 90 days | As for `APP` |
| `SECURITY` | 1 year | 1 year | As for `APP`, and never less than 1 year, unless its group's cap counts it |
| `AUDIT` | Forever | Forever | Forever, and never grouped |

- A window runs from the record's `timestamp`. The 30 days after a group is
  resolved or closed run from the group's `changedAt`.
- `DEBUG` is not in the table. A `DEBUG` record never reaches the aggregator,
  per `log-record.md`, which refuses one with `VAL-4006`.
- Forever means never deleted, never sampled, never capped by a storage
  quota, and never summarised. Every other record is kept whole until its
  window ends, then deleted, except a grouped record its group's cap counts
  instead, per **Cap and counts**. A store MAY keep counts of what it
  deleted, but nothing replaces an `AUDIT` record, which is also chained and
  never altered, per **Audit records**.

Each row answers the question its records are read for, for as long as that
question is asked:

- **`INFO`** is the volume: an `ACCESS` record per request, an `APP` record per
  state change. A month answers "what happened before this failed". `ACCESS`
  records are the most numerous, and who called what is asked within days, so
  they get two weeks.
- **`WARNING`** is a handled but degraded condition, and what matters is its
  pattern over time. A quarter is what a quarterly review reads, which is why
  the whole archive used to keep 90 days.
- **`SECURITY`** is kept a year at every severity. An intrusion is often found
  months after it began, and the investigation needs every failed sign-in
  since; a year is also what an audit of access commonly asks for.
- **`ERROR` and `FATAL`** are the evidence a fix is written from. Deleted on a
  fixed date, they can vanish while the fix is still being written; kept
  whole forever, the noise stays forever too. So a failure's records are kept
  while its group is unresolved, and 30 days beyond, for a regression to be
  compared against, and the cap keeps a failure that repeats to its first and
  latest hundred records, so the noise costs a count, not a copy.
- **`AUDIT`** is kept forever, because accountability does not expire: who
  changed what is asked years later, and a count cannot answer it.

`startDate` on `GET HOST/api/v1/logs` defaults to 90 days before now, the
window most records share. It is never clamped, unlike an app's own: no single
lower bound exists when each record has its own window, so an earlier
`startDate` returns whatever is still kept, `AUDIT` records from years ago
included, and `filterParams` echoes the value as requested.

An app's own `GET /api/admin/logs` reads a different store with a shorter
window. The two disagreeing is expected, not data loss.

### Grouped records

A grouped record is kept as its group's state says, within its group's cap:

| A group's records | Kept |
|-------------------|------|
| While the group is `open`, `linked` or `fix_merged` | Kept |
| Once the group is `resolved` or `closed` | Deleted 30 days after the state changed, unless the group returns to `linked` first |
| Arriving after a closure as `close:external` or `close:wont-fix` | Kept. Such a group keeps recurring without reopening, and its cap is what bounds it |
| A group's count entries | As long as the group |

A group itself, its state and its count entries, is never deleted. A record
that arrives years later is matched against it, and a regression is only a
regression while the fix it undoes is remembered.

## Audit records

An `AUDIT` record is the estate's accountability. It is kept forever, per
**Retention**, never grouped, capped or counted, per **Groups**, and never
altered:

- **Nothing deletes or alters one.** No endpoint, job or database role can.
  The aggregator's database user holds `INSERT` and `SELECT` on its table of
  audit records, and nothing else, so not even a defect in the aggregator can
  change one.
- **People are named only by `user=` and their principal key**, per
  `log-record.md`:
  never by a name, an email, a UPN or free text about them. When a person's
  data is erased, the employee directory is anonymised, and every audit record
  stays exactly as written while it no longer identifies anyone. Any other
  form would force a choice between breaking the rule above and keeping
  personal data forever.
- **The records of each day form a hash chain.** A day is the UTC+03:00
  calendar day a record arrives on. The aggregator gives each audit record a
  `chain`, and an app sends none:
  - `day` is that day;
  - `prev` is the `hash` of the record before it on that day. The day's first
    record carries the anchor of the last earlier day with audit records, and
    the first audit record of all carries 64 zeros;
  - `hash` is the SHA-256 digest, in lowercase hex, of the record's canonical
    JSON per RFC 8785: the record as `GET HOST/api/v1/logs/:recordId` returns
    it, without `chain.hash`.
- **A day's anchor is the `hash` of its last record.** The next day's first
  record carries it as `prev`, and when the day ends the aggregator emails it,
  with the day and the number of records, to a mailbox IT owns and the
  platform's administrators cannot alter.

Tampering is then detectable even by someone with full database access. An
altered record no longer hashes to its `hash`; a removed or inserted one breaks
the next record's `prev`; and a chain rewritten whole ends on an anchor other
than the one IT's mailbox received. Because the chain is cut into whole days,
old days can one day be removed without leaving the rest unverifiable: the
first remaining record still names an anchor IT holds.

These rules cannot change once the first audit record is written. Every record
written before the change would stop verifying, or keep the personal data the
change was meant to remove.

### Removing old days

Not built. When it is, it removes whole days, never single records. It needs
a requester and a different approver, under BioEksen's deletion policy, and it
writes an `AUDIT` record naming the days removed, their anchors, the requester
and the approver. Building it amends this section.

## Authorization

Both submission endpoints MUST require an app credential holding the
`logs.write` role from the registry in `sds-auth/references/credentials.md`,
and the credential MUST be the record's own. Requiring a credential is not enough by itself: any app
holding one could still submit records under another app's `id`, and the
forgery would pass every check that looks only at the credential.

The aggregator therefore resolves the token's `azp` — the client id of the
calling app — to a software id, and refuses a record whose `id` differs with
403 `PERM-4152`. That is step 9 of the selection procedure, so it takes
precedence over any validation fault in the same record. An `azp` that
resolves to no app is refused with `PERM-4150`: it names nothing the estate
knows.

The resolution is not the aggregator's configuration: it is served by
`bio-softop`'s registry, per **Configuration** in
`sds-auth/references/credentials.md`.

The read endpoints, `GET HOST/api/v1/logs`, `GET HOST/api/v1/logs/:recordId`
and `GET HOST/api/v1/groups/:groupId/occurrences`, MUST require an operator
credential — the aggregator holds every app's logs, which makes it the
highest-value read target in the estate. One exception: an app holding
`logs.resolve` MAY also call `GET HOST/api/v1/logs/:recordId`, which is how
the git service's integration finds the group of a record a `Fixes-Log:`
trailer names. It reads only the records commits name.

`GET HOST/api/v1/codes` MUST require an app credential holding `logs.write`,
or an operator credential. It returns the registry, which holds no record, and
an app that submits records is what has to know which codes are accepted.

`PUT HOST/api/v1/groups/:groupId/issue` MUST require an app credential holding
`logs.resolve`, which only the git service's integration holds. An operator
credential never satisfies it: a group's link follows its issue, so the place
to change it is the issue, in the git service, where the change is recorded
with the rest of the issue's history.