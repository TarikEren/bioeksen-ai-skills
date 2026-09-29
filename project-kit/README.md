# Project kit

What a project generator takes from this repository so that every new
BioEksen service starts on the `bioeksen-sds` conventions, and what each
generated project runs to stay on them.

## What the generator does

1. **Asks for the software id** and writes it to `.bioeksen/software-id`. The
   id is supplied — by the project, or by the id-issuing service once one
   exists — and never derived from the project's name; see
   `plugins/bioeksen-sds/skills/sds-logging/references/log-record.md`. A
   generator that cannot get one leaves the file out, and everything that
   needs the id then asks for it.
2. **Copies `template/`** into the new project:

   | File | Does |
   |------|------|
   | `.claude/settings.json` | Registers this marketplace and enables `bioeksen-sds`, pinned to a release, so the skills load for anyone who trusts the project folder |
   | `CLAUDE.md` | Tells an assistant where the id lives, which skills govern the project, and which checks to run. The project appends its own notes |
   | `.github/workflows/bioeksen.yml` | Runs the commit and release note checks, with a marked place for the conformance check |
   | `.githooks/commit-msg` | Checks each commit message locally, and mints its `Change-Id:` |

3. **Adds `.bioeksen-sds/` to the project's `.gitignore`.** That is where CI,
   and a developer who wants the local hook, check out this repository.

## What it never copies

The skills. A copied skill is a second copy of a contract, and it drifts from
the first the moment either changes — the failure this repository exists to
prevent. A project references the plugin through `.claude/settings.json`
instead.

Nor this repository's own `CLAUDE.md`, `.gitattributes` or
`scripts/check_invariants.py`. They describe editing the specifications, not
building a service.

## Pinning

`.claude/settings.json` and the workflow both name one release of this
repository, as `ref` and as `BIOEKSEN_SDS_REF`. The skills an assistant reads
and the checks CI runs then come from the same version, and a contract change
reaches a project when someone bumps both — never silently from `main`.
Invariant 10 in `scripts/check_invariants.py` keeps the template pinned to the
release it ships in.

Claude Code registers the marketplace once a person accepts the workspace trust
dialog for the project folder. The plugin is listed by a relative path, so it
then loads without a separate install.

## Private repository access

If this repository is private:

- A developer needs git credentials Claude Code can use without prompting, as
  it has no token of its own and a `GITHUB_TOKEN` in the environment does not
  authenticate it by itself. `gh auth login` followed by `gh auth setup-git`
  provides them.
- The workflow's second checkout needs a token that can read this repository,
  as the secret `BIOEKSEN_SDS_TOKEN`, with its commented `token:` line
  enabled.

## The tools

| Tool | Does | Needs |
|------|------|-------|
| `tools/change_id.py` | Prints a new `Change-Id` from `.bioeksen/software-id` | The standard library |
| `tools/commit_msg.py --hook FILE` | Checks one message as a commit-msg hook, minting a missing `Change-Id` | The standard library |
| `tools/commit_msg.py --range A..B` | Checks every non-merge commit in a range | The standard library |
| `tools/check_release_note.py VERSION` | Checks a release note against its range, after its commit and before the tag | The standard library |
| `conformance/check_service.py --base-url URL` | Checks a running instance's standard endpoints against `openapi.yaml` | `requirements.txt` |
| `conformance/check_service.py --self-test` | Checks the fixtures against the schemas, and every check against `stub_service.py` | `requirements.txt` |

This repository runs every one of them against itself in CI.
