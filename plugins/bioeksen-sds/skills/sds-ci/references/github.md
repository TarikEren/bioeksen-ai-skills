# GitHub

How a project whose `.bioeksen/git-provider` is `github` carries out
`SKILL.md`. Where a feature depends on the GitHub plan, this says so. A rule
the plan cannot enforce is recorded as a gap in the project's notes, because
the push gate is then its only layer.

## The CI definition

- Workflows live under `.github/workflows/`. The kit's `bioeksen.yml` is
  copied there at initialization, per `sds-project/SKILL.md`. The protected
  paths include `.github/**`.
- Every workflow sets `permissions: contents: read` at its top, so the
  automatic `GITHUB_TOKEN` reads its repository and writes nothing. A job
  that needs more names it in its own `permissions`; no `ci` job does.
- Actions are pinned to a full commit, the release in a comment.
- A pull request's commits are `github.event.pull_request.base.sha..head.sha`.
  A push to main's are `github.event.before..github.sha`, unless `before` is
  all zeros, which is a new branch.

## Runners

- Self-hosted runners are registered to a repository: the `deploy` runner to
  the deploy repository, the `ai` runner to the AI task repository. Never to
  the organisation or the enterprise, where every repository's workflows can
  request them.
- A job asks for a runner by its labels, `runs-on: [self-hosted, ci]`. The
  labels choose among the runners the repository can reach; registration
  decides which those are.
- GitHub-hosted runners are not `ci` runners: their egress cannot be held to
  the allowlist **Isolating `ci` jobs** requires.

## Secrets

- A repository secret reaches every workflow run from the repository's own
  branches, a pull request's included; a workflow run for a fork's pull
  request gets none.
- `BIOEKSEN_SDS_READ_TOKEN` is a fine-grained token with read-only access to
  the contents of `bioeksen-ai-skills`, and to nothing else.

## Protected paths, branches and tags

- **A push ruleset** targeting `ai/**` restricts file paths, so GitHub refuses
  a push that changes a protected path. Push rulesets depend on the plan;
  where it has none, record the gap.
- **A branch ruleset** on `main` requires a pull request, a person's
  approval and the `ci` check, and refuses force pushes and deletion. The
  bot account is not in its bypass list.
- **A tag ruleset** on `v*` and `*/v*` lets only the people in its bypass
  list create a matching tag; neither the bot account nor the automatic token
  can.
- Verify the push ruleset with a push that *creates* an `ai/` branch, per
  **Verifying** in `SKILL.md`.

## Pull requests

- Allow rebase merges or merge commits. A squash merge builds its message by
  concatenating the commits', so it holds every commit's `Change-Id:`; edit
  it as **Merging** in `sds-commit/SKILL.md` requires.
- A heading's anchor is its text in lower case, punctuation removed and each
  space a hyphen: `### R-001 — A defect` is `#r-001--a-defect`.
