# Roadmap

Everything listed here is a decision or a document that does not exist yet.

Each item is written so it can be picked up cold. It states the question, a
recommended answer with the reasoning behind it, the exact edits that follow
from taking that answer, and how to tell it is finished. Where a recommendation
is given, it is a default to accept or reject — not a decision already taken.

Nothing here is a contract. The moment an item lands it becomes one, in the
skill it names: treat landing it as an API change, per `CLAUDE.md`, and run
`python scripts/check_invariants.py` before committing.

## Decisions taken

| Date | Decision |
|------|----------|
| 2026-09-17 | Standard four endpoints unversioned, everything else `/api/v{major}/`, 90 day deprecation window. Item 1, landed |
| 2026-09-17 | Aggregator retains 90 days, apps retain 7 days locally, out-of-window `startDate` clamps. Item 3, landed |
| 2026-09-17 | Entra ID as the issuer, Keycloak as the documented fallback, not run in parallel. Item 2, landed |
| 2026-09-17 | Change identifiers are minted locally, never by a service. Item 11 |
| 2026-09-17 | Idempotency via `Idempotency-Key`, key reused with a different request yields `RES-4301`. Item 4, landed |
| 2026-09-17 | Circuit breaker required per target: 5 consecutive failures, 30 s cooldown doubling to 5 min. Item 4, landed |
| 2026-09-17 | Release notes adopted at `0.2.0`; `0.1.0` tagged retroactively and exempt. Item 6, landed |
| 2026-09-17 | Tag is `v{version}`, note file is `{version}.md`; marketplace version is independent of plugin versions. Item 6, landed |
| 2026-09-17 | One operator role kept; a read-only auditor is the trigger for a second. Item 7, landed |
| 2026-09-17 | `DB-5501` is `ERROR` while transient, `FATAL` — then named `CRITICAL` — once sustained past 60 s. Item 8, landed |
| 2026-09-29 | Six codes added — `VAL-4006`, `VAL-4007`, `RES-4302`, and `RES-4500`, `VAL-4550`, `VAL-4600` in new 405, 413 and 415 ranges. A domain failure is `RES-4302` unless a client must branch on it. Landed in `9a284d6` |
| 2026-09-29 | `fix` increments the patch version, as SemVer does. Landed in `c2d9aae` |
| 2026-09-29 | An app-specific success is `status: ok` with the payload beside it; lists page as the logs endpoint does. Landed in `d7b12f0` |
| 2026-09-29 | An operator holds both the operator scope and the operator role; roles are a closed registry, `operator` and `logs.write`. Landed in `4dec2d9` |
| 2026-09-29 | The aggregator's 500 is not retried; a record's `id` is bound to the submitting app's `azp`; batches of up to 500 are all or nothing. Landed in `855b673`, `ec2805f` and `aeab6f5` |
| 2026-09-29 | A repository's software id lives in `.bioeksen/software-id`. Item 11.1, landed in `55895d6` |
| 2026-09-29 | A project generator copies `project-kit/template/` and references the plugin pinned to a release; it never copies the skills. Landed in `6184b42` |
| 2026-10-02 | Change identifiers are minted by `sds-commit`'s own script, with the timestamp in UTC+03:00 and no zone suffix; identifiers minted earlier keep their UTC time and `Z` |
| 2026-10-05 | Test-first is a MUST with three named exemptions — `docs`, `config`, `generated` — and no rule against code written before its test; CI checks every `feat` and `fix` commit after `v0.4.0` for a test or a `Test-Exempt` trailer, and `sds-testing` catalogues the contract tests. Landed in `007a4ef`, `3d6de60` and `a1e3a5d` |
| 2026-10-06 | A new service starts at `0.1.0`, and its first release covers every commit from the root. Landed in `1672eed` |
| 2026-10-06 | A database failure takes the code of the selection step it meets: a foreign key naming a missing record is `VAL-4006`, a unique key `RES-4300`, a still-referenced delete `RES-4302`. An operation not implemented yet is `SYS-5000`, never 501. Landed in `7ffdfde` |
| 2026-10-06 | A request body is limited to 1 MiB unless an app records otherwise, counted on the bytes received. Landed in `8485563` |
| 2026-10-06 | No stack in a log record; `error` and `cause` are reserved tail keys; the lowest severity is `LOG_LEVEL`; a build MAY carry the software id compiled in, held equal to the file. Landed in `f6cfc17` and `b3cd696` |
| 2026-10-06 | Configuration gets its own skill, `sds-config`: validated at startup before the app reports ready, declared, secrets kept out. Landed in `d5ceaf0` |
| 2026-10-06 | `sds-testing` adds known defects as strict expected failures, no weakened tests, flaky and not-run reporting, guarded test databases and seams that fail closed. These rulings were taken from create-bioeksen-app, which had settled them first. Landed in `d09c906` |
| 2026-10-07 | Aggregator retention is by type and severity: `AUDIT` forever, `SECURITY` a year, `ERROR` and `FATAL` until their issue is resolved or closed plus 30 days (90 days when no issue names them), `WARNING` 90 days, `INFO` 30 days and `ACCESS` `INFO` 14. `DEBUG` never leaves the app. Item 3, landed in `be8a36a` |
| 2026-10-07 | The local git service links a record to its issue and, on merging a fix whose `Fixes-Log:` trailer names it, stores the fix's Change-Id on it, as an app holding `logs.resolve`. Landed in `5b47190` and `409b530` |
| 2026-10-07 | The versioning rules apply to a published library as to a service, and for a library they are its compatibility promise: breaking any caller of its public exports is breaking. Landed in `ee3cd01` |
| 2026-10-07 | Configuration names are fixed across the estate: `AGGREGATOR_URL`, `LOG_OUTBOX_PATH` and `LOG_OUTBOX_BOUND` for the log transport; `ENTRA_*`, `AUTH_CLOCK_SKEW_SECONDS` and `TRUSTED_PROXIES` for authentication. The `azp`-to-software-id mapping is served by `bio-softop`'s registry, not configured. Landed in `1461fb5` and `926a0ae` |
| 2026-10-07 | A TypeScript app logs through `@bioeksen/sdk` and runs the contract suites `@bioeksen/sdk/testing` exports. Landed in `1461fb5` and `a3bc071` |
| 2026-10-07 | `sds-ci` added: three runners told apart by registration, secrets on runner hosts, releases verified and deployed by bio-softop, AI task runs gated outside the model. The project kit's workflow moves to `.forgejo/workflows/` and runs the CI image's kit. Landed in `73b14fe` and `53e2d08` |
| 2026-10-07 | `sds-api-design` governs any API, a server action included; `details` belongs to the code: field errors for `VAL-4001` to `VAL-4007`, otherwise what the code's entry defines, or null. Landed in `e0b6ee3` |
| 2026-10-07 | Every unit of development has acceptance tests a tester writes ahead of the code and blind to it, hidden from the developer, red on the unit's branch; `Test-Exempt: acceptance` names them. Landed in `5c127c8` |
| 2026-10-07 | The scaffolder's skills join `bioeksen-sds`: testing into `sds-testing`, ci-cd into `sds-ci`, database and reviewing as `sds-database` and `sds-reviewing`, each with a `references/nextjs.md`; the backend and frontend skills as `sds-nextjs-backend` and `sds-nextjs-frontend`. `heroui-react` stays vendored in the template. Landed in `cc889c7`, `a8cfe3d`, `8be031a`, `ca86316`, `2002656` and `8f88bb9` |

