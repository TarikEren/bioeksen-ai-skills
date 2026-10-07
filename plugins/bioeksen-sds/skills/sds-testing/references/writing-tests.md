# Writing Good Tests

**Load this reference when:** writing or changing tests, adding mocks, selecting test layers, or adding test-only cleanup and helper methods.

## Overview

A test exists to catch a specific regression. Two principles govern everything here:

```text
1. Every test names the regression it catches.
2. Every test exercises the real subject under test.
```

Test-first development is required, per `SKILL.md`: write a failing test, implement the minimum change, then refactor. For regression tests, demonstrate that the test detects the defect before accepting the fix.

A test earns its place by protecting observable behavior, not by increasing coverage, freezing implementation details, or satisfying process requirements.

## Project-specific testing rules

This reference describes general test-quality principles. It does not
replace `SKILL.md`, the project's own testing workflow or specialized code skills.

**Before writing tests in a repository:**

1. Read `SKILL.md`, the project's own conventions, and its tests README.
   Follow their precedence rules.
2. Identify the test ownership model, visibility restrictions, available
   tiers, fixtures, test runner and execution interface.
3. Read the relevant backend or frontend skill for the subject under test.
4. Apply this reference's quality gates within the project's requirements.

### What `SKILL.md` and the project govern

`SKILL.md`, and within it the project's own conventions, govern:

* Who may write or inspect each test.
* Whether tests must be written before implementation.
* Which interfaces acceptance tests may exercise.
* The required test tiers, directory structure and naming conventions.
* Permitted mocks, fixtures, fakes and test seams.
* Test execution, reporting, database safety and cleanup procedures.
* Known-defect and expected-to-fail conventions.

This reference governs the general quality of test design:

* Meaningful regression detection.
* Independent expectations.
* Observable behavior and contract verification.
* Appropriate isolation and mock discipline.
* Determinism, maintainability and mutation resistance.

### Role-aware application

For specification-driven, black-box acceptance testing, derive
expectations from requirements and contracts without inspecting
implementation code. Respect any restrictions on source visibility.

For developer-owned unit and component tests, inspect the implementation
only as permitted by the project, while keeping expected results
independent of the implementation's logic.

For integration and end-to-end tests, follow the project's prescribed
boundaries, environment safeguards and execution interfaces.

### Conflict resolution

Never use this reference to override a stricter project-specific
requirement. In particular, do not bypass a mandated test runner,
expose restricted test source, replace required real integrations with
mocks, weaken database safeguards, or change test ownership.

When a project-specific rule conflicts with a general recommendation
here, follow the project-specific rule and preserve the underlying
quality objective wherever possible.

## Principle 1: Name the Regression

Before writing a test body, answer:

**What production change should make this test fail, and would that change be a bug or an intentional decision?**

A test earns its place by catching a wrong branch, missing side effect, incorrect argument, boundary case, or broken contract.

### Derive expectations independently

Use literals and hand-checked fixtures. Table-driven tests with independently derived `want` values are preferred.

An expectation computed by the code under test—or by its helpers—can reproduce the same defect and pass incorrectly.

```typescript
// ❌ Mirror assertion: both sides use the same builder.
const expected = buildSearchQuery({ tag: 'urgent' });
expect(buildSearchQuery({ tag: 'urgent' })).toBe(expected);

// ✅ Independently derived literal.
expect(buildSearchQuery({ tag: 'urgent' })).toBe('tag:"urgent"');
```

For complex outputs, use hand-verified fixtures or independently specified invariants. Do not use the implementation's own transformation logic to generate the expected result.

### No implementation change detectors

Avoid tests that only detect intentional implementation changes, such as assertions on:

* Private method names or internal object structures.
* Constant values without verifying their behavioral consequences.
* Exact error wording when the contract only requires an error category or response.
* Internal call sequences that are not part of the application's contract.

Instead, test the observable behavior that depends on the decision.

