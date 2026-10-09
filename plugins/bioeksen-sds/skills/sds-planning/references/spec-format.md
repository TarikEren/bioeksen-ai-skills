# The specification format

The skeleton of each file of a specification set, and of the stage plan, with
the reason for each part. `SKILL.md` is normative for the rules; this file
shows where each rule lands. `example/README.md` and `example/widgets.md` are a
complete set built from these skeletons, and the checker's tests hold them
consistent.

Placeholders are in braces. Everything else is the fixed wording the checker
and the readers rely on: the `**Label.**` paragraphs, the table headers, and
the `##` headings it names.

## The README

```markdown
# {Product} — Specifications

**Release {n}: {what the release holds}**

Version {n}, {date}

These files are the only authority for the build of {Product} release {n}.
They give the decisions, the items to make and the method for each item. You
do not need another file to build from them.

The text follows ASD-STE-100 (Simplified Technical English).

## Files

| File | Contents |
|---|---|
| `README.md` | How to use the files, the build order, the open decisions and the glossary |
| `{area}.md` | The decisions and the items `{PREFIX}` of {subject} |

**Where to find an ID.**
- The items `{PREFIX}` and `{PREFIX}` are in `{area}.md`.
- Each decision is in the file of its subject:
  - `{area}.md`: DEC-001 to DEC-011; DEC-013.

## How to use the files

**Authority.**
- These files have priority over all other texts.
- Each decision is a `DEC` row in these files. No other file holds a decision.
- If these files do not give a rule, ask the product owner. Do not take the
  rule from another file.

**Identifiers.**

| Form | Meaning |
|---|---|
| `DEC-nnn` | A decision, in the "Decisions" section of its file |
| `{PREFIX}-nn` | {what the items with this prefix cover} |
| `<item>.ACn` | The acceptance criterion *n* of an item, for example `{PREFIX}-30.AC4` |

The build items have numbers in groups of ten. ...

**How to read a build item.** ...

**Decision status.**

| Status | Meaning |
|---|---|
| **Decided** | The owner of the decision made it. Build it. |
| **Pending** | The owner must answer a question. The rule in the row is in force until the answer comes. The **Ask** column names the question. |
| **Default** | We made this choice. It is in force, and we can change it. |

**Owners.**
- `{CODE}`: {who}.

**The Ask column.** ...

**The Trace column and the Trace lines.** ...

**How to change a decision.**
1. ...

**Tests and code.** ...

**Names.** ...

## Build order

{Why the stages are in this order.}

{A tree of the stages, in a fenced block.}

| Need from {team} | For | First needed in |
|---|---|---|

| Stage | Items | Exit criterion |
|---|---|---|
| **B0 {name}** | {PREFIX}-01 to {PREFIX}-08 | {a result someone can check} |

| Phase | Items |
|---|---|
| B5.1 {name} | {items} |

## Open decisions

| Decision | First needed in |
|---|---|
| DEC-{nnn} | B{n} |

## Glossary

Each term has one meaning.

*{term in the users' language}* — **{English term}**: {meaning}.
```

| Part | Why it is there |
|---|---|
| Release and version | A test plan, a validation report and a question to an owner all name the version they were made from |
| Authority statement | Without it, an old requirements document, a ticket or the old code competes with the specification, and the build follows whichever its reader found first |
| **Files** and **Where to find an ID.** | A reader holding an id finds its file in one step. The checker reads the prefixes' files and the decision ranges from this list, and refuses an item or a decision outside them |
| **Identifiers.** | The item prefixes are the project's own; the checker reads them from this table's forms (`{PREFIX}-nn`) and treats nothing else as an item id. An id like `A-104` in a Trace column is left alone |
| **Decision status.**, **Owners.**, **The Ask column.** | They make a *Pending* row read as a rule in force with a named owner and question, not as a gap. The checker reads the owners from the list's backticked codes |
| **How to change a decision.** | The four steps of `SKILL.md`, **Questions**, where every editor sees them |
| **Tests and code.** | The citation rules, stated where the people who write tests and code read first |
| **Build order** | The stage table is the one the checker reads: a header whose first cell is `Stage`, the stage's id first in its first cell (`**B0 Foundation**`), its items, and its exit criterion. A table headed `Phase` names the phases an open decision may name |
| **Open decisions** | The owners' work list. The checker holds it equal to the *Pending* rows |
| **Glossary** | One meaning per term, and the users' word beside the English one, so a screen, a test and a rule say the same thing |

## An area file

