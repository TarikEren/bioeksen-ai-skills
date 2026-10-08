---
name: sds-testing
description: BioEksen test-first development and testing practice. Use before writing or changing behaviour in a BioEksen service — a feature, a bug fix, an endpoint, a log statement, an auth check — to write the failing test first and find the contract test a shared convention requires; and when writing, changing, running or reviewing tests — acceptance tests written ahead of the code and blind to it, cases derived from the specification, the lowest tier that can prove a claim, outcome assertions, fixtures and fakes, known defects, and running database and browser suites safely.
---

# Test-First Development

Every behaviour a BioEksen service gains or changes is driven by a test written
first. The shared conventions make this unusually direct: nearly every rule in
the other `sds-*` skills is already an assertion — `limit=0` is 400 `VAL-4005`,
a rejection's log record carries the response's code — so the expected value of
most tests is written down before the code exists.

A test is evidence that the code does what its specification asks. Test code
is held to the same bar as product code: **type-safe, secure and modular**. A
test that cannot fail, or that passes for the wrong reason, is worse than no
test, because it is trusted.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

- `references/contract-tests.md` — the cases a service's tests MUST contain for
  each convention it implements, each citing the document normative for it.
- `references/writing-tests.md` — general test-quality principles, ranked
  below this skill per **Test quality reference**.
- `references/nextjs.md` — how an app scaffolded from the nextjs template
  carries this skill out: its runners, its results-only script, its per-role
  schemas, and patterns.

Paths such as `sds-logging/references/log-record.md` name a file in another
skill of this plugin, relative to the plugin's skills directory: the parent
of `${CLAUDE_SKILL_DIR}`, which is this skill's own directory.

## Read first

1. **`references/contract-tests.md`**: the cases every service must contain.
2. **The project's tests README**, if it has one.
3. **The project's test scripts and runner configs**: which tiers exist, which
   files each one matches, its environment and its setup files.
4. **The existing helpers, fixtures and fakes.** Reuse them.
5. **The skill for the code under test.** Its rules are what the tests
   hold the code to.

## Test quality reference

Read `references/writing-tests.md` when writing, changing, reviewing or
debugging tests, adding mocks or fakes, or introducing test-only helpers and
cleanup methods.

This reference defines general test-quality principles:

* Name the regression each test is intended to catch.
* Derive expected results independently from the implementation.
* Test observable behavior rather than implementation details.
* Use mocks only at justified isolation boundaries.
* Keep tests deterministic, isolated and maintainable.
* Review realistic mutations to identify unprotected behavior.

**This skill's rules take precedence over the reference.**
In particular:

* Follow the ownership, visibility and black-box requirements in
  **Acceptance tests**. Acceptance tests must remain specification-driven
  and must not inspect product code.
* Follow the tiers and boundaries in **Keeping the suite honest**.
* Use only the results-only interface for running acceptance tests.
* Follow the database safety, worktree isolation and reporting
  requirements in **Test databases** and **Running the suites**.
* Follow the type-safety, fixture, accessibility,
  expected-to-fail and known-defect conventions.

Apply the reference's quality gates within these constraints. Where
the reference and this skill differ, this skill governs. Where the
project's own conventions or its tests README impose a
stricter rule, follow the stricter rule.

## The rule

Behaviour MUST NOT change without a test that failed before the change and
passes after it. That holds for a new feature, a bug fix, and any change to
what a caller, an operator or a reader of the logs can observe.

A refactor changes no behaviour, so it needs no new test — but it MUST start
with the behaviour it touches covered and green, and end the same way. A
refactor that needs a test changed before it passes is a behaviour change.

The failure is the point. A test written after its code passes the first time
it runs, so nobody has seen it able to fail, and a test that cannot fail tests
nothing. Watching it fail first is the only evidence that it checks what it
claims to.

The rule governs what reaches a shared branch, not the order keystrokes
happened in. CI checks that every `feat` or `fix` commit changes a test or
names an exemption; review checks that the test would have failed without the
change.

## Exemptions

| Exemption | Covers |
|-----------|--------|
| `docs` | Prose no test can read: documentation, comments, a specification |
| `config` | A configuration value, where the code that reads it is already tested |
| `generated` | Code produced by a generator from a source that is itself tested |
| `acceptance` | Behaviour driven by its unit's acceptance tests, already on its branch, per **Acceptance tests** |

These are the only exemptions. A commit relying on one names it with the
trailer `sds-commit/SKILL.md` defines, so the claim is visible in review and
checkable in CI.

