---
name: sds-planning
description: BioEksen specifications and build planning. Use when writing, changing or reviewing a service's specification — its decisions, build items and acceptance criteria — when a rule is missing and has to be asked, when ordering the build into stages with exit criteria, and when writing a stage's plan for the test-first loop; and when checking a specification, or the tests' citations of its acceptance criteria, with the checker that ships with this skill.
---

# Specifications and Planning

Every BioEksen service is built from a specification in one format: decisions
that say what is in force, build items that say what to make, and acceptance
criteria that say how to tell it is made. The format exists for what is
downstream of it:

- **A test cites the criterion it proves, and a code comment the item or
  decision it implements.** A reviewer can then judge each one against its
  source, and a change to a decision finds every test and every line it
  touches. That only works if each id names one thing, forever.
- **A rule nobody has decided yet is still written down**: as a *Pending*
  decision, with the rule that is in force until its owner answers. Nobody
  guesses, and when the answer comes, the guess that has to change is visible.
- **A stage ends on criteria that can be checked**, not on a date or a feeling
  that the work is done.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

- `references/spec-format.md` — the skeletons of every part of the set and of
  the stage plan, each with the reason for it.
- `references/example/README.md` and `references/example/widgets.md` — a small,
  complete specification set in this format. The checker's own tests hold it
  consistent, so it is always a valid model.
- `${CLAUDE_SKILL_DIR}/scripts/check_specs.py` — the checker (**Checking**).

Paths such as `sds-testing/SKILL.md` name a file in another skill of this
plugin, relative to the plugin's skills directory: the parent of
`${CLAUDE_SKILL_DIR}`, which is this skill's own directory.

## Read first

1. **The project's `/docs/specs/README.md`**, then the area file of the
   subject at hand. It gives the ids, the owners, the build order and the open
   decisions.
2. **The project's questions file**, `/docs/questions.md`, for the questions
   still open.
3. **The stage plan**, `/docs/plans/test_plan.md`, when a stage is under way.
4. **The `sds-*` skills the subject falls under.** A specification builds on
   the shared contracts; it never restates them, and never contradicts them
   without saying so (**Decisions**).

## The specification set

Every BioEksen service MUST have a specification in this format, in
`/docs/specs/` of the service's directory. In a monorepo that is the release
unit's directory, per **Release units** in
`sds-commit/references/release-notes.md`, so each app's specification travels
with the app.

The set is a README and one area file per subject:

| File | Holds |
|---|---|
| The README | The product, the release and its version, the authority statement, the files, where each id lives, how to read the set, the build order, the open decisions and the glossary |
| An area file | The decisions of its subject, the prose its items share (an architecture, a model, a layout), and its build items, grouped under `##` headings |

**The specification is the only authority for the build.** Each file says so,
and every other document defers to it. Where it gives no rule, the answer is
never taken from another document, from the old code, or from what seems
likely: the question goes to the decision's owner, and the rule in force until
the answer comes is written down as a *Pending* decision.

`references/spec-format.md` gives each file's skeleton, in order.

## Identifiers

| Form | Names | Example |
|---|---|---|
| `DEC-nnn` | A decision, three digits | `DEC-004` |
| `PREFIX-nn` | A build item; the README lists the project's prefixes | `WID-30` |
| `<item>.ACn` | The acceptance criterion *n* of an item | `WID-30.AC6` |

- **Item numbers come in groups of ten.** The first number of a group is the
  main item of a subject, and the other numbers of the group are its parts:
  `WID-30` and `WID-31`. A group leaves room for parts found later without
  renumbering anything.
- **Ids are unique across the files**, and the README says which file holds
  each prefix's items and each range of decisions.
- **An id is never renumbered and never reused.** A removed decision, item or
  acceptance criterion leaves a gap. Test titles, code comments, commits and
  review records cite ids; a renumbered or reused id silently points every one
  of them at a rule its author never saw. This is the error codes' rule in
  `sds-logging`, for the same reason.

## Decisions

Each area file opens with its decisions, in one table or in several under `###`
headings by subject:

| Column | Holds |
|---|---|
| ID | `DEC-nnn` |
| Decision | The rule in force, in one or a few sentences. One rule per row |
| Status | *Decided*, *Pending* or *Default* |
| Owner | Who decides it, from the README's **Owners** list |
| Ask | The question that decides or confirms it, `questions.md n`, or `—` |
| Affects | The build items that carry the rule |
| Trace | Where the rule came from: a section of an earlier document, a finding. History only; never needed for the build |

