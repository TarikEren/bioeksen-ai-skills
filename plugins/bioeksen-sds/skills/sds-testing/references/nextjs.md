# Testing in a Next.js app

This reference describes apps scaffolded from the nextjs template of
bioeksen-app-setup: a Next.js App Router project in TypeScript, tested with
Jest and Testing Library, Playwright, and Prisma against disposable databases.
It is how that template's tiers, helpers and roles carry out `SKILL.md`, which
outranks it. Another Next.js app maps the names below to its own.

The project's `/AGENTS.md` and its tests README name what this skill leaves
open: the runners, the tiers and their folders, the helpers and fixtures, how
requirements are cited, and the scripts. The tests README wins over this
reference where they disagree, and `/AGENTS.md` wins over both; `SKILL.md`, as
every `sds-*` skill does, wins over all three.

## Read first

1. **`package.json` scripts and the runner configs** (`jest.config.*`,
   `vitest.config.*`, `playwright.config.*`).
2. **The Next.js testing guides for the installed version**, under
   `node_modules/next/dist/docs/01-app/02-guides/testing/`. Jest and Vitest do
   not support async Server Components: test those end to end.
3. **The skill for the code under test**: `sds-nextjs-backend` for
   server code, `sds-nextjs-frontend` for UI.

## The roles

The template runs **Acceptance tests** as a loop of roles. `qa-engineer` is the
tester: it writes the tests before the code exists and never sees product
code. The developer roles never see the tests, only their titles and results.

| Kind | Where | Owner |
|---|---|---|
| Acceptance | `tests/`, `e2e/` | `qa-engineer` |
| Unit and component tests of internals | `lib/**/*.test.ts`, `app/**/*.test.ts`, `app/**/*.test.tsx` | The developer who owns the code |

In the template, an acceptance test reaches the code through: route
handlers and server actions called through their contract exports, with the
test seams for sign-in and time; components rendered through their exports and
queried by role and dictionary label; constraints and transactions against a
disposable database; flows end to end.

The matchers that print expected and received values are `toBe`,
`toMatchObject` and `toHaveTextContent`.

The skeleton's not-implemented error is `NotImplemented`. A new acceptance test
is not marked `it.failing`: expected-to-fail tests stay for defects found after
a task was done and deferred.

A developer who believes a test is wrong reports it by its title, and the
planner passes it on.

## `test:results`

`test:results` is the template's results-only interface. It is the only way
the tester and the developers run tests; a hook blocks the
runners themselves. The scaffold ships it in `tests/support/` (the tests README
describes it).

- It runs the tiers (all, or those named: `unit`, `component`, `integration`,
  `e2e`), optionally only the tests whose title matches `--grep <regex>`.
- When a tier with tests could not run, it prints `NOT RUN` and says why, and
  exits 2.
- It is built on the runners' machine-readable output (Jest's `--json`,
  Playwright's JSON reporter), not on trimming their console output. It is
  the user's to change, since it is what keeps the developers blind: a role
  that needs more from it says so in its report.
- `test:acceptance` runs the acceptance suite alone, for CI.

## Parallel worktrees

Each worktree names its schema after its role on the database URL
(`?schema=qa_engineer`), and its end-to-end port in `E2E_PORT`. The guard
empties the schema by applying the migrations and truncating
every table in it, never with `prisma migrate reset`, which Prisma refuses
when an agent runs it.

## The tiers

| Claim | Tier | How |
|---|---|---|
| Pure logic: a calculation, parsing, formatting, a state machine's table | Unit | Call it directly. No mocks |
| A service's rules: authorisation, validation, which records change | Unit | Mock the repositories it calls. Assert the result and the rejections |
| A repository's query semantics | Integration | Against a real, disposable database (`SKILL.md`, **Test databases**). Assert the rows returned |
| Raw SQL, constraints, transactions, locks, races | Integration | Against a real, disposable database (`SKILL.md`, **Test databases**) |
| A route handler or a server action | Unit | Import the export and call it: a `Request` and `{ params: Promise.resolve({ … }) }` for a handler, `FormData` for an action. Mock the service below |
| A client component's behaviour | Component | jsdom and Testing Library |
| A flow across server actions, the database, navigation or file storage; async Server Components; anything that needs a real browser | End to end | Playwright against the running app |

## TypeScript and the runners

- **No `any`, no `as unknown as T`**, and no `@ts-ignore` or
  `@ts-expect-error`: these are the type checker's escape hatches.
- **Type mocks with `jest.mocked(fn)` or `vi.mocked(fn)`**, not a cast.
- **`jest.mock` and `vi.mock` take a literal path at the top of the file.**
  They are hoisted, and a computed path is not.
