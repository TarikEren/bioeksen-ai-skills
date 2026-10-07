---
name: sds-config
description: BioEksen configuration conventions. Use when adding, reading or validating a configuration value, an environment variable or a secret, or deciding what an app does when one is missing or unusable.
---

# Configuration

Configuration is what changes between deployments of an app while its code
stays the same: connection strings, credentials, endpoints, and the empirical
values the other `sds-*` skills let an app override. Two things make it an
estate concern rather than one codebase's. Every load balancer trusts an app's
readiness probe to mean the app can serve, which an app running on a
configuration it cannot use breaks. And a secret that leaks out of one app's
configuration is everyone's incident.

The keywords MUST, SHOULD and MAY are used as in RFC 2119.

Paths such as `sds-logging/references/log-record.md` name a file in another
skill of this plugin, relative to the plugin's skills directory: the parent
of `${CLAUDE_SKILL_DIR}`, which is this skill's own directory.

## One module

An app MUST read its configuration in one module. It reads the environment,
or whatever the platform supplies instead, validates every value against a
schema, and exports typed values. No other code reads the environment.

A value read in five places is validated in none of them, and a rename
reaches four. One module is where a reviewer sees everything the app depends
on, and the only place each value's type is decided.

## When it is validated

Every value MUST be validated at startup, before the app reports ready:

- A required value that is absent is `CFG-5000`, and a value present but
  unusable is `CFG-5001`. Both are `FATAL`, per **Derived attributes** in
  `sds-logging/references/code-prefixes.md`.
- While either holds, the app MUST NOT report ready: `GET /api/health/ready`
  answers 503 with the body `status` `fail`, per
  `sds-api-design/references/standard-api-endpoints.md`. Configuration does
  not recover by itself, so it is a failure, not `not-ready`.

Validation MUST NOT be deferred to first use. Where a framework's build step
loads the code without the runtime configuration, as a Next.js build does, the
values are validated when the process starts: not at build time, where they
are absent, and not on the first request that needs one. Deferred, a startup
`FATAL` becomes one failed request hours later, on one code path, while the
probe has been reporting ready all along.

## Declaring every value

Every value the app reads MUST be listed in an example file committed with the
code, such as `.env.example` or the platform's equivalent, marked required or
optional, and with no real value. It is the one place a person setting up a
deployment learns what the app needs; a value missing from it is found only
when the app refuses to start.

## Secrets

A credential, a key, or a connection string carrying a password is a secret.
A secret:

- MUST NOT be committed, the example file included.
- MUST NOT appear in a log record, an error `message`, a `details` entry or a
  health response; see the forbidden list in `sds-logging/SKILL.md`. A failed
  validation names the variable, never its value.
- MUST NOT reach a browser or a client bundle. A variable a framework exposes
  to the client by its name, such as `NEXT_PUBLIC_*` or `VITE_*`, never
  carries one.

## Test-only settings

A setting that opens a test seam, such as the key a test sign-in is checked
with, MUST be refused in production: the app fails at startup with
`CFG-5001`. A production app that started with one set would accept identities
nobody issued. The seams themselves are in `sds-testing/SKILL.md`.

## Overriding an empirical value

The values the other skills call empirical are configuration: timeouts,
attempt counts, breaker thresholds, the 60 seconds before `DB-5501` is
`FATAL`, a request body limit. An app that overrides one MUST record the
override and its reason where its configuration lives, per
`sds-api-design/references/service-calls.md`, which is in this module, beside
the value.

## Names other skills fix

The lowest severity an app logs is configuration under the name
`sds-logging/SKILL.md` gives it, `LOG_LEVEL`, so an operator can change it on
any app without first finding what that app calls it.

Authentication values take the names in `sds-auth/references/credentials.md`,
**Configuration**, and the log transport's values take the names in
`sds-logging/SKILL.md`, **Transport**.

## Not configuration

The software id is not configuration. It is allocated once, never changed, and
read from `.bioeksen/software-id`, per `sds-logging/references/log-record.md`.
An environment variable would let one deployment change it, which severs that
deployment's records from every record the app wrote before.

## Tests

The cases an app's tests MUST contain for these rules are the Configuration
table in `sds-testing/references/contract-tests.md`.
