# Employee Directory API

The employee directory is the one store of BioEksen's employees: who they are,
whether they can sign in, and which company roles they hold. `bio-softop`
serves it, and its host is denoted `HOST`. No app connects to its database,
and no app keeps employees of its own: every app reads them here.

`employees-api.yaml` beside this file is the normative OpenAPI 3.1 definition
of these endpoints. This document is the rationale layer; where the two
disagree, the schema wins and this document MUST be corrected.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

## Where the data comes from

The identity provider is the source of truth. The directory copies it every
hour, read-only: through Microsoft Graph on Entra ID, through the admin API
on Keycloak. It never writes to a user there. An employee is keyed by
`userId`, their principal key, per **Required claims** in `credentials.md`.

| Field | Holds |
|-------|-------|
| `userId` | The employee's principal key: the key, the same in every app |
| `displayName`, `email`, `department` | From the identity provider. `null` once the employee's data is erased |
| `state` | `active` when the account can sign in, `disabled` when the identity provider has blocked or removed it, `erased` when the person's data was erased |
| `roles` | The company roles the employee holds now, per **Company roles** in `credentials.md` |

One store means one answer. Two apps each keeping a copy of who an employee is
disagree the day the copies drift, and a person who leaves keeps a role in
every copy nobody updated. The directory follows the identity provider, so the action that
removes a person's account removes them here within the hour.

## Erasure

When a person's data must be erased, the directory anonymises their personal
fields in place: `displayName`, `email` and `department` become `null`, they
hold no role, and their `state` is `erased`. Their `userId` remains, so
`GET HOST/api/v1/employees/:userId` still finds them.

Their `userId` is also what every log record names them by, per
`sds-logging/references/log-record.md`, and an `AUDIT` record is never altered,
per `sds-logging/references/aggregator-api.md`. Erasing the directory entry is
therefore enough: every record stays exactly as written, and no longer
identifies anyone.

## An app's own users

An app that kept users of its own keeps them as a profile table keyed by
`userId`, holding only what the app itself needs about a person: its existing
foreign keys keep working. The table holds no password, because employees sign
in with their Microsoft accounts, and no role, because the token carries the
company roles. Neither is copied from the directory.

## `GET HOST/api/v1/employees`

Returns the employees, paged as every list is, per
`sds-api-design/references/app-endpoints.md`, and ordered by `userId`, which
gives the total order paging needs.

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `role` | string | all | Only the employees holding this company role. A name the list in `credentials.md` does not hold is 400 `VAL-4002` |
| `state` | enum | all | `active`, `disabled` or `erased` |
| `page`, `limit` | integer | `1`, `50` | As every list's |

### Response

```json
{
    "status": "ok",
    "page": 1,
    "count": 1,
    "totalCount": 1,
    "employees": [
        {
            "userId": "0b2f6c1e-8a43-4d7e-9c15-6f0e2a7b9d31",
            "displayName": "Deniz Örnek",
            "email": "deniz.ornek@example.com",
            "department": "Quality Control",
            "state": "active",
            "roles": ["lab-manager"]
        }
    ],
    "filterParams": { "role": "lab-manager", "state": null, "page": 1, "limit": 50 }
}
```

### Responses

| HTTP | When |
|------|------|
| 200 | The matching employees. A page beyond the last returns an empty `employees` array and the true `totalCount` |
| 400 | A query parameter failed validation |
| 401 | No credential, or one that does not validate |
| 403 | Authenticated, but neither an app holding `employees.read` nor an operator — `PERM-4150` |
| 429 | Over the caller's allowance — `RATE-4400`, carrying `Retry-After` |
| 500 | The query failed |
| 503 | Not ready |

## `GET HOST/api/v1/employees/:userId`

Returns one employee, with `"status": "ok"` beside their fields, per
`sds-api-design/references/app-endpoints.md`. An erased employee is found,
with their personal fields `null`.

| HTTP | When |
|------|------|
| 200 | Found |
| 401 | No credential, or one that does not validate |
| 403 | Authenticated, but neither an app holding `employees.read` nor an operator — `PERM-4150` |
| 404 | No employee has that `userId` — `RES-4200` |
| 429 | Over the caller's allowance — `RATE-4400`, carrying `Retry-After` |
| 500 | The query failed |
| 503 | Not ready |

## Authorization

Both endpoints MUST require an app credential holding `employees.read`, or an
operator credential. The directory holds personal data, so it is read by the
apps that need it, which hold the role, and by operators; never by a person
for themselves. An app that needs to know who is calling it reads the token
it was sent, and the directory only for what the token does not carry.
