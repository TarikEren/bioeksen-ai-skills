---
name: sds-nextjs-backend
description: "Backend conventions for a Next.js App Router project in TypeScript: route handlers, server actions, a server-only data access layer (services and repositories), Zod validation at every boundary, authentication and authorisation, safe errors and logging, transactions. Rules for type-safe, secure and modular server code. Use when writing, changing or reviewing server-side code: an endpoint, a server action, a service, a repository, a validation schema, an auth check, database access, configuration or a background job."
metadata:
  author: Tarık Eren Tosun
---

# Next.js backend

Server-side code in a Next.js App Router project written in TypeScript must be
**type-safe, secure and modular**. These three rank above speed, brevity and
cleverness. When a task cannot be done without giving up one of them, stop and
say so instead of shipping the compromise.

The project's own conventions name what this skill leaves open: the ORM, the
key types, the error class, the transaction helper and the access context.
The codes are the registry's and the logger is `@bioeksen/sdk`, per
`sds-logging/SKILL.md`. This skill outranks the project's conventions, as
every `sds-*` skill does, and **every other `sds-*` skill outranks this one**:
it is how a Next.js app carries them out, never the source of their rules.

## Read first

1. **The Next.js docs for the installed version**, not memory. The installed
   version has breaking changes. Under `node_modules/next/dist/docs/01-app/`:
   - `01-getting-started/`: `07-mutating-data`, `08-caching`,
     `09-revalidating`, `10-error-handling`, `15-route-handlers`, `16-proxy`;
   - `02-guides/`: `data-security`, `server-actions`, `backend-for-frontend`,
     `authentication`, `environment-variables`.
2. **The `sds-*` skills:** `sds-api-design`, `sds-auth`, `sds-logging`,
   `sds-config` and `sds-database`. They decide response shapes, credentials,
   rejection codes, configuration, error codes, log format and data access,
   and the rules below apply within them. If one cannot be loaded, say so in
   your report.
3. **The module you are changing**, its tests, and the layers above and below
   it. Reuse what exists before adding anything.

## 1. Layers and modules

Server code sits in four layers. Dependencies point down only, and no layer
skips the one below it:

| Layer | Does | Never |
|---|---|---|
| **Route handler** (`app/**/route.ts`) or **server action** (`"use server"`) | Builds the caller's context, parses input, calls one service function, maps errors to a response or a result | Touch the ORM, hold business rules |
| **Service** | Business rules, authorisation decisions, transactions | Know about `Request`, `Response` or `FormData` |
| **Repository** | Data access: queries and nothing else | Decide who may do what |
| **Database client** | One process-wide instance | Get imported above the repository layer |

- **Handlers and actions stay thin.** When an operation is reachable both as
  a route handler and as a server action, both call the same service function.
- **Server components call services directly.** They never fetch the app's own
  route handlers: that is an extra HTTP round trip, and it fails at build time
  when there is no server to answer.
- **Pure domain logic** (state machines, calculations, derivations) lives in
  I/O-free functions with their own unit tests.
- **One module per domain**, with a small public API and no circular imports.
  Another module's data is reached through its service, never its repository.
- **Mark server modules with `import "server-only"`**: services, repositories,
  configuration and the database client. The build then fails if client code
  imports them.
- **Process-wide instances** (database client, cache, logger) are module-level
  singletons, never properties on `globalThis`. The one exception is the
  database client's development cache (e.g. `lib/db.ts`): `next dev` re-evaluates
  modules on every edit, and a client held only by its module would leave a
  connection pool behind each time.
- **Configuration lives in the one module `sds-config/SKILL.md` requires.** It reads `process.env` once,
  validates it with a schema, and exports typed values. Nothing else reads
  `process.env`.
- **Build on the project's shared base classes**, such as a
  `BaseRepository`, a `BaseService` and the error classes (e.g. in
  `lib/api/shared/`). Beyond them, no speculative abstraction: generalise when
  the second real use appears.

## 2. Type safety

- **Compile with `strict`.** No `any`, explicit or implicit: use `unknown` and
  narrow it.
- **No assertions that silence the compiler.** No `as T` on data, never
  `as unknown as T`, and no `!` unless the line above proves the invariant.
  `as const` and `satisfies` are fine.
- **No `@ts-ignore`, `@ts-expect-error` or `eslint-disable`** in application
  code.
- **Validate at every boundary**, with a Zod schema that produces a typed
  value:
  - request bodies, route params, query strings and the headers you rely on;
  - `FormData` reaching a server action, and every server action argument;
  - cookies and session payloads;
  - environment variables;
  - responses from other services;
  - rows from raw SQL.

  Past the boundary, no code sees `unknown`.
- **Schemas are the single source of truth for input types.** Derive the type
  with `z.infer<typeof Schema>`; never write a parallel interface by hand.
- **Use Zod 4 idioms:**
  - `z.strictObject({…})` for a body, whose unknown fields are refused; a
    query string's schema drops unknown keys instead;
  - top-level formats: `z.email()`, `z.uuid()`, and
    `z.iso.datetime({ offset: true })`, since a timestamp carries its offset;
  - `z.coerce.*` for values that arrive as strings (params, `FormData`);
  - `safeParse` at a boundary, then turn each issue into a `details` entry,
    `{ field, issue }`, under the code the selection procedure gives the first
    fault.
