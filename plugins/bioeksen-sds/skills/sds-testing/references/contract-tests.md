# Contract Tests

The cases a BioEksen service's tests MUST contain for each convention it
implements, each seen failing for the missing behaviour in the project's test
order, per `SKILL.md`. A service with no list
endpoint needs no list cases; a service that serves one needs all of them.

Each case restates one assertion and names its **Source**, the document
normative for it. Where a case names a code or a status, the source is right
and this table only restates it: invariant 11 checks every code here against
the registry and every status against its code, and requires a case for every
step of the validation order. An empirical value — a threshold, a timeout — is
the app's configured value, never a number copied into the test.

For the five standard endpoints, the conformance check this skill ships,
`sds-testing/scripts/check_service.py`, already runs the cases visible from
outside a service. Its own tests still cover what
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
| Body too large | A body one byte over the endpoint's limit: 1 MiB, unless the app records another | It is submitted | 413 `VAL-4550` | `sds-api-design/references/standard-api-endpoints.md` |
| Understated length | A body over the limit sent chunked, or under a `Content-Length` that understates it | It is submitted | 413 `VAL-4550`, refused before it is read whole | `sds-api-design/references/standard-api-endpoints.md` |
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
| No store | Any of the five standard endpoints | It is called | The response carries `Cache-Control: no-store` | `sds-api-design/references/standard-api-endpoints.md` |

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
| Version 1 token | An unexpired version 1 token from the configured tenant | A protected endpoint is called | 401 `AUTH-4101` | `sds-auth/references/credentials.md` |
| Keyed by oid | Two tokens for one person, with the same `oid` and `tid` and different `sub` values | Each is presented | The app treats them as one person, and its records name them by the same `user=` | `sds-auth/references/credentials.md` |
| Issuer unreachable | A token with an unknown `kid` while the key fetch fails | A protected endpoint is called | 503 `AUTH-5500` | `sds-auth/references/credentials.md` |
| Foreign origin | A request whose `Origin` is another site's | An endpoint that accepts only its app's own origin is called | 403 `PERM-4153` | `sds-auth/SKILL.md` |
| Origin before role | A non-operator's request from another site | An operator endpoint that accepts only its app's own origin is called | 403 `PERM-4153`, not `PERM-4151` | `sds-logging/references/code-prefixes.md` |
| App at an operator endpoint | A valid app credential | An operator endpoint is called | 403 `PERM-4151` | `sds-auth/SKILL.md` |
| Person without the role | A delegated token with the operator scope and no `operator` role | An operator endpoint is called | 403 `PERM-4151` | `sds-auth/references/credentials.md` |
| Another principal's resource | A submitted log record whose `id` is another app's | It reaches the aggregator | 403 `PERM-4152` | `sds-logging/references/aggregator-api.md` |
| Missing role | An app credential without the role the endpoint requires | The endpoint is called | 403 `PERM-4150` | `sds-auth/references/credentials.md` |
| Employee without the company role | An employee's token without the company role an endpoint of the app requires | The endpoint is called | 403 `PERM-4150` | `sds-auth/references/credentials.md` |
| App at an employee endpoint | A valid app credential | An endpoint that requires an employee is called | 403 `PERM-4150` | `sds-auth/references/credentials.md` |
| Says nothing more | Any 401 or 403 | The response is sent | `message` and `details` name no claim, and reveal nothing about the target or the principal | `sds-auth/SKILL.md` |
| Refresh lead | An app credential whose lifetime, read from `exp`, is L | The app keeps running | It refreshes at 75% of L, before any request is rejected | `sds-auth/references/credentials.md` |
| Open probes | A request with no credential | `GET /api/health/live` or `GET /api/health/ready` is called | It is answered without a 401 | `sds-auth/SKILL.md` |