- **Wait for a condition** with `findBy…`,
  `waitFor`, or Playwright's retrying `expect`.
- **Query by role and accessible name:**
  `getByRole("button", { name: labels.save })`.
- **Click the submit `Button`.** `fireEvent.submit` and calling a handler
  directly skip the browser's own validation. Use
  `user-event` if the project has it.
- **Focus lands** as `sds-nextjs-frontend`'s forms rules place it.
- **A malformed id on a page** calls `notFound()`.

## Running the suites

1. the typecheck: `typecheck` for app code and `typecheck:tests` for test
   code, after any type generation the project needs (`db:generate`);
2. the linter;
3. the test tiers, through `test:results`.

## Patterns

The module paths and names below are placeholders: use the contract's. The
envelope, the sign-in and the i18n helpers are the project's own
(`/tests/README.md`).

**An expected-to-fail test and its precondition** (Jest):

```ts
/**
 * Transfers. Source: REQ-0042, a transfer never overdraws the account.
 */
import { transferService } from "@/lib/services/transfer";
import { ACCOUNT_ID, ACTOR } from "../helpers/fixtures";

describe("REQ-0042 a transfer never overdraws the account", () => {
  // Precondition for the expected failure below: the setup reaches the check.
  it("accepts a transfer within the balance", async () => {
    const account = await transferService.transfer(ACTOR, { accountId: ACCOUNT_ID, amount: 50 });
    expect(account.balance).toBe(50);
  });

  // Known defect ISSUE-123: the balance is read outside the transaction.
  // Promote to `it` when ISSUE-123 is fixed.
  it.failing("refuses a transfer above the balance", async () => {
    await expect(
      transferService.transfer(ACTOR, { accountId: ACCOUNT_ID, amount: 150 }),
    ).rejects.toMatchObject({ code: "RES-4302" });
  });
});
```

**A route handler, called directly, signed in:**

```ts
import { GET } from "@/app/api/v1/widgets/[id]/route";
import { OPERATOR, signedInAs } from "../support/sign-in";

describe("REQ-0013 a widget is read by its numeric id", () => {
  it("REQ-0013 T4: answers a malformed id as not found, with RES-4200", async () => {
    const request = new Request("http://test/api/v1/widgets/abc", { headers: signedInAs(OPERATOR) });
    const response = await GET(request, { params: Promise.resolve({ id: "abc" }) });

    expect(response.status).toBe(404);
    // The SDS error envelope: { status: "fail", code, message, details }.
    expect(await response.json()).toMatchObject({ status: "fail", code: "RES-4200" });
  });

  it("REQ-0013 T4: asks for a credential with AUTH-4100", async () => {
    const response = await GET(new Request("http://test/api/v1/widgets/1"), { params: Promise.resolve({ id: "1" }) });

    expect(response.status).toBe(401);
    expect(await response.json()).toMatchObject({ code: "AUTH-4100" });
  });
});
```

**A form, driven by role and dictionary labels:**

```tsx
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { dictionaryFor } from "@/lib/i18n/dictionaries";
import { renderWithI18n } from "../support/render";
import { WidgetForm } from "@/app/(app)/widgets/_components/widget-form";
import type { ActionResult } from "@/lib/actions";

const labels = dictionaryFor("en").widgetForm;

describe("REQ-0021 the server's field errors", () => {
  it("still submits after the server rejects a field", async () => {
    const action = jest.fn(
      async (_data: FormData): Promise<ActionResult> => ({
        status: "fail",
        code: "VAL-4006",
        message: "Field value invalid",
        details: [{ field: "name", issue: "Taken" }],
      }),
    );
    renderWithI18n(<WidgetForm action={action} />);
    const name = screen.getByRole("textbox", { name: labels.name });
    const save = screen.getByRole("button", { name: labels.save });

    fireEvent.change(name, { target: { value: "Pump" } });
    fireEvent.click(save);
    expect(await screen.findByText("Taken")).toBeInTheDocument();

    fireEvent.change(name, { target: { value: "Pump 2" } });
    fireEvent.click(save);
    await waitFor(() => expect(action).toHaveBeenCalledTimes(2));
    expect(action.mock.calls[1][0].get("name")).toBe("Pump 2");
  });
});
```

The first pattern's code is the one the selection procedure gives a refused
domain rule, `RES-4302`, per `sds-logging/references/code-prefixes.md`. The
second answers an id that does not parse as one that does not exist, per
**The cases** in `SKILL.md`. The third returns the error envelope
`sds-api-design/SKILL.md` requires of a server action.

## Before handing back

In TypeScript, a type escape hatch is an `any`, a cast, or a `@ts-ignore`.
