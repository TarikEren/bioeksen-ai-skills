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

## Bug fixes

A bug is a missing test. Before fixing one, write the test that reproduces it —
the input that gets the wrong answer, asserting the right one — and watch it
fail. When the bug is a wrong error code, the selection procedure decides the
right one.

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

## Rationalizations

| It sounds like | What it is |
|----------------|------------|
| "This is too simple to need a test" | Simple code breaks too, and its test is the cheapest one to write |
| "I will add the test afterwards" | A test written afterwards has never been seen failing, and afterwards rarely comes |
| "I tested it by hand" | Once, in one state; the next change will not repeat it |
| "The test would only repeat the code" | Then its expectation came from the code; take it from the contract |
| "There is no time" | The time is spent anyway, later, finding what the test would have caught |