| Status | Meaning |
|---|---|
| **Decided** | Its owner made it. Build it |
| **Pending** | Its owner must answer a question. The rule in the row is in force until the answer comes |
| **Default** | The team chose it. It is in force, and can change without asking anyone |

- **Every row's rule is in force,** whatever its status. A *Pending* row is not
  a gap: it is the rule the build follows until its owner says otherwise.
- **A *Pending* row MUST name its question** in its Ask column, and appear in
  the README's **Open decisions** list. A *Decided* row MAY name one too: a
  question that asks its owner to confirm it, while it stays in force.
- **A decision lives in the file of its subject, and nowhere else.** Items
  cite it by id instead of restating it, so it changes in one place.
- **A deviation from an `sds-*` skill is a decision**: its row names the skill
  and the section it departs from, says why, and says what ends it. Without
  the row, the deviation is a defect a reviewer reports.

## Build items

Each item is a `### PREFIX-nn Title` heading in its area file, with these
blocks, each a paragraph opening with its bold label:

| Block | Required | Holds |
|---|---|---|
| **What.** | Yes | One sentence: what the item gives |
| **Rules.** | Yes | The rules, numbered, each citing the decisions and items it carries. *The item follows DEC-…* is enough where the decisions say it all |
| **Data.**, **Screens.**, **States.**, **Moves.**, **Jobs.** | Where they apply | The tables, columns, pages, states, transitions and scheduled work the rules need |
| **Acceptance.** | Yes | The acceptance criteria, `- **AC1.**` onwards |
| **Trace.** | No | Where the item came from, as for a decision |

## Acceptance criteria

The acceptance criteria are the cases. A tester writes the tests from them
without seeing the code, and a developer builds to them without seeing the
tests (`sds-testing/SKILL.md`, **Acceptance tests**). So each criterion has to
be checkable by itself:

- **One behaviour, observable from outside the code**: a response, a stored
  row, an audit record, what a user sees, a refusal. It names only what the
  contract exposes; never a function, a class or a query.
- **Written as a condition and its result**: *When* an action happens, the
  result; *If* a condition holds, the result. A criterion with no condition is
  usually two criteria, or none.
- **Concrete values**: "after 31 minutes without activity", not "after the
  timeout"; "the 61st upload in one hour", not "too many uploads". A value the
  tester has to choose is a value the developer may choose differently.
- **Both sides of a rule**: what it allows, and what it refuses.
- **A refusal is defined once.** The group's heading paragraph says what
  "fails" means, for example: the system refuses the action with its reason,
  and no row changes.
- An optional line before the criteria MAY fix a notation they share.

A criterion nobody can check ("the page is fast", "the code is clean") is a
defect in the specification: rewrite it with the value that would decide it,
or record the missing value as a *Pending* decision. A build item is complete
when each of its criteria has an acceptance test that passes.

## Build order

The README orders the build into stages:

- **Stages follow dependency, not dates.** A tree shows which stage needs
  which. The engines other items are built on come first, so no later item
  works around one that is missing.
- **Each stage has an exit criterion that can be checked**, in the stage table
  beside its items. A stage is complete when its exit criterion passes and
  each acceptance criterion of its items has a test that passes.
- **An item split across stages names its part, in parentheses, in each**:
  `WID-30 (the moves 4 and 5)`. Its criteria are due at the last stage that
  lists it.
- **The order within a stage**, and its phases where it has them, follow the
  table, in a line or a table of their own.
- **What others must supply**, and the first stage that needs it, is a table:
  the environments, the accounts, the reference data. It takes the longest, so
  it starts first.

## Open decisions

The README lists every *Pending* decision, and nothing else, with the first
stage or phase that needs its answer, in that stage's order. It is the list
the owners work from, so a stage never starts with a question it needs
answered still unasked.

## Glossary

The README's glossary gives each term one meaning. Where the users see a term
in another language, the glossary gives that term in italics, then the English
term in bold, then its meaning:

> *Parça* — **Widget**: a `widget.widget` row. Never "item" in data or events.

The files use the glossary's term every time, and never a synonym: a second
word for one thing reads as a second thing.

## Questions

The questions file, `/docs/questions.md`, holds the questions to the owners,
numbered, in the language the owners read. A number is permanent while the
file exists, because rows cite it. When an answer comes:

1. Change the decision's row: the rule and its status. An answer makes a
   *Pending* row *Decided*.
2. Remove the row from the README's **Open decisions** list.
3. Change the build items in its Affects column, and their acceptance
   criteria.
4. Change the tests that cite those criteria.

