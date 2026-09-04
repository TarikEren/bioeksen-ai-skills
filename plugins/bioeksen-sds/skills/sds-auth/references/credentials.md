# Credentials

Token format, claims and lifetimes for the two principals defined in
`SKILL.md`.

## Format

Both credential types are JWTs, signed (never `alg: none`, never symmetric
keys shared between services). A JWT is chosen over an opaque token for one
reason that the specs already depend on: `AUTH-4102` requires distinguishing
*expired* from *invalid* without a call to the issuer, which needs a readable
`exp`.

## Required claims

| Claim | Meaning | Rule |
|-------|---------|------|
| `iss` | Issuer | MUST match the configured issuer exactly |
| `sub` | The principal | App id for an app, stable user id for an operator |
| `aud` | Intended audience | MUST name the receiving app; a token for one service MUST NOT be accepted by another |
| `exp` | Expiry | MUST be present; see lifetimes |
| `iat` | Issued at | MUST NOT be in the future beyond the skew allowance |
| `typ` | Principal type | `app` or `operator`. A token without it is rejected |

`typ` is what makes "an app credential MUST NOT satisfy an operator
requirement" checkable. Without it, that rule depends on inspecting `sub`
formats, which is guesswork.

Operator tokens additionally carry `roles`, an array of strings. The only role
these specs require is `operator`.

## Validation

Every claim above MUST be checked. In particular:

- `aud` MUST be verified. Skipping it means any service holding a valid token
  can replay it against every other service.
- Signature MUST be verified against the issuer's published key, with the
  algorithm taken from the configured expectation, not from the token header.
- Clock skew tolerance is **60 seconds**, applied to `exp` and `iat`. Beyond
  that the token is expired.

## Lifetimes

| Credential | Lifetime |
|------------|----------|
| Operator | 1 hour |
| App | 24 hours |

Short operator lifetimes bound the damage of a leaked token from a person's
machine. App tokens are longer because rotation is automated and a failed
refresh takes a service down.

An app MUST refresh before expiry rather than on rejection: discovering
expiry through a 401 means the failure surfaces as a request error rather
than as a background retry.

## Rotation

- Signing keys MUST be rotatable without downtime: verifiers accept any key
  currently published by the issuer, so a new key can be introduced before it
  is used to sign.
- A compromised app credential MUST be revocable by rotating that app's
  signing key or its `sub` registration.
- Credentials MUST NOT be committed to a repository, baked into an image, or
  passed on a command line. They arrive as environment configuration; a
  missing one at startup is `CFG-5000`, and an unusable one is `CFG-5001`.

## Open decisions

Unresolved, and needed before the first app implements this:

- **Issuer.** Whether tokens come from an existing identity provider or a
  BioEksen-operated service. Everything above holds either way; the issuer
  URL, key publication endpoint and operator login flow depend on it.
- **Operator roles beyond `operator`.** The estate currently needs exactly one
  role. Adding a second is a change here, not per app.