## Logging

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| No secrets | A request carrying a bearer token | It is handled and logged | The token appears in no record | `sds-logging/SKILL.md` |
| Id from the file | An app built from its repository, or from its directory in a monorepo | It writes a record | The record's `id` is the content of the nearest `.bioeksen/software-id` above the app's code, never the monorepo's own | `sds-logging/references/log-record.md` |
| Code on failure | An `ERROR` or `FATAL` record | It is written | Its `code` is not null | `sds-logging/references/log-record.md` |
| One line | A failure whose context contains a newline | It is logged | The record's `message` is a single line | `sds-logging/references/log-record.md` |
| No stack | A failure that carries a stack trace | It is logged | The record's `message` holds no stack; a stack, if kept, goes to stderr with the same `code` and `request=` | `sds-logging/references/log-record.md` |
| Own text in the tail | A failure whose error says more than its code's meaning | It is logged | The prose is the code's meaning, and the error's name and text are under `error=`, as `Name: message` | `sds-logging/references/log-record.md` |
| Name survives the build | An error class the app defines, in a production build | An error of it is logged | `error=` carries the name the class sets, not one the build derived | `sds-logging/references/log-record.md` |
| Operation from a template | A request to a path carrying an identifier | It fails and is logged | `op=` carries the operation's template, and not the identifier | `sds-logging/references/log-record.md` |
| Person by oid | A request by a signed-in person | A record names them | It carries `user=` and the `oid` of their token, and no name, email or UPN | `sds-logging/references/log-record.md` |
| Redacted cause | A driver error quoting a connection string with a password | It is logged | The password appears in no record | `sds-logging/references/log-record.md` |
| Level from LOG_LEVEL | `LOG_LEVEL` set to `WARNING` | An `INFO` event happens | No record of it is written | `sds-logging/SKILL.md` |
| DEBUG stays local | `LOG_LEVEL` set to `DEBUG` | A `DEBUG` event happens | It is in the record outbox, and is never submitted | `sds-logging/references/log-record.md` |
| Outbox first | An unreachable aggregator | A record is written | `GET /api/admin/logs` returns it, though no submission has succeeded | `sds-logging/references/log-record.md` |
| Audit in the transaction | A change that writes an `AUDIT` record | The change's transaction rolls back | Neither the change nor its `AUDIT` record is kept | `sds-logging/references/log-record.md` |
| Both outboxes read | An `AUDIT` record and an `APP` record, both written | `GET /api/admin/logs` is called | Both are returned | `sds-api-design/references/standard-api-endpoints.md` |
| Kept a week | A record the aggregator stored, 6 days after its `timestamp` | The outbox is cleaned | It is kept | `sds-logging/references/log-record.md` |
| Pending outlasts the week | An unreachable aggregator, and pending `ERROR`, `FATAL` and `AUDIT` records 8 days after their `timestamp` | The outboxes are cleaned | Each is kept until the aggregator stores it | `sds-logging/references/log-record.md` |
| Refused AUDIT stays | An `AUDIT` record the aggregator refused, 8 days after its `timestamp` | The audit outbox is cleaned | It is kept | `sds-logging/references/log-record.md` |
| Over the bound | An unreachable aggregator, and a record outbox at its bound | Records keep coming | The oldest `DEBUG`, `INFO` and `WARNING` records are dropped, no `ERROR` or `FATAL` record is, and one `LOG-5500` record carries `dropped=` with the number dropped | `sds-logging/references/log-record.md` |
| Aggregator down | An unreachable aggregator | A request is handled | It succeeds, and no slower than with the aggregator up | `sds-logging/references/log-record.md` |
| Malformed record | An aggregator that answers 400 | The submission is handled | It is not retried, and the app records `LOG-4000` locally | `sds-logging/references/log-record.md` |
| Aggregator unavailable | An aggregator that answers 503 | Records keep coming | They stay pending in the outbox, and are retried behind the breaker | `sds-logging/references/log-record.md` |
| Delivered before a run ends | A component that runs only inside jobs, with pending records | Its run ends | It has submitted them first, and any the aggregator did not store are still in the outbox on the runner host | `sds-api-design/references/standard-api-endpoints.md` |
| Left over, sent first | Records an earlier run left pending on the runner host | The next run starts | They are submitted before that run's own records | `sds-api-design/references/standard-api-endpoints.md` |
| Batch rejected | A batch answered 400 naming two records | The app resubmits | Without those two, under a new `Idempotency-Key` | `sds-logging/references/aggregator-api.md` |

## Client errors