The same four steps apply to any change of a decision. A changed criterion
with an unchanged test is a test that now checks a rule nobody holds.

## Citing

- **A test cites the acceptance criterion it proves**, by its id, at the start
  of its title. `sds-testing/SKILL.md` is normative for that.
- **A code comment cites the item or the decision the code implements**, for
  example `WID-30` or `DEC-004`, where a reader would otherwise ask why the
  code is the way it is. `sds-nextjs-backend/references/code-documentation.md`
  shows the form in a TypeScript module header.

## Writing

The text SHOULD follow ASD-STE-100, Simplified Technical English: a
specification is read by people for whom English is a second language, by
translators, and by models, and every one of them reads a short, literal
sentence the same way. In practice:

- one instruction or one fact per sentence, and short sentences;
- the active voice, with the actor named: "the system refuses", not "it is
  refused";
- one meaning per word, and one word per meaning: the glossary's;
- no idiom, no "etc.", and no "should" for a rule: a rule says what happens.

## The stage plan

Before a stage's tests are written, whoever runs the loop writes the stage
plan, `/docs/plans/test_plan.md`. It holds the current stage only, and the
next stage replaces it. The tester and the developers work from it; neither
writes it, because each must not shape what the other is held to.

| Part | Holds |
|---|---|
| The stage | Its items, its exit criterion, and the *Pending* rules in force for it |
| The contract | The API surface with its error codes, the data model with its migrations, the UI with its accessible names and dictionary keys, and the test seams. The acceptance tests reach the code only through it |
| The skeleton | The task that builds the contract's surface before any behaviour, per the stack skill's **Skeleton** rules, so the tests compile and fail for the missing behaviour |
| The tasks | In order. Each names the criteria it closes, its *Done when*, and the test tier for each criterion, per `sds-testing/SKILL.md` |
| Fixtures and helpers | The data each tier needs, and the helpers to reuse or add |

The acceptance criteria are the cases, so the plan cites them and never
restates them: a restated criterion drifts from its source, and then the
tests follow whichever copy their author read.

## The stage loop

A stage is built in this loop. Each step's own skill is normative for it:

1. **Decisions.** List the stage's *Pending* decisions. Their rules are in
   force; ask the questions that are not yet asked.
2. **Plan.** Write the stage plan (**The stage plan**).
3. **Skeleton.** Build the contract's surface, with no behaviour, per the stack
   skill.
4. **Tests.** The tester writes the acceptance tests from the criteria and the
   plan, blind to the code, and sees each fail for the missing behaviour, per
   **Acceptance tests** in `sds-testing/SKILL.md`.
5. **Build.** The developers make them pass, one criterion at a time, blind to
   the tests.
6. **Review.** Per `sds-reviewing/SKILL.md`.
7. **Exit.** The stage's exit criterion passes; each acceptance criterion of
   its items has a test that passes; and the coverage floor, the typecheck,
   the linter and the production build pass.

## Checking

The checker ships with this skill and needs only Python's standard library:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/check_specs.py --specs docs/specs
python ${CLAUDE_SKILL_DIR}/scripts/check_specs.py --specs docs/specs --tests tests e2e --through B2
```

The first form checks the set itself:

- every id is defined once, in the file the README names for it, and every
  reference to an id resolves;
- every decision row has the seven columns, a known status and owner, an Ask
  that is `—` or a question, and affected items that exist;
- every *Pending* row names its question, and the **Open decisions** list holds
  exactly the *Pending* rows, each with a stage or phase that exists;
- every item has its **What.**, **Rules.** and **Acceptance.** blocks, and
  criteria whose numbers rise, each used once;
- every item is in a stage, and an item in several stages names its part in
  each.

The second form also reads every file under the test paths for criterion ids.
Each one cited must exist, and every criterion due by `--through`, the last
stage by default, must be cited at least once. A citation is not a pass:
whether the tests pass is the runner's to say.

It exits 0 when everything checked holds, 1 when it found a defect, each
reported with its file and line, and 2 when it could not run: no directory, no
README, a test path that does not exist, or a stage the build order lacks.
Report a 2 as not run, never as passed.

It cannot judge meaning: whether a criterion is observable, whether a rule
contradicts a skill, whether the glossary's terms are used. Those are the
review's.

## Before handing back

- The checker passes on the set, and on the stage's acceptance tests when there
  are some.
- Every rule you could not settle is a *Pending* decision, with its question
  in the questions file and its row in the **Open decisions** list.
- Every new criterion names one observable behaviour, with concrete values.
- No id was renumbered or reused, and every test citing a changed criterion
  was changed with it, or named in your report.
