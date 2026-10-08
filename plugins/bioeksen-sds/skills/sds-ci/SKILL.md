---
name: sds-ci
description: BioEksen CI, runner, delivery and AI task conventions. Use when writing, changing or proposing a forge workflow, registering or configuring a runner, setting up deployment, changing a container image or a local-development compose file, preparing a release, finding out why a run failed, or delegating a task to an AI model that pushes to the forge.
---

# CI, Runners and AI Tasks

Every workflow runs code, and the forge lets whoever writes a workflow choose
where it runs. A workflow file is read from the commit that triggered it, so
anyone able to push a branch, a person or a model working on a task, can
write a workflow that asks for any runner its repository can reach. These
rules decide which code runs where, and holding what, so that the answer does
not depend on who wrote the workflow.

The pipeline is only worth trusting if it runs the same checks a developer
runs and cannot be talked out of a failure. So: **the pipeline runs the
project's own scripts**, and **a gate is never weakened to get a run green**.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

- `references/nextjs.md` — how an app scaffolded from the nextjs template
  carries this skill out: its toolchain checks, its branches, its image and
  its migration step.

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
| `deploy` | The application server | Building and deploying an app's release, or publishing a library's, from a release tag (`v*`, or `{software-id}/v*` in a monorepo) on a commit of a repository's protected main branch, and nothing else | The deployment and registry-write credentials, on its host only |

- The `deploy` runner MUST be registered to the deploy repository alone, and
  the `ai` runner to the AI task repository alone: never to an app
  repository, an organisation or the instance. No other runner is registered
  on the application server.
- No app repository contains a deployment workflow. When a release tag is
  pushed, `v*` in a repository holding one service and `{software-id}/v*` in a
  monorepo, the git service's integration, bio-softop, verifies the release,
  per **Releases and deployment** below, and dispatches the deploy
  repository's workflow, from that repository's own protected main branch,
  with the released unit's software id, the version and the commit. A merge
  to main deploys nothing.
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
- MUST run build tools with their telemetry off, and MUST NOT write to a
  build cache shared across jobs. A shared cache, where one is added, may be
  read by `ci` jobs, and a release build never reads it.

A cache entry is trusted by whoever reads it, and a `ci` job runs code nobody
has reviewed. Written from a model's task branch, an entry could record a
passing result under the very key the main branch's build computes next.

A `ci` job's automatic token can write to its own repository's unprotected
branches. Nothing trusts an unprotected branch: a branch reaches main only
through review, so what the token can write is never acted on unreviewed.

- Release tags, `v*`, or `{software-id}/v*` in a monorepo, per
  `sds-commit/references/release-notes.md`, MUST be protected tags that only
  people can create.

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
defines one: a version, its release note, and its tag, `v{version}`, or
`{software-id}/v{version}` for a release unit of a monorepo, created by a
person. In a monorepo each unit is released, and deployed, on its own. Deploying releases rather than merges means everything running in
production has a version and a release note, and a merged fix reaches
production at a moment the estate can name.

- Every release is deployed, whatever it increments: patch, minor or major.
- Before dispatching, the git service's integration verifies that:
  - the tag points to a commit reachable from the repository's protected
    main branch;
  - the release's note exists in that commit, at `/release-notes/{version}.md`,
    or in a monorepo at `{unit}/release-notes/{version}.md`;
  - the version is exactly the one the commits since the previous tag of the
    same kind imply, per **Versioning** in `sds-commit/SKILL.md`, including the
    shift below `1.0.0` and the first release at `0.1.0`. In a monorepo those
    are the commits of the unit's release range, per **Release units** in
    `sds-commit/references/release-notes.md`;
  - the note's entry count equals the number of commits in that range,
    `git log --no-merges {previous}..{tag}` in a repository holding one
    service;
  - once an aggregator runs, it accepts every error code the release's build
    contains, so that no record the release writes is refused and lost.

  A release failing any check is not deployed. The refusal is logged as
  `JOB-4000`, its check in the structured tail, e.g. `reason=version-mismatch`,
  and the person who pushed the tag is notified.
- An app's pre-release tag, e.g. `v1.0.0-beta.1`, is verified but not
  deployed: no environment exists for it yet.
- A library's release is published, not deployed: the `deploy` runner builds
  the tagged commit and publishes that version to the package registry. A
  unit that holds several packages publishes all of them together, each at
  the tag's version. A
  library's pre-release tag is published too, under the `next` dist-tag, so
  apps can try it; an app's main branch never pins one.
- A published version is never removed or overwritten. Apps pin exact
  versions, and their lockfiles would break. A bad version is superseded by a
  fix release.
- The release image is built by the `deploy` runner from the tagged commit and
  tagged with the version. A `ci` job never writes to the registry, so nothing
  built from an unreviewed branch can be deployed. In a monorepo, each
  deployable package of the unit gets its own image, built from the unit's
  closure alone, with Turborepo by `turbo prune <package> --docker`, so it
  holds nothing of the other units.
