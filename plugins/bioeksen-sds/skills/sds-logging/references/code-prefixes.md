# Code Prefixes

The complete, closed list of error codes. A code is `<PREFIX>-<NNNN>`.

The log record's `id` field already says which app emitted a failure, so the
prefix says *what kind of failure it was*, not which app it came from. The
same code means the same thing in every app.

## Rule for assistants and generated code

**Every code you emit MUST appear verbatim in a table below. Never invent a
prefix, never invent a number, never abbreviate.**

If nothing fits, use `SYS-5000`. That is always the correct fallback —
inventing a code is never correct, because a code that exists in one place and
nowhere else is invisible to every filter, runbook and dashboard.

You never *choose* the HTTP status, severity, log type or message prose for a
failure. All four are determined by the code — see Derived attributes.

A code also decides what an error response's `details` holds, per
`sds-api-design/references/standard-api-endpoints.md`: the field errors for
`VAL-4001` to `VAL-4007`, and for any other code the object its entry below
defines, or `null` when it defines none. No entry defines one yet. Adding one
is a change to that code's entry, made here and nowhere else.

The list is enforced, not merely documented: `ErrorCode` in
`sds-api-design/references/openapi.yaml` enumerates these exact values, so an
unlisted code fails schema validation.

## Format

```
[A-Z][A-Z0-9]{1,7}-[45][0-9]{3}
```

There is exactly one `-` in a code, so it always splits unambiguously into
prefix and number. `4xxx` is the caller's fault, `5xxx` is the app's.

## Selection procedure

Evaluate in this order. **The first condition that holds determines the code;
stop there.** Do not weigh which code fits best — order decides.

Where a request has several faults at once, the code is still the first
condition that holds over all of them; the rest are reported as `details`
entries under that one code. See the rule in `error-codes.md`.

| # | Condition | Code |
|---|-----------|------|
| 1 | Caller is over a rate limit — its request allowance, or its failed-authentication allowance | `RATE-4400` |
| 2 | No credential supplied | `AUTH-4100` |
| 3 | Credential supplied but not parseable as one | `AUTH-4103` |
| 4 | Credential parses, expiry is in the past | `AUTH-4102` |
| 5 | Credential parses, not expired, not accepted | `AUTH-4101` |
| 6 | Identity provider could not be reached to verify | `AUTH-5500` |
| 7 | Authenticated; endpoint requires operator, caller is not | `PERM-4151` |
| 8 | Authenticated; target belongs to another principal | `PERM-4152` |
| 9 | Authenticated; not permitted for any other reason | `PERM-4150` |
| 10 | Path exists; the method is not one it serves | `RES-4500` |
| 11 | Request body larger than the endpoint accepts | `VAL-4550` |
| 12 | Request body in a media type the endpoint does not accept | `VAL-4600` |
| 13 | Request body present but unparseable | `VAL-4000` |
| 14 | Required field absent from body | `VAL-4001` |
| 15 | Field present, value outside its enumeration | `VAL-4002` |
| 16 | Query parameter present but unparseable | `VAL-4003` |
| 17 | `endDate` earlier than `startDate` | `VAL-4004` |
| 18 | `page` below 1, or `limit` outside 1 to its maximum | `VAL-4005` |
| 19 | Field or query parameter parses; value invalid for its type, format or range, or names a related record that does not exist | `VAL-4006` |
| 20 | Body carries a field the endpoint does not define | `VAL-4007` |
| 21 | Resource the request addresses does not exist | `RES-4200` |
| 22 | Resource being created, or a unique key a write sets, already exists | `RES-4300` |
| 23 | Resource changed under a concurrent write | `RES-4301` |
| 24 | Resource exists; its current state does not allow the operation | `RES-4302` |
| 25 | Required configuration value absent at startup | `CFG-5000` |
| 26 | Configuration value present but unusable | `CFG-5001` |
| 27 | Database connection could not be established | `DB-5500` |
| 28 | Connection pool exhausted before a connection was free | `DB-5501` |
| 29 | Connection held; read statement failed | `DB-5000` |
| 30 | Connection held; write statement failed | `DB-5001` |
| 31 | Transaction rolled back | `DB-5002` |
| 32 | Cache connection could not be established | `CACHE-5500` |
| 33 | Cache reachable; operation failed | `CACHE-5000` |
| 34 | Upstream service returned no response | `UP-5500` |
| 35 | Upstream service exceeded the call timeout | `UP-5501` |
| 36 | Upstream responded; body unusable or unexpected | `UP-5000` |
| 37 | Job invoked with unusable parameters | `JOB-4000` |
| 38 | Job exceeded its time budget | `JOB-5001` |
| 39 | Job failed for any other reason | `JOB-5000` |
| 40 | Log record rejected as malformed | `LOG-4000` |
| 41 | Log aggregator could not be reached | `LOG-5500` |
| 42 | Log submission rejected for any other reason | `LOG-5000` |
| 43 | App not yet ready to serve | `SYS-5500` |
| 44 | Anything else | `SYS-5000` |

