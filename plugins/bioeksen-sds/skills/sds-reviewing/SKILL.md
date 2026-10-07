---
name: sds-reviewing
description: "Reviewing code changes and recording the review in a BioEksen service. Part A covers the review: an independent reviewer's stance, scope and base commit, who reviews what (application code, or data changes), the rules to review against, passes in priority order (security, correctness, type safety, modularity, tests, UI, comments; and for data changes migration safety, integrity, concurrency, queries, drift, privacy and audit), verifying each finding, severity and the report. Part B covers the record that keeps every finding, decision and open question traceable: checking every claim before it is recorded, a review log, one file per review, stable finding IDs, statuses, later-review notes and closing a review. Use when reviewing a diff, a commit range or a pull request, when checking another reviewer's or an agent's findings, or when writing a review into the project's review record."
metadata:
  author: Tarık Eren Tosun
---

# Reviewing

A review is evidence about a change: what it breaks, what it leaves open, and
what holds. In a regulated project the review record is part of the quality
record, so two things matter as much as finding defects: **every finding can
be defended**, and **nothing that was found is lost**.

- **Part A** is how to review a change. The code reviewer and the database
  reviewer follow it, each for its own part of the change (§ 2).
- **Part B** is how to record a review. The reviewer records its own review,
  and anyone recording a report from elsewhere follows it too; either way,
  every claim is checked before it is written down.

The project's own conventions name what this skill leaves open: where the
review record lives, its severity scale, how findings are cited, and what a
review covers by default. The record's own README wins over Part B for that
record. This skill, as every `sds-*` skill does, outranks the project's
conventions where they disagree.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

- `references/record-templates.md` — skeletons for a project that has no
  review record yet.
- `references/nextjs.md` — how an app scaffolded from the nextjs template
  carries this skill out: its reviewers, the skill sections each pass checks,
  its commands and its record's folders.

Paths such as `sds-logging/references/log-record.md` name a file in another
skill of this plugin, relative to the plugin's skills directory: the parent
of `${CLAUDE_SKILL_DIR}`, which is this skill's own directory.

## Read first

1. **The project's own conventions.**
2. **The review record's README**, if the project keeps one: the open
   findings, the questions and the test gaps.
3. **The skills for the code under review:** the stack's UI and server
   skills, `sds-database/SKILL.md` and `sds-testing/SKILL.md`. Their rules
   are what the review holds the code to.
4. **The other `sds-*` skills**: API design, authentication,
   logging, configuration, testing, commits and CI. They are required; if one
   cannot be loaded, say so in the report.

# Part A — Reviewing a change

## 1. Stance

- **You did not write the code, and you change none of it.** You report;
  someone else decides and fixes.
- **The author's account is a claim.** "tsc passes", "added tests",
  "authorised in the service": check each one.
- **Every finding is one you can defend.** A review with ten findings of which
  three are wrong costs more than one with seven that hold.

## 2. Scope

1. **Take the scope from the task:** a diff, a commit range, a pull request,
   or paths.
2. **Otherwise use the default the project defines.** If it defines none,
   review the uncommitted changes plus the commits since the base branch.
3. **Record the exact scope and the base commit** (`git rev-parse HEAD`).
4. **Read each changed file whole, not just its hunks.** Follow each change
   one layer up (its callers) and one layer down (what it calls). Unchanged
   code enters the review only when the change depends on it or makes it
   worse.
5. **Check every open finding in the record that touches the scope:** fixed
   (and by which commit), still open, or regressed.

### Who reviews what

A change is split between two reviewers, so that a data change is read by
someone who reads nothing else:

| Reviewer | Reviews |
|---|---|
| The code reviewer | Application code: pages, components, styles, dictionaries, endpoints, services, validation, configuration, and the tests of all of these |
| The database reviewer | Data changes: the schema (DDL or ORM schema), migrations, seeds, database objects (triggers, views, functions), raw SQL, the query semantics of repositories, transaction boundaries, and the integration tests covering them |

