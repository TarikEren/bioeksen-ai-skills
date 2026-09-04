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

| # | Condition | Code |
|---|-----------|------|
| 1 | Caller exceeded its request allowance | `RATE-4400` |
| 2 | No credential supplied | `AUTH-4100` |
| 3 | Credential supplied but not parseable as one | `AUTH-4103` |
| 4 | Credential parses, expiry is in the past | `AUTH-4102` |
| 5 | Credential parses, not expired, not accepted | `AUTH-4101` |
| 6 | Identity provider could not be reached to verify | `AUTH-5500` |
| 7 | Authenticated; endpoint requires operator, caller is not | `PERM-4151` |
| 8 | Authenticated; target belongs to another principal | `PERM-4152` |
| 9 | Authenticated; not permitted for any other reason | `PERM-4150` |
| 10 | Request body present but unparseable | `VAL-4000` |
| 11 | Required field absent from body | `VAL-4001` |
| 12 | Field present, value outside its enumeration | `VAL-4002` |
| 13 | Query parameter present but unparseable | `VAL-4003` |
| 14 | `endDate` earlier than `startDate` | `VAL-4004` |
| 15 | `page` below 1, or `limit` above its maximum | `VAL-4005` |
| 16 | Named resource does not exist | `RES-4200` |
| 17 | Resource being created already exists | `RES-4300` |
| 18 | Resource changed under a concurrent write | `RES-4301` |
| 19 | Required configuration value absent at startup | `CFG-5000` |
| 20 | Configuration value present but unusable | `CFG-5001` |
| 21 | Database connection could not be established | `DB-5500` |
| 22 | Connection pool exhausted before a connection was free | `DB-5501` |
| 23 | Connection held; read statement failed | `DB-5000` |
| 24 | Connection held; write statement failed | `DB-5001` |
| 25 | Transaction rolled back | `DB-5002` |
| 26 | Cache connection could not be established | `CACHE-5500` |
| 27 | Cache reachable; operation failed | `CACHE-5000` |
| 28 | Upstream service returned no response | `UP-5500` |
| 29 | Upstream service exceeded the call timeout | `UP-5501` |
| 30 | Upstream responded; body unusable or unexpected | `UP-5000` |
| 31 | Job invoked with unusable parameters | `JOB-4000` |
| 32 | Job exceeded its time budget | `JOB-5001` |
| 33 | Job failed for any other reason | `JOB-5000` |
| 34 | Log record rejected as malformed | `LOG-4000` |
| 35 | Log aggregator could not be reached | `LOG-5500` |
| 36 | Log submission rejected for any other reason | `LOG-5000` |
| 37 | App not yet ready to serve | `SYS-5500` |
| 38 | Anything else | `SYS-5000` |

The order is deliberate at two points.

Rate limiting is evaluated first, so a caller past its allowance receives
`RATE-4400` rather than a repetition of the failure it is retrying — otherwise
a client hammering an expired credential is told only that the credential is
expired, and never that it has been throttled.

Authentication is then evaluated before validation, so an unauthenticated
caller MUST NOT receive an error that describes the shape of the payload —
including `VAL-4000`, which would otherwise reveal whether the body parsed.

`sds-auth/SKILL.md` restates steps 1-9 as its validation order. The two MUST
stay in step.

## Derived attributes

Given the code, everything else follows. No implementer decides these.

**HTTP status** — from the number, per the range table in `error-codes.md`.

**Severity**

| Rule | Severity |
|------|----------|
| Any `4xxx` code | `WARNING` |
| Any `5xxx` code | `ERROR` |
| `DB-5500`, `CFG-5000`, `CFG-5001`, `SYS-5500` | `CRITICAL` |

The `CRITICAL` row wins where it applies. A record with no code carries no
severity constraint from this document.

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

## RES — resource state

| Code | HTTP | Meaning |
|------|------|---------|
| `RES-4200` | 404 | Resource does not exist |
| `RES-4300` | 409 | Resource already exists |
| `RES-4301` | 409 | Conflicting concurrent update |

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