The order is deliberate at three points.

Rate limiting is evaluated first, so a caller past its allowance receives
`RATE-4400` rather than a repetition of the failure it is retrying — otherwise
a client hammering an expired credential is told only that the credential is
expired, and never that it has been throttled.

Authentication is then evaluated before validation, so an unauthenticated
caller MUST NOT receive an error that describes the shape of the payload —
including `VAL-4000`, which would otherwise reveal whether the body parsed.

Method, size and media type are then evaluated before the body is parsed,
because a body the endpoint will not read cannot be validated — and still
after authentication, so an unauthenticated caller learns neither which
methods a path serves nor what an endpoint accepts.

`sds-auth/SKILL.md` restates steps 1-9 as its validation order, for readers
protecting an endpoint. **This table is the normative one**; where the two
disagree, this file wins and `sds-auth/SKILL.md` MUST be corrected. Changing a
condition here means changing it there in the same commit.

## Database failures

A database driver reports a failure in its own terms — a SQLSTATE, an ORM's
error class — and the code is still the first condition above that holds. This
table restates which condition each usual driver failure meets, so two apps on
different drivers answer the same failure with the same code. It names steps
by number; where it and the procedure disagree, the procedure wins.

| Database condition | Step | Code |
|--------------------|------|------|
| A unique or primary key violation | 22 | `RES-4300` |
| The row an update or delete addresses does not exist | 21 | `RES-4200` |
| A foreign key names a record that does not exist | 19 | `VAL-4006` |
| A delete refused because other rows still reference the row | 24 | `RES-4302` |
| A serialization failure, or an optimistic version that no longer matches | 23 | `RES-4301` |
| A transaction rolled back for any other reason | 31 | `DB-5002` |
| No pooled connection free within the pool's timeout | 28 | `DB-5501` |
| The database refused or dropped the connection | 27 | `DB-5500` |
| A check or not-null constraint violated | 30 | `DB-5001` |
| Any other failed read | 29 | `DB-5000` |
| Any other failed write | 30 | `DB-5001` |

A foreign key is a field's value, not the resource the request addresses.
`POST /api/v1/widgets` naming a `siteId` no site has addresses a collection
that exists, so a 404 would tell the caller the endpoint is missing. The field
is what is wrong: step 19 holds, before step 21 is reached, and `details` names
the field. A referenced record that exists but belongs to another principal is
step 8, `PERM-4152`, earlier still.

A check or not-null violation reaching the database means the app wrote a
value its own validation should have refused with `VAL-4001` or `VAL-4006`.
The fault is the app's, so the code is `DB-5001`, and the fix is the missing
validation rather than a 400 mapped from the driver's error.

## Derived attributes

Given the code, everything else follows. No implementer decides these.