For `POST /api/client-errors`. The conformance check runs the refusals visible from outside; these cases also cover what the app logs.

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Report logged | A report from the app's own origin, naming one of its route templates | It is submitted | 200 `{"status": "ok"}`, and one `ERROR` `APP` record with `SYS-5000`, `op="client {route}"`, and the report's `error=` and `cause=` | `sds-api-design/references/standard-api-endpoints.md` |
| No credential needed | A report with no session and no `Authorization` header | It is submitted | 200, and the record carries no `user=` | `sds-api-design/references/standard-api-endpoints.md` |
| Person by oid | A report sent with the app's session | It is submitted | The record carries `user=` and the person's oid, and nothing else about them | `sds-api-design/references/standard-api-endpoints.md` |
| Foreign origin | A report whose `Origin` is another site's | It is submitted | 403 `PERM-4153`, and no report is logged | `sds-api-design/references/standard-api-endpoints.md` |
| No origin | A report carrying no `Origin` | It is submitted | 403 `PERM-4153` | `sds-api-design/references/standard-api-endpoints.md` |
| Foreign route | A report naming a route the app does not serve | It is submitted | 400 `VAL-4006`, with `route` in `details` | `sds-api-design/references/standard-api-endpoints.md` |
| Extra field | A report carrying a field it does not define | It is submitted | 400 `VAL-4007` | `sds-api-design/references/standard-api-endpoints.md` |
| Report too large | A report one byte over 16 KiB | It is submitted | 413 `VAL-4550` | `sds-api-design/references/standard-api-endpoints.md` |
| Rate limited | One source past its allowance of reports, 10 a minute unless the app records another | It submits another | 429 `RATE-4400`, carrying `Retry-After` | `sds-api-design/references/standard-api-endpoints.md` |
| Secret redacted | A report whose `error` quotes a token | It is logged | The token appears in no record | `sds-logging/references/log-record.md` |

## Bridges

For a bridge that logs third-party software.

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Failure forwarded | The software writes an error to its output | The bridge reads it | One `ERROR` record under the component's id, with `SYS-5000` and the software's text under `error=` | `sds-logging/SKILL.md` |
| Routine output dropped | The software writes a routine line | The bridge reads it | No record is written | `sds-logging/SKILL.md` |
| Unreachable after startup | Software that answered once, now unreachable | The bridge checks it | An `ERROR` record with `UP-5500`, and the bridge's health reports the software `fail` | `sds-logging/SKILL.md` |
| Still starting | Software not yet answering since the bridge started | The bridge checks it | No record, and `GET /api/health/ready` answers 503 `not-ready` | `sds-logging/SKILL.md` |
| Secret redacted | An error line from the software that quotes a credential | The bridge forwards it | The credential appears in no record | `sds-logging/references/log-record.md` |

## Configuration

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Missing value | A required value unset | The app starts | It does not report ready, and writes a `FATAL` record carrying `CFG-5000` | `sds-config/SKILL.md` |
| Unusable value | A value its schema refuses | The app starts | It does not report ready, and writes a `FATAL` record carrying `CFG-5001` | `sds-config/SKILL.md` |
| Checked at startup | A required value unset | The app starts, before any request arrives | `GET /api/health/ready` already answers 503, not only after a request needs the value | `sds-config/SKILL.md` |
| Value not echoed | An unusable secret | The failure is logged | The record names the variable and never contains its value | `sds-config/SKILL.md` |
| Test seam refused | A production deployment with a test seam's setting | The app starts | It does not report ready, with `CFG-5001`, and accepts no test credential | `sds-config/SKILL.md` |
| Job fails on its configuration | A component that runs only inside jobs, with a required value unset | Its run starts | It does no work, writes a `FATAL` record carrying `CFG-5000`, and its job fails | `sds-config/SKILL.md` |

## Retention

