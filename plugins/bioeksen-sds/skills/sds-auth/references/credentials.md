# Credentials

Token format, claims and lifetimes for the two principals defined in
`SKILL.md`.

## Format

Both credential types are JWTs, signed (never `alg: none`, never symmetric
keys shared between services). A JWT is chosen over an opaque token for one
reason that the specs already depend on: `AUTH-4102` requires distinguishing
*expired* from *invalid* without a call to the issuer, which needs a readable
`exp`.

## Issuer

Tokens are issued by **Microsoft Entra ID**, from one tenant, for both
principal types.

Entra was chosen because BioEksen operators already have managed accounts in
it. Operator identity, MFA, conditional access and offboarding arrive with the
directory rather than being built, and someone who leaves loses their tokens by
the same action that removes their mailbox — which is the part of an identity
system that is hardest to get right and easiest to forget.

| Value | Form |
|-------|------|
| `iss` | `https://login.microsoftonline.com/{tenantId}/v2.0` |
| Discovery | `{iss}/.well-known/openid-configuration` |
| Signing keys | `https://login.microsoftonline.com/{tenantId}/discovery/v2.0/keys` |
| `aud` | The receiving app's Application ID URI, e.g. `api://logs-aggregator` |

Every app is registered once, with the Application ID URI `api://{software-id}`
— its software id, allocated per `sds-logging/references/log-record.md`. A
caller asks for a token for the app it is about to call, using the client
credentials grant and the scope `api://{that app}/.default`. That is what makes
`aud` name the receiving app, as the claims table requires, without any app
arranging it.

Naming the URI after the software id makes `aud` readable as an app's id, and
lets anything with read access to the directory derive which client id
belongs to which software id. The aggregator needs exactly that mapping to
refuse a record submitted under another app's `id` — see
`sds-logging/references/aggregator-api.md`.

### Principal type

The claims table requires a token to say which principal it carries. Entra does
not let an app-only token carry an arbitrary claim, so the type is **derived
from claims Entra does emit**:

| Token | Principal |
|-------|-----------|
| `scp` absent, `roles` present | App |
| `scp` holds the configured operator scope, and `roles` holds `operator` | Operator |
| `scp` present otherwise | A person who is not an operator. No endpoint in these specs accepts one |
| Neither present | Rejected, `AUTH-4101` |

This is the distinction the issuer itself draws between a delegated and an
app-only token, so it cannot drift from what the issuer actually does — which a
convention invented here could.

Two claims make an operator because each answers a different question. The
scope says the token was issued *for operator use of this app*: the person's
tool asked for it, and the directory consented. The role says the person *is*
an operator: the directory assigned it to them. A scope without the role is
someone who signed in to an operator tool without being an operator; a role
without the scope is an operator's token issued for some other purpose. Neither
is an operator request.

What an endpoint answers follows from the principal it requires:

| Endpoint requires | Caller | Result |
|-------------------|--------|--------|
| Operator | Operator | Proceeds |
| Operator | An app, or a person who is not an operator | `PERM-4151` |
| App | An app holding the role the endpoint requires | Proceeds |
| App | An app without it, or any person | `PERM-4150` |

`scp` rather than `roles` is the discriminator because a delegated token can
carry both: operator roles are app roles assigned to a person, and they arrive
in the same `roles` claim an app-only token uses. That is also why `operator`
is assignable to users only, per **Roles**: an app-only token can never carry
it, and one that somehow did would still have no `scp`. The rule that matters
is unchanged and still mechanically checkable: an app credential MUST NOT
satisfy an operator requirement.

### Keycloak, the documented fallback

Keycloak, self-hosted, is the named alternative. It is not deployed, and it is
not accepted in parallel: one issuer at a time. A verifier that accepts either
of two issuers has twice the surface and an `iss` check that no longer means
anything.

Move to it if any of these turns out to hold:

- App-only tokens cannot be made to carry what **Principal type** needs.
- The access token lifetime below proves unworkable and cannot be changed.
- Apps must authenticate somewhere Entra cannot be reached.

Everything else in this document holds either way. What changes is this
section: `iss` becomes `https://{host}/realms/{realm}`, keys move to
`{iss}/protocol/openid-connect/certs`, and the principal type is carried by a
literal `typ` claim from a protocol mapper instead of being derived.

## Required claims

