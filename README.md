# BioEksen AI Skills

Shared skills for apps built by BioEksen Ar-Ge Teknolojileri A.Ş.,
written to be loaded by coding assistants as well as read by people.

Everything ships as one plugin, [`bioeksen-sds`](plugins/bioeksen-sds/). Each
skill is a directory under `plugins/bioeksen-sds/skills/` with a `SKILL.md` entry
point and, where the detail warrants it, a `references/` folder. It holds three
kinds of skill:

- **The contract**, what two services must agree on: `sds-api-design`,
  `sds-auth`, `sds-logging` and `sds-commit`.
- **The shared practice**, how every BioEksen codebase is built whatever its
  stack: `sds-config`, `sds-testing`, `sds-database`, `sds-reviewing` and
  `sds-ci`. `sds-testing` is here because its contract tests are how two
  services know they keep the agreements, and test-first is what keeps those
  tests able to fail. `sds-config` is here because an app that reports ready on
  a configuration it cannot use breaks the promise every load balancer relies
  on, and a secret leaked from one app's configuration is the whole estate's
  incident. The others are here because a schema, a review or a pipeline that
  each codebase invents for itself is one more place for the estate to drift.
- **The stack skills**, how a Next.js app carries the rest out:
  `sds-nextjs-backend` and `sds-nextjs-frontend`. Every other skill outranks
  them, and neither is ever the source of a shared rule. A generic skill's own
  Next.js specifics sit in its `references/nextjs.md`, written for apps
  scaffolded from the nextjs template.

## Licence

Proprietary. Copyright (c) 2026 BioEksen Ar-Ge Teknolojileri A.Ş., all rights
reserved — see [LICENSE](LICENSE). The repository is publicly readable, which
is not a grant of permission to use it; the installation steps below are for
BioEksen personnel and authorised parties.

## Skills

| Skill | Covers |
|-------|--------|
| [`sds-api-design`](plugins/bioeksen-sds/skills/sds-api-design/) | HTTP API conventions, both sides of a call: the standard health and admin endpoints, response envelopes, error shape, pagination and status codes — and, for a caller, deadlines, timeouts, retries, circuit breaking and idempotency |
| [`sds-auth`](plugins/bioeksen-sds/skills/sds-auth/) | Who may call what: operator and app credentials, how they are presented and validated |
| [`sds-logging`](plugins/bioeksen-sds/skills/sds-logging/) | Log records, severities and types, the error code registry, the log aggregator API |
| [`sds-config`](plugins/bioeksen-sds/skills/sds-config/) | Configuration: one validated module, checked before the app reports ready, every value declared, secrets kept out of logs, commits and clients |
| [`sds-commit`](plugins/bioeksen-sds/skills/sds-commit/) | Conventional commit format and the release version it implies |
| [`sds-planning`](plugins/bioeksen-sds/skills/sds-planning/) | Specifications and build planning: decisions with their status, owner and open question, build items with numbered acceptance criteria that every test cites, a build order of stages with checkable exit criteria, the stage plan, and a checker for the set and the tests' citations |
| [`sds-testing`](plugins/bioeksen-sds/skills/sds-testing/) | Test-first development: no behaviour change without a test that failed first, acceptance tests written ahead of the code and blind to it, how tests are written and run, and the contract tests every convention above requires |
| [`sds-database`](plugins/bioeksen-sds/skills/sds-database/) | Schemas and migrations: one source of truth, constraints that enforce the specification, forward-only migrations safe on a live database, transactions, parameterised and indexed queries, and disposable databases only |
| [`sds-reviewing`](plugins/bioeksen-sds/skills/sds-reviewing/) | Reviewing a change and recording the review: an independent reviewer's passes in priority order, every finding verified before it is reported, and a record in which no finding is lost |
| [`sds-nextjs-backend`](plugins/bioeksen-sds/skills/sds-nextjs-backend/) | Server code in a Next.js App Router app in TypeScript: route handlers, server actions, services and repositories, validation at every boundary, authorisation, and the TypeScript references behind them |
| [`sds-nextjs-frontend`](plugins/bioeksen-sds/skills/sds-nextjs-frontend/) | UI in a Next.js App Router app styled with HeroUI v3 and Tailwind CSS v4: the server/client trust boundary, the palette and its contrast, copy from dictionaries, forms, tables and icons |
| [`sds-ci`](plugins/bioeksen-sds/skills/sds-ci/) | CI, runners and AI tasks: where workflows live and who changes them, which runner runs what and holds which secret, how a release is verified and deployed, how a model's work is kept to its branch, what the jobs and the image hold, and how a failed run is read |

## How they fit together

```
sds-api-design ──── error envelope carries a code ────┐
      │                                               │
      │ standard endpoints require a credential       │
      ▼                                               ▼
  sds-auth ──── auth outcomes map to AUTH-/PERM- ──► sds-logging
                                                   (code registry,
                                                    log records)

sds-config ─── every value validated before the app reports ready, as CFG- codes
sds-testing ── a contract test for each rule above, written before the code
sds-commit ─── the test lands in its feat or fix commit, or the commit names
               its exemption
sds-database ─ constraints that hold the specification, and migrations that
               lose nothing
sds-reviewing ─ every change read by someone who did not write it, and every
                finding kept
sds-ci ─────── which runner runs what, and a release verified before it deploys
sds-nextjs-* ─ how a Next.js app carries all of the above out
```

Skills cross-reference each other by paths relative to
`plugins/bioeksen-sds/skills/`, the root they are installed under — so a link
written as `sds-logging/references/log-record.md` resolves the same way whether
the plugin is installed or the repository is being read directly.

- **Error codes** — `sds-logging/references/code-prefixes.md`. The closed list
  of all 44 codes, mirrored as an enforced enum in the OpenAPI schema.
- **Log record shape** — `sds-logging/references/log-record.md`.
- **API response and error envelopes** — `sds-api-design/references/openapi.yaml`
  is normative; the markdown beside it is the rationale.
- **The aggregator's own endpoints** — `sds-logging/references/aggregator-api.yaml`,
  normative on the same terms. It references the schemas above rather than
  copying them, so the two cannot drift apart.
- **Calling another service** — `sds-api-design/references/service-calls.md`.
  What a caller does when a call is slow, fails, or must not be repeated.

## Conventions used in these documents

- MUST, SHOULD and MAY carry their RFC 2119 meanings.
- Each fact is stated in exactly one file; others link to it. Where a fact is
  restated for readability, the restating document names the normative one.
- Where a machine-checkable artifact exists, it is normative and the prose is
  explanatory.

`scripts/check_invariants.py` enforces the cross-file invariants these
conventions depend on, and runs in CI on every push and pull request.

## Installation

Run:
```bash
/plugin marketplace add TarikEren/bioeksen-ai-skills
/plugin install bioeksen-sds@bioeksen-skills
```
in your claude code instance or using the gui add `https://github.com/TarikEren/bioeksen-ai-skills` as a marketplace.

Adding the marketplace only makes the plugin available; the second command is
what installs it.

## Using in a new project

A project generator does not copy the skills: a copy is a second contract that
drifts from the first. It copies `project-kit/template/` — a settings file
enabling this plugin pinned to a release, a project `CLAUDE.md`, a CI workflow
and a commit hook — and asks for the project's software id. See
[project-kit/README.md](project-kit/README.md). Once installed, the skills load on demand — each one's
`description` says when it applies, so an assistant picks them up without being
told which to read.