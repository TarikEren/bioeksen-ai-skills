# Widget Registry — Widgets

The foundation and the widget register.
Read `README.md` first. It explains the IDs, the decision status and the build order.

## Decisions

Each row is one decision. The **Decision** column gives the rule that is in
force. A *Pending* rule stays in force until the owner answers.

| ID | Decision | Status | Owner | Ask | Affects | Trace |
|---|---|---|---|---|---|---|
| DEC-001 | The application uses Next.js (App Router) and TypeScript. The database is PostgreSQL 16 or later. | Decided | PO | — | FND-01, FND-02 | §2 |
| DEC-002 | Tests come first, from the acceptance criteria, and cite them. The coverage floor only goes up. | Decided | PO | — | FND-02 | §5 |
| DEC-003 | A widget gets its code from the next number of the register at the first save. The code never changes. | Pending | QA | questions.md 1 | WID-10 | §3.1 |
| DEC-004 | The system never deletes a widget. `RETIRED` is the end state. | Decided | PO | questions.md 2 | WID-10, WID-30, WID-40 | §3.2 |
| DEC-005 | The creator and the reviewer of a widget are two different persons. | Default | PO | — | WID-20, WID-30 | §3.3 |
| DEC-006 | A return from review needs a reason. | Pending | QA | questions.md 3 | WID-30 | §3.4 |
| DEC-007 | QA decides a retire request in 3 working days. | Default | QA | — | WID-40 |  |

## Foundation

### FND-01 Repository and CI

**What.** One repository, and a CI pipeline that stops each bad change.

**Rules.**
1. On every change, CI runs the type check, the lint, the tests and the
   production build (DEC-001).
2. CI deploys each build that passes all checks to the test environment.

**Acceptance.**
- **AC1.** If a change has a type error, a lint error or a failed test, CI
  fails and deploys nothing.
- **AC2.** If all checks pass, CI deploys the build to the test environment,
  and that environment answers ready.

**Trace.** §2, §5

### FND-02 Tests

**What.** The tests during the build.

**Rules.** The item follows DEC-001 and DEC-002.

**Acceptance.**
- **AC1.** When CI checks the suite, each acceptance test names an AC ID that
  exists.
- **AC2.** If the coverage is below the floor, CI fails.

**Trace.** §5

## Widgets

The module `widget` keeps the widget register. In the acceptance criteria,
"fails" means that the system refuses the action with its reason, and no row
changes.

### WID-10 Widgets and codes

**What.** The system keeps widgets with their codes.

**Rules.**
1. The code comes from the next number of the register at the first save, and
   never changes (DEC-003).
2. The system never deletes a widget (DEC-004).
3. A request names a widget by its numeric id.

**Data.** `widget.widget`: the code (unique), the name, the state and the
creator.

**Acceptance.**
- **AC1.** When a widget is first saved, it gets the next unique code.
- **AC2.** If a person tries to change the code, the code stays.
- **AC3.** If a person deletes a widget, the deletion fails, and the row
  stays.
- **AC4.** If a request names a widget by an id that does not parse, the
  system answers as for a widget that does not exist.

**Trace.** §3.1, §3.2

### WID-20 Roles

**What.** These roles act on widgets.

**Rules.**

| Role | TR | Who |
|---|---|---|
| Creator | *Oluşturan* | a person with the `CREATOR` role |
| Reviewer | *İnceleyen* | a person with the `REVIEWER` role |

1. Two different persons create and review a widget (DEC-005).

**Acceptance.**
- **AC1.** If a person without the `CREATOR` role creates a widget, the
  creation fails.
- **AC2.** If the creator of a widget approves it, the approval fails.

**Trace.** §3.3

### WID-30 Lifecycle

**What.** A widget has four states and five moves.

**Rules.**
1. The system never deletes a widget (DEC-004).
2. Each move stores a reason, and writes one audit row.
3. A return needs a reason (DEC-006).
4. The creator and the reviewer are two persons (DEC-005, WID-20).

**States.**

| State | TR | Owner |
|---|---|---|
| `DRAFT` | *Taslak* | creator |
| `IN_REVIEW` | *İncelemede* | reviewer |
| `ACTIVE` | *Aktif* | creator |
| `RETIRED` | *Kullanım dışı* | nobody |

**Moves.** If a check fails, the move fails.

| # | From | Move | To | Who | Checks |
|---|---|---|---|---|---|
| 1 | none | *Oluştur* | `DRAFT` | creator | name |
| 2 | `DRAFT` | *Gönder* (the send) | `IN_REVIEW` | creator | name, code |
| 3 | `IN_REVIEW` | *İade et* | `DRAFT` | reviewer | reason |
| 4 | `IN_REVIEW` | *Onayla* | `ACTIVE` | reviewer | none |
| 5 | `ACTIVE` | retire approved | `RETIRED` | QA | WID-40 |

**Acceptance.**
- **AC1.** When a creator creates a widget with a name, it gets `DRAFT` and
  an audit row. Without a name, the creation fails.
- **AC2.** When the creator sends the widget, it gets `IN_REVIEW`.
- **AC3.** If a check of move 2 fails, the send fails and names the check.
- **AC4.** When the reviewer approves, the widget gets `ACTIVE`.
- **AC5.** When the reviewer returns the widget with a reason, it gets
  `DRAFT`.
- **AC6.** If a return has no reason, the return fails.
- **AC7.** When a move occurs, one audit row records both states, the actor,
  the reason and the time.

**Trace.** §3.4

### WID-40 Retire requests

**What.** A creator asks to retire an `ACTIVE` widget. QA decides.

**Rules.**
1. QA decides in 3 working days (DEC-007).
2. An approved request moves the widget to `RETIRED` (WID-30, move 5). The
   widget stays readable (DEC-004).

**Acceptance.**
- **AC1.** When the creator sends a retire request with a reason, QA gets a
  task due in 3 working days.
- **AC2.** When QA approves, the widget gets `RETIRED` and stays readable.
- **AC3.** If QA rejects without a reason, the rejection fails.

**Trace.** §3.5

### WID-41 Retire notices

**Acceptance.**
- **AC1.** When QA decides a retire request, the creator gets a notice.
- **AC2.** When a widget gets `RETIRED`, its reviewer gets a notice.
