---
name: sds-auth
description: BioEksen authentication and authorization conventions. Use when protecting an endpoint, deciding which credential a caller needs, validating a token, or choosing the error code for a rejected request.
---

# Authentication and Authorization

Two kinds of caller exist across the estate, and every protected endpoint
accepts exactly one of them.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

- `references/credentials.md` — token format, claims, lifetimes and rotation.

## Principals

| Principal | Is | Used for |
|-----------|-----|---------|
| **App** | A service acting as itself, with no human behind the call | Service-to-service calls, and submitting log records to the aggregator |
| **Operator** | A person, authenticated as themselves | Administrative endpoints — `GET /api/admin/logs`, the full health report, the aggregator's read endpoints |

There is no third kind. An endpoint that seems to need one is either
misdesigned or is an end-user endpoint belonging to a specific app's own
domain, which this skill does not cover.

An app credential MUST NOT satisfy an operator requirement, or any service
able to reach an admin endpoint could read every app's logs.

## Presenting a credential

```
Authorization: Bearer <token>
```

- Credentials MUST be sent in the `Authorization` header, never in a query
  string, path segment, or request body. A token in a URL is written into
  `ACCESS` log records, where `sds-logging` forbids it from appearing — and it
  is then retained, replicated to the aggregator, and visible to every
  operator.
- All endpoints requiring a credential MUST be served over TLS.
- Credentials MUST NOT appear in logs, error messages, `details` entries, or
  health output. See the forbidden list in `sds-logging/SKILL.md`.

## Validation order

Validate in exactly this order and stop at the first failure. The order is
fixed by the error code selection procedure in
`sds-logging/references/code-prefixes.md`, and the two MUST stay in step.

| Step | Condition | Code | HTTP |
|------|-----------|------|------|
| 1 | Source is over its failed-authentication allowance | `RATE-4400` | 429 |
| 2 | No `Authorization` header, or not a `Bearer` scheme | `AUTH-4100` | 401 |
| 3 | Token present but not parseable | `AUTH-4103` | 401 |
| 4 | Token parses, `exp` is in the past | `AUTH-4102` | 401 |
| 5 | Token parses, unexpired, signature or claims rejected | `AUTH-4101` | 401 |
| 6 | Verification needs the identity provider and it is unreachable | `AUTH-5500` | 503 |
| 7 | Authenticated; endpoint requires operator, caller is an app | `PERM-4151` | 403 |
| 8 | Authenticated; target belongs to another principal | `PERM-4152` | 403 |
| 9 | Authenticated; not permitted for any other reason | `PERM-4150` | 403 |

Expiry is checked before signature validity so that an expired token yields
`AUTH-4102` rather than `AUTH-4101`. The distinction matters operationally:
one means a client needs to refresh, the other means something is wrong.

Rate limiting is checked before authentication so that a throttled caller is
told it has been throttled, rather than receiving the same authentication
failure it is already retrying.

Authentication is evaluated before request validation, so an unauthenticated
caller never receives an error describing the payload shape — including
`VAL-4000`, which would otherwise reveal whether the body parsed.

## What a rejection may say

A 401 or 403 response MUST NOT reveal whether the target exists, which claim
failed, or whether the principal exists. The `code` distinguishes the cases
for the caller's own client; `message` and `details` MUST NOT add specifics.

The log record for the rejection carries the full reason, since it goes to
operators rather than to the caller. Those records are `SECURITY` type, which
follows automatically from the `AUTH-`/`PERM-` prefix.

## Requirements by endpoint

Drawn from the endpoints already specified elsewhere:

| Endpoint | Principal |
|----------|-----------|
| `GET /api/health/live` | None |
| `GET /api/health/ready` | None |
| `GET /api/health` | Operator |
| `GET /api/admin/logs` | Operator |
| `POST HOST/api/logs` | App |
| `GET HOST/api/logs`, `GET HOST/api/logs/:id` | Operator |

The two probe endpoints are deliberately unauthenticated: they expose nothing,
and a probe that can fail on credential expiry is a probe that will eventually
take a healthy service out of rotation.

## Rate limiting

Failed authentication MUST be rate limited per source. Once the limit is
exceeded the response is `RATE-4400` / 429, which takes precedence over
repeating the authentication failure — this is step 1 of the validation order
above. Default rate limit is 10 failures per minute per source, but the service
MAY choose a different limit.