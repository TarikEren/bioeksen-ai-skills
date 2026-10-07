---
name: sds-testing
description: BioEksen test-first development. Use before writing or changing behaviour in a BioEksen service — a feature, a bug fix, an endpoint, a log statement, an auth check — to write the failing test first, and to find the contract test a shared convention requires.
---

# Test-First Development

Every behaviour a BioEksen service gains or changes is driven by a test written
first. The shared conventions make this unusually direct: nearly every rule in
the other `sds-*` skills is already an assertion — `limit=0` is 400 `VAL-4005`,
a rejection's log record carries the response's code — so the expected value of
most tests is written down before the code exists.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

- `references/contract-tests.md` — the cases a service's tests MUST contain for
  each convention it implements, each citing the document normative for it.

Paths such as `sds-logging/references/log-record.md` name a file in another
skill of this plugin, relative to the plugin's skills directory: the parent
of `${CLAUDE_SKILL_DIR}`, which is this skill's own directory.

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

## The standard endpoints

For the four standard endpoints the failing suite already exists: the project
kit's conformance check. Run it against the service before implementing them,
and its failures are the red list:

```bash
python .bioeksen-sds/project-kit/conformance/check_service.py --base-url http://localhost:8080
```

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
   its comment cites the defect.
2. Put a plain precondition test beside it, proving the setup reaches the
   rule: the record exists, the request gets as far as the step that fails. An
   expected failure passes on any error, so without its precondition a broken
   fixture would keep it green.
3. The `fix` commit for the defect promotes it to a plain test. That test is
   the one that failed before the fix and passes after it.

Adding the expected-to-fail test is a `test` commit: it covers behaviour that
already exists, wrongly. A test is never marked expected to fail because it is
flaky, slow or hard to set up. That would hide a test; this records a defect.

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
  not run, with the reason, and CI MUST treat it as a failure. A green run
  that ran nothing is the most misleading result a suite can give.
- **Test each claim at the lowest tier that can prove it** (SHOULD): a pure
  function directly, a service against fakes, a query or a constraint against
  a real disposable database, a flow end to end. A claim proved low is not
  proved again higher up without a reason, since every tier up is slower and
  fails for more reasons.
- **Each test names its source** (SHOULD): the requirement it was derived
  from, or, for a contract case, the document its **Source** column names, in
  its own title or its suite's. A test with no source cannot be judged right
  or wrong when it fails.

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

## Commits

The test lands in the same commit as the behaviour it drives, typed for that
behaviour as `feat` or `fix`: one commit is one change, per
`sds-commit/SKILL.md`. A `test` commit is for tests added to behaviour that
already exists. A red state is never pushed to a shared branch.

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
