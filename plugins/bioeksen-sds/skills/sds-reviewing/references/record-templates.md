# Review record templates

Skeletons for a project that has no review record yet. Replace everything in
angle brackets. Keep the headings: the README's rows link to them.

## `<record>/README.md`

````markdown
# Review findings

The running record of code reviews for this repository. Each review has a
file of its own, `review_N.md`, with its summary and the findings it found.
This file holds what spans reviews: the log, the status of every finding,
coverage, the questions, the test gaps and the strengths.

- A finding keeps its ID (`R-nnn`) for life. IDs are never reused or
  renumbered.
- A finding lives in the file of the review that found it. A later review's
  notes on it are added there, so a finding reads whole in one place.
- A review is closed once every finding it found is `Fixed`: its file is
  renamed `fixed_review_N.md`, and the links to it are updated.
- Status is one of `Open`, `Fixed (<commit>)`, `Tracked (<backlog entry>)` or
  `Won't fix (<reason>)`.
- Severity: *Critical* (wrong record, security, data loss), *Major*,
  *Minor*.
- Line numbers are as of the review that last touched the finding; the
  symbol is the stable anchor.

## Review log

| # | Date | Scope | Base | Verdict |
|---|---|---|---|---|
| [1](review_1.md) | <YYYY-MM-DD> | <what was reviewed, by whom, and that every claim was checked> | `<commit>` | <verdict, and the findings that decide it> |

## Status at a glance

| ID | Title | Severity | Status |
|---|---|---|---|
| [R-001](review_1.md#r-001--<heading-slug>) | <the defect> | <severity> | **Open** — found in review 1 |

## Coverage

| Area | Reviewed in |
|---|---|
| <paths> | 1 (<how: read in full, reproduced, measured>) |

## Questions for the author

| # | Question | Status |
|---|---|---|
| Q-1 | <the question, and why it matters> | Open (review 1) |

## Test coverage gaps

| Missing test | Finding | Status |
|---|---|---|
| <the behaviour no test checks> | R-001 | **Open** |

## Strengths

Recorded so later reviews do not undo them.

- **Review 1:** <what holds, and why it matters>
````

## `<record>/review_N.md`

````markdown
# Review <N> — <what it covered>

| # | Date | Scope | Base | Verdict |
|---|---|---|---|---|
| <N> | <YYYY-MM-DD> | <scope; who reviewed; every claim checked before it was recorded> | `<commit>` | <verdict> |

The log of every review, and the status of every finding: [README](README.md).

## Summary

<What was found, how each claim was checked, what matters most.>

**Verdict: <Approve | Approve with follow-ups | Request changes>.** <What
blocks, or what comes first.>

## Findings

Line numbers are as of `<commit>`.

<one block per finding, most severe first>

## Earlier findings

- **R-<nnn>:** <fixed in `<commit>` | still open | regressed>.
````

## A finding

````markdown
### R-<nnn> — <the defect, as a sentence>

- **Status:** **Open** · **Severity:** <Critical | Major | Minor> · **Proposed rank:** <rank, if the backlog ranks> · **Found:** review <N> (<by whom; confirmed, reproduced, or Plausible and why>)
- **Where:** `<path>:<line>`, `<symbol>`.
- **Problem:**
  - <the failure scenario: input or sequence, and the wrong result>
  - <the evidence: lines, command output, the test that shows it>
- **Fix:** <what should change, described>
````

A later review's note, added at the end of the finding:

```markdown
- **Review <M>:** <still open at `<commit>` | fixed in `<commit>`, checked by … | regressed in `<commit>`>. <What changed, and any decision taken.>
```