**HTTP status** — from the number, per the range table in `error-codes.md`.

**Severity**

| Rule | Severity |
|------|----------|
| Any `4xxx` code | `WARNING` |
| Any `5xxx` code | `ERROR` |
| `DB-5500`, `CFG-5000`, `CFG-5001` | `FATAL` |
| `SYS-5500` after the app's startup budget has elapsed | `FATAL` |
| `DB-5501` sustained for more than 60 seconds | `FATAL` |

The `FATAL` row wins where it applies. A record with no code carries no
severity constraint from this document.

Two rows are conditional, and for the same reason: the condition they describe
is normal at one duration and an outage at another.

`SYS-5500`. An app reporting "not ready" during startup or a rolling deploy is
behaving correctly, and `FATAL` is defined in `SKILL.md` as something a
person must act on now — so emitting it on every deploy would page someone for
a healthy release, and train them to ignore the severity. Not-ready is `ERROR`
until the app has been given its configured time to come up, and `FATAL`
once it has missed that deadline, which is the point at which a person
genuinely does need to look.

`DB-5501`. A pool exhausted by a burst of traffic drains again on its own,
and `SKILL.md` is explicit that a condition nothing can be done about is an
`ERROR`. A pool that stays exhausted is a different thing: the app is serving
nobody, and no one has been told. Both unconditional answers are wrong in the
way this table has already been wrong once — always `ERROR` leaves a real
outage unpaged, and always `FATAL` pages on every traffic spike until the
severity means nothing.

Sixty seconds is an empirical value in the sense of
`sds-api-design/references/service-calls.md`: long enough to ride out a burst,
short enough that a genuine outage reaches someone within the minute. An app
MAY use a different figure and MUST record that it has.

**Log type**

| Rule | Type |
|------|------|
| Any `AUTH-` or `PERM-` code | `SECURITY` |
| Any `JOB-` code | `JOB` |
| Every other code | `APP` |

**Message prose**

The message MUST be the code's Meaning text below with only its first character
lowercased, otherwise unchanged, followed by the logfmt tail. `DB-5001` is
logged as `write failed request=8c21` — never `failed to create row`, never a
reworded variant. Context goes in the tail, never in the prose.

Only the first character changes, so identifiers keep their casing: `VAL-4004`
is logged as `endDate earlier than startDate request=8c21`, not
`enddate earlier than startdate`.

## AUTH — authentication

| Code | HTTP | Meaning |
|------|------|---------|
| `AUTH-4100` | 401 | Credential missing |
| `AUTH-4101` | 401 | Credential invalid |
| `AUTH-4102` | 401 | Credential expired |
| `AUTH-4103` | 401 | Credential malformed |
| `AUTH-5500` | 503 | Identity provider unavailable |

## PERM — authorization

| Code | HTTP | Meaning |
|------|------|---------|
| `PERM-4150` | 403 | Not permitted |
| `PERM-4151` | 403 | Operator role required |
| `PERM-4152` | 403 | Resource belongs to another principal |

## VAL — request validation

| Code | HTTP | Meaning |
|------|------|---------|
| `VAL-4000` | 400 | Request body malformed |
| `VAL-4001` | 400 | Required field missing |
| `VAL-4002` | 400 | Unknown value for an enumerated field |
| `VAL-4003` | 400 | Query parameter malformed |
| `VAL-4004` | 400 | endDate earlier than startDate |
| `VAL-4005` | 400 | Pagination out of range |
| `VAL-4006` | 400 | Field value invalid |
| `VAL-4007` | 400 | Unknown field |
| `VAL-4550` | 413 | Request body too large |
| `VAL-4600` | 415 | Unsupported media type |

## RES — resource state

| Code | HTTP | Meaning |
|------|------|---------|
| `RES-4200` | 404 | Resource does not exist |
| `RES-4300` | 409 | Resource already exists |
| `RES-4301` | 409 | Conflicting concurrent update |
| `RES-4302` | 409 | Operation not allowed in current state |
| `RES-4500` | 405 | Method not allowed |