## Order of work

| # | Item | Blocked by | Blocks | Size |
|---|------|-----------|--------|------|
| ~~1~~ | ~~API versioning~~ | — | — | **done** |
| ~~2~~ | ~~Identity provider~~ | — | — | **done** |
| ~~3~~ | ~~Log retention window~~ | — | — | **done** |
| ~~4~~ | ~~Service-to-service call conventions~~ | — | — | **done** |
| ~~5~~ | ~~Aggregator OpenAPI schema~~ | — | — | **done** |
| ~~6~~ | ~~Release notes and version bump~~ | — | — | **done** |
| ~~7~~ | ~~Operator roles beyond `operator`~~ | — | — | **done** |
| ~~8~~ | ~~`DB-5501` severity~~ | — | — | **done** |
| 9 | Promoting `request` to a record field | a real need | — | deferred deliberately |
| ~~10~~ | ~~Reference-link and restatement checks~~ | — | — | **done** |
| 11 | Software id registry service | the service existing | — | 11.1 and 11.2 done, 11.3 waits |
| 12 | Move the repository to the company organisation | a decision on visibility | the install path in the kit | a transfer and one commit |

Items 1 to 8 and 10 are settled. What remains is item 9, deferred on purpose;
item 11.3, which waits on a service that does not exist; and item 12, which is
an administrative step rather than a specification change.

