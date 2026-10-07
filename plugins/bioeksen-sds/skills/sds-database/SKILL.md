---
name: sds-database
description: "BioEksen database conventions: one source of truth for the schema and a drift check, modelling with constraints that enforce the specification's invariants, forward-only migrations that are safe on a live database (expand and contract, locks, backfills, no silent data loss), transactions and concurrency, parameterised and indexed queries, the data contract handed to the server code, and working only against disposable databases. Use when designing, changing, running or reviewing a schema, a migration, a seed, a database object such as a trigger or view, raw SQL, a repository's queries or a transaction boundary."
---

# Database

The data outlives every version of the code that writes it. A bug in a
handler is fixed by the next deploy; a migration that drops the wrong column,
or a missing constraint that let bad rows in, is not. So schema work is held
to two bars above the ones the code skills set: **nothing stored is lost
without someone deciding it**, and **every invariant the specification states
is enforced by the database itself**, not only by the code in front of it.

The project's own conventions name what this skill leaves open: the database
engine, the ORM, which file is the schema's source of truth, where migrations
and seeds live, the commands that run them, and how a disposable database is
named. This skill, as every `sds-*` skill does, outranks them where they
disagree. If the project says the data layer has not been chosen yet, stop
and ask before creating any of it.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

- `references/nextjs.md` — how an app scaffolded from the nextjs template
  carries this skill out: its ORM, its roles and its per-role schemas.

Paths such as `sds-logging/references/log-record.md` name a file in another
skill of this plugin, relative to the plugin's skills directory: the parent
of `${CLAUDE_SKILL_DIR}`, which is this skill's own directory.

## Read first

1. **The project's data conventions**, and its tests README for the integration
   suite and its database guard.
2. **The ORM's and the database's documentation for the installed
   versions**, not memory: migrations, transactions, raw queries, and the
   engine's locking behaviour for each statement you plan to run.
3. **The schema's source of truth, the migrations already applied, and the
   seeds.** Reuse the naming, key types and patterns already there.
4. **The code skill for the server**: the layers the schema is used from, and
   the rules they follow.
5. **The requirements and decisions the change cites.** An invariant comes
   from the specification, never from what the code happens to do today.

## 1. Who changes what

- **The data model** (the schema, migrations, seeds, database objects, and
  the scripts that build, check or seed the database) is changed by the
  database developer, and reviewed by the database reviewer.
- **Repositories** (the code that queries the schema) are written by the
  server developer, and their queries and transactions are reviewed by the
  database reviewer against § 5 and § 6 here.
- A change that needs both is two tasks: the data change first, handed over
  as a data contract (§ 7), then the code that uses it.
- **In the test-first loop,** the tests of constraints, database objects and
  raw SQL are acceptance tests, written by the tester before the change
  from the plan's data contract, and hidden from the developers, per
  **Acceptance tests** in `sds-testing/SKILL.md`.

### Skeleton

A plan's skeleton task for the data model holds the models, columns and types
the contract names, with the migration that creates them, so that the
generated client gives the tests and the server code their types.
Constraints, indexes, triggers and seeds belong to the implementation task,
so that the tests for them fail, for the right reason, until then. A later
migration adds them; the skeleton's migration is never edited once applied
anywhere but a disposable database.

## 2. One source of truth

- **The schema has exactly one authority**, which the project names: the DDL,
  or the ORM's schema file. Everything else is generated from it or checked
  against it. Never change the generated side by hand.
- **A drift check proves the two agree.** If the project has one (a script,
  or the ORM's diff command), run it after every schema change. If it has
  none and both sides exist, say so in your report: drift is otherwise found
  in production.
- **Generated clients and types are regenerated**, never edited, after every
  schema change, and the typecheck is run on top of them.

## 3. Modelling

- **Constraints enforce the specification's invariants.** Uniqueness is a
  unique constraint, a reference is a foreign key, an allowed range or state
  is a check constraint. Code checks too, for a friendly message, but the
  constraint is what holds under concurrency and against every other writer.
- **NOT NULL by default.** A nullable column needs a reason: the value is
  genuinely unknown, not merely unset yet.
- **Keys use the type the project names.** Never mix key types across
  tables, and never expose an internal sequential key where the specification
  forbids it.
- **Foreign keys state their delete behaviour** deliberately. Cascading a
  delete across a regulated or audited record is almost always wrong: prefer
  restricting it.
- **Time is stored with its time zone** (`timestamptz` or the engine's
  equivalent), in UTC. Dates without a time are stored as dates.
- **Money and exact quantities are decimals**, never floating point.
- **A closed set of values** (a status, a type) is a check constraint or a
  lookup table, matching the pattern the schema already uses.
- **Personal data is marked.** Name each column that holds it in the report,
  so retention and access rules can follow it.
- **Name things consistently** with the existing schema: case, plurals, key
  and foreign-key column names, constraint and index names.

## 4. Migrations

A migration runs against the data the database holds, not an empty one, and
it cannot be taken back once applied. Write each one for the production
database.

- **Never edit a migration that has been applied** anywhere other than your
  own disposable database. Fix it with a new migration.
- **One purpose per migration**, named for what it does.
- **Forward-only.** Do not rely on a down migration to recover data. If the
  project writes down migrations, a down that loses data says so in a
  comment.
- **Destructive steps only when the task says so**: dropping or narrowing a
  column, table or constraint, or changing a type in a way that can lose
  values. State in the report what data is lost or where it was preserved.
- **Breaking changes go through expand and contract**, across separate
  migrations and releases:
  1. add the new column or table, nullable or with a default;
  2. write to both, and backfill the old rows;
  3. add the constraint, once every row satisfies it;
  4. switch the reads;
  5. drop the old one, in a later release.

  A rename is an add, a copy and a drop, never a rename the running code
  cannot see.
- **A constraint added over existing rows** fails the migration if one row
  breaks it. Check the data first, or backfill in the same migration before
  the constraint.
- **Mind the locks.** Know which statements rewrite or lock a whole table on
  the engine in use: adding a column with a volatile default, changing a
  type, adding a constraint that must validate every row, building an
  index. Use the engine's online forms where they exist (on PostgreSQL,
  `CREATE INDEX CONCURRENTLY`, and `NOT VALID` then `VALIDATE CONSTRAINT`),
  and note any lock the migration still takes.