| Claim | Meaning | Rule |
|-------|---------|------|
| `iss` | Issuer | MUST match the configured issuer exactly |
| `sub` | The principal | App id for an app, stable user id for an operator |
| `azp` | The calling client | MUST be present. The client id of the application the token was issued to — for an app principal, the calling app itself |
| `aud` | Intended audience | MUST name the receiving app; a token for one service MUST NOT be accepted by another |
| `exp` | Expiry | MUST be present; see lifetimes |
| `iat` | Issued at | MUST NOT be in the future beyond the skew allowance |
| `tid` | Tenant | MUST match the configured tenant |
| `scp` / `roles` | Principal type | The type is derived from these — see **Principal type** |

The principal type is what makes "an app credential MUST NOT satisfy an
operator requirement" checkable. Without it, that rule depends on inspecting
`sub` formats, which is guesswork. It is a derived value rather than a claim
named `typ` only because the issuer cannot emit one on an app-only token; the
requirement is identical.

`tid` and `iss` are redundant in a single-tenant configuration, which is the
point of checking both. `iss` is a string comparison that a copied
configuration survives intact, and `tid` is the one that fails it.

`roles` is an array of strings: the app roles the directory has assigned to the
person, or to the calling app. Which roles exist is a closed list — see
**Roles**.

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
| Both | The issuer's — on Entra, 60 to 90 minutes |

**A lifetime MUST NOT be assumed.** Entra randomises access token lifetime
within that range and does not expose it as a policy, so an app reads `exp` and
works from that. Anything that hardcodes a duration will be wrong for most
tokens and catastrophically wrong on the day the issuer changes.

This document previously set 24 hours for app credentials, on the grounds that
a failed refresh takes a service down. That is not achievable here, and on
inspection it was not the right answer anyway: the cure for a failed refresh is
a retry policy, not a token that stays valid for a day. Nothing implements the
old rule yet, so nothing has to migrate.

Short lifetimes bound the damage of a leaked token — from a person's machine
for an operator, and from a compromised host for an app. The lifetime is also
what bounds the revocation window below, which is the more important of the
two.

An app MUST refresh before expiry rather than on rejection: discovering expiry
through a 401 means the failure surfaces as a request error rather than as a
background retry.

The lead time is **75% of the lifetime read from `exp`**, per
`sds-api-design/references/service-calls.md`. The remaining quarter is what
gives a failed refresh room to retry before the token actually expires.

## Rotation and revocation

Signing keys belong to the issuer, not to any app. A verifier:

- Fetches keys from the configured JWKS endpoint and caches them.
- Re-fetches when a token arrives carrying an unknown `kid`, rate limited, so
  that a token with a junk `kid` cannot be used to hammer the issuer.
- Refreshes unconditionally at least daily, so a rotation lands before a key it
  has never seen does.

A cached key is why verification normally needs no call to the issuer at all.
`AUTH-5500` — step 6 of the validation order — is therefore narrower than it
looks: it is for the case where a token carries a `kid` the verifier does not
hold *and* the fetch to resolve it fails. A verifier that reaches the issuer on
every request has misread this section.

That is what "rotatable without downtime" means in practice: the issuer
publishes a new key before signing with it, and a verifier that re-fetches on an
unknown `kid` never sees a gap.

Revoking an app credential means rotating that app's client secret or
certificate, disabling its service principal, or removing its app role
assignment. **None of those invalidates a token already issued.** The revocation
window is therefore the token lifetime, up to 90 minutes. An incident that
cannot wait that long needs the receiving app to stop accepting the `sub`
itself — a deny list, which is a different mechanism from a credential rotation
and belongs to whoever runs the incident.

- Credentials MUST NOT be committed to a repository, baked into an image, or
  passed on a command line. They arrive as environment configuration; a
  missing one at startup is `CFG-5000`, and an unusable one is `CFG-5001`.
- A certificate or a federated workload identity SHOULD be preferred over a
  client secret. A secret that must be rotated on a calendar is a secret that
  expires in production on a Friday.

## Roles

Roles are a closed list, like error codes, and this table is it:

