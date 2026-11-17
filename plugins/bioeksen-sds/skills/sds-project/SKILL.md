---
name: sds-project
description: BioEksen project facts, services and comment limits. Use at the start of work in a BioEksen project, before the first change, to read the choices recorded under .bioeksen/ — the git provider, the identity provider and the test order — and the services the project relies on, such as a log aggregator, an email service or a shared database, and to ask the user for any that are missing; when work first needs a service nobody has determined; when the user changes a fact or a service; and when writing or reviewing code comments, which are limited to 5 lines a block and 30 words a line.
---

# Project facts

A BioEksen project records the choices other skills depend on, rather than
leaving each skill to assume them. Which git provider runs the project's CI,
which identity provider issues its tokens, whether a log aggregator receives
its records, which service sends its email: a skill that guessed would be
right for one project and silently wrong for the next, and nothing would flag
it.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

- `${CLAUDE_SKILL_DIR}/scripts/read_facts.py` — reads the facts and the
  services, and names the missing ones (**Initialization**).
- `${CLAUDE_SKILL_DIR}/scripts/check_comments.py` — checks the comment limits
  (**Comments**).

Paths such as `sds-logging/references/log-record.md` name a file in another
skill of this plugin, relative to the plugin's skills directory: the parent
of `${CLAUDE_SKILL_DIR}`, which is this skill's own directory.

## The facts

Each fact is one file under `.bioeksen/`, holding one value and nothing else;
surrounding whitespace is ignored.

| File | Values | Decides | Read by |
|------|--------|---------|---------|
| `software-id` | The app's id | Who the app is, in its records and its commits | Per **Allocating an id** in `sds-logging/references/log-record.md`, which is normative for it |
| `git-provider` | `github`, `gitlab` | The CI file, how protected paths and branches are enforced | `sds-ci/SKILL.md` |
| `identity-provider` | `entra-id`, `keycloak` | Who issues the tokens, and what their claims are called | `sds-auth/SKILL.md` |
| `test-order` | `tests-first`, `implementation-first` | Whether a behaviour's tests or its code come first | `sds-testing/SKILL.md` |

A fact is read from the nearest `.bioeksen/{fact}` above the file at hand,
never looking past the repository's root, as the software id is. In a
monorepo the root's facts hold for every unit, and a unit MAY record its own
`test-order`. `git-provider` and `identity-provider` are the repository's,
recorded at its root only.

`.bioeksen/test-paths`, the kit's list of test paths, is not a choice and is
never asked; the project kit's README describes it.

## Services

A service is anything outside the app that the project may rely on: a log
aggregator, an email service, a shared database, file storage. None is
assumed. Each is settled in two steps, and recorded:

1. **Determine whether the project needs it.** Infer it from the
   specification when a decision states it, citing that decision; otherwise
   ask the user. A service the project does not need is recorded as
   `not used`, so the question is not asked twice.
2. **Learn it from the user**, only when it is needed: one question for each
   field below. Never guess one, and never carry one over from another
   project, for the reason a fact is never guessed.

Each service is the file `.bioeksen/services/{capability}.md`, named after
what it provides, not who provides it: `email`, not `bio-email`. The file
opens with `Key: value` lines, one per field; notes MAY follow a blank line.

| Field | Given | Holds |
|-------|-------|-------|
| `Status` | Always | `used` or `not used` |
| `Answered by` | Always | The person who answered, or the decision the need was inferred from |
| `Service` | When used | Its name |
| `Purpose` | When used | What the project uses it for |
| `Reached by` | When used | How an app reaches it: an address, stdout, a database connection |
| `Configuration` | When it takes any | The variables an app is configured with for it, by name only, per `sds-config/SKILL.md`. Never a value, and never a secret |
| `Interface` | When used | Where its contract is documented: a link, or a path |

A skill that reads a capability MAY require fields of its own, and names them
where it reads them.

```
Status: used
Service: bio-email
Purpose: Sends the notifications the specification's decisions call for
Reached by: HTTPS, at EMAIL_URL
Configuration: EMAIL_URL
Interface: https://git.example.com/bio-software/apps/bio-email/README.md
Answered by: Deniz Örnek
```

- **When it is determined:** `log-aggregator` at initialization, because
  every app logs. Any other when the specification or the work first needs
  it, and before any code depends on it.
- **Where it is read:** from the nearest `.bioeksen/services/` above the file
  at hand, as a fact is. In a monorepo the root's file holds for every unit,
  and a unit MAY record its own.
- **What it means:** an app relies on no service its project has not recorded
  as `used`. A call to one follows `sds-api-design/references/service-calls.md`.

## Initialization

Before the first change in a project, read every fact and service:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/read_facts.py
```

It prints each fact as `fact=value` and each service as
`services/{capability}=used` or `=not used`. It exits 0 when every one is
recorded, 1 when one holds a value or field outside its rules, and 2 when one
is missing, including a `log-aggregator` nobody has determined.

1. **Ask the user for every missing fact**, in one question each, offering
   the values the table allows, and **settle every missing service** per
   **Services**. Never guess, and never carry a value over from another
   project: a guessed fact looks right, so nothing flags it.
2. **Record each answer** in its file, at the repository's root unless the
   user names a unit.
3. **Set up what the answer needs**, per the skill the table names: the CI
   file for the git provider, the authentication values for the identity
   provider, the transport's values when an aggregator is used.

A run nobody attends, such as an AI task in CI, cannot ask, and cannot write
`.bioeksen/`, which `sds-ci/SKILL.md` protects. It reports each missing fact
or service as not run, and stops before changing anything.

## Changing a fact or a service

A fact or a service changes only when the user says so; a skill never
changes one to suit itself. Rewrite the file, then do what the change needs:

| Change | Then |
|--------|------|
| `git-provider` | Replace the CI file with the new provider's, and move the protected-path and branch rules, per `sds-ci/SKILL.md` |
| `identity-provider` | Change the authentication values, per `sds-auth/SKILL.md`. Records keep the `user=` values they were written with |
| A service | Set or remove its configuration, and start or stop using it, per the skill that reads it; `log-aggregator`'s is `sds-logging/SKILL.md` |
| `test-order` | Nothing to set up. Work under way finishes in the order it began in; the next unit of work follows the new one |

## Comments

Every comment in a project's code, in any language, MUST hold:

- **at most 5 lines a block**: a run of lines holding only comments, a block
  comment's delimiter lines included, so a doc comment of 3 lines of text
  fits;
- **at most 30 words a line**.

Module headers and doc comments are comments, and hold to the same limits.

A comment says what the code cannot: why it is the way it is, and which item
or decision it implements, by its id, per **Citing** in
`sds-planning/SKILL.md`. A longer reason belongs in the specification, where
it is decided and kept true; a long comment is skipped by its readers, and
drifts from the code it describes without anyone noticing.

```bash
python ${CLAUDE_SKILL_DIR}/scripts/check_comments.py src
```

It reports each block over 5 lines and each line over 30 words, with its file
and line, and exits 0 when there is none, 1 when there is one, and 2 when a
path does not exist. It reads the comments of C-like languages, `#`-languages,
SQL, CSS and markup, and skips strings.

## Before handing back

- Every fact and service the work depended on was read, and none was
  guessed.
- A service the work needed was determined, then learned, before any code
  depended on it.
- A fact or a service changed only on the user's word, with what the change
  needs done.
- The comment checker passes on every file you changed.