- **Database types come from the ORM client.** Do not hand-write row types.
- **Use the key type the schema defines.** Never assume UUID strings or plain
  numbers, and convert at the boundary (a `bigint` travels as a string in
  JSON).
- **Type route context** with the generated `RouteContext<"/path/[id]">`, and
  await `params`.
- **Errors are the project's typed error class**, each with a code from the
  registry in `sds-logging/references/code-prefixes.md`.
  A `catch` receives `unknown` and normalises it.
- **Close every state machine and discriminated union** with an exhaustive
  `never` check.
- **Exported service and repository functions declare their return types.**
  They are the module's public contract.
- **Literal unions instead of enums**, and `import type` for type-only imports.

The references hold the TypeScript background: `references/type-system.md`,
`references/generics.md` and `references/typescript-summary.md`.

## 3. Security

### Every entry point checks the caller

- **Authenticate and authorise inside every route handler and every server
  action.** A server action is a public POST endpoint, reachable by anyone who
  sends the same request, whether or not your UI renders it. A check on the
  page does not cover the actions defined in it.
- **Put the checks in the service, with the data.** Keep `"use server"`
  actions and handlers as thin callers.
- **Proxy (`proxy.ts`) is for optimistic checks only**, such as redirecting a
  signed-out user. It is never the authorisation layer.
- **Deny by default, and authorise the object.** The caller must be allowed
  to act on *this* record, not merely hold a role. A missing ownership check
  is an IDOR.
- **Guard destructive operations harder.** Deletes and irreversible changes
  may warrant re-authentication or an elevated session, and they fail loudly
  when a check misses.

### Input

- **Treat all request data as untrusted:** bodies, `FormData`, route params
  (every `[param]` folder is user input), query strings, headers and cookies.
- **Check content type and size** before parsing, per
  `sds-api-design/references/standard-api-endpoints.md`: 413 `VAL-4550` past
  the limit, 415 `VAL-4600` for a media type the endpoint does not take.
- **Refuse unknown body fields** with 400 `VAL-4007`, and ignore unknown query
  parameters, per `sds-api-design/references/app-endpoints.md`. Never
  spread a request body into an ORM `data` object. Map field by field.
- **Never mutate on `GET`,** and never mutate during render: no setting
  cookies, writing to the database or revalidating inside a page or
  component.

### Output

- **Return DTOs, not records.** A server action's return value and a route
  handler's body are both serialised to the client. Shape them to what the
  caller renders; never return password hashes, tokens or internal fields.
- **Errors take the envelope `sds-api-design` defines**, from a route handler
  and a server action alike. No stack traces, SQL,
  internal messages or identifiers the caller may not see.
- **Do not copy incoming headers into the response**, but echo
  `X-Request-Id`, as `sds-logging/references/log-record.md` requires, and put
  nothing sensitive in response headers.

### Data access

The schema, migrations and seeds are not server code: they follow
[`../sds-database/SKILL.md`](../sds-database/SKILL.md) and belong to the database developer.
If a task needs a table, column, constraint or index that does not exist,
stop and name the data change in your report. The rules below are for the
repositories and services that use the schema; `sds-database` § 5 and
§ 6 hold the rest.

- **Never build SQL from strings** (`sds-database` § 6). Use the ORM's query builder or a
  tagged-template raw query; never `$queryRawUnsafe` or `$executeRawUnsafe`
  with input in it.
- **Read, check and write inside one transaction** (`sds-database` § 5). Let
  database constraints enforce uniqueness, and map each constraint violation
  to the code the **Database failures** table in
  `sds-logging/references/code-prefixes.md` gives it.
- **Audit what `sds-logging` says to audit** (**Choosing a type**): write the
  record through the logger's audit call, inside the transaction that makes
  the change, so the two commit or roll back together (`sds-database` § 5).

### Secrets and configuration

- **Secrets come from the validated configuration module**, and stay out of
  code, logs and responses, per `sds-config/SKILL.md`.
- **Never put a secret in a `NEXT_PUBLIC_*` variable** (`sds-config/SKILL.md`).
  Those are inlined into the client bundle at build time.
- **Do not capture secrets in inline server actions.** Next.js encrypts
  closed-over variables, but encryption alone is not the protection. A
  self-hosted deployment with several instances sets
  `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` to one shared key.

### Logging

- **Log through `@bioeksen/sdk`**, the TypeScript binding `sds-logging/SKILL.md`
  requires, so every record carries the request's correlation id.
- **Never log** what `sds-logging/SKILL.md` forbids: secrets and tokens, a
  body in full, or personal data beyond the identifier needed to correlate.

### Abuse and resources

- **Rate-limit** sign-in, uploads, previews and any other expensive or
  sensitive endpoint, as the rate limiting rule in `sds-auth/SKILL.md` says.