- A deployment runs the release's migrations first, from the tagged commit, so
  a failed migration stops it with the running release untouched. It then
  moves the app to the new image, and waits for `GET /api/health/ready` to
  report `ok` within the app's startup budget.
- Rolling back an app is deploying an earlier release's version again,
  dispatched by an operator. It creates no tag.
- A release's database migrations MUST leave the schema usable by the
  previous release, so that rolling back never needs a down-migration.

### Preparing a release

- **The version is derived from the commits**, as `sds-commit` says, never
  picked by hand.
- **Every release has its note**, at the path and in the format
  `sds-commit/references/release-notes.md` gives it.
- **A person creates the release tag**, and bio-softop verifies and deploys
  it, as above. A role or a model prepares the version and the note;
  it never tags, publishes or deploys.

## Workflow definitions

- Workflow files live in `.forgejo/workflows/`, a repository's only workflow
  directory. They are written and changed only by people, in `ops` commits
  per `sds-commit/SKILL.md`, and reviewed like code.
- A repository MUST NOT contain `.gitea/workflows/` or `.github/workflows/`.
  The forge runs workflows from either when `.forgejo/workflows/` is absent,
  so a file added there would replace the reviewed ones.
- A repository's **protected paths** are `.forgejo/**`, `.gitea/**`,
  `.github/**`, `**/.bioeksen/**`, every AGENTS.md and CLAUDE.md file, and
  every path an AGENTS.md assigns to no role, `.claude/**` among them. They
  are the workflow directories, the software ids, and the rules the
  repository's roles and models work under. In a monorepo they also include
  the root build files, the shared packages and the tooling, `packages/**`
  and `tooling/**` in `bio-software`: a change there reaches every unit at
  once.
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
which is isolated for unreviewed code. In a monorepo a branch rule cannot know
which unit a task is for, so the push gate alone refuses a change to another
unit.

## The jobs

Read first, before proposing a change to a workflow:

1. **The project's delivery conventions, and its scripts**: which checks
   exist and what each one runs.
2. **The workflows, the image definition and any local-development compose
   file.** Propose changes in their own style.
3. **`sds-testing/SKILL.md`, Running the suites**: the order the test tiers
   run in, and **Test databases**: how a suite that creates or resets a
   database is guarded.
4. **`sds-commit/SKILL.md`**: how a version is derived from the commits,
   and the release-notes format.

The workflow is the user's. You propose a change to it in your report, as the
exact YAML and the reason; you never edit `.forgejo/`.

- **Each job runs a script the project already has**, the same one a developer
  runs locally. If a check has no script, the script is added first, by the
  role that owns it, and the job calls it.
- **Tiers run in `sds-testing`'s order**: types and lint, then unit and
  component tests, then the build; integration and end-to-end tests against
  disposable database services after that. A cheap tier fails before an
  expensive one starts.
- **The commits job** runs the `bioeksen-sds` project kit's checks on every
  pull request: one `Change-Id` per commit, carrying the id `sds-commit` gives
  it, and in a monorepo exactly the `Affects:` and `Changes-Package:` trailers
  its paths give it; and a test or a `Test-Exempt:` trailer on every `feat`
  and `fix` (`sds-testing`). It runs the CI image's copy of the kit, under
  `/opt/bioeksen-sds/{tag}/`, at the release `.claude/settings.json` pins; the
  two versions move together. The job's token reads only this repository, so
  the kit is never checked out.
- **The pinned release must be in the image.** A job that cannot find it
  there reports not run and fails, per **Keeping the suite honest** in
  `sds-testing/SKILL.md`. A newer release existing never fails a job: the pin
  moves when a person moves it. A task whose result depends on the pinned
  release lists the pin file among its cache inputs, so moving the pin runs
  it again.
- **In a monorepo, a job runs only what a change affects**, and a change to a
  root build file affects every unit. One final job, named `ci`, depends on
  every other job, runs whether they ran or were skipped, and fails if any
  failed. It is the main branch's one required check, so the check exists on
  every pull request whatever was skipped.
- **Installs follow the lockfile.**
- **The toolchain comes from the estate's CI image.** The image is built by
  the `deploy` runner and pinned by digest. It carries the runtime, the
  package manager and the monorepo's build tool at the versions the
  repository pins, the browsers and engines the tests need, Python for the
  `sds-*` scripts, and each `bioeksen-sds` release in use. A job checks that
  each tool is the version the project pins; it never sets one up, and never
  downloads a browser, a system package or a tool. A step that needs more than
  the egress allows (**Isolating `ci` jobs**) fails there: name what it needs
  in your report, for the image.