## RATE — throttling

| Code | HTTP | Meaning |
|------|------|---------|
| `RATE-4400` | 429 | Rate limit exceeded |

## DB — database

| Code | HTTP | Meaning |
|------|------|---------|
| `DB-5000` | 500 | Query failed |
| `DB-5001` | 500 | Write failed |
| `DB-5002` | 500 | Transaction rolled back |
| `DB-5500` | 503 | Database unavailable |
| `DB-5501` | 503 | Connection pool exhausted |

## CACHE — cache

| Code | HTTP | Meaning |
|------|------|---------|
| `CACHE-5000` | 500 | Cache operation failed |
| `CACHE-5500` | 503 | Cache unavailable |

## UP — upstream services

For calls this app makes to another service.

| Code | HTTP | Meaning |
|------|------|---------|
| `UP-5000` | 500 | Upstream response unusable |
| `UP-5500` | 503 | Upstream unavailable |
| `UP-5501` | 503 | Upstream timed out |

## CFG — configuration

| Code | HTTP | Meaning |
|------|------|---------|
| `CFG-5000` | 500 | Required configuration missing |
| `CFG-5001` | 500 | Configuration value invalid |

## JOB — background work

| Code | HTTP | Meaning |
|------|------|---------|
| `JOB-4000` | 400 | Job parameters invalid |
| `JOB-5000` | 500 | Job failed |
| `JOB-5001` | 500 | Job timed out |

## LOG — logging and the aggregator

| Code | HTTP | Meaning |
|------|------|---------|
| `LOG-4000` | 400 | Log record malformed |
| `LOG-5000` | 500 | Log submission rejected |
| `LOG-5500` | 503 | Log aggregator unavailable |

## SYS — everything else

| Code | HTTP | Meaning |
|------|------|---------|
| `SYS-5000` | 500 | Unhandled error |
| `SYS-5500` | 503 | Not ready |

## Extending the list

Adding a code is a change made by a human, to this file **and** to the
`ErrorCode` enum in `sds-api-design/references/openapi.yaml`, and to the
selection procedure above. All three, or the code is not usable.

- A code, once listed, is permanent: never renumbered, never redefined, never
  reused for a different meaning.
- A retired code stays in its table marked retired rather than being deleted.
- A new number MUST keep the range-to-HTTP correspondence in
  `error-codes.md`.
- A new condition MUST be inserted at the position in the selection procedure
  where it is unambiguous, not appended.

### Domain failures

The codes above name failures every app can have. A failure only one app's
domain can have — an order already shipped, a balance too low — is handled in
one of two ways, and neither is inventing a code at the point of use:

- **No client branches on which rule refused the request.** It is
  `RES-4302`: the resource exists, and its current state does not allow the
  operation. The specific rule goes in the API response's `message` and in the
  log record's structured tail, e.g. `reason=already-shipped` — never in the
  log record's prose, and never in a code of its own.
- **A client must branch on it.** Then it needs a code, added here by a human
  under a prefix naming that domain, on exactly the terms above: the table,
  the selection procedure and the `ErrorCode` enum, in one commit.

The first is the default. A domain code is justified by a client that
behaves differently because of it, not by the failure being interesting.

### Not implemented

An operation the contract names but no code implements yet — a stub written so
that its tests can be seen failing first, per `sds-testing/SKILL.md` — is
`SYS-5000`, answered 500. No earlier condition in the procedure holds, so step
44 decides.

It is never 501. No range in `error-codes.md` maps to 501, and a code added
for a state every operation leaves before it ships would stay in the registry
forever, since codes are never retired from it. The response's `message` MAY
say the operation is not implemented, as `message` is written for people; the
log record's prose stays the code's own, `unhandled error`.