```typescript
// ❌ Freezes an implementation decision.
expect(MAX_RETRIES).toBe(5);

// ✅ Protects the retry behavior, at the configured attempt count.
await expect(runWithRetry(operation)).resolves.toBe('success');
expect(operation).toHaveBeenCalledTimes(config.retry.maxAttempts);
```

The example assumes the operation succeeds on its last permitted attempt. An attempt count is an empirical value, so the test reads the configured one, per `SKILL.md`. If retry exhaustion is also part of the contract, test that separately, including the final attempt and resulting error.

Intentional business rules are valid test targets when they define externally observable contracts. For example, authorization, audit retention, document approval, and data-integrity rules should be tested through their effects, not merely through internal constants.

### Test behavior, not source text

Asserting that a script, skill, or configuration contains an exact line proves only that the text exists.

* Run scripts against controlled inputs and assert outputs, side effects, and exit codes.
* Test configuration through the application or tool that consumes it.
* Test agent instructions by evaluating the consuming agent's behavior against representative scenarios.
* Do not write tests that merely grep source text or assert that a symbol remains present or absent.

Human-facing documentation that has no executable contract does not need a behavioral test.

### Test your contract, not the framework

Test the contract your code establishes at its boundaries: the route you register, the query you emit, the payload you produce, or the state transition you guarantee.

Do not duplicate upstream framework tests. For example, asserting that a router invokes a registered handler tests the router's mechanics, not your application.

When upstream behavior genuinely surprised you, write one narrow characterization test documenting the specific assumption your application relies on.

Apply the same boundary within your own code. Constructors, getters, constants, and trivial forwarding methods need tests only when they validate, normalize, default, derive, enforce, or cause meaningful side effects. Otherwise, test the first consumer-visible behavior that depends on them.

### Gate Function

```text
BEFORE writing the test body:

  Name the production change that should make the test fail.

  Cannot name one:
    → Redesign around an observable behavior.

  "The source text changed":
    → Execute the artifact and assert its effects.

  Only intentional implementation changes:
    → Change detector. Test the observable behavior
      that depends on the decision.

  Confirm the expected value is independently derived.

  IF it reuses the implementation's logic or helpers:
    → Replace it with a literal, hand-checked fixture,
      or independently specified invariant.

  Confirm the test verifies an application contract,
  not merely an upstream framework's behavior.
```

## Principle 2: Exercise the Real Subject

**Every test exercises the real subject under test.** Dependencies may be isolated when their behavior is outside the test's scope, but mocks must not replace the behavior the test claims to verify.

### The mock earns no assertions

A mock assertion passes when the mock is present and fails when it is absent. It says nothing about the real component unless the mock interaction itself is part of the subject's contract.

```typescript
// ✅ Real component behavior.
expect(screen.getByRole('navigation')).toBeInTheDocument();

// ❌ Mock existence.
expect(screen.getByTestId('sidebar-mock')).toBeInTheDocument();
```

Review question:

**Are we testing the behavior of a mock instead of the behavior of the application?**

If so, remove the assertion, use the real component, or move the test to the correct integration boundary.

### Mock at the right level

Understand the real method's side effects before replacing it. Keep the behavior the test depends on real; mock only the slow, external, nondeterministic, or otherwise unsuitable dependency.

```typescript
// ❌ The mock swallows a configuration write
// that duplicate detection depends on.
vi.mock('ToolCatalog', () => ({
  discoverAndCacheTools: vi.fn().mockResolvedValue(undefined)
}));

// ✅ Mock only the slow or external server startup.
// Keep the relevant configuration write real.
vi.mock('MCPServerManager');
```

When unsure, run the test against the real implementation first and observe which dependency actually needs isolation.

Do not mock merely to make a test easier to write or to avoid understanding the production behavior.

### Make doubles specific

When arguments, call counts, return values, or ordering are part of the contract, assert them explicitly.

* Use distinct fixtures for success, failure, and malformed responses.
* Configure each branch deliberately so an incorrect branch cannot satisfy the expectation.
* Avoid permissive fakes that accept arbitrary inputs or return generic success values.
* Verify meaningful side effects and outcomes, not simply that a dependency was called.

