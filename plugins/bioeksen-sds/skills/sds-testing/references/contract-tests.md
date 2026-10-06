# Contract Tests

The cases a BioEksen service's tests MUST contain for each convention it
implements, written before the code, per `SKILL.md`. A service with no list
endpoint needs no list cases; a service that serves one needs all of them.

Each case restates one assertion and names its **Source**, the document
normative for it. Where a case names a code or a status, the source is right
and this table only restates it: invariant 11 checks every code here against
the registry and every status against its code, and requires a case for every
step of the validation order. An empirical value — a threshold, a timeout — is
the app's configured value, never a number copied into the test.

For the four standard endpoints, the project kit's conformance check already
runs the cases visible from outside a service. Its own tests still cover what
it logs and what it calls.

## Errors

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Envelope | Any endpoint | A request fails | The body has `status: fail`, `code`, `message` and `details`, and `code` is a registered code | `sds-api-design/references/openapi.yaml` |
| Status from the code | Any failure | The response is sent | Its HTTP status is the one its code's range maps to | `sds-logging/references/error-codes.md` |
| Same code in the log | A request that fails | Its failure is logged | The log record's `code` equals the response's `code` | `sds-logging/references/log-record.md` |
| Severity from the code | A failure | It is logged | `WARNING` for a 4xxx code, `ERROR` for a 5xxx code, `FATAL` where the derived attributes say so | `sds-logging/references/code-prefixes.md` |
| Fixed prose | A failure | It is logged | `message` starts with the code's meaning, its first letter lowercased, followed by the logfmt tail | `sds-logging/references/code-prefixes.md` |
| First fault wins | A body missing one field and carrying an unknown enumeration value in another | It is submitted | 400 `VAL-4001`, with both faults in `details` | `sds-logging/references/error-codes.md` |
| Invalid field value | A body field of the wrong type, format or range | It is submitted | 400 `VAL-4006` | `sds-logging/references/code-prefixes.md` |
| Unknown body field | A body carrying a field the endpoint does not define | It is submitted | 400 `VAL-4007` | `sds-api-design/references/app-endpoints.md` |
| Dangling reference | A body field naming a related record that does not exist | It is submitted | 400 `VAL-4006`, with that field in `details` | `sds-logging/references/code-prefixes.md` |
| Unserved method | A path that exists | It is called with a method it does not serve | 405 `RES-4500` | `sds-logging/references/code-prefixes.md` |
| Missing resource | An id no resource has | It is requested | 404 `RES-4200` | `sds-logging/references/code-prefixes.md` |
| Duplicate key | A write setting a unique key another record already holds | It is submitted | 409 `RES-4300` | `sds-logging/references/code-prefixes.md` |
| Still referenced | A record other records refer to | It is deleted | 409 `RES-4302` | `sds-logging/references/code-prefixes.md` |
| Domain rule | A resource whose current state forbids an operation | The operation is requested | 409 `RES-4302`, the rule named in `message` | `sds-logging/references/code-prefixes.md` |
| Unhandled | A failure nothing handles | It reaches the edge | 500 `SYS-5000`, with no stack trace in the body | `sds-logging/references/code-prefixes.md` |
| Not implemented | An operation the contract names that no code implements yet | It is called | 500 `SYS-5000`, never a 501 | `sds-logging/references/code-prefixes.md` |

## Database

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Concurrent write | Two writes to one record, the second made from a version that is no longer current | The second is submitted | 409 `RES-4301` | `sds-logging/references/code-prefixes.md` |
| Pool exhausted | No pooled connection free within the pool's timeout | A request needs one | 503 `DB-5501` | `sds-logging/references/code-prefixes.md` |
| Database down | A database that refuses connections | A request needs it | 503 `DB-5500` | `sds-logging/references/code-prefixes.md` |
| Constraint validated first | A value a database check constraint would refuse | It is submitted | 400 `VAL-4006` from validation, before the database sees it | `sds-logging/references/code-prefixes.md` |