---

## 1. API versioning — done

Landed 2026-09-17 in `b82b828`, closing the open decision.

The standard four endpoints stay unversioned; everything else, including the
aggregator's own log endpoints, is served under `/api/v{major}/`. Major only,
bumped only for a change that would carry `!`, both versions served for 90
days, and an unrecognised version answered with 404 and `RES-4200`.

The rule lives in `standard-api-endpoints.md` under `## Conventions`, and
invariant 4 in `scripts/check_invariants.py` fails if a fifth path appears in
`openapi.yaml` or an aggregator endpoint is written without its version.

**Consequence for item 9.** Promoting `request` to a record field is a breaking
change to `LogRecord`, so it is now a `v2` of the aggregator endpoints rather
than an edit to `v1`.

---

## 2. Identity provider — done

Landed 2026-09-17 in `0689fcc`, closing the open decision.

**Microsoft Entra ID**, one tenant, both principal types. Chosen because
operators already have managed accounts there, so identity, MFA, conditional
access and offboarding come with the directory. **Keycloak** is recorded in
`credentials.md` as the named fallback, with the three findings that would
trigger a move — deliberately not run in parallel, since accepting either of
two issuers guts the `iss` check.

Two consequences the provider dictated rather than the other way round:

- **Principal type is derived, not declared.** Entra cannot put an arbitrary
  claim on an app-only token, so the type comes from `scp` and `roles` rather
  than a literal `typ`. The rule it makes checkable is unchanged.
- **App tokens no longer last 24 hours.** Entra randomises access token
  lifetime between 60 and 90 minutes and does not expose it as a policy. The
  old rule was unachievable *and* wrong: a failed refresh wants a retry policy,
  not a day-long token. Committed as a breaking change.

**Verify in a spike before the first app ships.** The `scp`/`roles` derivation
and the operator scope need confirming against a real tenant; if app-only
tokens cannot be made to carry what **Principal type** needs, that is fallback
trigger one.

**Still open.** Revocation does not invalidate an issued token, so the
revocation window is the token lifetime — up to 90 minutes. An incident needing
faster than that requires a deny list on `sub` at the receiving app, which is a
mechanism nothing has specified and nobody owns.

---

## 3. Log retention window — done

Landed 2026-09-17 in `91c6c37`, and replaced 2026-10-07 in `be8a36a` and `5b47190`.

The aggregator is the archive, and keeps a record for as long as its type and
severity call for: the **Retention** table in `aggregator-api.md`, from 14
days for `ACCESS` `INFO` to forever for `AUDIT`. `ERROR` and `FATAL` records
are kept while an issue names them and for 30 days after it is resolved or
closed, and 90 days when none ever does; the local git service records both
through `PUT HOST/api/v1/logs/:recordId/issue`. `DEBUG` never reaches the
aggregator.

An app keeps **7 days** of its own records, which is what
`GET /api/admin/logs` reads, and the only store that keeps `DEBUG`. The
windows differ on purpose, and both documents say so, so an operator comparing
them does not read the gap as data loss.

An app's own `startDate` earlier than its window is clamped, and
`filterParams` echoes the clamped value. The aggregator's is never clamped,
since its records have no single window.