A spike is not an exemption. Spike code answers a question and is thrown away;
it is never merged, and the real implementation starts again, test-first.

## The cycle

1. **Red.** Write one test for one behaviour. Run it and watch it fail — and
   fail *for the missing behaviour*: an assertion that the status, the code or
   the field is wrong. A failure from an import error, a typo or a fixture that
   crashed proves nothing; fix the test until it fails the way the missing code
   makes it fail.
2. **Green.** Write the least code that makes it pass. Run that test, then the
   whole suite.
3. **Refactor.** Tidy the code and the test with everything green, and keep it
   green.
4. Repeat for the next behaviour.

## Acceptance tests

Every unit of development — a feature, a sprint, a task — MUST have acceptance
tests that are red before its code exists, written by someone who has not seen
that code, for a developer who does not see them:

- **The tester writes them from the specification**: the requirements, the
  contract the `sds-*` skills define, and the architecture decisions taken for
  the unit. Never from the code, which the tester does not see.
- **The developer MUST NOT see them.** The developer works from each test's
  name, the references it cites, its description and its result, alongside
  the same architecture decisions and specifications, and makes it pass.
- **They land first, red,** in `test` commits on the unit's branch, each seen
  failing for the missing behaviour, not for a missing name: the developer
  first builds the skeleton the tests compile against. They are never marked
  expected to fail. They are red because the behaviour is not there yet, not
  because of a defect.
- **The unit's branch is red until the unit ends; the main branch only ever
  receives green.** Merging the unit into it is the loop's last gate.

A developer's own tests, such as a unit test beside the code it drives, still
follow **The cycle** and land in the commit with their behaviour. A `feat` or
`fix` commit whose only tests are its unit's acceptance tests, already on its
branch, names the `acceptance` exemption.

A developer who writes both the code and its only test can shape either to fit
the other. A test written blind to the code cannot be bent to it, and code
written blind to the test can pass it only by doing what the specification
says. Two people who never saw each other's work agreeing on the result is the
evidence one author cannot give.

### Two kinds of test, two owners

| Kind | Where | Owner | Written from |
|---|---|---|---|
| Acceptance | The project's acceptance folders | The tester | The requirements and the plan's contract, black-box, one or more per task |
| Unit and component tests of internals | Beside the code | The developer who owns the code | The code's own rules (the code skills' test sections) |

An acceptance test reaches the code only through the contract. It never
imports anything the contract does not name. A service's internals are the
developer's to test.

### What the developers see

- **Titles are the developers' view of the test.** Each starts with its
  requirement and task ids, then states the rule:
  `REQ-0031 T5: refuses a second widget with the same code on one site`. A
  developer who reads only the title and the failure message must know which
  rule failed.
- **Failure messages carry the evidence without the code.** Assert with
  matchers that print expected and received values, and add a message where
  the matcher's alone would not say which rule failed.
- **The developers run the tests only through a results-only interface.** For
  each test it prints its title, its status and its failure message, then a
  summary. It prints nothing else: no test source, no code frames, no stack
  traces, and no file paths. It exits 0 when every test passed, 1 when a test
  failed or a file failed to load, and 2 when a tier with tests could not run.
  A tier that could not run is never a pass.

### Red for the right reason, against the skeleton

**The cycle** still holds, adapted. Before implementation the developers build a
skeleton of the contract: exports that throw a not-implemented error, routes
that answer `SYS-5000` (500), components that render a stub. Each new test
runs against it and must fail with the rule's own signal: the not-implemented
error, a 500 `SYS-5000` (never a 501, which no SDS code maps to), or the
element not found. A type error, a missing module or a setup failure is a gap
in the skeleton or the contract: report it, and never loosen the test to
compile.

### Parallel worktrees

Each role works in its own git worktree, and two roles may run suites at the
same time. So each worktree gets its own schema in each disposable database,
named after the role, and its own end-to-end port. The guard (**Test
databases**) checks the database's name and the schema's.

### Disputes

A developer who believes a test is wrong reports it by its title; whoever runs
the loop passes it on. Re-read the requirement: fix the test if it is wrong, or
say which source makes it right.

## Where the expected value comes from

When an `sds-*` skill governs the behaviour, the test's expectation comes from
the contract, never from running the code and copying what it did:

- the error code from the selection procedure in
  `sds-logging/references/code-prefixes.md`
- the HTTP status from the range table in
  `sds-logging/references/error-codes.md`
