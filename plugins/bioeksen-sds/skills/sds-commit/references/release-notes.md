# Release Notes

This document is the normative definition of a BioEksen release note: where it
lives, the version it is named for, and the entry format every change is
written in. The commit format the entries are derived from is in `SKILL.md`.

- Each release MUST come with its own release note in `/release-notes/{version}.md`.

The audience is developers and language models reading the history of a
service or library, and the note is part of the project's change record. Both
readings require the same thing: a complete list, in a fixed shape, with no
editorial selection applied.

## Location and naming

| Rule | Value |
|------|-------|
| Path | `/release-notes/{version}.md`, relative to the repository root. In a monorepo, `{unit}/release-notes/{version}.md`, in the release unit's own directory |
| `{version}` | The released version, no `v` prefix, e.g. `/release-notes/2.4.0.md` |
| Tag | `v{version}`, e.g. `v2.4.0`; in a monorepo `{software-id}/v{version}`, naming the unit, e.g. `bio-inventory/v2.4.0`. On the commit that adds the note |
| Existence | The note MUST be committed before the release is tagged |

The tag carries the `v` and the file does not. That is the one place the two
spellings differ, and it is recorded here so nobody has to guess from whichever
they saw last. A monorepo's tag also carries the unit's id, which the note's
directory already gives it.

One file per release, never a single accumulating changelog. A released version
is immutable, so its note is immutable too: it is written once and afterwards
only corrected for factual error, never rewritten to reflect later releases.

## Release units

A monorepo holds several services or libraries that each release on their own,
as `bio-software` holds every BioEksen app. Each is a **release unit**. These
rules decide which commits belong to which unit, so that a unit's change
identifiers, release notes and history name the commits that changed it and
no others. A repository holding one service is a single unit, its root, and
nothing in this section applies to it.

- **Release unit.** A directory below the repository's root that holds
  `.bioeksen/software-id`, per `sds-logging/references/log-record.md`. One unit
  may hold several packages under its one id, such as an app's web and worker
  processes, or libraries published together. The root holds the monorepo's
  own id. Units do not nest.
- **Closure of a unit**, as of a commit:
  1. the unit's own directory;
  2. every workspace package its packages depend on through `workspace:`
     dependencies, in any dependency field, transitively;
  3. the root build files: `/package.json`, `/pnpm-workspace.yaml`,
     `/turbo.json`, `/.npmrc`, `/.nvmrc` and the root `tsconfig` files.

  The closure is read from a pnpm workspace, the kind the estate's monorepo
  is.
- **The lockfile.** `/pnpm-lock.yaml` belongs to the units whose own package
  manifests, those in their directories, the same commit changes. A commit
  that changes the lockfile and no package manifest belongs to every unit.
- **Affected units** of a commit: the units whose closure, as of that commit,
  contains a path the commit changes compared with its first parent, and those
  the lockfile rule gives it.
- **Attribution.** A commit's change identifier, per **Change identifiers**
  below, carries:

  | Affected units | `{software-id}` | Trailers |
  |----------------|-----------------|----------|
  | Exactly one | That unit's id | None beyond those `SKILL.md` defines for every commit |
  | Several | The monorepo's id | `Affects: {software-id}`, one per affected unit; `Changes-Package: {package name}`, one per changed workspace package that sits in no unit's directory |
  | None, e.g. only `.claude/`, workflows or root documents | The monorepo's id | `Changes-Package:` for each such package changed; no `Affects:` |

  The script **Footer** in `SKILL.md` names computes the id and the trailers
  from the staged changes. A person never writes them, and CI checks them
  against the commit's paths.
- **History from before the monorepo.** A commit whose tree holds no id at the
  root predates the monorepo: it came in with a history moved there. It
  belongs to the unit whose directory holds its paths, and it is not checked
  against these rules, which it was not written under.
- **Release range** of a unit's release: the non-merge commits between the
  unit's previous tag and this one,
  `{software-id}/v{previous}..{software-id}/v{version}`, whose affected units
  include the unit. Each commit is judged as of itself, by the rule that gave
  it its trailers. A commit that changes only the lockfile, and so affects
  every unit, is in every unit's next release, and the history before a unit
  existed is in none of its releases.

The rules read paths rather than a person's judgement. A person deciding which
apps a shared change reaches either names too few, and an app ships a change
its note never mentions, or names every app to be safe, and every note fills
with changes that never reached it. The dependency graph already holds the
answer, and reading it gives the same answer every time.

## Version

In a monorepo, each release unit is versioned on its own, from the commits in
its **Release range**, so everything below applies to one unit at a time.

These versions name releases of a deployed service or of a published
library. For a service, nothing resolves them as a dependency range, so the
version tells a reader what kind of change they are about to receive. For a
library, dependents do resolve them, so the same rules are also its
compatibility promise: a change that breaks any caller of its public exports
is breaking, whether or not the library's own tests changed.

The version is the one the release's commits imply, per the versioning rules in
`SKILL.md`. Applied to the whole set of commits in the release, highest match
wins:

| If any commit in the release... | Increment |
|---------------------------------|-----------|
| Carries `!` in its subject, or a `BREAKING CHANGE:` footer | Major |
| Is `feat` | Minor |
| Otherwise | Patch |

Incrementing a component resets the ones below it to zero: a major bump from
`2.4.3` gives `3.0.0`, a minor bump gives `2.5.0`.

A `fix` is a patch, as SemVer and the conventional-commit release tools define
it. A fix restores behaviour a caller was already promised, so it tells a
reader nothing new about the interface; a minor bump says the interface grew.
Keeping the tools' definition also means semantic-release, release-please or
a commitlint preset computes the same version this table does, with no
configuration to drift from it.

