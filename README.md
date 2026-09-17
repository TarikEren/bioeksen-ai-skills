# BioEksen AI Skills

Shared skills for apps built by BioEksen Ar-Ge Teknolojileri A.Ş.,
written to be loaded by coding assistants as well as read by people.

Everything ships as one plugin, [`bioeksen-sds`](plugins/bioeksen-sds/). Each
skill is a directory under `plugins/bioeksen-sds/skills/` with a `SKILL.md` entry
point and, where the detail warrants it, a `references/` folder. Conventions that
two services must agree on live here; anything that only affects how one codebase
is written does not.

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
| [`sds-commit`](plugins/bioeksen-sds/skills/sds-commit/) | Conventional commit format and the release version it implies |

## How they fit together

```
sds-api-design ──── error envelope carries a code ────┐
      │                                               │
      │ standard endpoints require a credential       │
      ▼                                               ▼
  sds-auth ──── auth outcomes map to AUTH-/PERM- ──► sds-logging
                                                   (code registry,
                                                    log records)
```

Skills cross-reference each other by paths relative to
`plugins/bioeksen-sds/skills/`, the root they are installed under — so a link
written as `sds-logging/references/log-record.md` resolves the same way whether
the plugin is installed or the repository is being read directly.

- **Error codes** — `sds-logging/references/code-prefixes.md`. The closed list
  of all 38 codes, mirrored as an enforced enum in the OpenAPI schema.
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
what installs it. Once installed, the skills load on demand — each one's
`description` says when it applies, so an assistant picks them up without being
told which to read.