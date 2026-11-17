# GitLab

How a project whose `.bioeksen/git-provider` is `gitlab` carries out
`SKILL.md`. A pull request is a merge request here, and a workflow a
pipeline. Where a feature depends on the GitLab tier, this says so. A rule the
tier cannot enforce is recorded as a gap in the project's notes, because the
push gate is then its only layer.

## The CI definition

- The pipeline is `.gitlab-ci.yml` at the root, and the files it includes
  live under `.gitlab/`. The kit's `.gitlab-ci.yml` is copied at
  initialization, per `sds-project/SKILL.md`. The protected paths include
  `.gitlab-ci.yml` and `.gitlab/**`, and the project's CI configuration path
  stays at its default, so no other file becomes the pipeline.
- Includes, components and images are pinned to a commit or a digest.
- Clones are shallow by default. A job that reads history, as the kit's
  commit checks do, sets `GIT_DEPTH: "0"`.
- A merge request's commits are
  `CI_MERGE_REQUEST_DIFF_BASE_SHA..CI_COMMIT_SHA`, in a pipeline whose
  `CI_PIPELINE_SOURCE` is `merge_request_event`. A push to main's are
  `CI_COMMIT_BEFORE_SHA..CI_COMMIT_SHA`, unless the first is all zeros.

## Runners

- Project runners: the `deploy` runner is registered to the deploy project,
  the `ai` runner to the AI task project. Never a group or an instance
  runner, which every project in its scope can request.
- The `deploy` and `ai` runners run protected branches and tags only, so a
  job from an unprotected branch never reaches them, even in their project.
- A job asks for a runner by `tags: [ci]`. Tags choose among the runners the
  project can reach; registration decides which those are.
- Shared runners are not `ci` runners: their egress cannot be held to the
  allowlist **Isolating `ci` jobs** requires.

## The job token

`CI_JOB_TOKEN` reads its own project, and cannot push to it. Its allowlist
names no other project, so a job reaches nothing else with it.

## Secrets

- A CI/CD variable marked protected reaches only the pipelines of protected
  branches and tags; any other reaches every pipeline, a merge request's
  included.
- `BIOEKSEN_SDS_READ_TOKEN` and the registry's read-only token are masked and
  unprotected, because every `ci` job needs them and they harm nothing when
  read. The kit's repository is on GitHub, so `BIOEKSEN_SDS_READ_TOKEN` is a
  GitHub fine-grained token, read-only on `bioeksen-ai-skills`.

## Protected paths, branches and tags

- GitLab has no rule that refuses a push to one branch by the paths it
  changes. The second layer is `.gitlab/CODEOWNERS`, naming people for every
  protected path, with code owner approval required on `main`: such a change
  reaches `main` only with a person's approval. Code owner approval depends on
  the tier; where it has none, record the gap.
- `main` is a protected branch: nobody pushes to it, people merge into it,
  its pipeline must succeed, and force pushes are refused.
- `v*` and `*/v*` are protected tags that only people may create.
- Verify the code owner approval with a merge request from a newly created
  `ai/` branch, per **Verifying** in `SKILL.md`.

## Merge requests

- A squash merge writes its message from the project's squash template, by
  default the merge request's title, which carries no `Change-Id:`. Turn
  squashing off, or edit the message as **Merging** in `sds-commit/SKILL.md`
  requires.
- A heading's anchor is its text in lower case, punctuation removed, each
  space a hyphen, and repeated hyphens made one: `### R-001 — A defect` is
  `#r-001-a-defect`.
