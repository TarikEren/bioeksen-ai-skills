# Widget Registry — Specifications

**Release 1: the widget register and its review**

Version 1, 9 October 2026

These files are the only authority for the build of Widget Registry release 1.
They give the decisions, the items to make and the method for each item. You
do not need another file to build from them.

The text follows ASD-STE-100 (Simplified Technical English).

## Files

| File | Contents |
|---|---|
| `README.md` | How to use the files, the build order, the open decisions and the glossary |
| `widgets.md` | The decisions, the foundation (FND) and the widget items (WID) |

**Where to find an ID.**
- The items `FND` and `WID` are in `widgets.md`.
- Each decision is in the file of its subject:
  - `widgets.md`: DEC-001 to DEC-007.

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
| `FND-nn` | A foundation item: the repository, the environments and the tests |
| `WID-nn` | A widget item |
| `<item>.ACn` | The acceptance criterion *n* of an item, for example `WID-30.AC6` |

The build items have numbers in groups of ten. The first number of a group
(for example `WID-30`) is the main item of a subject. The other numbers of the
same group are parts of that subject. All IDs are unique across the files. An
ID is never used again, also after its row or item is removed.

**How to read a build item.**
Write the tests first, from the acceptance criteria (DEC-002).

**Decision status.**

| Status | Meaning |
|---|---|
| **Decided** | The owner of the decision made it. Build it. |
| **Pending** | The owner must answer a question. The rule in the row is in force until the answer comes. The **Ask** column names the question. |
| **Default** | We made this choice. It is in force, and we can change it. |

**Owners.**
- `PO`: the product owner.
- `QA`: Quality Assurance.
- `IT`: the infrastructure and operations team.

**The Ask column.**
- `questions.md n` names the question that the owner answers. The file is
  `/docs/questions.md`.
- On a *Decided* row, the question asks the owner to confirm the decision. The
  decision stays in force.
- `—` shows that nobody asks a question.

**The Trace column and the Trace lines.** `§n` is a section of the
requirements document that these files replace. They show the history only.
You do not need them for the build.

**How to change a decision.**
1. Change the `DEC` row: the rule and the **Status**. An answer makes a
   *Pending* row *Decided*.
2. Remove the row from the *Open decisions* list below.
3. Change the build items in its **Affects** column and their acceptance
   criteria.
4. Change the tests that cite those criteria.

**Tests and code.**
- Each test cites the acceptance criterion that it proves, for example
  `WID-30.AC6`.
- A code comment cites the build item or the decision that the code
  implements, for example `WID-30` or `DEC-004`.
- A build item is complete when each of its acceptance criteria has a test
  that passes.

**Names.** State codes are in English. The interface shows the Turkish and
English labels from the dictionaries. The files give a Turkish label in
italics where the users see it.

## Build order

Build the register first. Then the review uses widgets that exist. The stages
follow their dependencies, not dates. A stage is complete when its exit
criterion passes and each acceptance criterion of its items has a test that
passes.

```
B0 Foundation
 └─ B1 The register
     └─ B2 Review and retirement
```

| Need from IT | For | First needed in |
|---|---|---|
| A test server with Docker, and a CI runner that can deploy to it | FND-01 | B0 |

| Stage | Items | Exit criterion |
|---|---|---|
| **B0 Foundation** | FND-01 to FND-02 | CI deploys an empty application to the test server. A test that cites an AC ID that does not exist stops the build. |
| **B1 The register** | WID-10, WID-20, WID-30 (the states and the moves 1 to 3) | A creator creates a widget, sends it to review, and gets it back with a reason. Each move has its audit row. |
| **B2 Review and retirement** | WID-30 (the moves 4 and 5), WID-40 | A reviewer approves a widget. QA retires it on request. |

**The B1 order.** WID-10, WID-20, WID-30. The data model comes first, and the
lifecycle comes last.

## Open decisions

This list shows the decisions that an owner must still answer. The order is
the first stage that needs the answer. The rule in force, the owner and the
question are in the row of the decision.

| Decision | First needed in |
|---|---|
| DEC-003 | B1 |
| DEC-006 | B1 |

## Glossary

Each term has one meaning.

*Parça* — **Widget**: a `widget.widget` row. Never "item" in data or events.

*Oluşturan* — **Creator**: the person who creates a widget and sends it to
review (WID-20).

*İnceleyen* — **Reviewer**: the person who approves or returns a widget
(WID-20).

*Kullanım dışı* — **Retired**: the end state of a widget. A retired widget is
never deleted (DEC-004).
