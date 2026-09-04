# BioEksen AI Skills

Shared skills for apps built by BioEksen Ar-Ge Teknolojileri A.Ş.,
written to be loaded by coding assistants as well as read by people.

Each skill is a directory under `.claude/skills/` with a `SKILL.md` entry point
and, where the detail warrants it, a `references/` folder. Conventions that two
services must agree on live here; anything that only affects how one codebase is
written does not.

## Skills

| Skill | Covers |
|-------|--------|
| [`sds-api-design`](.claude/skills/sds-api-design/) | HTTP API conventions: the standard health and admin endpoints, response envelopes, error shape, pagination, status codes |
| [`sds-auth`](.claude/skills/sds-auth/) | Who may call what: operator and app credentials, how they are presented and validated |
| [`sds-logging`](.claude/skills/sds-logging/) | Log records, severities and types, the error code registry, the log aggregator API |
| [`sds-commit`](.claude/skills/sds-commit/) | Conventional commit format and the release version it implies |

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

Paths below are relative to `.claude/skills/`, the root the skills themselves
link from.

- **Error codes** — `sds-logging/references/code-prefixes.md`. The closed list
  of all 38 codes, mirrored as an enforced enum in the OpenAPI schema.
- **Log record shape** — `sds-logging/references/log-record.md`.
- **API response and error envelopes** — `sds-api-design/references/openapi.yaml`
  is normative; the markdown beside it is the rationale.

## Conventions used in these documents

- MUST, SHOULD and MAY carry their RFC 2119 meanings.
- Each fact is stated in exactly one file; others link to it.
- Where a machine-checkable artifact exists, it is normative and the prose is
  explanatory.# bioeksen-ai-skills
