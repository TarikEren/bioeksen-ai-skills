---
name: sds-ci
description: BioEksen CI, runner and AI task conventions. Use when writing or changing a forge workflow, registering or configuring a runner, setting up deployment, or delegating a task to an AI model that pushes to the forge.
---

# CI, Runners and AI Tasks

Every workflow runs code, and the forge lets whoever writes a workflow choose
where it runs. A workflow file is read from the commit that triggered it, so
anyone able to push a branch, a person or a model working on a task, can
write a workflow that asks for any runner its repository can reach. These
rules decide which code runs where, and holding what, so that the answer does
not depend on who wrote the workflow.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

Paths such as `sds-logging/references/log-record.md` name a file in another
skill of this plugin, relative to the plugin's skills directory: the parent
of `${CLAUDE_SKILL_DIR}`, which is this skill's own directory.

## Runners

Three kinds of runner exist. They are told apart by where they run, what they
hold and what they are registered to, never by their labels:

| Runner | Host | Runs | Holds |
|--------|------|------|-------|
| `ci` | The AI workstation | Every job except AI task runs and deployment: builds, tests and checks on any branch | No secret beyond **Secrets** below |
| `ai` | The AI workstation | AI task runs, from the AI task repository's protected main branch, and nothing else | The bot account's token and the wrapper's app credential, on its host only, given to the wrapper and never to the model |
| `deploy` | The application server | Building and deploying an app's release, or publishing a library's, from a `v*` tag on a commit of a repository's protected main branch, and nothing else | The deployment and registry-write credentials, on its host only |

- The `deploy` runner MUST be registered to the deploy repository alone, and
  the `ai` runner to the AI task repository alone: never to an app
  repository, an organisation or the instance. No other runner is registered
  on the application server.
- No app repository contains a deployment workflow. When a release tag is
  pushed to an app's repository, the git service's integration, bio-softop,
  verifies the release, per **Releases and deployment** below, and dispatches
  the deploy repository's workflow, from that repository's own protected main
  branch, with the app's software id, the version and the commit. A merge to
  main deploys nothing.
- The deploy and AI task repositories' workflows are changed only by people,
  and their main branches are protected like every other.

A label is a request, not a boundary. A runner takes any job carrying its
labels from any repository it is registered to, so a `deploy` runner
registered to an app repository runs whatever a branch of that repository asks
it to, including a workflow written on that branch a minute earlier.
Registering it to a repository no app branch can write to is what puts it out
of reach, whatever a workflow says. The same holds for the `ai` runner, whose
credentials can push to every app repository's `ai/**` branches.

Everything the application server hosts, the forge, the databases and the
apps, is therefore out of reach of unreviewed code. The `ci` runner is where
unreviewed code is expected to run, and it is isolated for that.

## Isolating `ci` jobs

A `ci` job runs code nobody has reviewed yet: a person's feature branch, a
model's task branch, and the tests either of them wrote. Its job containers:

- MUST be created for one job and destroyed after it.
- MUST NOT reach the host's container engine, through a mounted socket or
  otherwise, and MUST NOT run privileged or on the host network.
- MUST have network egress limited to an allowlist: the forge, the package
  registries a build needs, and, for AI task runs, the model server.
  Everything else is refused, the application server's databases included.

A `ci` job's automatic token can write to its own repository's unprotected
branches. Nothing trusts an unprotected branch: a branch reaches main only
through review, so what the token can write is never acted on unreviewed.

- Release tags, `v*` per `sds-commit/references/release-notes.md`, MUST be
  protected tags that only people can create.

## Secrets

- Deployment credentials MUST exist only on the `deploy` runner's host, and
  the bot account's token and the wrapper's app credential only on the `ai`
  runner's host, each as that host's own configuration. None of them is
  stored as a forge secret.
- The only forge secret a workflow MAY be given is one that harms nothing
  when read: a read-only token for the package registry.
