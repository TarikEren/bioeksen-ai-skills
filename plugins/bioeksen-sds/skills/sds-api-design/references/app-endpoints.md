# App-Specific Endpoints

The conventions every endpoint an app serves follows, beyond the four standard
ones. `standard-api-endpoints.md` defines those four, and the conventions every
endpoint shares with them — types and units, correlation, the error envelope,
rate limiting, and the 405, 413 and 415 responses. This document adds what only
app-specific endpoints need.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

App-specific endpoints have no shared schema, because every app's resources
differ. What two services must still agree on is the shape around the
resource: how a success is wrapped, how a list pages, how a path is spelt,
and what each method means. A caller written against one app should read
another's responses without learning a new envelope.

## Paths

- Every app-specific path is served under `/api/v{major}/`, per the versioning
  rule in `standard-api-endpoints.md`.
- A collection is a plural noun in kebab-case: `/api/v1/purchase-orders`. One
  member is the collection followed by its id:
  `/api/v1/purchase-orders/{id}`.
- An operation on a whole collection that is not creating one member is a
  sub-path named for the operation: `/api/v1/logs/batch`. That is the only
  verb-like segment a path carries.
- An id in a path is opaque. A caller MUST NOT parse one or construct one.

## Bodies

- Request and response bodies are JSON objects, never bare arrays or scalars,
  so that a field can later be added to any of them without breaking a
  caller.
- Field names are camelCase: `totalCount`, `createdAt`. That is the spelling the
  standard endpoints already use, and one spelling across the estate is what
  lets a caller map fields without a table per app.
- Ids are strings in bodies too, even where an app stores integers. An
  integer id stops fitting a JavaScript number past 2^53, and changing an id's
  type later breaks every caller.
- The types and units table in `standard-api-endpoints.md` applies unchanged.

## A successful response

A success body is an object carrying `"status": "ok"`, with the payload's fields
beside it at the top level. It is the shape `GET /api/admin/logs` already
returns, and the success counterpart of the error envelope's `"status": "fail"`:

```json
{
    "status": "ok",
    "id": "42",
    "total": 19.5,
    "createdAt": "2026-09-03T14:05:00.123Z"
}
```

A client reads `status` the same way on every response from every app, success
or failure, and reads the resource without unwrapping it.

Because the envelope and the payload share one level, a resource MUST NOT use
these top-level names for anything else: `status`, `code`, `message`,
`details`, `page`, `count`, `totalCount`, `filterParams`. A resource whose
natural field collides with one renames it — `orderStatus`, not `status`.

The body `status` table in `standard-api-endpoints.md` — `ok`, `not-ready`,
`fail` — describes the health endpoints. An app-specific endpoint's success is
always `ok`, and its failure is always the error envelope.

## Lists

A list pages exactly as `GET /api/admin/logs` does:

- Query parameters `page`, 1-based and defaulting to `1`, and `limit`,
  defaulting to `50` and allowed from `1` to `200`. Outside that is 400
  `VAL-4005`.
- Response fields `page`, `count` and `totalCount`, and `filterParams` echoing
  every filter after defaults are resolved, including the `page` and `limit`
  the server used.
- The records under a field named for the collection — `orders`, as `logs`
  there. An empty array when nothing matches, never `null`.
- A page beyond the last returns 200, an empty array, and the true
  `totalCount`.
- A stable order whose tie-break gives a total order, so records do not swap
  between adjacent pages.

```json
{
    "status": "ok",
    "page": 1,
    "count": 1,
    "totalCount": 7,
    "orders": [
        { "id": "42", "total": 19.5 }
    ],
    "filterParams": { "page": 1, "limit": 50 }
}
```

## Methods

Methods carry their RFC 9110 semantics, which is what the retry rules in
`service-calls.md` rely on:

| Method | Use | Success |
|--------|-----|---------|
| `GET` | Read, with no side effects | 200 |
| `POST` | Create one member of a collection, or run a collection operation | 201 for a create, 200 for an operation |
| `PUT` | Replace a member entirely | 200, with the member |
| `PATCH` | Change some fields of a member | 200, with the member |
| `DELETE` | Remove a member | 204, with no body |

- A create answers 201 with a `Location` header naming the new member, and the
  member in the body. A collection operation that creates several has no
  single `Location`, and names what it created in its body.
- A `PATCH` body is a JSON Merge Patch, RFC 7396: a field left out is
  unchanged, and a field set to `null` is removed. One patch format across the
  estate means a caller never has to ask which one an app took.
- A state-changing `POST` honours `Idempotency-Key`, per `service-calls.md`.
- A method the path does not serve is 405 `RES-4500`.

## Unknown input

- An unknown query parameter is ignored. A query string is where caches,
  proxies and tracing tools add parameters of their own, and rejecting those
  fails requests nobody wrote wrong.
- An unknown field in a request body is rejected with 400 `VAL-4007`. The
  caller alone writes a body, so an unknown field is the caller's mistake — a
  misspelt `quantitiy` that would otherwise be dropped silently while the
  request succeeds. The aggregator's rejection of a submitted `recordId` is
  this rule.

Adding an optional request field is therefore a change the serving app deploys
before any caller sends the field, which is the order an additive change takes
anyway.