For the aggregator. Time passes on an injected clock.

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| INFO window | An `APP` `INFO` record | 30 days pass | It is deleted | `sds-logging/references/aggregator-api.md` |
| ACCESS window | An `ACCESS` `INFO` record | 14 days pass | It is deleted | `sds-logging/references/aggregator-api.md` |
| Unresolved group | An `ERROR` record whose group is `open`, `linked` or `fix_merged` | 90 days pass | It is still kept | `sds-logging/references/aggregator-api.md` |
| Resolved group | A group resolved by a deployed fix | 30 days pass after it was resolved | Its records are deleted, and the group and its count entries are kept | `sds-logging/references/aggregator-api.md` |
| Security floor | A `SECURITY` `ERROR` record whose group was resolved a month after its `timestamp` | 30 days pass | It is still kept, until a year after its `timestamp` | `sds-logging/references/aggregator-api.md` |
| Security year | A `SECURITY` `WARNING` record | 90 days pass | It is still kept, until a year after its `timestamp` | `sds-logging/references/aggregator-api.md` |
| Audit forever | An `AUDIT` record | Any time passes | It is never deleted | `sds-logging/references/aggregator-api.md` |
| DEBUG refused | A `DEBUG` record | It is submitted | 400 `VAL-4006`, and nothing is stored | `sds-logging/references/aggregator-api.md` |
| Person by email refused | A record whose `user=` is an email | It is submitted | 400 `VAL-4006`, and nothing is stored | `sds-logging/references/aggregator-api.md` |
| Not clamped | Records older than 90 days still kept | `GET /api/v1/logs` is called with a `startDate` a year ago | Every record kept since then is returned, and `filterParams` echoes that `startDate` | `sds-logging/references/aggregator-api.md` |

## Groups

For the aggregator. Every case submits records as an app holding `logs.write`, and links as one holding `logs.resolve`.

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| One failure, one group | Two `ERROR` records with the same `id`, `code` and `op`, whose `error=` values differ only in a number | Both are stored | Both carry the same `group` | `sds-logging/references/aggregator-api.md` |
| Names tell apart | Two `ERROR` records alike but for the error name in `error=` | Both are stored | They carry different groups | `sds-logging/references/aggregator-api.md` |
| Not grouped | A `WARNING` record, and an `AUDIT` record at `ERROR` | Both are stored | Each carries `group: null` | `sds-logging/references/aggregator-api.md` |
| Signature cap | One `id`, `code` and `op` with 20 signatures already grouped | A record with a 21st signature is stored | It joins the `overflow` group of that `id`, `code` and `op` | `sds-logging/references/aggregator-api.md` |
| First and latest kept | A group of 250 records | `GET /api/v1/groups/:groupId/occurrences` is called | Its entries count 50; the first 100 and the latest 100 records are still returned by their `recordId`, and a counted one is 404 `RES-4200` | `sds-logging/references/aggregator-api.md` |
| Fix merged | A `linked` group | A fix naming one of its records merges | The group is `fix_merged`, carrying the fix's Change-Id | `sds-logging/references/aggregator-api.md` |
| Resolved only by its fix | A `linked` group | The git service sends `resolved` for it | 409 `RES-4302`, and the group is still `linked` | `sds-logging/references/aggregator-api.md` |
| Closure needs a label | A `linked` group | The git service sends `closed` without a label | 400 `VAL-4001`, and the group is still `linked` | `sds-logging/references/aggregator-api.md` |
| Fixed stays fixed | A group in `fix_merged` or `resolved` | The git service sends `closed` for its issue | 200, and the group's state is unchanged | `sds-logging/references/aggregator-api.md` |
| Regression | A `resolved` group | A new record of it arrives | The group is `linked` again, without its Change-Id | `sds-logging/references/aggregator-api.md` |
| Fix not yet deployed | A `fix_merged` group | A new record of it arrives | The group is still `fix_merged` | `sds-logging/references/aggregator-api.md` |
| Closed as not reproducible | A group closed `close:not-reproducible` | A new record of it arrives | The group is `linked` again | `sds-logging/references/aggregator-api.md` |
| Closed as external | A group closed `close:external` | A new record of it arrives | It is stored, and the group is still `closed` | `sds-logging/references/aggregator-api.md` |
| Unknown group | A `groupId` no group has | The git service links it | 404 `RES-4200` | `sds-logging/references/aggregator-api.md` |
| Group submitted | A record carrying `group` | It is submitted | 400 `VAL-4007`, and nothing is stored | `sds-logging/references/aggregator-api.md` |
| Link without the role | An app credential without `logs.resolve`, or an operator's | It links a group to an issue | 403 `PERM-4150` | `sds-auth/references/credentials.md` |
| Record read to find its group | An app credential holding `logs.resolve` | It reads a record by its `recordId` | 200, the record with its `group` | `sds-auth/references/credentials.md` |

