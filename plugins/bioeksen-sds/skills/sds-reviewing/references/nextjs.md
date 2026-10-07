# Reviewing in a Next.js app

This reference describes apps scaffolded from the nextjs template of
bioeksen-app-setup: a Next.js App Router project in TypeScript, styled with
HeroUI v3. It is how that template carries out `SKILL.md`, which outranks it.
Another Next.js app maps the names below to its own.

- **`/AGENTS.md`** holds the project's conventions: where the review record
  lives, its severity scale, how findings are cited, and what a review covers
  by default. Read it first.
- **The reviewers** are the `code-reviewer` and `db-reviewer`
  agents. The planner runs the loop and routes each finding.
- **The skills for the code under review** are `sds-nextjs-frontend` and
  `sds-nextjs-backend`. Each pass checks these sections:

  | Pass | Sections |
  |---|---|
  | Security | `sds-nextjs-backend` § 3; `sds-nextjs-frontend` § 2 |
  | Type safety | `sds-nextjs-backend` § 2; `sds-nextjs-frontend` § 1 |
  | Modularity | `sds-nextjs-backend` § 1; `sds-nextjs-frontend` § 3 |
  | UI conventions | `sds-nextjs-frontend` §§ 4–8 |
  | Concurrency and transactions | `sds-nextjs-backend` § 3 "Data access" |

- **Entry points** are route handlers and server actions: authentication, and
  authorisation of the specific record, inside every one. The security pass
  also checks the `server-only` markers.
- **Type safety:** `any`, silencing casts, `@ts-ignore`.
- **Modularity:** `globalThis`, beyond the database client's development cache
  in `lib/db.ts`.
- **UI conventions:** HeroUI only.
- **Overfitting:** `NODE_ENV === "test"` outside the test seams.
- **Red for the right reason:** the skeleton's not-implemented error is
  `NotImplemented`.
- **Commands:** `pnpm run typecheck`; `pnpm run lint` with the changed paths;
  the tests through `test:results`. Never run `next build` unless asked.
- **The record:** each reviewer's folder is `docs/review_findings/<reviewer>/`,
  for example `docs/review_findings/code-reviewer/`.
