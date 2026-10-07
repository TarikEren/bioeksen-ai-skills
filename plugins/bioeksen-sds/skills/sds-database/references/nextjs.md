# Databases in a Next.js app

This reference describes apps scaffolded from the nextjs template of
bioeksen-app-setup: a Next.js App Router project in TypeScript, on PostgreSQL
through Prisma 7. It is how that template carries out `SKILL.md`, which
outranks it. Another app maps the names below to its own.

- **`/AGENTS.md` § Data** names what `SKILL.md` leaves open: the database
  engine, the ORM, which file is the schema's source of truth, where
  migrations and seeds live, the commands that run them, and how a disposable
  database is named. If it says the data layer has not been chosen yet, stop
  and ask before creating any of it.
- **The roles.** The data model is changed by `db-developer`, and reviewed by
  `db-reviewer`. Repositories are written by `nextjs-backend-developer`, and
  their queries and transactions are reviewed by `db-reviewer`. The
  acceptance tests of constraints, database objects and raw SQL are written
  by `qa-engineer`.
- **The layers** the schema is used from are `sds-nextjs-backend` § 1 and § 3
  "Data access".
- **`BaseRepository` maps** each constraint violation to its code.
- **Raw queries** use the ORM's tagged-template raw query, never its `Unsafe`
  variants with input in them. Rows from raw SQL are validated at the
  boundary (`sds-nextjs-backend` § 2).
- **Per-worktree schemas** are named on the database URL, after the role,
  e.g. `?schema=qa_engineer` (`/AGENTS.md` § Data).
- **Prisma 7 refuses** `prisma migrate reset`, and its other commands that
  drop data, when an AI agent runs them.