A repository sits on the line: the code reviewer reviews its layering and
types, the database reviewer its queries and transactions. When the scope
holds the other reviewer's part, list those paths under *Not reviewed* in the
report, naming the reviewer, rather than reviewing them lightly.

## 3. The rules to review against

| What changed | Review it against |
|---|---|
| Pages, layouts, components, styles, dictionaries | The stack's UI skill |
| Endpoints, services, repositories, validation schemas, configuration | The stack's server skill |
| The database schema, migrations, seeds, database objects, raw SQL, queries and transactions | `sds-database` |
| Tests, or a change that needs them | `sds-testing` |
| Endpoints and outbound calls; credentials and rejection codes; log lines and error codes; configuration; tests; commit messages; migrations and releases | The `sds-*` skills, which are required and outrank everything else in this table. If one cannot be loaded, say so in the report |
| Everything | The project's own conventions, which override its own skills; and the requirements, spec sections or decisions the code cites. A change that contradicts its own citation is a finding |

## 4. Review in priority order

Take one pass per concern, in this order.

1. **Security.** The server and UI skills' security sections.
   - authentication, and authorisation of the specific record, inside every
     entry point;
   - input validated at every boundary;
   - DTO outputs, and narrow client props;
   - no SQL built from strings, and no secrets in client code or logs;
   - uploads, origin checks, rate limits.
2. **Correctness.**
   - logic and edge cases: empty, missing, duplicate, boundary values;
   - error paths;
   - read-check-write races and transaction boundaries;
   - state machines;
   - cache revalidation after a mutation;
   - dictionary keys in every language.
3. **Type safety.** Both code skills' type-safety sections:
   - escape hatches from the type checker;
   - unvalidated boundaries;
   - types written by hand that can drift from their schema or ORM.
4. **Modularity.** The server and UI skills' sections on layers and modules.
   - layer skips, such as a handler touching the ORM;
   - business rules in the wrong layer;
   - reaching into another module's repository;
   - duplicated helpers, module state, global singletons.
5. **Tests.** `sds-testing`: **The cases**, **Writing tests**, **A test that
   cannot fail proves nothing** and **Known defects**.
   - Does each changed rule have a test for its success path, a validation
     failure and an authorisation failure?
   - Do the tests assert outcomes rather than call shapes?
   - Does each expected-to-fail test have a precondition test beside it?