- **Every outbound call follows `sds-api-design/references/service-calls.md`**:
  its deadline, timeouts, retries and breaker. Never fetch a user-supplied URL
  without an allowlist (SSRF).
- **Handle uploads defensively:**
  - enforce size and type limits on the server;
  - derive stored names yourself, and never let a client file name reach a
    path (no path traversal);
  - stream large bodies.

  A server action's body is capped at 1 MiB by default, so files go to a route
  handler, and the form carries only the handle.
- **Make retried writes idempotent** with `Idempotency-Key`, where
  `sds-api-design/references/service-calls.md` requires it.

### Cross-site requests

- **Server actions compare `Origin` with `Host`** and reject a mismatch.
  Behind a reverse proxy or CDN, list the extra origins in
  `serverActions.allowedOrigins`. Never disable the check.
- **Route handlers get no such check.** A state-changing handler that
  authenticates by cookie verifies the request's origin itself, and sets
  cookies `httpOnly`, `secure` and `sameSite`.

### Dependencies

- **Do not add a package** where the platform or an existing dependency
  already does the job. A new dependency is a decision to report, not a
  default.

## 4. Next.js specifics

- **Route handlers** use the Web `Request` and `Response` APIs. They are not
  cached by default; only `GET` can opt in, and other methods never are.
- **Server actions** are for mutations. Actions are queued, so fetching data
  through them serialises requests. After a mutation, call `revalidatePath` or
  `revalidateTag` for what changed, and return the envelope `sds-api-design`
  requires of every API: `{ status: "ok", … } | { status: "fail", code,
  message, details }`.
- **`cookies()`, `headers()`, `params` and `searchParams` are asynchronous.**
  Await them.
- **Malformed URL input on a page** (an id that does not parse, a record that
  does not exist) calls `notFound()`. It does not reach the error boundary.
- **`forbidden()` and `unauthorized()` are experimental** in this version.
  Do not depend on them unless the project enables `authInterrupts`.

## 5. Tests

What to test is below. How to write and run tests, including known defects
and database suites, is in [`../sds-testing/SKILL.md`](../sds-testing/SKILL.md).
In the test-first loop, the acceptance tests are the tester's and hidden from
you; the tests below are your own unit tests, beside the code
(e.g. `lib/**/*.test.ts`), run through the project's results-only interface.

- **Every service function you change gets tests** for at least the success
  path, a validation failure and an authorisation failure. Add not-found and
  conflict cases where they apply.
- **Assert outcomes, not call shapes.** A test that checks which ORM method was
  called breaks on a harmless rewrite, and proves nothing about the result.
- **Pure domain logic** is tested directly, without mocks.
- **Raw SQL, constraints and transaction boundaries** are tested against a real
  database, in the project's integration suite, and only a disposable one
  (`sds-database` § 8).

### Skeleton

In the test-first loop, a plan's skeleton task builds the contract's surface
before any behaviour, so that the tester can write tests that compile and fail
for the right reason. A skeleton holds:

- **the Zod schemas** the contract names, and the types inferred from them;
- **service and repository exports** with their final names and signatures,
  whose bodies throw the project's `NotImplemented` error;
- **server actions** with their final signatures, which throw
  `NotImplemented`;
- **route handlers** at their final paths, answering `SYS-5000` (500, "Not
  implemented") through the project's error mapping;
- **the test seams** the plan names.

No behaviour, and no guessing: every name and type is the contract's. A
difference is a change to the contract, and goes back to whoever runs the loop.

### Test seams

A seam is product code that lets a black-box test drive the system:

- **Test sign-in:** a way for a test to act as a given user with given
  permissions, through the same session type every entry point reads.
- **An injected clock:** services take the current time from their context,
  not from `Date.now()` directly, so tests can fix it.
- **Fakes for outside services,** behind the interface the real client
  implements, chosen by configuration.

A seam must be impossible to reach in production, per **Test seams** in
`sds-testing/SKILL.md`: enabled only from the validated configuration module
in a test environment, and refused at startup with `CFG-5001` everywhere
else. A test sign-in reachable in production is a Critical security hole.

Where the project ships a test sign-in and a clock, build on them rather than
add a second of either.

## 6. Before handing back

Run the checks the project lists. At least:

```bash
pnpm run typecheck
```

```bash
pnpm run lint
```

The unit tests for what you changed, and `pnpm run build` if you added or
changed route files.

Then go through the audit list from the Next.js data-security guide:

- **Data access:** is database and `process.env` access confined to the
  server-only layer?
- **`"use server"` files:** is every argument validated, and is the caller
  authenticated *and* authorised for this record? Are return values filtered?
- **`[param]` folders:** is every param validated?
- **`route.ts` and `proxy.ts`:** they have the most power, so read them most
  carefully.

## References

- [`references/type-system.md`](references/type-system.md): annotations,
  unions, narrowing, `satisfies`
- [`references/generics.md`](references/generics.md): constraints, mapped and
  conditional types, template literal types
- [`references/typescript-summary.md`](references/typescript-summary.md):
  quick reference, with Zod at the boundary
- [`references/code-documentation.md`](references/code-documentation.md):
  header comments, doc comments and what not to comment