- the fields from `sds-api-design/references/openapi.yaml`

An expectation copied from the code's output tests only that the code does
what it does. The case to write is in `references/contract-tests.md`.

A value the specifications class as empirical — a timeout, a breaker
threshold, the 60 seconds before `DB-5501` is `FATAL` — is asserted as the
app's configured value, read from where the app configures it, because an app
MAY override it and record that it has.

## The cases

- **Derive each case from its source:** a requirement, a recorded decision, an
  API contract, a database constraint, or a standard for API design,
  authentication or logging. The expected value comes from that source.
- **Read the implementation only to find its seams:** what to call, what to
  mock, what to seed. A test copied from the code proves only that the code
  does what it does.
- **Where the code and the source disagree, that is a defect.** Write the test
  from the source and treat it as a known defect (**Known defects**). Where the
  source is silent or ambiguous, ask. Do not pick an answer and encode it.
- **List the cases before writing any.** For each rule, go through:

| Case | For example |
|---|---|
| Success | The record is created and returned |
| Validation | Each field empty, too long, the wrong type, on each boundary; an unknown key under a strict schema |
| Unauthenticated | No session or credential |
| Unauthorised | Another user's record; a missing permission |
| Not found | An id that does not exist, and one that does not parse |
| Conflict | A duplicate; a stale version |
| State | Every transition the state machine forbids, not only the allowed ones |
| Concurrency | Two writers at once, where the rule depends on a read |
| Language | Each locale the UI supports, where copy or formatting changes |
| Accessibility | The accessible name, what is announced, where focus goes |

Drop a row only when it cannot apply, and say why in the report.

- **Add the contract cases.** For every endpoint, configuration value and log
  record a task adds, the cases `references/contract-tests.md` says every
  service must contain, every table of it that applies. They are never
  dropped, and their source is the document the table names.

## The standard endpoints

For the four standard endpoints the failing suite already exists: this
skill's conformance check, which ships with it. Run it against the service
before implementing them, and its failures are the red list:

```bash
pip install -r ${CLAUDE_SKILL_DIR}/scripts/requirements.txt
python ${CLAUDE_SKILL_DIR}/scripts/check_service.py --base-url http://localhost:8080 --operator-token <token>
```

It checks every response against `sds-api-design/references/openapi.yaml`,
and what no schema can express: the `X-Request-Id` echo, 401 `AUTH-4100`
without a credential, and, with an operator token, the code for each bad
query parameter. It exits 0 when every check passed, 1 when one failed, and 2
when one was not run: the packages are missing, the service cannot be
reached, or no operator token was given. Report a 2 as not run, never as
passed.

Implement until every check passes. The service's own tests still cover what
the conformance check cannot see from outside: what the service logs, and what
it calls.

A TypeScript app also runs the contract suites `@bioeksen/sdk/testing`
exports. They cover the cases in `references/contract-tests.md` that the
conformance check cannot see from outside: what the app logs and what it
calls.

## Bug fixes

A bug is a missing test. Before fixing one, write the test that reproduces it —
the input that gets the wrong answer, asserting the right one — and watch it
fail. When the bug is a wrong error code, the selection procedure decides the
right one.

## Known defects

A test written from the contract sometimes exposes a defect the change at hand
will not fix. It is committed anyway, so the defect is recorded where it
cannot be forgotten:

1. Mark it expected to fail, strictly, so it fails the suite the moment it
   starts to pass: `it.failing` in Jest, `test.fails` in Vitest, `test.fail()`
   in Playwright, `pytest.mark.xfail(strict=True)`. Its title states the rule;
   its comment cites the source, and the defect once it has been recorded.
2. Put a plain precondition test beside it, proving the setup reaches the
   rule: the form renders, the record exists, the request gets as far as the
   step that fails. An expected failure passes on any error, so without its
   precondition a broken fixture would keep it green.
3. **Add it to the project's known-defect table**, if the tests README keeps
   one.
4. **Report the defect.** Whoever called you records it.
5. The `fix` commit for the defect promotes it to a plain test, and takes it
   out of the table. That test is the one that failed before the fix and
   passes after it.

Adding the expected-to-fail test is a `test` commit: it covers behaviour that
already exists, wrongly. A test is never marked expected to fail because it is
flaky, slow or hard to set up. That would hide a test; this records a defect.

## Writing tests

### Sources and names

- **One claim per test.** The title states the rule, not the steps: "refuses a
  second revision with the same number", not "calls create twice".
