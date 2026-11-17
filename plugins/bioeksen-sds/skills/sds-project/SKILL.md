---
name: sds-project
description: BioEksen project facts and comment limits. Use at the start of work in a BioEksen project, before the first change, to read the choices recorded under .bioeksen/ — the git provider, the identity provider, the log aggregator, bio-softop's services and the test order — and to ask the user for any that are missing; when the user changes one of them; and when writing or reviewing code comments, which are limited to 5 lines a block and 30 words a line.
---

# Project facts

A BioEksen project records the choices other skills depend on, rather than
leaving each skill to assume them. Which git provider runs the project's CI,
which identity provider issues its tokens, whether a log aggregator receives
its records: a skill that guessed would be right for one project and silently
wrong for the next, and nothing would flag it.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

- `${CLAUDE_SKILL_DIR}/scripts/read_facts.py` — reads the facts, and names the
  missing ones (**Initialization**).
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
| `log-aggregator` | `present`, `none` | Whether records are submitted, or the app's outbox is their archive | `sds-logging/SKILL.md` |
| `bio-softop` | `present`, `none` | Whether bio-softop's services are used: the employee directory, release verification, the id registry | `sds-auth/SKILL.md`, `sds-ci/SKILL.md` |
| `test-order` | `tests-first`, `implementation-first` | Whether a behaviour's tests or its code come first | `sds-testing/SKILL.md` |

A fact is read from the nearest `.bioeksen/{fact}` above the file at hand,
never looking past the repository's root, as the software id is. In a
monorepo the root's facts hold for every unit, and a unit MAY record its own
`log-aggregator`, `bio-softop` or `test-order`. `git-provider` and
`identity-provider` are the repository's, recorded at its root only.

`.bioeksen/test-paths`, the kit's list of test paths, is not a choice and is
never asked; the project kit's README describes it.

## Initialization

Before the first change in a project, read every fact:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/read_facts.py
```

It prints each as `fact=value`, and exits 0 when every one is recorded, 1
when one holds a value outside its choices, and 2 when one is missing.

1. **Ask the user for every missing fact**, in one question each, offering
   the values the table allows. Never guess, and never carry a value over
   from another project: a guessed fact looks right, so nothing flags it.
2. **Record each answer** in its file, at the repository's root unless the
   user names a unit.
3. **Set up what the answer needs**, per the skill the table names: the CI
   file for the git provider, the authentication values for the identity
   provider, the transport's values when an aggregator is present.

A run nobody attends, such as an AI task in CI, cannot ask, and cannot write
`.bioeksen/`, which `sds-ci/SKILL.md` protects. It reports each missing fact
as not run, and stops before changing anything.

## Changing a fact

A fact changes only when the user says so; a skill never changes one to suit
itself. Rewrite the file, then do what the change needs:

| Change | Then |
|--------|------|
| `git-provider` | Replace the CI file with the new provider's, and move the protected-path and branch rules, per `sds-ci/SKILL.md` |
| `identity-provider` | Change the authentication values, per `sds-auth/SKILL.md`. Records keep the `user=` values they were written with |
| `log-aggregator` | Set or remove the transport's values, and start or stop submitting, per `sds-logging/SKILL.md` |
| `bio-softop` | Start or stop reading the employee directory, and move release verification, per `sds-auth/SKILL.md` and `sds-ci/SKILL.md` |
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

- Every fact the work depended on was read, and none was guessed.
- A fact changed only on the user's word, with what the change needs done.
- The comment checker passes on every file you changed.