A mock call assertion is appropriate when the call itself is an observable contract, such as verifying that a notification is sent to the correct recipient with the correct payload.

### Use realistic fixtures

Mock and fake responses must satisfy the complete relevant contract of the real dependency.

* Include all required fields and documented fields consumed by downstream behavior.
* Use realistic values, types, nullability, and relationships.
* Preserve meaningful distinctions between absent, null, empty, malformed, and valid values.
* Include optional fields when their presence or absence affects the tested behavior.

Do not reproduce irrelevant incidental fields solely for completeness. Large fixtures should remain maintainable through shared test factories or fixture files, provided expected values remain independently derived and each test's relevant inputs remain clear.

### Production classes carry production methods only

Cleanup and helpers used exclusively by tests belong in test utilities, not in production classes.

Ask:

* Is this method called only from test files?
* Does the production class actually own the lifecycle of this resource?
* Would the method still make sense in production?

If the method exists only to support tests, put it in a test utility. If the production class owns the resource lifecycle, keep its legitimate lifecycle methods in production.

### Prefer real components over complex mocks

When mock setup outgrows the test logic, mocks omit methods the real components provide, or tests break whenever mock implementations change, consider an integration test using real components.

Review question:

**Do we actually need a mock here?**

Prefer a real implementation when it is practical, deterministic, and sufficiently fast. Use test doubles when they provide a clear isolation boundary without hiding the behavior under test.

### Gate Function

```text
BEFORE adding a mock or test helper:

  Identify the subject under test and its real side effects.

  Keep real the behavior on which the test depends.
  Mock only the justified external or unsuitable dependency.

  Ensure doubles represent the complete relevant contract,
  including fields and values consumed downstream.

  Give each meaningful branch a specific fixture.

  Confirm test-only cleanup and helpers live in test utilities,
  unless the production class genuinely owns the lifecycle.

  IF setup is dominated by mocks:
    → Reconsider the test boundary.
    → Prefer a focused integration test where appropriate.

  IF an assertion checks only mock existence:
    → Remove it or test the real behavior.

  IF the mock call itself is contractual:
    → Assert its meaningful arguments, count, and ordering.
```

## Principle 3: Choose the Right Test Layer

Use the narrowest test layer that adequately verifies the contract. Do not force every behavior into a unit test or duplicate exhaustive assertions at every layer.

| Test layer       | Purpose                                                              | Typical example                                              |
| ---------------- | -------------------------------------------------------------------- | ------------------------------------------------------------ |
| Unit             | Verify a focused business rule or transformation.                    | Validation, authorization decisions, query construction.     |
| Integration      | Verify interactions between real application components.             | Service, database transaction, event dispatch, persistence.  |
| End-to-end       | Verify critical user-facing workflows across application boundaries. | Document submission, review, approval, and resulting status. |
| Characterization | Document a surprising, observed dependency behavior.                 | A specific upstream response or compatibility assumption.    |

### Selection rules

* Prefer unit tests for isolated logic with clear inputs and outputs.
* Use integration tests when correctness depends on component interactions, persistence, transactions, or actual event processing.
* Use end-to-end tests for a small number of critical workflows that require confidence across the application boundary.
* Use characterization tests sparingly to preserve important observed behavior while refactoring or replacing dependencies.
* Avoid testing framework mechanics unless your application relies on a specific, surprising behavior.

A critical workflow may need focused unit tests for its edge cases and a smaller number of integration or end-to-end tests for its complete contract.

## Principle 4: Isolate Tests and Keep Them Deterministic

Tests must produce reliable results independent of execution order, unrelated state, or environmental timing.

### Isolation

* Each test establishes the state it requires.
* Tests do not depend on another test running first.
* Tests clean up resources they create, including temporary files, database records, environment modifications, processes, and subscriptions.
* Shared fixtures are immutable where possible; mutable state is recreated or reset for each test.
* Tests do not modify developer data, production resources, or shared environments.

Use the test framework's lifecycle hooks or dedicated utilities for setup and cleanup. Avoid adding test-only lifecycle methods to production classes.