| Role | Assignable to | Defined on | Grants |
|------|---------------|------------|--------|
| `operator` | Users only | Every app's registration | Every operator endpoint in the estate: the full health report, an app's own `GET /api/admin/logs`, and the aggregator's read endpoints |
| `logs.write` | Applications only | The aggregator's registration | Submitting log records, `POST /api/v1/logs` and `POST /api/v1/logs/batch` |
| `logs.resolve` | Applications only | The aggregator's registration | Linking a stored record to the issue that names it and the fix that resolved it, `PUT /api/v1/logs/{recordId}/issue`. Held by the git service's integration alone |

"Assignable to" is the app role's allowed member type in the directory. It is
what makes a user role unobtainable by an app, and the reverse, without any
receiving app having to check.

An app role that an app grants to its callers is named `<resource>.<action>`,
lowercase, e.g. `logs.write`. `operator` keeps its bare name, being the one
role that means the same thing on every app.

A role is added to this table by a human, in the same commit as the spec of
the endpoint that requires it, and only then created on the owning app's
registration. An app MUST NOT require a role this table does not list: a role
defined in one service is an authorization decision in a place nobody auditing
access will look for it.

An app checks for the role it requires and ignores any others present in
`roles`. Adding a role to the directory therefore cannot break a deployed app.

### One operator role

There is exactly one operator role, `operator`, and that is a decision rather
than a gap waiting to be filled.

### The gradient this accepts

Those endpoints are not equally sensitive. A health report exposes capacity
numbers. The aggregator holds every app's records, including whatever
identifiers the structured tail carries, which is why
`sds-logging/references/aggregator-api.md` calls it the highest-value read
target in the estate. One role covers both, so anyone who can read a dashboard
can read the estate's logs.

That is acceptable while the operator population is small and uniformly
trusted. It stops being acceptable the moment someone needs one of those
endpoints and should not have the other — most likely a read-only auditor who
needs the log history but has no business seeing an app's connection pool and
disk internals. **That person arriving is the trigger**, and the reason this is
written down rather than left to be rediscovered when they do.

### Adding a second operator role

A second operator role is added to the table above on the same terms as any
role, assignable to users only. Because an app ignores roles it does not
check for, adding one cannot break anything deployed, which is what makes
keeping one role today a cheap decision rather than a commitment.

## Acting for a person

A tool an operator uses — a dashboard, a CLI — calls operator endpoints for
that person, not as itself. Its own app credential never satisfies an operator
endpoint, so it presents the person's delegated token instead:

- A tool the person signs in to directly, such as a CLI or a single-page app,
  obtains a token for the target app with the authorization code flow and
  PKCE, requesting that app's operator scope.
- A server-side tool that already holds the person's token for itself exchanges
  it for one addressed to the target app with the on-behalf-of flow, again
  requesting the target's operator scope.

Either way the token that arrives carries the person's `sub`, `scp` and
`roles`, so the receiving app sees an operator — or refuses a person who is not
one — exactly as if the person had called it directly. A tool MUST NOT fall
back to its own credential when the person's is unavailable: an app credential
able to act as an operator is the escalation the principal rule exists to
prevent.

## Configuration

Every value below arrives as environment configuration. This is the concrete
list `CFG-5000` and `CFG-5001` refer to: a missing one is `CFG-5000` at
startup, a present but unusable one is `CFG-5001`.

| Value | Required of | Purpose |
|-------|-------------|---------|
| Tenant id | Every app | The Entra tenant, checked against `tid` |
| Issuer | Every app | The exact `iss` string to compare against |
| JWKS URI | Every app | Where signing keys are fetched |
| JWKS cache max age | Every app | How long keys are held before an unconditional refresh |
| Audience | Every app | This app's Application ID URI — the value `aud` must equal |
| Client id | Every app | This app's own identity, used when it calls another app |
| Client credential | Every app | The certificate or secret backing that identity |
| Operator scope | Every app | The `scp` value marking a delegated token as an operator |
| Clock skew | Every app | 60 seconds, per **Validation** |
| Client id to software id | The aggregator | Resolves a submitting app's `azp` to the software id its records must carry |
| Trusted proxies | Apps behind a proxy | The addresses whose `X-Forwarded-For` entries are believed when finding a request's source, per the rate limiting rule in `SKILL.md` |

An app MUST fail to start when any value required of it is missing, rather
than starting and rejecting every request it receives. A service that is up but can
authenticate nobody is harder to diagnose than one that never came up, and it
stays in the load balancer's rotation while it does it.