The version is a consequence of the commits, not a decision taken at release
time. If the release deserves a different number, the disagreement is with a
commit's type, and that is where it gets fixed.

### Before 1.0.0

While the major version is `0`, the service or library carries no
compatibility promise and the increments shift down one place:

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

### The first release

A new service or library starts at `0.1.0`. Its first release is `0.1.0`
whatever its commits are, because there is no earlier version for them to
increment, and it covers every commit from the repository's root. The root
commit is `chore: initial commit`, with a `Change-Id:` like any other, so it
is the first release's first `chore` entry.

A release unit of a monorepo starts at `0.1.0` too. Its first release covers
the commits that reached it, from the one that created it: the monorepo's
history before the unit existed is in none of its releases.

Starting below `1.0.0` puts a new service under the rule above from its first
commit. Starting at `0.0.1`, as a patch from nothing, would be just as
arbitrary and would say less: the first release is the one that introduced
the interface, which is what a minor increment means.

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

- auth-service-20260904T170512-a3f9 feat(api): operators cannot currently list logs without shell access
  - What changed: add `GET /api/admin/logs`, paginated, operator credential required
- auth-service-20260904T181130-7b0c fix(auth): expired tokens were rejected as invalid, hiding the real cause
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
| `{software-id}` | The release unit the commit affects, which in a repository holding one service is its root's: the same value as the `id` field of a log record, in the same format — see `sds-logging/references/log-record.md`. In a monorepo, the monorepo's own id for a commit that affects several units or none, per **Release units** |
| `{unique string}` | A timestamp in UTC+03:00, written `YYYYMMDDTHHMMSS` with no zone suffix, followed by `-` and at least four random characters, e.g. `20260904T170512-a3f9` |

Both parts are lowercase apart from the `T` of the timestamp, and use only
`[a-z0-9-]`. The compact timestamp form is deliberate: RFC 3339's colons are
illegal in Windows filenames and awkward inside an identifier, and the random
tail keeps two entries minted in the same second distinct.

The timestamp is minted in UTC+03:00, the time BioEksen works in, so an
identifier reads as the local time its commit was written. The offset is fixed
here rather than written into each identifier: a `+0300` suffix would add a
character outside `[a-z0-9-]` that needs escaping wherever an identifier goes
into a URL, and Türkiye has kept UTC+03:00 all year since 2016, so the offset
never shifts or repeats an hour. It is a fixed offset, not a named zone, so a
future change to the country's clocks does not change what an identifier
means.

Identifiers minted before 2026-10-02 carry a UTC time ending in `Z`, e.g.
`20260917T101500Z-4c1e`. They stay valid and are never rewritten, like the
notes that hold them; the `Z` is what tells the two forms apart.

Reusing the log record `id` as the software part means an identifier read out
of a release note and one read out of a log line name the same service without
a lookup table — which matters when the reader is aggregating notes across the
estate, or is a model with only the text in front of it. A monorepo's own id
names no service, so its entries name the units they reached instead, per
**Which commits appear**.

### When the software id is unknown

The software id is supplied by the project, or by the id-issuing service once
one exists, is allocated per the rule in
`sds-logging/references/log-record.md`, which is normative for it, and is read
from the `.bioeksen/software-id` file that rule names.

When it has not been supplied, the identifier MUST NOT be written with a guess:
ask for it, or emit the literal placeholder `<software-id>` for a person to
replace.

```
<software-id>-20260904T170512-a3f9 feat(api): ...
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
In a monorepo it does the same, and the commit's `Affects:` trailers say which
units' notes list it.

Minting is local: the identifier is built from the stored software id, the
clock and a random tail, and MUST NOT require a network call. A commit that
depended on a service being reachable would either stop when the service is
down or have the rule bypassed under pressure, leaving gaps in the history
that look exactly like commits predating the rule. The random tail is what
makes a locally minted identifier collision-resistant without coordination.

## Which commits appear

- Every commit reachable from the release tag and not from the previous one
  MUST have an entry, whatever its type. `docs`, `style` and `chore` commits
  are listed like any other. In a monorepo, that is every commit of the unit's
  **Release range**, and the previous release is the unit's own previous tag.
- An entry minted with a monorepo's own id ends its reason by naming the units
  the commit affects, as its `Affects:` trailers list them:
  `- bio-software-20261008T101500-a3f9 feat(sdk): … (affects bio-inventory, bio-softop)`.
- Merge commits are not listed. The commits they bring in are.
- A first release has no previous tag. Its range is every commit from the
  root, so the initial commit has an entry too.
- One commit is one entry. A commit whose change cannot be stated as a single
  entry is a commit that should have been split.
- **The commit that adds the note carries an entry for itself.** The tag sits
  on that commit, so it is inside the range the count is taken over. Mint its
  change identifier first, with the script **Footer** in `SKILL.md` names,
  write the entry with it, then commit using it as the trailer. Without this
  the count is short by one at every release, and the check stops meaning
  anything.

Listing every commit is what makes the note checkable against `git log`:
the entry count MUST equal `git log --no-merges {previous}..{version}`, and
in a monorepo the number of that range's commits that reach the unit.
Filtering by perceived importance breaks that check, and makes a change that
was never in the release indistinguishable from one judged too small to
mention — a distinction the change record has to preserve.

## Order

Breaking changes first, then the remaining entries in the order the type table
in `SKILL.md` lists them — `feat`, `fix`, `refactor`, `perf`, `style`, `test`,
`docs`, `build`, `ops`, `chore`, `revert`. Within one type, keep commit order.

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

In a monorepo, an entry keeps its commit's `!` in every note that lists it, but
the change is breaking only for the unit its scope names, per **Versioning** in
`SKILL.md`. Another unit's note lists it first like any breaking entry, while
its version counts the commit by its type alone.