- **Generated code is generated in the job.**
- **Databases are service containers.** The job runs in a container, so it
  reaches each by its service name. The suite's own guard still decides
  whether it may empty one.
- **Every job has a timeout**, and artifacts that explain a failure (test
  reports, traces) are kept with a retention limit.
- **Actions are pinned to full commits**, with the release in a comment, and
  resolve through the forge's own mirror. Untrusted input (branch names, pull
  request titles, commit messages) reaches a `run:` step only through an
  environment variable.

### Gating the test-first loop

The acceptance tests of a unit are merged into its branch before the code
that makes them pass, per **Acceptance tests** in `sds-testing/SKILL.md`. So:

- **A unit's branch** runs every suite on every push and pull request. Red
  acceptance tests there are expected until the unit's iteration ends, so they
  report without blocking merges inside the unit.
- **`main`** requires every suite green, the acceptance suite included.
  Merging a unit into `main` is the loop's last gate.
- **CI runs the acceptance suite through the runners directly** and keeps
  their reports as artifacts. The results-only rule is for the role sessions,
  not for CI.

## The container image

- **Multi-stage builds**: dependencies, build and runtime stages, with only
  the runtime stage's files in the final image.
- **A pinned base image**, by digest, with the runtime version the project
  pins.
- **Run as a non-root user.**
- **The image carries only the files the server needs.**
- **A `.dockerignore`** that keeps out `.git`, installed dependencies, build
  output, `.env*` files and local data.
- **No secrets in the image**: not in a layer, a build argument or a copied
  `.env` file. They arrive at run time; a build that needs the registry token
  receives it as a build secret, per **Secrets**.
- **No migrations in the image.** They run from the release's tagged commit,
  as a step of its deployment.
- **Compose files are for local development only.** Production compose
  definitions live in the deploy repository.

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
  main branch, with the target repository, in a monorepo the task's release
  unit, and the task passed as inputs. A
  run, a revision included, therefore never executes a workflow from any
  branch a model wrote.
- **No credential for the model.** The model works on a copy of the checkout
  inside its sandbox. In a monorepo the copy holds only the task's unit and
  that unit's closure, with Turborepo the output of `turbo prune`, less the
  role's can't-read paths, so the model sees nothing else of the repository. The push is made by the wrapper with the bot account's
  token, which is never mounted into the sandbox.
- **The push gate.** Before pushing, the wrapper refuses the run when any
  commit:
  - changes a path outside the task's allowed paths, or any protected path,
    per **Workflow definitions**;
  - in a monorepo, changes a path outside the task's release unit;
  - lacks exactly one `Change-Id:` trailer carrying the id `sds-commit` gives
    it, the task's unit's in a monorepo, minted per `sds-commit/SKILL.md`,
    whose script the sandbox image therefore includes, with Python to run it;
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
| A push to `ai/{task-id}` changing a shared package, the tooling, a root build file or another unit, in a monorepo | The push gate |
| A unit's release whose version ignores a breaking commit that names the unit as its scope | The release verification: the range is the unit's own |
| A `ci` job writing to a build cache shared across jobs | The cache's credentials: `ci` jobs can at most read it |

A check that could not be run is reported as not run, never as passed, per
**Keeping the suite honest** in `sds-testing/SKILL.md`.

## Reading a failed run

1. **Read the failure, not the summary**: the failed job's log and its
   artifacts, from the forge's run page, as the user gives them to you.
2. **Classify it:**
   - **Code:** the change is wrong. It goes to the developer who owns it.
   - **Test:** a test is wrong, or proves a defect. It goes to the tester.
   - **Flaky:** it passes on a re-run of the same commit. It is still a
     finding, and goes to whoever owns the test, with every failure you saw.
   - **Commits:** a commit lacks its `Change-Id` or its test. It goes to the
     role that made the commit.
   - **Infrastructure:** the runner, the image, a service or the registry.
     It goes to the user.
   - **Configuration:** the Dockerfile or a compose file is wrong, which you
     fix; or the workflow is, which you propose.
3. **Reproduce it locally** with the same script, where you can.

## Never

- Edit a workflow directory, or add a workflow anywhere (**Workflow
  definitions**).
- Skip, disable or delete a check, or mark a gate `continue-on-error`, to get
  a run green.
- Add retries, longer timeouts or sleeps to hide a flaky test.
- Lower a coverage or quality threshold without the task saying so.
- Print, create or ask for a secret, or propose one beyond what **Secrets**
  allows.
- Push, tag, re-run, cancel, merge or deploy, or change branch protection or
  required checks.

## Before handing back

- The scripts a proposed job runs exist, and pass locally, or each one that
  cannot run locally is named with the reason.
- The Docker image builds, if you changed it and Docker is available.
- A proposed workflow change is in the report as the exact YAML, its actions
  pinned to full commits.
- The report names the gates, what each one runs, and anything you could not
  check.
