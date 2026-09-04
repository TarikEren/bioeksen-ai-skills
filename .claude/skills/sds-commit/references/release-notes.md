# Release Notes

This document is the normative definition of a BioEksen release note: where it
lives, the version it is named for, and the entry format every change is
written in. The commit format the entries are derived from is in `SKILL.md`.

- Each release MUST come with its own release note in `/release-notes/{version}.md`.

The audience is developers and language models reading the history of a
service, and the note is part of the project's change record. Both readings
require the same thing: a complete list, in a fixed shape, with no editorial
selection applied.

## Location and naming

| Rule | Value |
|------|-------|
| Path | `/release-notes/{version}.md`, relative to the repository root |
| `{version}` | The released version, no `v` prefix, e.g. `/release-notes/2.4.0.md` |
| Existence | The note MUST be committed before the release is tagged |

One file per release, never a single accumulating changelog. A released version
is immutable, so its note is immutable too: it is written once and afterwards
only corrected for factual error, never rewritten to reflect later releases.

## Version

These versions name releases of a deployed service, not of a published
library. Nothing resolves them as a dependency range, so the version exists to
tell a reader what kind of change they are about to receive.

The version is the one the release's commits imply, per the versioning rules in
`SKILL.md`. Applied to the whole set of commits in the release, highest match
wins:

| If any commit in the release... | Increment |
|---------------------------------|-----------|
| Carries `!` in its subject, or a `BREAKING CHANGE:` footer | Major |
| Is `feat` or `fix` | Minor |
| Otherwise | Patch |

Incrementing a component resets the ones below it to zero: a major bump from
`2.4.3` gives `3.0.0`, a minor bump gives `2.5.0`.

The version is a consequence of the commits, not a decision taken at release
time. If the release deserves a different number, the disagreement is with a
commit's type, and that is where it gets fixed.

### Before 1.0.0

While the major version is `0`, the service carries no compatibility promise
and the increments shift down one place:

| If any commit in the release... | Increment |
|---------------------------------|-----------|
| Carries `!` in its subject, or a `BREAKING CHANGE:` footer | Minor |
| Anything else | Patch |

So a breaking change at `0.4.2` gives `0.5.0`, and everything else gives
`0.4.3`.

`1.0.0` is therefore never reached by accident. It is released deliberately, to
declare that the service now has an interface others may depend on. Without
this rule the first rename in a new project ships `1.0.0`, the next one ships
`2.0.0`, and the major version stops meaning anything before the service is
even stable.

### Pre-release labels

A release that is not yet ready for general use MAY carry a pre-release suffix:

```
1.0.0-beta.1        /release-notes/1.0.0-beta.1.md
1.0.0-beta.2        /release-notes/1.0.0-beta.2.md
1.0.0               /release-notes/1.0.0.md
```

The label is a suffix on the version it leads to, not a prefix. A prefix like
`beta-1.0.0` sorts under `b`, scattering a project's releases across the
directory listing and breaking the ordering of both `ls` and any tool that
sorts by version. As a suffix, the beta releases sort immediately before the
version they precede, and rank lower than it, which is what they are.

Each pre-release gets its own note, on the same terms as any other release.

## Contents

A note is the title, the release date, and the list of changes:

```markdown
# 2.4.0

Released 2026-09-04.

- auth-service-20260904T140512Z-a3f9 feat(api): operators cannot currently list logs without shell access
  - What changed: add `GET /api/admin/logs`, paginated, operator credential required
- auth-service-20260904T151130Z-7b0c fix(auth): expired tokens were rejected as invalid, hiding the real cause
  - What changed: return `AUTH-4102` instead of `AUTH-4101` when only `exp` has passed
```

### Entry format

Every change is one entry, in exactly this form:

```
- {commit id} {change_type}: {change reason}
  - What changed: {changes}
```