- A build that needs a registry token receives it as a build secret. It is
  never a build argument, a copied file or an environment variable in the
  image, all of which leave it in an image layer.

A forge secret is available to every workflow that runs from its repository's
own branches, a pull request's included. A secret stored there is readable by
any workflow a branch adds, which is exactly the workflow no reviewer has
seen. Kept on a runner's host, a credential is readable only by jobs that
runner takes, and only the one repository it is registered to can give it
one.

## Releases and deployment

A deployment is a release, as `sds-commit/references/release-notes.md`
defines one: a version, its release note, and its `v{version}` tag, created by
a person. Deploying releases rather than merges means everything running in
production has a version and a release note, and a merged fix reaches
production at a moment the estate can name.

- Every release is deployed, whatever it increments: patch, minor or major.
- Before dispatching, the git service's integration verifies that:
  - the tag points to a commit reachable from the repository's protected
    main branch;
  - `/release-notes/{version}.md` exists in that commit;
  - the version is exactly the one the commits since the previous `v*` tag
    imply, per **Versioning** in `sds-commit/SKILL.md`, including the shift
    below `1.0.0` and the first release at `0.1.0`;
  - the note's entry count equals `git log --no-merges {previous}..{tag}`.

  A release failing any check is not deployed. The refusal is logged as
  `JOB-4000`, its check in the structured tail, e.g. `reason=version-mismatch`,
  and the person who pushed the tag is notified.
- An app's pre-release tag, e.g. `v1.0.0-beta.1`, is verified but not
  deployed: no environment exists for it yet.
- A library's release is published, not deployed: the `deploy` runner builds
  the tagged commit and publishes that version to the package registry. A
  library's pre-release tag is published too, under the `next` dist-tag, so
  apps can try it; an app's main branch never pins one.
- A published version is never removed or overwritten. Apps pin exact
  versions, and their lockfiles would break. A bad version is superseded by a
  fix release.
- The release image is built by the `deploy` runner from the tagged commit and
  tagged with the version. A `ci` job never writes to the registry, so nothing
  built from an unreviewed branch can be deployed.
- Rolling back an app is deploying an earlier release's version again,
  dispatched by an operator. It creates no tag.
- A release's database migrations MUST leave the schema usable by the
  previous release, so that rolling back never needs a down-migration.

## Workflow definitions

- Workflow files live in `.forgejo/workflows/`, a repository's only workflow
  directory. They are written and changed only by people, in `ops` commits
  per `sds-commit/SKILL.md`, and reviewed like code.
- A repository MUST NOT contain `.gitea/workflows/` or `.github/workflows/`.
  The forge runs workflows from either when `.forgejo/workflows/` is absent,
  so a file added there would replace the reviewed ones.
- A repository's **protected paths** are `.forgejo/**`, `.gitea/**`,
  `.github/**`, `.bioeksen/**`, and every path its `/AGENTS.md` assigns to no
  role, `.claude/**` and `/AGENTS.md` itself among them. They are the workflow
  directories, the software id, and the rules the repository's roles and
  models work under.
- Every `ai/**` branch MUST be covered by a branch protection rule listing the
  protected paths as protected file patterns, so the forge refuses a push that
  changes one.
  - Write the patterns with `**`. The forge's glob treats `.` as a separator
    as well as `/`, so `.forgejo/workflows/*` does not match `ci.yml`.
  - Verify on the deployed version of the forge that the rule refuses a push
    that *creates* a branch, not only one that updates it. A defect in the
    forge family once let a newly created branch through.

This rule is the second layer, not the first. The push gate under **AI task
runs** refuses the same changes before they leave the workstation, and a
workflow change that slipped past both could reach only the `ci` runner,
which is isolated for unreviewed code.

## AI task runs

