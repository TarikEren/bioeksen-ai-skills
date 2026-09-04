---
name: sds-commit
description: BioEksen conventional commit format. Use when writing or amending a commit message, reviewing commit history, or deciding a release version from a set of commits.
---

# Conventional Commits
Each commit SHOULD abide by the following format:

```
<type>(<scope>): <description>

[empty line]
<body>
[empty line]
<footer>
```

## Type

| Type | Definition |
|------|-------------|
| feat | Commits that add, adjust or remove a feature to/of/from the API or UI |
| fix | Commits that fix an API or UI bug of a preceded `feat` commit |
| refactor | Commits that rewrite or restructure code without altering API or UI behavior |
| perf | Commits are special type of refactor commits that specifically improve performance |
| style | Commits that address code style (e.g., white-space, formatting, missing semi-colons) and do not affect application behavior | 
| test | Commits that add missing tests or correct existing ones |
| docs | Commits that exclusively affect documentation |
| build | Commits that affect build-related components such as build tools, dependencies, project version etc. |
| ops | Commits that affect operational aspects like infrastructure (IaC), deployment scripts, CI/CD pipelines, backups, monitoring, or recovery procedures |
| chore | Commits that represent tasks like initial commit, modifying etc. |

## Scope
Optional and provides additional contextual information.
- Allowed scopes vary and are typically defined by the specific project
- Do not use issue identifiers as scopes

### Breaking Changes Indicator
A commit that introduce breaking changes must be indicated by an `!` before the `:` in the subject line e.g. `feat(api)!: remove status endpoint`
- Breaking changes should be described in the commit footer section, if the commit description isn't sufficiently informative

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
The footer should contain the change identifier, issue references and informations about `Breaking Changes`
- The footer is a mandatory part: every commit carries a `Change-Id:` trailer
- `Change-Id:` carries the identifier its release note entry is written under, e.g. `Change-Id: auth-service-20260904T140512Z-a3f9`
  - Mint it when writing the commit and copy it verbatim into the note, so an entry resolves to the commit that produced it
  - See [release-notes](references/release-notes.md) for the identifier format
- Optionally reference issue identifiers (e.g., Closes #123, Fixes JIRA-456)
- Breaking changes must start with the phrase `BREAKING CHANGE:`
  - For a single line description just add a space after `BREAKING CHANGE:`
  - For a multi line description add two new lines after `BREAKING CHANGE:`

## Versioning
If your next release contains commit with...
- Breaking Changes incremented the major version
- API relevant changes (feat or fix) incremented the minor version
- Else increment the patch version
- Below `1.0.0` these shift down one place: a breaking change increments the minor version, everything else the patch version
- Refer to [release-notes](references/release-notes.md) for more information on versioning and release notes.

## Rules
- Keep the subject concise.
- Describe the change, not the implementation process.
- Use a scope when it materially improves clarity.
- Do not include unrelated changes in one commit.
- Use BREAKING CHANGE when a change breaks compatibility.
- Do not fabricate issue or ticket references.