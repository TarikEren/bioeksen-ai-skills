# Working in this repository

A Claude Code plugin marketplace holding one plugin, `bioeksen-sds`, whose
skills are the shared specifications every BioEksen service is built against.

There is no application code here — no build, no test suite, nothing for an LSP
to navigate. It is Markdown plus one OpenAPI file, so grep is the right tool.

Editing a skill changes a contract that services in other repositories already
implement. Treat a change here as an API change, not a docs tweak.

## Layout

- `.claude-plugin/marketplace.json` — marketplace manifest
- `plugins/bioeksen-sds/.claude-plugin/plugin.json` — plugin manifest
- `plugins/bioeksen-sds/skills/<skill>/SKILL.md` — entry point, with the
  `name` + `description` frontmatter that decides when the skill loads
- `plugins/bioeksen-sds/skills/<skill>/references/` — the detail

Skills cross-reference each other by paths relative to `skills/`, e.g.
`sds-logging/references/log-record.md`. Keep that form: it resolves the same
way whether the plugin is installed or the repository is read directly.

## Which file wins

Facts are restated across skills for readability. Where two documents overlap,
one is normative and the other says so:

| Fact | Normative in |
|------|--------------|
| The error code list | `sds-logging/references/code-prefixes.md` |
| Error code selection order | `sds-logging/references/code-prefixes.md` — `sds-auth/SKILL.md` restates steps 1-9 |
| The log record contract | `sds-logging/references/log-record.md` |
| Standard endpoint schemas | `sds-api-design/references/openapi.yaml` — the markdown beside it is rationale |

When two disagree, the normative one is right and the other gets corrected.

## Invariants

These MUST hold after any change. Nothing enforces them yet — check by hand.

1. The same 38 error codes appear in all three of: the per-prefix tables in
   `code-prefixes.md`, the selection procedure in the same file, and the
   `ErrorCode` enum in `sds-api-design/references/openapi.yaml`.
2. Steps 1-9 of that selection procedure and the validation order in
   `sds-auth/SKILL.md` list the same codes in the same order. Compare the
   **codes**, not the prose — the conditions deliberately differ in wording,
   one being credential-agnostic and the other JWT-specific.
3. Every code's HTTP status matches the range table in `error-codes.md`.

## Rules for editing

- **Never invent an error code.** The list is closed. If nothing fits, the
  answer is `SYS-5000` — a code that exists in one place and nowhere else is
  invisible to every filter, runbook and dashboard.
- Adding a code means editing the prefix table *and* the selection procedure in
  `code-prefixes.md`, *and* the `ErrorCode` enum. All three, or it is unusable.
- Codes are permanent: never renumbered, never redefined, never reused for a
  different meaning. A retired code stays in its table marked retired.
- **Never invent a software id.** It is supplied by the project or by the
  id-issuing service; when it has not been, ask. A guessed id looks correct, so
  nothing flags it — see `sds-logging/references/log-record.md`.
- State each fact once. Where it must be restated, name the normative source in
  the restating document.
- MUST, SHOULD and MAY carry RFC 2119 meanings. Use them deliberately.
- Keep the rationale. These documents explain *why* each rule exists; a rule
  stripped of its reason gets re-argued in six months.

## Commits

This repository is subject to its own `sds-commit` skill: conventional format,
imperative present tense, no capitalised first letter, no trailing period, and
the mandatory `Change-Id:` footer trailer.

Mint the identifier as `bioeksen-sds-<UTC timestamp>-<4+ random chars>`, e.g.
`bioeksen-sds-20260917T101500Z-4c1e`. The software id is `bioeksen-sds`, the
plugin that gets versioned and released. Commits made before 2026-09-17 predate
the trailer and do not carry one.

Still unadopted: the `/release-notes/{version}.md` file `sds-commit` requires of
every release. The Change-Id trailers above are what those notes will reference
once they exist. Ask before introducing them; it is a workflow decision, not a
cleanup.