## Correlation

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Adopted | A request carrying `X-Request-Id: abc123` | It is handled | The response echoes `abc123`, and every record logged for it carries `request=abc123` | `sds-logging/references/log-record.md` |
| Generated | A request with no `X-Request-Id` | It is handled | The response carries one in the identifier format | `sds-logging/references/log-record.md` |
| Replaced | A request whose `X-Request-Id` is malformed | It is handled | It still succeeds, and the response carries a fresh identifier, not the malformed one | `sds-logging/references/log-record.md` |
| Echoed on errors | A request that fails | The error response is sent | It echoes `X-Request-Id` too | `sds-logging/references/log-record.md` |
| Propagated | A request that leads to a call to another BioEksen service | The call is made | It carries the adopted `X-Request-Id` | `sds-logging/references/log-record.md` |

## Responses

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Success body | A request that succeeds | The response is sent | `status: ok`, with the payload beside it at the top level | `sds-api-design/references/app-endpoints.md` |
| List defaults | A list endpoint | It is called with neither `page` nor `limit` | `filterParams` echoes `page: 1` and `limit: 50` | `sds-api-design/references/app-endpoints.md` |
| Limit too low | A list endpoint | It is called with `limit=0` | 400 `VAL-4005` | `sds-logging/references/code-prefixes.md` |
| Limit too high | A list endpoint | It is called with `limit=201` | 400 `VAL-4005` | `sds-logging/references/code-prefixes.md` |
| Past the last page | A list with fewer records than one page | Page 2 is requested | 200, an empty array, and the true `totalCount` | `sds-api-design/references/app-endpoints.md` |
| Create | A collection | A member is created | 201, a `Location` header naming the member, and the member in the body | `sds-api-design/references/app-endpoints.md` |
| Merge Patch | A member | A JSON Merge Patch sets one field to `null` and leaves another out | The first field is removed and the second unchanged | `sds-api-design/references/app-endpoints.md` |
| Delete | A member | It is deleted | 204, with no body | `sds-api-design/references/app-endpoints.md` |
| No store | Any of the four standard endpoints | It is called | The response carries `Cache-Control: no-store` | `sds-api-design/references/standard-api-endpoints.md` |

## Throttling

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Retry-After | A caller over its allowance | It sends another request | 429 `RATE-4400`, carrying `Retry-After` in whole seconds | `sds-api-design/references/standard-api-endpoints.md` |

## Service calls

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Deadline passed on | An inbound `X-Request-Deadline-Ms` | The service calls another | The outbound value is no more than what remains of the inbound one or of the configured default, whichever is less | `sds-api-design/references/service-calls.md` |
| Too little time | An inbound deadline shorter than the work needs | The request arrives | 503 `UP-5501`, before the work starts | `sds-api-design/references/service-calls.md` |
| Timed-out POST | A `POST` without an `Idempotency-Key` that times out | The caller handles the failure | It does not retry | `sds-api-design/references/service-calls.md` |
| Replayed key | A `POST` repeated with the same key and body after the original completed | It is sent | The stored response, echoing the current request's `X-Request-Id` | `sds-api-design/references/service-calls.md` |
| Reused key | The same key with a different body | It is sent | 409 `RES-4301` | `sds-api-design/references/service-calls.md` |
| 4xx does not trip | A target that answers 4xx | Calls to it keep failing | The circuit breaker stays closed | `sds-api-design/references/service-calls.md` |
| Open breaker | A target that failed the configured number of times in a row | The next call is made | It fails with `UP-5500` and no network attempt | `sds-api-design/references/service-calls.md` |
| Retry-After honoured | A target that answers 429 with `Retry-After` | The caller retries | Not before that interval has passed | `sds-api-design/references/service-calls.md` |