## Codes

For the aggregator.

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Codes for an app | An app credential holding `logs.write` | `GET /api/v1/codes` is called | 200, every code of the aggregator's registry, each once, in ascending order | `sds-logging/references/aggregator-api.md` |
| Codes for an operator | An operator credential | `GET /api/v1/codes` is called | 200, the same codes | `sds-auth/references/credentials.md` |
| Codes without the role | An app credential without `logs.write` | `GET /api/v1/codes` is called | 403 `PERM-4150` | `sds-auth/references/credentials.md` |
| Unlisted code refused | A record whose code `GET /api/v1/codes` does not list | It is submitted | 400 `VAL-4002`, and nothing is stored | `sds-logging/references/aggregator-api.md` |

## Employee directory

For the directory, and for an app that reads it.

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Directory for an app | An app credential holding `employees.read` | `GET /api/v1/employees` is called | 200, a page of employees ordered by `oid` | `sds-auth/references/employees-api.md` |
| Directory without the role | An app credential without `employees.read` | `GET /api/v1/employees` is called | 403 `PERM-4150` | `sds-auth/references/credentials.md` |
| Unknown employee | An `oid` no employee has | `GET /api/v1/employees/:oid` is called | 404 `RES-4200` | `sds-auth/references/employees-api.md` |
| Unknown company role | A `role` filter the company roles list does not hold | `GET /api/v1/employees` is called | 400 `VAL-4002` | `sds-auth/references/employees-api.md` |
| Erased employee | An employee whose data was erased | They are fetched by `oid` | 200, `state: erased`, every personal field `null`, and no role | `sds-auth/references/employees-api.md` |
| Roles without P1 | An app on a tenant without Entra ID P1, and an employee in a `bio-role-*` group | The employee calls an endpoint requiring that role | The app finds the role through the directory, and the call proceeds | `sds-auth/references/credentials.md` |

## Audit chain

For the aggregator. Time passes on an injected clock.

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Chained within a day | Two `AUDIT` records stored on one day | They are read back | The second's `chain.prev` is the first's `chain.hash`, and each `chain.hash` is the SHA-256 of its record's canonical JSON without `chain.hash` | `sds-logging/references/aggregator-api.md` |
| Chained across days | `AUDIT` records stored on one day, and one stored on the next | The next day's is read back | Its `chain.prev` is the earlier day's anchor, the `chain.hash` of that day's last record | `sds-logging/references/aggregator-api.md` |
| Anchor sent | A day with `AUDIT` records | The day ends | Its anchor, the day and the number of records reach the configured mailbox | `sds-logging/references/aggregator-api.md` |
| Only chained when audit | An `APP` record | It is read back | Its `chain` is `null` | `sds-logging/references/aggregator-api.md` |
| Chain submitted | A record carrying `chain` | It is submitted | 400 `VAL-4007`, and nothing is stored | `sds-logging/references/aggregator-api.md` |
| No deletion | The aggregator's database user | It deletes or updates a stored `AUDIT` record | The database refuses, and the record is unchanged | `sds-logging/references/aggregator-api.md` |
| Tampering detected | A stored `AUDIT` record whose `message` was changed in the database | The chain is verified | Verification fails at that record | `sds-logging/references/aggregator-api.md` |

## Health

| Case | Given | When | Then | Source |
|------|-------|------|------|--------|
| Live ignores dependencies | A database that is down | `GET /api/health/live` is called | It answers 200 | `sds-api-design/references/standard-api-endpoints.md` |
| Ready gates on dependencies | A dependency that gates traffic is down | `GET /api/health/ready` is called | It answers 503, with `status: fail` | `sds-api-design/references/standard-api-endpoints.md` |
| Not ready yet | An app still starting | `GET /api/admin/logs` is called | 503 `SYS-5500`, in the error envelope | `sds-api-design/references/standard-api-endpoints.md` |
| Health needs an operator | A request with no credential | `GET /api/health` is called | 401 `AUTH-4100` | `sds-api-design/references/standard-api-endpoints.md` |