The 90-day flat window this replaced left `AUDIT` with no archive at all. The
table answers that: `AUDIT` is kept forever, never sampled, capped or
summarised.

---

## 4. Service-to-service call conventions — done

Landed 2026-09-17 across `1a71fbf`, `1eed454`, `138f4c9` and `5d2cba0`.

`sds-api-design/references/service-calls.md` now covers call classes,
deadlines, timeouts, retryability, retry budgets, circuit breaking and
idempotency. The three rules that leaned on it — the aggregator's unbounded
backoff, the credential refresh lead time, and the rate limit a caller had no
way to respect — now point at it, and `attempt=` joins `request=` in the
logfmt tail.

Four structural choices, all of which matter more than the numbers:

- **Deadlines propagate** as a remaining duration, not a timestamp, so clock
  skew never becomes an availability dependency and no service works on a
  request its caller has abandoned.
- **Retries are budgeted as a ratio**, not counted per request, because counts
  multiply down a call tree and land hardest on a dependency already failing.
- **Retryability derives from the code numbering** — the `5500` split already
  separates *unavailable* from *broken*. Invariant 5 keeps the two from
  drifting apart.
- **A circuit breaker** fails fast while a target is down, because retries
  alone make an outage worse.

**Every number in it is a guess and is labelled as one.** They are classed
structural, agreed or empirical so a reader knows which may be changed; they
carry the formula relating them; and each has a named observable that would
falsify it, all of which the existing error codes already make visible. The
document states how to replace them with measurements once a service has 30
days of production data.

**Open, and now the sharpest gap.** Nothing owns the deny list that
`credentials.md` says an incident would need, and nothing has measured any of
these values. The first service to reach production should be treated as the
calibration run for the whole table.

---

## 5. Aggregator OpenAPI schema — done

Landed 2026-09-17 across `4320015`, `8d39bfa`, `d43a702` and `9c4e949`.

`sds-logging/references/aggregator-api.yaml` defines the aggregator's endpoints —
three when this landed, four since the batch endpoint — and is normative; `aggregator-api.md` becomes the rationale layer, matching how
`standard-api-endpoints.md` defers to `openapi.yaml`.

**The trap was avoided.** Nothing is copied: the enumerations, the error
envelope, the six record fields and the page wrapper are all `$ref`ed across
files from `openapi.yaml`. That needed `openapi.yaml` split into `LogFields`
and `LogPageBase` so the aggregator could compose rather than restate — and
`unevaluatedProperties` instead of `additionalProperties`, because the latter
cannot see through `allOf` and would reject every field it was meant to permit.
Both choices are commented in the file, since the instinct is to simplify them
back.

Invariant 6 walks every `$ref` in both files and fails when one resolves to
nothing, which is the new risk that referencing introduces in place of the old
one. Invariant 4 now also requires the markdown and the schema to document the
same endpoints.

The schema settles one thing the prose left implicit: a submission carrying
`recordId` is rejected rather than ignored.

**Since done.** Validating real documents against the schemas was left out
here for want of a JSON Schema dependency. It landed on 2026-09-29 in
`0855c92`: `project-kit/conformance/check_service.py --self-test` validates
fixtures against both schemas in CI, and checks a running service's standard
endpoints. The invariant checker itself stays PyYAML-only.

---

## 6. Release notes and version bump — done

Landed 2026-09-17 across `a4f24d5`, `06ba576` and `82dc5e4`, and tagged:
`v0.1.0` at `df84917`, `v0.2.0` at `82dc5e4`, the commit that adds the note.

`release-notes/0.2.0.md` holds 45 entries, matching
`git log --no-merges v0.1.0..v0.2.0` exactly — which
`project-kit/tools/check_release_note.py 0.2.0 --head v0.2.0` now confirms
rather than a count by hand.

**0.2.0, not 0.1.1.** Two commits carry `!` and a BREAKING CHANGE footer — the
path versioning and the Entra token lifetime — and below 1.0.0 a breaking
change increments the minor.