- Titles and comments follow the language of the file you are editing.

### Assertions

- **Assert outcomes, not call shapes:** the returned value, the stored rows,
  the status and error code, what the user sees. A test that checks which ORM
  method ran breaks on a harmless rewrite and proves nothing about the result.
- **A side effect that is itself the rule** (an audit row written, nothing
  written after a rejection) is asserted through the state the fake holds or
  the rows in the database, not through a call count.
- **At a boundary, what crossed it is the outcome.** For a form, assert what
  reached the server action; for an outbound call, what was sent.
- **Assert the specific error:** its code or class. A bare `toThrow()` also
  passes on a typo in the setup.

### Type safety

- **No escape hatch from the type checker** to get a fixture through. The
  compiler checking the tests is part of what they prove.
- **Build rows with typed builders** that take overrides.
- **Type a fake to the real interface**, so a change to the schema or the
  interface breaks the build until the fake follows it.

### Modularity

- **Reuse and extend the project's helpers, fixtures and fakes.** Never start a
  second set beside them.
- **Mock at the boundary the unit depends on:** the repository under a service,
  the service under a handler. Never mock the unit under test.
- **Restore what a test changes:** environment variables, spies, timers,
  globals.

### Determinism

- **No sleeps and no arbitrary timeouts.** Wait for a condition.
- **Rules that depend on time** use fake timers or an injected clock.
- **On a shared database, each test creates its own rows** with unique codes,
  and never depends on another test's rows or on test order.
- **No network,** except to the app under test.

### UI

- **Query by role and accessible name.** A query by test id or CSS
  class passes on an element no user can find.
- **Take labels from the dictionaries**, never from string literals, so a copy
  change does not break the test and a missing key does.
- **Act as a user.** Type into fields and **click the submit button**.
  Submitting the form or calling a handler directly skips the browser's own
  validation, so it cannot catch a form that refuses to submit.
- **Assert what is announced,** not just what is in the DOM. A rejection must
  be inside a `role="alert"` region, and a success inside a `role="status"`
  region.
- **Assert where focus lands** after each kind of result, as the UI's own
  forms rules place it, and after a dialog closes.
- **Cover each locale** where the change affects copy or formatting.

### Server boundary

- **No credential:** the status and error code the authentication standard
  names.
- **Another user's record:** the rejection the standard names, with nothing
  about the record in the body.
- **A malformed body:** a validation error. **An id that does not parse:** not
  found, as for an id that does not exist.
- **The response carries only its DTO's fields:** no internal ids, paths,
  secrets or stack traces.

### Never

- Whole-tree snapshots. Once accepted, they pass on anything.
- `.only` or `.skip` in committed code. A known defect is marked expected to
  fail instead (**Known defects**).
- **Weakening a test to get it green** (**Keeping the suite honest**). If an
  existing test contradicts its source, report it.

## A test that cannot fail proves nothing

**The cycle** has every new test seen failing for the missing
behaviour. Where the code already exists, do it like this:

1. Feed it the case the rule forbids, or change its expected value locally.
2. Confirm it goes red **with the rule's own message**, not a setup error, a
   missing mock or a type error.
3. Restore it.

Never edit product code to do this. If the only way to see a test fail is to
break the implementation, say so in the report instead. A test that stays
green when its expectation is changed asserts nothing: fix it before going on.

## Keeping the suite honest

- **Never weaken a test to get it green.** No loosened assertion, deleted
  test, longer timeout, added retry, or expected value changed to match the
  code, unless the source the test cites has changed. A test believed wrong is
  argued against that source, and changes only if the source says so.
- **A failure that might be flaky is re-run in isolation, up to three
  times.** A test that then passes is still reported as flaky, with the
  failures seen. Flakiness is never hidden with retries, longer timeouts or
  sleeps: a test that passes one time in three cannot be seen failing.
- **Not run is never passed.** A suite or tier that could not run, for want
  of a database, a browser, the right runtime or a variable, is reported as
  not run, with the reason and what would make it runnable, and CI MUST treat
  it as a failure. A green run that ran nothing is the most misleading result
  a suite can give.
- **Test each claim at the lowest tier that can prove it** (SHOULD): a pure
  function directly, a service against fakes, a query or a constraint against
  a real disposable database, a flow end to end. A claim proved low is not
  proved again higher up without a reason, since every tier up is slower and
  fails for more reasons.