| Field | Content |
|-------|---------|
| `{commit id}` | The change identifier, per the next section |
| `{change_type}` | The commit's type with its scope and breaking indicator, verbatim from the subject line and without the `:` — `feat`, `fix(auth)`, `feat(api)!` |
| `{change reason}` | Why the change was made: the motivation from the commit body, or the reason implied by the subject when there is no body |
| `{changes}` | What the change does, in terms an operator or a caller of the API can observe |

Reason and changes are both written in the commit style of `SKILL.md`: lower
case first letter, no trailing period. The reason describes the situation the
change addresses, in past or present tense; `{changes}` uses the imperative
present, like the commit description it comes from.

The two halves MUST NOT restate each other. `{change reason}` answers why the
change exists and `{changes}` answers what a reader will notice — an entry
whose reason is "add the logs endpoint" has recorded nothing that the commit
history did not already hold.

## Change identifiers

Every entry is identified by:

```
{software-id}-{unique string}
```

| Part | Rules |
|------|-------|
| `{software-id}` | The service the release belongs to. The same value as the `id` field of a log record — see `sds-logging/references/log-record.md`. Constant across every entry in every note for that project |
| `{unique string}` | A UTC timestamp followed by `-` and at least four random characters, e.g. `20260904T140512Z-a3f9` |

Both parts are lowercase apart from the `T` and `Z` of the timestamp, and use
only `[a-z0-9-]`. The compact timestamp form is deliberate: RFC 3339's colons
are illegal in Windows filenames and awkward inside an identifier, and the
random tail keeps two entries minted in the same second distinct.

Reusing the log record `id` as the software part means an identifier read out
of a release note and one read out of a log line name the same service without
a lookup table — which matters when the reader is aggregating notes across the
estate, or is a model with only the text in front of it.

### When the software id is unknown

The software id is supplied by the project. When it has not been, the
identifier MUST NOT be written with a guess: ask for it, or emit the literal
placeholder `<software-id>` for a person to replace.

```
<software-id>-20260904T140512Z-a3f9 feat(api): ...
```

A note MUST NOT be committed with a placeholder still in it. The placeholder is
written in angle brackets precisely so that it is greppable and fails review
rather than surviving into the record as a plausible-looking name.

### Traceability

The change identifier names the entry, not a git object, so an entry cannot be
resolved to its commit by the identifier alone.

The commit therefore carries it. The identifier is minted when the commit is
written, recorded there as a mandatory `Change-Id:` footer trailer per the
footer rules in `SKILL.md`, and copied verbatim into the note. That trailer is
what lets `git log --grep` take an entry back to the change that produced it,
and what keeps the note verifiable once the subject lines have been forgotten.

## Which commits appear

- Every commit reachable from the release tag and not from the previous one
  MUST have an entry, whatever its type. `docs`, `style` and `chore` commits
  are listed like any other.
- Merge commits are not listed. The commits they bring in are.
- One commit is one entry. A commit whose change cannot be stated as a single
  entry is a commit that should have been split.

Listing every commit is what makes the note checkable against `git log`:
the entry count MUST equal `git log --no-merges {previous}..{version}`.
Filtering by perceived importance breaks that check, and makes a change that
was never in the release indistinguishable from one judged too small to
mention — a distinction the change record has to preserve.

## Order

Breaking changes first, then the remaining entries in the order the type table
in `SKILL.md` lists them — `feat`, `fix`, `refactor`, `perf`, `style`, `test`,
`docs`, `build`, `ops`, `chore`. Within one type, keep commit order.

The reader looking for what will break their integration finds it at the top,
without a heading structure the format does not have.

## Breaking changes

An entry for a breaking change MUST keep the `!` in `{change_type}`, and its
reason MUST carry the `BREAKING CHANGE:` text from the commit footer rather
than paraphrasing it. Where the footer is multi-line, the entry states what
breaks and `{changes}` states what to do instead.

A major release whose note contains no `!` entry is a contradiction, and one of
the two is wrong. The single exception is `1.0.0`, which is a declaration of
stability rather than a consequence of a breaking change.