- **Backfill large tables in batches**, never in one statement that holds a
  lock for minutes.
- **Seeds are idempotent** (re-running them changes nothing) and hold
  development data only. Reference data the application needs in production
  belongs in a migration.

## 5. Transactions and concurrency

- **Read, check and write inside one transaction**, or let a constraint make
  the check: a check done in a separate read can be stale by the time of the
  write.
- **Constraint violations become typed errors,** each with the code the
  **Database failures** table in `sds-logging/references/code-prefixes.md`
  gives it,
  never one chosen here. The repository layer maps them; a raw driver error
  never reaches a caller.
- **Know the isolation level** the transaction runs at, and what it does not
  protect against. Where a rule depends on rows another writer can change, lock
  them (`SELECT … FOR UPDATE`) or use a constraint.
- **An audit record is written in the same transaction** as the change it
  records, through the logger's audit call, which keeps it in the app's own
  database until the aggregator has stored it
  (`sds-logging/references/log-record.md`). What makes a change auditable is
  `sds-logging`'s **Choosing a type**.
- **Keep transactions short.** No network calls, file I/O or user waits
  inside one.

## 6. Queries

- **Parameters only.** Never build SQL from strings. Use the ORM's query
  builder or its parameterised raw query, never a variant that takes a string
  built from input. Validate rows from raw SQL at the boundary.
- **The query returns what the specification asks for,** and nothing the
  caller may not see: other tenants' or other owners' rows, soft-deleted rows,
  columns the DTO does not carry.
- **Every new filter, join and sort on a table that grows has an index** that
  serves it, or a reason in the report why it does not need one. Check the
  plan (`EXPLAIN`) on a disposable database for anything non-trivial.
- **No N+1 queries.** Load related rows in one query, or a bounded number.
- **No unbounded result sets.** Lists paginate. A list an API returns pages
  as `sds-api-design/references/app-endpoints.md` says; an internal batch,
  preferably by key.

## 7. The data contract

A data change is handed to the server developer as a contract, in the report:

- **Tables and columns** added or changed: type, nullability, default, and
  which are personal data.
- **Constraints**, each with the rule it enforces and the error it should map
  to (§ 5).
- **Indexes**, and the queries each one serves.
- **The migration**: its name, the locks it takes, any backfill and how long
  it runs, and what is irreversible.
- **What changes for existing code**: generated types, renamed or removed
  fields, and the expand-and-contract step the schema is now in.

## 8. Safety

- **Migrate, seed and test only against a disposable database**: one named
  apart from the development database by a fixed suffix, per **Test
  databases** in `sds-testing/SKILL.md`, that nothing else depends on.
- **One disposable schema per worktree.** Roles work in parallel worktrees,
  and two suites resetting one schema wipe each other's data. Each worktree
  names its own on its database URLs, after its role.
- **Before running anything that creates, resets, migrates or seeds a
  database, check where it points.** Read the environment and setup files it
  uses. If it could reach a development, shared or production database, or
  you cannot tell, do not run it: report it as not run, and why.
- **Never print `.env` files or connection strings**, and never put one in a
  report, a log line or a commit.
- **Never run destructive SQL by hand** against any database but your own
  disposable one.
- **An ORM that refuses an agent is right.** Some ORMs refuse a reset, and
  their other commands that drop data, when an AI agent runs them. When a
  migration needs a reset, report it, with the reason
  and what would be lost; the user decides. Never get around the refusal: not
  with a consent variable, not with hand-written SQL, not with another tool.

## 9. Before handing back

- The schema's authority, the generated client and the migrations agree: the
  drift check passes, or you said why it could not run.
- Every migration applies from empty on a disposable database, and on a copy
  of the previous schema with data in it where the change touches existing
  rows.
- The typecheck is clean after regenerating the client.
- The integration tests for constraints, raw SQL and transactions pass
  (`sds-testing/SKILL.md`, **Running the suites**), or each one not run is
  named with the reason.
- The report carries the data contract (§ 7).