- **Each test names its source** (SHOULD): the requirement it was derived
  from, or, for a contract case, the document its **Source** column names, in
  its own title or its suite's, the way the project cites requirements. A test
  with no source cannot be judged right or wrong when it fails.

## Running the suites

Run in this order, using the project's own scripts, and run the acceptance
tiers through the results-only interface. Get your own tests green at one level
before moving to the next:

1. the typecheck, for app code and for test code, after any type generation
   the project needs;
2. the linter, on the test paths;
3. unit and component tests;
4. integration tests;
5. end-to-end tests.

## Test databases

A suite that creates, migrates or empties a database MUST refuse to run unless
the target is disposable:

- named apart from the development database, by a fixed suffix such as
  `_integration` or `_e2e`;
- not the database the app's own configuration names;
- on this machine, or on a host the suite has been told it may use.

It MUST NOT point at a shared or production database, and MUST NOT print a
connection string. A guard that cannot tell refuses, and the suite is
reported as not run.

In a monorepo, each app's disposable databases are its own: named with its
software id in snake case before the suffix, e.g. `bio_inventory_integration`,
and a suite empties only its own app's. Apps sharing one database server then
cannot empty each other's data, and a name says whose it is. A name longer
than the engine allows an identifier, 63 bytes in PostgreSQL, is refused
rather than truncated, because two truncated names can collide.

**A suite that creates or resets a database runs only after you have checked
its guard.**
- Read the suite's environment and global setup files.
- If the guard is missing, or you cannot tell, do not run the suite. Report it
  as not run, and why.
- Never print `.env` files or connection strings.

## Bookkeeping

- **If the tests README keeps a coverage map** (which file covers which
  requirement), add a row for each new file and update the rows you changed.
- **If the tests README describes the helpers**, describe each helper you add
  or change there too.
- **If the project keeps a review record with a list of missing tests**,
  report which of its rows your tests close. Whoever called you updates the
  record.

## Commits

A developer's test lands in the same commit as the behaviour it drives, typed
for that behaviour as `feat` or `fix`: one commit is one change, per
`sds-commit/SKILL.md`. A `test` commit is for tests added to behaviour that
already exists, and for a unit's acceptance tests, written ahead of it. A red
state is never pushed to a shared branch, except the acceptance tests on their
own unit's branch, per **Acceptance tests**; the main branch only ever
receives green.

## When it seems impossible to test first

| The behaviour depends on | Write the test by |
|--------------------------|-------------------|
| Time — a startup budget, a sustained exhaustion, a token's `exp` | Injecting the clock and advancing it |
| Another service being down, slow or wrong | Faking that service at the client boundary |
| The identity provider | Signing test tokens with a key the verifier is configured to trust in tests |
| What is logged | Capturing the records the logging binding emits, and asserting on them |

## Test seams

A test seam is product code that lets a test drive what it cannot reach from
outside: a test sign-in, an injected clock, a fake for another service. A seam
MUST be enabled only by validated configuration in a test environment, and
MUST fail closed everywhere else: a production deployment refuses its setting
at startup with `CFG-5001`, per `sds-config/SKILL.md`. A test sign-in that
works in production lets anyone mint an identity.

## Before handing back

- Every rule in scope has its case list, and every dropped case has a reason.
- Every new test cites its source, asserts an outcome, and has been seen to
  fail for the right reason.
- The diff has no type escape hatch, `.only`, `.skip` or whole-tree snapshot,
  and no existing test has been weakened.
- Every known defect has an expected-to-fail test, a precondition test beside
  it, and a line in the report.
- The typecheck, the linter, and every tier you could run are green. Each tier
  you could not run is named, with the reason.

## Rationalizations

| It sounds like | What it is |
|----------------|------------|
| "This is too simple to need a test" | Simple code breaks too, and its test is the cheapest one to write |
| "I will add the test afterwards" | A test written afterwards has never been seen failing, and afterwards rarely comes |
| "I tested it by hand" | Once, in one state; the next change will not repeat it |
| "The test would only repeat the code" | Then its expectation came from the code; take it from the contract |
| "There is no time" | The time is spent anyway, later, finding what the test would have caught |
| "Just add a retry" | A retry makes a flaky test pass and the race behind it invisible; find the race |
| "It passed on the second run" | Then it fails some of the time; report it as flaky |
| "Skip it for now" | A skipped test is a deleted test nobody reviewed; a known defect is marked expected to fail instead |
| "I need to read the acceptance test to pass it" | Then the code would fit the test, not the specification; work from its name, its references and the specification |
