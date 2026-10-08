---
name: sds-commit
description: BioEksen conventional commit format. Use when writing or amending a commit message, minting its Change-Id, reviewing commit history, or deciding a release version from a set of commits.
---

# Conventional Commits
Each commit MUST abide by the following format:

```
<type>(<scope>): <description>

[empty line]
<body>
[empty line]
<footer>
```

Paths such as `sds-logging/references/log-record.md` name a file in another
skill of this plugin, relative to the plugin's skills directory: the parent
of `${CLAUDE_SKILL_DIR}`, which is this skill's own directory.

## Type

| Type | Definition |
|------|-------------|
| feat | Commits that add, change or remove a feature of the API or UI |
| fix | Commits that fix a bug in the API or UI |
| refactor | Commits that rewrite or restructure code without altering API or UI behavior |
| perf | Refactor commits whose purpose is to improve performance |
| style | Commits that address code style (e.g., white-space, formatting, missing semi-colons) and do not affect application behavior |
| test | Commits that add missing tests to behaviour that already exists, correct existing tests, or add a unit's acceptance tests ahead of its behaviour. A developer's test for new or changed behaviour lands in that behaviour's own `feat` or `fix` commit, per `sds-testing/SKILL.md` |
| docs | Commits that exclusively affect documentation |
| build | Commits that affect build-related components such as build tools, dependencies, project version etc. |
| ops | Commits that affect operational aspects like infrastructure (IaC), deployment scripts, CI/CD pipelines, backups, monitoring, or recovery procedures |
| chore | Commits that change nothing a user, caller or operator can observe and fit no other type: the initial commit, or housekeeping such as ignore files |
| revert | Commits that undo an earlier commit — see **Reverts** below |

## Scope
Optional and provides additional contextual information.
- Allowed scopes vary and are typically defined by the specific project
- Do not use issue identifiers as scopes
- In a monorepo, a breaking commit's scope is the id of the release unit it breaks, per **Versioning** below

### Breaking Changes Indicator
A commit that introduces a breaking change MUST be marked by an `!` before the `:` in the subject line e.g. `feat(api)!: remove status endpoint`
- A breaking change MUST also carry a `BREAKING CHANGE:` footer stating what breaks. Its release note entry copies that text rather than paraphrasing it, per [release-notes](references/release-notes.md), so the footer is where the text has to be

## Description
The mandatory description contains a concise description of the change.
- Use the imperative, present tense: Instead of "changed" or "changes" use `"change"`
  - Think of `This commit will...` or `This commit should...`
- Do not capitalize the first letter
- Do not end the description with a period (.)
- In case of breaking changes also see breaking changes indicator

## Body
The body should include the motivation for the change and contrast this with previous behavior.
- The body is an optional part. Use the imperative, present tense: Instead of "changed" or "changes" use `"change"`

## Footer
The footer should contain the change identifier, issue references and information about breaking changes
- The footer is a mandatory part: every commit carries a `Change-Id:` trailer
- `Change-Id:` carries the identifier its release note entry is written under, e.g. `Change-Id: auth-service-20260904T170512-a3f9`, its timestamp in UTC+03:00
  - Mint it when writing the commit and copy it verbatim into the note, so an entry resolves to the commit that produced it
  - Mint it with this skill's script, `${CLAUDE_SKILL_DIR}/scripts/mint_change_id.py`, run with Python from inside the repository the commit belongs to, after staging the commit. In a repository holding one service it reads the software id from `.bioeksen/software-id` at the root and prints a fresh identifier. In a monorepo it works out which release units the staged changes affect, per **Release units** in [release-notes](references/release-notes.md): it mints with that unit's id when they affect exactly one, and otherwise with the monorepo's own id, printing after the identifier the `Affects:` and `Changes-Package:` trailers the commit carries. When a file it needs is missing, empty or malformed it exits non-zero rather than guess: ask for the id, write it there, and run the script again. Never compose an identifier or those trailers by hand, and never reuse one
  - See [release-notes](references/release-notes.md) for the identifier format
  - Exactly one `Change-Id:` per commit: one commit is one entry
  - Gerrit uses a `Change-Id:` trailer of its own, `I` followed by 40 hex digits. The two formats cannot share one trailer, so a repository reviewed through Gerrit MUST NOT install Gerrit's commit-msg hook alongside this convention