6. **UI conventions.** The UI skill's colour, component, copy, component-kind
   and page-structure sections.
   - palette and tokens (run the skill's grep);
   - contrast pairings: list the new ones for the caller to measure;
   - accessible names, the component library the UI skill names, copy in the
     dictionaries;
   - the forms pattern, including how results are announced and where focus
     goes;
   - phone width.
7. **Comments and traceability.** Header comments, citations, and comments
   the change has made untrue.

### Reviewing a data change

The database reviewer takes these passes instead, in this order.
`sds-database`'s sections are the rules.

1. **Data loss and migration safety.** `sds-database` § 4.
   - a dropped or narrowed column, table or constraint, and whether the data
     in it survives;
   - an applied migration edited, or migrations out of order;
   - locks on large tables, table rewrites, backfills in one statement;
   - whether the migration runs on the data the database holds, not only on
     an empty one: a new NOT NULL or unique constraint over existing rows.
2. **Integrity.** `sds-database` § 3.
   - every invariant the specification states is a constraint, not only a
     check in code;
   - foreign keys, their delete behaviour, and the key types;
   - nullability, defaults, time zones, money.
3. **Concurrency and transactions.** `sds-database` § 5, and the server
   skill's data access rules.
   - read-check-write inside one transaction, or guarded by a constraint;
   - constraint violations mapped to the codes the **Database failures**
     table in `sds-logging/references/code-prefixes.md` gives them;
   - audit rows written in the same transaction as the change.
4. **Queries.** `sds-database` § 6.
   - no SQL built from strings; parameters only;
   - results match the specification: filters, ordering, soft-deleted and
     other tenants' rows left out;
   - an index for each new filter, join and sort on a table that grows;
     N+1 queries; unbounded result sets.
5. **Drift.** `sds-database` § 2: the ORM schema, the DDL and the migrations
   describe one database.
6. **Privacy and audit.** Personal data columns, retention, what reaches
   logs, and the audit trail the project keeps.
7. **Tests.** `sds-testing`, **Keeping the suite honest** and **Test
   databases**: constraints, raw SQL, transactions
   and races are covered by integration tests against a disposable database.

### Reviewing tests before implementation

In the project's test-first loop, the code reviewer reviews the tester's new
tests before any implementation (`sds-testing`, **Acceptance tests**). There
is no code yet, only the skeleton, so the tests are the thing under review.
The passes, in order:

1. **Traceability.**
   - Every *Done when* item of the implementation tasks has at least one test.
   - Every test title starts with its requirement and task ids.
   - A test that asserts what no source states is a finding: it would make
     the developers build behaviour nobody asked for.
2. **Correctness against the source.** Expected values come from the
   requirement or the contract, not from a guess; boundaries are tested on
   both sides; every case the source states is there.
3. **Black-box.** Tests reach the code only through the contract: its exports,
   routes, accessible names and constraints. A developer must be able to make
   them pass from the contract alone.
4. **Red for the right reason.** Run the tests through the results-only
   interface against the skeleton: each new test fails with the
   not-implemented error (`SYS-5000`, 500) or the element not found, and none
   fails on a type error, a missing module or its setup.
5. **What the developers will see.** A developer who sees only a title and its
   failure message can tell which rule failed.
6. **`sds-testing`'s rules** (**Writing tests**): outcome assertions,
   determinism, typed fixtures, no type escape hatch, and a guard on every
   suite that resets a database.

### The anti-overfitting pass

After implementation, both reviewers see the tests and the code together, which
nobody else does. Check that the code meets the requirement, not just the
tests:

- **No branching on test values.** Look for constants equal to fixture values,
  checks on test-only inputs, headers or the environment's name outside the
  test seams.
- **No rule narrower than its requirement.** A rule implemented only for the
  cases the tests happen to try fails the untested ones.
- **Test seams can't be reached in production.** A test sign-in or fake that a
  production build can reach is a security hole: Critical. A seam is enabled
  only by validated configuration in a test environment, and a production
  deployment refuses its setting at startup with `CFG-5001`, per **Test
  seams** in `sds-testing/SKILL.md`.

## 5. Verify before reporting

For every candidate finding:

1. **Try to refute it.** Read the caller, the guard one layer up, the test
   that might cover it, and the configuration that might change it. Most
   false findings die here.
2. **Write the failure scenario:** a concrete input or sequence, and the wrong
   result it produces.
3. **Gather evidence:** the lines that prove it, a command's output, or a
   failing test you ran.
4. **Label it:**
   - **Confirmed:** proven from the code or reproduced.
   - **Plausible:** real if a runtime condition holds that you could not
     check, such as database state or production configuration. Name the
     condition.

Drop a candidate the code refutes. A point you could neither confirm nor
refute is not dropped silently: list it under *Not verified*, with what would
settle it.

Do not report:
- what the linter or compiler already catches, unless the check is disabled;
- preferences that no rule in the skills, the project's conventions or the
  specs backs;
- "consider…" suggestions with no defect behind them.

## 6. Commands

Run only commands that leave the working tree as you found it:

- `git status`, `git diff`, `git log`, `git show`, `git rev-parse`;
- the project's typecheck;
- the project's linter with the changed paths;
- the tests covering the change: in the test-first loop, through the
  results-only interface, which reviewers may also run directly with the
  runners.

Never do any of the following:
- stage, commit, checkout, stash, reset or clean;
- install packages;
- edit or create any file but the review record, including throwaway tests.
  If a finding needs a reproduction you cannot run, describe it in the
  review;
- run database migrations, seeds, or test suites that create or reset
  databases, unless the task says so;
- run a production build unless asked;
- print the contents of `.env` files or other secrets.

## 7. Severity

Use the scale the project or the record defines, if there is one. Otherwise:

- **Critical:** a security hole, data loss or corruption, or a wrong or
  unauditable regulated record.
- **Major:** wrong behaviour; an unvalidated boundary; a type-safety hole a
  caller can reach; a layer violation; a changed rule without tests.
- **Minor:** conventions, maintainability, comments.

If the project ranks its backlog (for example S0–S3), also propose the rank
the finding would take there.

## 8. The report

The report is what the review file records (Part B), and what whoever asked
for the review reads. Every claim in it is checked against the code before
it is recorded, so make every claim checkable.

- **Scope:** what you reviewed, the base commit, and what you left out.
- **Not reviewed:** the paths in scope that belong to the other reviewer
  (§ 2), naming it.
- **Checks:** each command you ran and its result, including the
  results-only interface's summary. Never claim a check you did not run.
- **Verdict:** *Approve*, *Approve with follow-ups*, or *Request changes*,
  naming what blocks. In the test-first loop, whoever runs the loop ends an
  iteration only when no Critical or Major finding is open.
- **Findings**, most severe first. Each one has:
  - **Title:** one line stating the defect.
  - **Severity** and **category** (security, correctness, type safety,
    modularity, tests, UI, comments, overfitting; for a data change: migration
    safety, integrity, concurrency, queries, drift, privacy), and
    **Confirmed** or **Plausible**.
  - **Owner:** the role that fixes it. Whoever runs the loop routes the
    finding to that role, and the tester and the developers each see only
    their own side, so the rule and the problem must make sense without the
    quoted lines.
  - **Where:** `path:line` and the symbol. The symbol is the stable anchor.
  - **Rule:** the skill section, the project's convention, requirement or
    standard it breaks.
  - **Problem:** the failure scenario, as input and wrong result.
  - **Evidence:** the lines, output or test that shows it.
  - **Fix:** what should change, described, not applied. No patches beyond a
    line or two of illustration.
- **Earlier findings:** for each open finding in the record that touches the
  scope, whether it is fixed (with the commit), still open, or regressed.
- **Not verified:** what you could not check or settle, why, and what would
  settle it.
- **Questions:** anything the author has to answer before a finding can be
  settled.

# Part B — Recording a review

## 9. Check every claim first

- **A report is a set of claims**, whether it comes from a person, an agent,
  another tool or your own review. Check each one against the code at the
  base commit before recording it:
  - read the lines it cites;
  - re-run the checks it reports;
  - settle each Plausible finding where a command § 6 allows can; otherwise
    describe the reproduction that would.
- **Each claim ends up in one of five states:**
  - recorded as it stands;
  - recorded corrected, saying what changed;
  - merged with another that has the same cause and the same fix;
  - added as a note to the finding that already records it;
  - rejected, with the reason in the review's summary.
- **Record what the check found beyond the report.** A reproduction that
  surfaces a second defect is a finding of the same review.
- **Nothing noticed is left out.** A point you could not settle is recorded
  as Plausible, with the condition that would settle it, or as a question
  for the author.

## 10. The record's layout

Use the project's layout: where its conventions name the record's place, file
names, finding ids, statuses or severities, those win over §§ 10–13. If the
project has none yet, start this one; the skeletons are in
[`references/record-templates.md`](references/record-templates.md).

| File | Holds |
|---|---|
| `<record>/README.md` | The rules, the review log, the status of every finding, coverage, tracked backlog entries, questions, test coverage gaps and strengths |
| `<record>/review_N.md` | One review: its header, summary, findings, and the state of earlier findings it touched |
| `<record>/fixed_review_N.md` | The same file, renamed once every finding in it is fixed |

If code cites findings through a single file name, keep that file as a pointer
to the record.

In the test-first loop each reviewer keeps its own folder,
`<record>/<reviewer>/`, with its own review numbering, so that two reviewers
working in parallel never write the same file or take the same number. Only
reviewers and whoever runs the loop read the record: whoever runs the loop
routes each finding to its owner.

## 11. Findings

- **IDs are `R-nnn`**, unless the project gives another format, taking the
  next free number. When two reviewers write to one record, each needs its
  own prefix (the project names them, e.g. `CR-` and `DR-`), or both must read
  the record for the next free number just before writing. An ID is never
  reused or renumbered, even after a fix. A rejected claim gets no ID.
- **A finding lives in the file of the review that found it.** A later review
  adds its notes inside the finding, as `- **Review N:** …`, so the finding
  reads whole in one place.
- **Each finding has this shape:**
  - a heading, `### R-nnn — <the defect, as a sentence>`;
  - a status line: status, severity, proposed rank if the project ranks its
    backlog, and the review that found it (and how, for example "the
    reviewer agent; confirmed");
  - **Where:** `path:line` and the symbol, with line numbers as of the base
    commit;
  - **Problem:** the failure scenario and its evidence;
  - **Fix:** what should change.
- **Status** is one of:
  - `Open`;
  - `Fixed (<commit>)`;
  - `Tracked (<backlog entry>)`;
  - `Won't fix (<reason>)`.

  A finding a commit only partly closes stays `Open`, with a note on what is
  left. A finding becomes `Fixed` only when a later review has checked the
  fix.

## 12. The review file

- **Header table:** `#`, date, scope, base commit, verdict. The scope says who
  reviewed (a person, an agent, a separate reviewer) and that every claim was
  checked before it was recorded.
- **Summary:** what was found, how each claim was checked, what matters most,
  and the verdict.
- **Findings**, most severe first.
- **Earlier findings:** each open finding the review touched, and its state.

## 13. The README

For each review, update:

- **The review log:** one row.
- **Status at a glance:** a row for each new finding, linked to its heading,
  and the rows of earlier findings the review changed. Anchors follow the
  forge's slug rules; on Forgejo, lower case, punctuation dropped, spaces
  turned to hyphens.
- **Coverage:** what was reviewed, and how.
- **Questions:** new ones as `Open`. When the author answers, the status
  becomes `Answered (review N):` and the decision.
- **Test coverage gaps:** one row per missing test, with its status:
  - `Open`;
  - `Pinned in <commit>`, for an expected-to-fail test;
  - `Covered in <commit>`.
- **Strengths** worth keeping, so a later change does not undo them.
- **Backlog entries** the review confirmed, if the project tracks work
  elsewhere.

## 14. Decisions

A decision the author takes during or after a review is recorded where the
next reader will look:

- **The question's status**, with the decision.
- **The finding it changes:** a note giving the decision and its
  consequence for the fix.
- **The rule it settles:** if a skill or the project's conventions state the
  rule, say so in the note, and tell the author which file carries it.

## 15. Closing, citing and correcting

- **Close a review** when every finding in it is `Fixed`: rename it
  `<record>/fixed_review_N.md` and update every link to it. A finding that is
  `Tracked` or `Won't fix` keeps its review open.
- **Cite findings by ID** in code, tests and commits, in the form the project
  uses. A commit that fixes a finding names it in its footer, as the issue
  reference `sds-commit/SKILL.md` allows, e.g. `Refs: R-012`.
- **Do not rewrite the record.** Correct a factual error with a note saying
  what was wrong; never delete a finding.
- **Check the links.** After every edit, every link and anchor in the record
  must resolve.

## 16. Before handing back

- Every claim in the report was checked, and each ended in one of the five
  states in § 9.
- Every new finding has an ID, the full shape, and a row under *Status at a
  glance*.
- The review file, the log row, coverage, questions and test gaps agree.
- Every decision is in the question, the finding it changes, and a note on
  the rule it settles.
- Every link and anchor in the record resolves.