**A contradiction in the skill, fixed.** The note must be committed before the
tag, and the entry count must equal the commits in the range. The tag therefore
sits on the note's own commit, which is inside that range with no entry, so the
count was short by one at every release forever. The note now carries an entry
for itself, minted before the commit is written. The tag name was also never
stated: `v{version}` for the tag, `{version}.md` for the file.

**Version fields.** `plugin.json` and its mirror in `marketplace.json` moved to
`0.2.0`; the marketplace's own version stayed at `0.1.0`, because it tracks
which plugins are offered rather than what is inside them. Invariant 7 enforces
the mirror, which matters once third-party plugins are added.

**The next release is 0.3.0.** `27b20f8` renamed the `CRITICAL` severity to
`FATAL` after the tag, a breaking change, and below 1.0.0 a breaking change
increments the minor. The 2026-09-29 work added more breaking changes on top.

---

## 7. Operator roles beyond `operator` — done

Landed 2026-09-17 in `6ccecfd`, closing the last open decision in the specs.

Since 2026-09-29 (`4dec2d9`) the one operator role sits in a closed role
registry beside `logs.write`, and an operator request needs the operator scope
as well as the role. The decision below is unchanged.

**One role, deliberately.** `operator` grants every operator endpoint in the
estate. What was missing was never the second role — it was the reason for the
first, and the cost of having only it.

**The accepted gradient, now written down.** A health report exposes capacity
numbers; the aggregator holds every app's records and whatever identifiers
their tails carry. One role covers both, so anyone who can read a dashboard can
read the estate's logs. Acceptable while the operator population is small and
uniformly trusted; not acceptable once someone needs one endpoint and should
not have the other. **A read-only auditor arriving is the trigger.**

Two rules keep this cheap rather than a commitment: a role is defined in
`credentials.md` and assigned in the directory, never invented by an app; and
an app checks for the role it requires and ignores the rest, so adding one
later cannot break anything deployed.

---

## 8. `DB-5501` severity — done

Landed 2026-09-17 in `caca710`. The severity was named `CRITICAL` then, and
`FATAL` since `27b20f8`; nothing else about the decision changed.

**Conditional, matching `SYS-5500`:** `ERROR` while transient, `FATAL` once
sustained past 60 seconds.

Both unconditional answers reproduce a mistake this table already made once.
Left at `ERROR`, an app serving nobody pages no one. Raised to `FATAL`,
every traffic burst pages someone until the severity is ignored — which is
precisely what the `SYS-5500` row was rewritten to undo. The condition is
normal at one duration and an outage at another, which is what a conditional
row is for.

Sixty seconds is classed empirical per `service-calls.md`: an app may change it
and must record that it has.

---

## 9. Promoting `request` to a record field

**Open decision in** `log-record.md`, with a recommendation already attached:
leave it in the structured tail until indexed lookup by request is actually
needed.

Kept on the list so the trigger is written down rather than remembered.
Revisit when an operator asks for lookup by request often enough to be a
workflow, or when the log store gains an index that makes unbounded cardinality
cheap. Note that promoting it is a breaking change to `LogRecord`, so it wants
to land with item 1's versioning rule already in place.

---

## 10. Reference-link and restatement checks — done

Landed 2026-09-29 in `e8d460a`, as invariants 8 and 9 in `CLAUDE.md`.

The question was that the pointers one file makes to another, and the facts
restated with a named source, were unchecked — and a restatement had drifted
once already: `standard-api-endpoints.md` and `openapi.yaml` described the log
record's `id` as "assigned by the emitting app" after `log-record.md` had been
changed to say it is allocated and never derived at the point of use.

- **Invariant 9** resolves every file a skill document names the way an
  installed copy would — from `skills/`, beside the naming file, or from the
  naming skill's directory — and fails a repository-root path outright. That
  covers steps 10.1 to 10.3 as planned, including the `SKILL.md` reference
  lists. On its first run it found a bare `aggregator-api.yaml` in a comment in
  `openapi.yaml`, fixed in `c360907`.