```markdown
# {Product} — {Subject}

{One line: what this file holds.}
Read `README.md` first. It explains the IDs, the decision status and the build order.

## Decisions

Each row is one decision. The **Decision** column gives the rule that is in
force. A *Pending* rule stays in force until the owner answers.

### {A subject, where the decisions are many}

| ID | Decision | Status | Owner | Ask | Affects | Trace |
|---|---|---|---|---|---|---|
| DEC-{nnn} | {The rule, in force.} | Pending | {CODE} | questions.md {n} | {PREFIX}-{nn}, {PREFIX}-{nn} | {source} |

## {Prose the items share: an architecture, a model, a layout}

## {A group of items}

{What the group covers. In the acceptance criteria, "fails" means that the
system refuses the action with its reason, and no row changes.}

### {PREFIX}-{nn} {Title}

{The item's blocks: see below.}
```

- **The decisions come first**, because every item below cites them. A reader
  who reads the file in order meets each rule before the items that carry it.
- **The decision table's header is fixed**: `ID`, `Decision`, `Status`,
  `Owner`, `Ask`, `Affects`, `Trace`, in that order. The checker refuses a
  decision table with other columns rather than guess which cell is which.
- **The group's paragraph defines "fails"** once, so no criterion has to.

## A build item

```markdown
### {PREFIX}-{nn} {Title}

**What.** {One sentence: what the item gives.}

**Rules.**
1. {A rule, citing what it carries} (DEC-{nnn}, {PREFIX}-{nn}).
2. ...

**Data.** {Tables and columns, where the item adds them.}

**Screens.** {Pages, where the item adds them.}

**States.** {A table: state, its label in the users' language, its owner.}

**Moves.** {A table: number, from, move, to, who, checks.}

**Jobs.** {Scheduled work, and what runs it.}

**Acceptance.** {An optional line fixing a notation the criteria share.}
- **AC1.** When {an action}, {the observable result}.
- **AC2.** If {a condition}, {the observable result}.

**Trace.** {sources} · {findings}
```

- **What.**, **Rules.** and **Acceptance.** are required; the checker reports
  an item without one. A part, an item that is not the first of its group,
  needs only **Acceptance.**, under its own heading:

```markdown
### {PREFIX}-{n1} {Title}

**Acceptance.**
- **AC1.** ...
```
- **The criteria's numbers rise, and each is used once.** A removed criterion
  leaves its number unused, as a removed item does: renumbering the ones after
  it would silently re-point every test that cites them.
- **A Moves table numbers its moves**, so a rule or a criterion can name "move
  5" and a stage can list "the moves 4 and 5".

## The stage plan

`/docs/plans/test_plan.md`, the current stage only:

```markdown
# Stage {B n}: {name}

**Items.** {the stage's items, as the build order lists them}

**Exit criterion.** {as the build order states it}

**Pending rules in force.** DEC-{nnn}, DEC-{nnn}: {one line each, or "none"}

## Contract

### API
| Method and path | Request | Success | Errors |
|---|---|---|---|

### Data
| Table | Columns and constraints | Migration |
|---|---|---|

### UI
| Page or component | Accessible names | Dictionary keys |
|---|---|---|

### Test seams
{The seams the tests may use: a test sign-in, an injected clock, a fake
service. Each enabled only by validated configuration in a test environment.}

## Skeleton

{The task that builds the contract's surface with no behaviour: exports that
throw the not-implemented error, routes that answer it, components that render
a stub, and the migration.}

## Tasks

| Task | Closes | Tier per criterion |
|---|---|---|
| T1 {name} | {PREFIX}-{nn}.AC1 to AC4 | AC1-AC3 unit; AC4 integration |

## Fixtures and helpers

{What each tier needs, and the helpers to reuse or add.}
```

- **The contract is the only door.** The tester writes against it and the
  developers build to it, so a name missing from it is a name neither side may
  use. That is what lets the two work blind to each other.
- **Each task's Closes column is its *Done when***: the task is done when
  those criteria's tests pass. A reviewer checks that every criterion of the
  stage's items is in exactly one task.
- **The tier** is the lowest that can prove each criterion, per
  `sds-testing/SKILL.md`, decided before the tests are written so the tester
  and the developers expect the same seams.

## The questions file

`/docs/questions.md`:

```markdown
# Questions

## 1. {A short title}

{The question, in the language its owner reads, with the rule in force until
the answer comes and why it matters.}

**For:** DEC-{nnn}, DEC-{nnn}. **Owner:** {CODE}.

**Answer:** {empty until answered; the date and who answered, after}
```

The number is permanent while the file exists, because decision rows cite it.
An answered question stays until its answer is in the decision rows; the file
goes when every answer is.
