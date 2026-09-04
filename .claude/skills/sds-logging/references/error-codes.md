# Error Codes

An error code identifies *what went wrong*, stably, across the API response a
client sees and the log record an operator reads. Message text is written for
humans and will be reworded; the code is the part that MUST NOT change.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

## Format

```
<PREFIX>-<NNNN>
```

- `PREFIX` identifies the *kind* of failure and MUST be one of the prefixes
  listed in `code-prefixes.md`, used exactly as written there. It is never
  derived from the app name, abbreviated, or invented at the point of use.
  Which app failed is already carried by the record's `id` field.
- `NNNN` is a four digit number, also taken verbatim from `code-prefixes.md`.
  The first digit marks fault:

| Range | Fault | Typical HTTP |
|-------|-------|--------------|
| `4000-4999` | The caller's — bad input, missing or insufficient credentials, absent resource | 400, 401, 403, 404 |
| `5000-5999` | The app's — a dependency failed, an invariant broke, an unhandled path | 500, 503 |

Non-HTTP failures use the same ranges with the same meaning: a job that
received bad configuration is `4xxx`, a job that crashed is `5xxx`.

Numbers are blocked by concern — `4000-4099` validation, `4100-4149`
authentication, and so on — so the number alone determines the HTTP status
regardless of prefix.

## HTTP mapping

Each code MUST map to exactly one HTTP status. The reverse does not hold: many
codes share a status, which is the entire point of having codes.

| Code range | HTTP | Meaning |
|------------|------|---------|
| `4000-4099` | 400 | Malformed or invalid input |
| `4100-4149` | 401 | Missing or invalid credential |
| `4150-4199` | 403 | Authenticated, not permitted |
| `4200-4299` | 404 | Resource does not exist |
| `4300-4399` | 409 | Conflict with current state |
| `4400-4499` | 429 | Rate limited |
| `5000-5499` | 500 | Unhandled server error |
| `5500-5999` | 503 | A required dependency is unavailable |

## Where codes appear

**In the API error envelope**, as the `code` field — see
`sds-api-design/references/standard-api-endpoints.md`:

```json
{
    "status": "fail",
    "code": "VAL-4004",
    "message": "endDate is earlier than startDate",
    "details": [
        { "field": "endDate", "issue": "must be at or after startDate" }
    ]
}
```

**In the log record**, as the `code` field — see `log-record.md`:

```json
{
    "id": "logs-service",
    "timestamp": "2026-09-03T14:05:00.123Z",
    "severity": "WARNING",
    "type": "APP",
    "code": "VAL-4004",
    "message": "endDate earlier than startDate request=8c21"
}
```

The two MUST be the same code for the same failure. That equality is what lets
an operator take a code from a user's screenshot and filter the aggregator
straight to the matching records.

The code MUST NOT be repeated inside `message`. It is a field precisely so
that filtering does not depend on parsing free text.

## Registry rules

`code-prefixes.md` is the single registry for the whole estate. Apps do not
keep their own; a code that exists in one repository and nowhere else cannot
be filtered, alerted on, or looked up.

- A code, once used, is permanent. Its meaning MUST NOT be redefined.
- A retired code MUST NOT be reused for something else. Mark it retired and
  allocate a new number.
- Codes MUST NOT be renumbered. Clients and runbooks reference them.
- Message text MAY be reworded freely; that is why the code exists.
- A new failure mode gets a new code rather than an existing code with a
  different message.

## Choosing between a code and a detail

Use a **code** for a distinct failure mode a caller might handle differently.
Use `details` for per-field validation feedback under a single code — four
invalid fields in one request is one `VAL-4000` with four `details` entries,
not four codes.