A task delegated to a model runs on the `ai` runner, as a workflow of the AI
task repository, whose code is the wrapper: the BioEksen-owned program that
prepares the run, starts the model and outlives it. The wrapper is reviewed
code, holds the run's credentials, and checks the target repository out. The
model runs in a **sandbox** container the wrapper starts, which follows every
rule in **Isolating `ci` jobs** and holds no credential at all. The wrapper
starts sandboxes through a container engine reserved for them, rootless where
the host allows; no sandbox can reach that engine.

- **Branch.** The model's work is pushed to `ai/{task-id}` and to no other
  ref. `{task-id}` MUST NOT match the error code format in
  `sds-logging/references/error-codes.md`, so that no tool reading either
  takes one for the other.
- **Dispatch.** A run is dispatched on the AI task repository's protected
  main branch, with the target repository and the task passed as inputs. A
  run, a revision included, therefore never executes a workflow from any
  branch a model wrote.
- **No credential for the model.** The model works on a copy of the checkout
  inside its sandbox. The push is made by the wrapper with the bot account's
  token, which is never mounted into the sandbox.
- **The push gate.** Before pushing, the wrapper refuses the run when any
  commit:
  - changes a path outside the task's allowed paths, or any protected path,
    per **Workflow definitions**;
  - lacks exactly one `Change-Id:` trailer carrying the repository's
    software id, minted per `sds-commit/SKILL.md`, whose script the sandbox
    image therefore includes, with Python to run it;
  - would be pushed anywhere but `ai/{task-id}`, or would need a force push.

  A refused run ends as `JOB-5000` with its rule in the structured tail,
  e.g. `reason=protected-path`, per **Domain failures** in
  `sds-logging/references/code-prefixes.md`. Nothing is pushed.
- **The bot account** can push to `ai/**` and open pull requests. It is never
  an administrator and never a reviewer, and it cannot approve.
- **Merging** an AI pull request takes a person's approval, like any other
  pull request.
- **Transcripts**, the model's conversation, its tool calls and the files it
  read, are stored as the run's artifacts. They are never log records: they
  are unbounded and carry code, which `sds-logging/references/log-record.md`
  keeps out of the aggregator.

## Instructions are not controls

Skills, prompts and the scripts a model is told to use shape what it tries to
do. They do not bound what it can do. A model misreads an instruction, and
text in the repository it works on, a README, a comment or an issue, can
instruct it otherwise through the same channel a skill arrives by.

Every restriction a model is expected to follow MUST also be enforced by
something the model cannot change: the push gate, branch protection, runner
registration, the egress allowlist. A restriction that exists only in a skill
is a suggestion. It SHOULD still be written there, because a model told the
rule wastes fewer runs against the gate that enforces it.

## Verifying

After a runner, a protection rule, an egress rule or the push gate changes,
each of these MUST be attempted and seen refused:

| Attempt | Refused by |
|---------|-----------|
| A workflow on an app branch asking for the `deploy` or `ai` runner's labels | Runner registration: no runner takes the job |
| The model's sandbox reading the bot token or the wrapper's credential | Neither is mounted into the sandbox |
| A push that creates `ai/{task-id}` with a change under `.forgejo/workflows/` | The push gate, and the branch protection rule behind it |
| A push to `ai/{task-id}` adding `.gitea/workflows/` or `.github/workflows/`, or changing `.claude/hooks/` or `/AGENTS.md` | The push gate, and the branch protection rule behind it |
| A `ci` job connecting to a database port on the application server | The egress allowlist |
| A `ci` job connecting to an arbitrary internet host | The egress allowlist |
| A `ci` job publishing a package or pushing to another repository | Its credentials: the automatic token and a read-only registry token |
| The bot account pushing to main, or approving a pull request | Branch protection and the bot's permissions |
| A merge to main with no release tag reaching production | Deployment is dispatched only for a verified release tag |
| A tag whose version disagrees with its commits being deployed | The release verification |

A check that could not be run is reported as not run, never as passed, per
**Keeping the suite honest** in `sds-testing/SKILL.md`.