- A `feat` or `fix` commit that changes no test MUST carry a `Test-Exempt:` trailer naming the exemption it relies on, a value from the exemptions table in `sds-testing/SKILL.md`, e.g. `Test-Exempt: docs`
  - At most one per commit, in the final trailer paragraph beside `Change-Id:`. Any other commit carries none
  - The trailer makes the claim visible in review and checkable in CI; a commit that changes a test needs no trailer
- A `fix` commit SHOULD name each aggregator record of the failure it fixes with a `Fixes-Log:` trailer carrying the record's `recordId`, e.g. `Fixes-Log: 01J9Z4K7XQ2M8N`
  - One trailer per record, in the final trailer paragraph beside `Change-Id:`. Any other type carries none: only a fix resolves a failure
  - When the pull request carrying the commit is merged, the git service stores the commit's Change-Id on each record it names, and the aggregator deletes the record 30 days later, per `sds-logging/references/aggregator-api.md`. A record no fix names stays until its issue is closed, or its own window ends
- A commit minted with a monorepo's own id carries an `Affects:` trailer for each release unit it affects and a `Changes-Package:` trailer for each shared package it changes, e.g. `Affects: bio-inventory` and `Changes-Package: @bioeksen/ui`
  - In the final trailer paragraph beside `Change-Id:`, one per line, exactly as the script prints them. A commit minted with a unit's id carries neither, and so does every commit in a repository holding one service
  - They say which units the commit reached, and so which units' release notes list it, per **Release units** in [release-notes](references/release-notes.md)
- Optionally reference issue identifiers (e.g., Closes #123, Fixes JIRA-456)
- Breaking changes must start with the phrase `BREAKING CHANGE:`
  - For a single line description just add a space after `BREAKING CHANGE:`
  - For a multi line description add two new lines after `BREAKING CHANGE:`

## Reverts
`git revert` writes `Revert "<original subject>"`, which fails the format. Reword it before committing:

```
revert: <the reverted commit's description>

This reverts commit <sha>.

Change-Id: <a freshly minted identifier>
```

- The description is the reverted commit's own, verbatim, and the body names it by the hash git wrote
- The `Change-Id:` is new. A revert is a change of its own with its own release note entry, and reusing the original's identifier would make one identifier name two opposite changes
- A revert that undoes a released change callers depend on is breaking in its own right, and carries `!` and a `BREAKING CHANGE:` footer

## Merging
One commit is one release note entry, so a branch MUST reach the main branch with every commit's message and trailer intact:
- **Rebase-merge, or a merge commit**, keeps each commit as written. A merge commit itself carries no entry, per [release-notes](references/release-notes.md)
- **Squash-merge** replaces a branch's commits with one, and GitHub builds its message by concatenating theirs — several `Change-Id:` trailers in one commit, or none if the message is replaced. A squash-merged commit MUST be edited before merging into this format, with a description covering the whole branch, exactly one freshly minted `Change-Id:`, and, in a monorepo, the trailers the script prints for the branch's combined change

## Versioning
The next release's version follows from the commits it contains, as in SemVer:
- Any breaking change increments the major version
- Otherwise, any `feat` increments the minor version
- Otherwise — `fix` and every other type — increment the patch version
- Below `1.0.0` these shift down one place: a breaking change increments the minor version, everything else the patch version
- A new service or library starts at `0.1.0`: its first release is `0.1.0` whatever its commits, and its root commit is `chore: initial commit`
- In a monorepo, each release unit is versioned on its own, from the commits in its release range, per **Release units** in [release-notes](references/release-notes.md)
  - A commit's type applies to every unit it affects. A change that is a feature for one unit and only a refactor for another is two commits
  - A breaking commit names the one unit it breaks as its scope, e.g. `feat(bio-sdk)!: rename createLogger`. It is breaking for that unit alone, and every other unit it affects counts it by its type. So a change to a shared package's API that updates every caller in the same commit breaks no app: nothing outside the monorepo calls it. A unit that publishes packages, such as `bio-sdk`, is broken by a change to their API, and that commit names it
- Refer to [release-notes](references/release-notes.md) for more information on versioning and release notes.

## Rules
- Keep the subject concise.
- Describe the change, not the implementation process.
- Use a scope when it materially improves clarity.
- Do not include unrelated changes in one commit.
- Use BREAKING CHANGE when a change breaks compatibility.
- Do not fabricate issue or ticket references.