- **Invariant 8** compares every copy of the severity and type values with the
  schema — the restatement the `FATAL` rename had to carry through six edits by
  hand.

The `id` drift itself remains item 5's job, by making the schema the single
definition; since `90d5192` the schema enforces the id's format too.

---

## 11. Software id registry service

A future service is expected to handle the software registry and repository
management. The question raised on 2026-09-17 was whether it should also mint
change identifiers.

### The answer: no for minting, yes for the id and for verification

A `Change-Id` is minted at `git commit` time. A network call there puts the
service on the critical path of every commit in the estate — offline, in a
container, in a pre-commit hook, in CI. When it is down, either commits stop or
the rule gets bypassed, and a rule bypassed under pressure is worse than none,
because the history then has gaps indistinguishable from commits that predate
it. It also buys nothing: `{software-id}-{timestamp}-{random}` is
collision-resistant by construction, which is why the format has a random tail.

The software id is the opposite case. It must be unique across the estate,
stable forever, and identical in log records and release notes — none of which
anything local can enforce. That is the registry's job, and
`log-record.md` already writes the spec for it: *"supplied by the project
itself, or by the id-issuing service once one exists."*

| Concern | Where |
|---------|-------|
| Allocate a software id, once, at repository creation | The service |
| Resolve, list and retire ids | The service |
| Store the allocated id | A file in the repository |
| Mint a `Change-Id` | Locally, from the stored id |
| Verify ids resolve, and no identifier repeats | CI, asynchronously |

Verification is the useful integration, not generation: it catches an invented
id loudly without a commit ever depending on a service being reachable.

### Work, before the service exists

| # | File | Edit |
|---|------|------|
| ~~11.1~~ | `log-record.md` | **Done** in `55895d6`: a repository stores its id in `.bioeksen/software-id`, and this one holds `bioeksen-sds` |
| ~~11.2~~ | `release-notes.md` | **Done** in `55895d6`: minting is local and MUST NOT require a network call |
| 11.3 | — | When the service exists: the allocation and resolution endpoints, specified like any other app, under `/api/v1/`. The aggregator's `azp`-to-id mapping is no longer configuration: since `926a0ae` it is served by `bio-softop`'s registry |

The verification row above now has its local half: `project-kit/tools/commit_msg.py`
fails a `Change-Id` whose software id is not the one in `.bioeksen/software-id`.
Checking that the id resolves estate-wide waits on 11.3.

---

## 12. Move the repository to the company organisation

The repository lives under a personal GitHub account, publicly readable under
a proprietary licence, and every generated project will reference it through
`project-kit/template/`. A contract every service depends on should be owned
by the company, and whether its internals — the auth design, the endpoint
list — should be public is a decision nobody has taken.

### Work

| # | Step | Detail |
|---|------|--------|
| 12.1 | Transfer | Move it to the company organisation. GitHub redirects the old path, so nothing breaks on the day |
| 12.2 | Decide visibility | If private, developers need `gh auth login` and `gh auth setup-git`, per `project-kit/README.md`. CI needs nothing: since `sds-ci` it runs the kit the CI image carries |
| 12.3 | One commit | Point `README.md`'s install commands, and the `repo` in the template's `settings.json`, at the new path |
| 12.4 | Workflows | If it moves to the estate's forge, this repository's own `.github/workflows/invariants.yml` moves to `.forgejo/workflows/`, as `sds-ci` requires of every repository there. The project template's workflow already lives there |

---

## Not on this list

Recorded so nobody re-derives them as gaps:

- **A second language binding.** `sds-logging/SKILL.md` already says to split
  `sds-<language>` skills out when a second language is in use. Until then
  there is nothing to write, and the conformance check in `project-kit/`
  holds any language to the contract without one.
- **End-user authentication.** `sds-auth` covers app and operator principals
  deliberately. An app's own end users are that app's domain.
- **Metrics and tracing.** `X-Request-Id` gives correlation; a metrics
  convention is a separate contract nobody has asked for yet.