## Auth

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Over the limit | A source over its failed-authentication allowance | It sends another bad credential | 429 `RATE-4400`, not a repeat of the authentication failure | `sds-auth/SKILL.md` |
| No credential | A request with no `Authorization` header | A protected endpoint is called | 401 `AUTH-4100` | `sds-auth/SKILL.md` |
| Unparseable | `Authorization: Bearer not-a-jwt` | A protected endpoint is called | 401 `AUTH-4103` | `sds-auth/SKILL.md` |
| Expired | A token whose `exp` passed beyond the skew allowance | A protected endpoint is called | 401 `AUTH-4102` | `sds-auth/SKILL.md` |
| Expired and forged | An expired token that also carries a bad signature | A protected endpoint is called | 401 `AUTH-4102`, because expiry is checked first | `sds-auth/SKILL.md` |
| Bad signature | An unexpired token signed by a key the verifier does not trust | A protected endpoint is called | 401 `AUTH-4101` | `sds-auth/SKILL.md` |
| Wrong audience | An unexpired token whose `aud` names another app | It is presented here | 401 `AUTH-4101` | `sds-auth/references/credentials.md` |
| Issuer unreachable | A token with an unknown `kid` while the key fetch fails | A protected endpoint is called | 503 `AUTH-5500` | `sds-auth/references/credentials.md` |
| App at an operator endpoint | A valid app credential | An operator endpoint is called | 403 `PERM-4151` | `sds-auth/SKILL.md` |
| Person without the role | A delegated token with the operator scope and no `operator` role | An operator endpoint is called | 403 `PERM-4151` | `sds-auth/references/credentials.md` |
| Another principal's resource | A submitted log record whose `id` is another app's | It reaches the aggregator | 403 `PERM-4152` | `sds-logging/references/aggregator-api.md` |
| Missing role | An app credential without the role the endpoint requires | The endpoint is called | 403 `PERM-4150` | `sds-auth/references/credentials.md` |
| Says nothing more | Any 401 or 403 | The response is sent | `message` and `details` name no claim, and reveal nothing about the target or the principal | `sds-auth/SKILL.md` |
| Refresh lead | An app credential whose lifetime, read from `exp`, is L | The app keeps running | It refreshes at 75% of L, before any request is rejected | `sds-auth/references/credentials.md` |
| Open probes | A request with no credential | `GET /api/health/live` or `GET /api/health/ready` is called | It is answered without a 401 | `sds-auth/SKILL.md` |

## Logging

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| No secrets | A request carrying a bearer token | It is handled and logged | The token appears in no record | `sds-logging/SKILL.md` |
| Code on failure | An `ERROR` or `FATAL` record | It is written | Its `code` is not null | `sds-logging/references/log-record.md` |
| One line | A failure whose context contains a newline | It is logged | The record's `message` is a single line | `sds-logging/references/log-record.md` |
| Aggregator down | An unreachable aggregator | A request is handled | It succeeds, and no slower than with the aggregator up | `sds-logging/references/log-record.md` |
| Malformed record | An aggregator that answers 400 | The submission is handled | It is not retried, and the app records `LOG-4000` locally | `sds-logging/references/log-record.md` |
| Aggregator unavailable | An aggregator that answers 503 | Records keep coming | They are buffered and retried behind the breaker, the oldest dropped first when the buffer is full | `sds-logging/references/log-record.md` |
| Batch rejected | A batch answered 400 naming two records | The app resubmits | Without those two, under a new `Idempotency-Key` | `sds-logging/references/aggregator-api.md` |

## Health

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Live ignores dependencies | A database that is down | `GET /api/health/live` is called | It answers 200 | `sds-api-design/references/standard-api-endpoints.md` |
| Ready gates on dependencies | A dependency that gates traffic is down | `GET /api/health/ready` is called | It answers 503, with `status: fail` | `sds-api-design/references/standard-api-endpoints.md` |
| Not ready yet | An app still starting | `GET /api/admin/logs` is called | 503 `SYS-5500`, in the error envelope | `sds-api-design/references/standard-api-endpoints.md` |
| Health needs an operator | A request with no credential | `GET /api/health` is called | 401 `AUTH-4100` | `sds-api-design/references/standard-api-endpoints.md` |