### Determinism

* Control clocks, randomness, and external inputs when they influence expected behavior.
* Avoid arbitrary sleeps and timing assumptions.
* Synchronize asynchronous work using explicit conditions, promises, events, or framework-provided waiting utilities.
* Do not rely on network services or external systems unless the test specifically verifies that integration.
* Ensure temporary paths, generated identifiers, and concurrent operations do not collide.
* Verify that tests behave correctly under the repository's supported execution and parallelization modes.

A test that passes only when run alone is not reliable protection for the application.

### Cleanup

Cleanup must be reliable even when assertions fail.

Use `try/finally`, test lifecycle hooks, or equivalent framework mechanisms where necessary. Clean up only resources the test owns; never erase shared or externally managed data indiscriminately.

## Principle 5: Follow a Verifiable TDD Workflow

Test-first is required for new behavior and regression fixes, per `SKILL.md`.

```text
RED:
  Write a focused test for the expected observable behavior.
  Run it against the current implementation.
  Confirm it fails for the intended reason.

GREEN:
  Implement the minimum production change.
  Run the test again, then the whole suite.
  Confirm it passes.

REFACTOR:
  Simplify the implementation and tests without
  changing the verified behavior.
  Rerun the whole suite.
```

### When test-first seems impractical

These situations make test-first harder, never optional. The exemptions in
`SKILL.md` are the only ones. Test-first may seem impractical when:

* Investigating an unfamiliar legacy system.
* Reproducing a difficult intermittent failure.
* Exploring an undocumented external dependency.
* Building a spike to discover the correct contract. A spike is thrown away, never merged, per `SKILL.md`.
* Working in an environment where the test harness must first be repaired.

In these cases, establish the behavior and contract first, then write the test and see it fail before the implementation it drives. For regression fixes, reproduce the defect and demonstrate that the test detects it before accepting the implementation change.

Do not claim a test was written first or observed failing unless that actually happened.

### Tests ship with the implementation

A complete behavior change includes the tests needed to protect its contract.

Ship the tests that meaningfully cover the behavior, including relevant boundaries and failure modes. Trivial code, human-facing prose, and implementation details do not earn tests merely for coverage.

## Principle 6: Review Test Isolation, Coverage, and Mutation Resistance

Before finishing a test file, review the protection it provides.

### Coverage is not test quality

* **Code coverage** measures which code was executed.
* **Assertions** verify particular outcomes and conditions.
* **Mutation testing** provides evidence that selected code changes are detected.
* **Requirements coverage** checks whether specified behaviors have corresponding tests.

None of these alone proves that a test suite is complete or correct.

Prioritize meaningful behavioral protection over arbitrary coverage percentages.

### The Mutation Check

Before finishing, mentally mutate the production code. At least one relevant test should fail for each realistic mutation.

Consider:

* Wrong constant or argument.
* Wrong branch handler.
* Missing state change or side effect.
* Empty, default, or incorrect return.
* Missing validation for zero, empty, null, unauthorized, or malformed input.
* Incorrect persistence or transaction behavior.
* Duplicate, omitted, or incorrectly ordered event processing.
* Incorrect handling of asynchronous failure or retry exhaustion.

A mutation that nothing catches identifies an unprotected behavior—or a test that does not meaningfully verify the intended contract.

### Automated mutation testing

Use automated mutation testing when the repository has suitable tooling and the expected benefit justifies the runtime and maintenance cost.

* Prefer targeted mutation runs for critical logic.
* Investigate surviving mutations that represent realistic defects.
* Distinguish equivalent mutations from genuine gaps in test protection.
* Do not treat a mutation score as a universal quality threshold.
* Do not add mutation tooling solely to satisfy a process requirement.

The mental mutation review remains required even when automated mutation testing is unavailable.

## Agent Execution Workflow

When asked to write or modify tests, follow this procedure:

```text
1. INSPECT
   Identify the test framework, relevant existing tests,
   fixtures, setup, conventions, and available commands.

2. DEFINE
   Name the observable behavior, intended contract,
   and realistic production regression the test catches.

3. SELECT
   Choose the appropriate test layer and isolation boundary.

4. DESIGN
   Construct independent expectations and realistic fixtures.
   Identify meaningful boundary and failure cases.

5. IMPLEMENT
   Write the test first and see it fail, per `SKILL.md`.
   Keep the subject real and justify every test double.

6. VERIFY
   Run the focused test.
   For regression tests, confirm the defect is detected.
   Run relevant neighboring tests, then the whole suite.

7. REVIEW
   Check isolation, determinism, cleanup, mock fidelity,
   assertion quality, and realistic mutations.

8. REPORT
   Summarize the behavior covered, tests added or changed,
   commands executed, actual results, and remaining limitations.
```

### Handling failures

When a test fails:

* Determine whether the failure is caused by a production defect, an incorrect expectation, a fixture problem, test contamination, or an environmental issue.
* Do not weaken an assertion to obtain a passing result. Change it only when the source it cites has changed, per `SKILL.md`.
* Correct tests whose expectations contradict the actual documented contract.
* Preserve regression coverage when adjusting a test for a legitimate contract change.
* Report failures that remain unresolved; do not imply the suite passed when it did not.

When a test cannot be executed, explain why and distinguish reviewed code from verified behavior.

## Quick Reference

| When you...                  | Do                                                                        |
| ---------------------------- | ------------------------------------------------------------------------- |
| Write any test               | Name the realistic regression it catches.                                 |
| Build an expected value      | Derive it independently; never reuse the implementation's logic.          |
| Test a script or document    | Execute the artifact or evaluate its consumer's behavior.                 |
| Test a dependency            | Verify your application's boundary contract.                              |
| Choose a test layer          | Use the narrowest layer that adequately verifies the behavior.            |
| Reach for a mock             | Identify the real side effects and justify the isolation boundary.        |
| Assert a mock call           | Verify meaningful arguments, count, ordering, or contractual interaction. |
| Build a mock response        | Satisfy the complete relevant contract with realistic data.               |
| Add a test helper            | Keep test-only methods in test utilities.                                 |
| Handle temporary resources   | Isolate state and guarantee cleanup.                                      |
| Test asynchronous behavior   | Synchronize explicitly; avoid arbitrary sleeps.                           |
| Encounter complex mock setup | Reconsider the boundary and consider an integration test.                 |
| Finish a regression test     | Demonstrate that it detects the defect.                                   |
| Finish a test file           | Review realistic mutations and run relevant tests.                        |
| Report test results          | State what was actually executed, passed, failed, or remains unverified.  |

## Warning Signs

* Setup and assertion share the same object or computation, guaranteeing equality.
* Expected values are hidden behind builders or helpers that reuse the implementation's logic.
* The test can fail only through a panic, crash, or missing selector.
* The test fails on every intentional change but misses accidental behavioral breakage.
* The test greps source text instead of exercising the artifact.
* The test would still matter if only the framework remained.
* The test exists for coverage without verifying a meaningful outcome.
* An assertion checks a mock's existence rather than the application's behavior.
* A mock swallows a side effect that the real implementation performs.
* Mock setup is more than half the test and its necessity cannot be explained.
* Fixtures omit fields consumed by downstream behavior.
* Tests depend on execution order, uncontrolled time, or shared mutable state.
* Arbitrary sleeps are used to synchronize asynchronous operations.
* Cleanup is skipped when a test fails.
* A test-only method has been added to a production class without a production lifecycle justification.
* A regression test passes without ever having demonstrated that it detects the defect.
* The test suite is declared successful despite unresolved failures or unexecuted tests.

## Final Standard

A good test has a clear behavioral purpose, an independently derived expectation, an appropriate test boundary, and a realistic failure mode.

A good test suite additionally remains isolated, deterministic, maintainable, and resistant to plausible regressions.

**The objective is not to maximize the number of tests. It is to maximize meaningful, reliable protection against unintended changes in production behavior.**