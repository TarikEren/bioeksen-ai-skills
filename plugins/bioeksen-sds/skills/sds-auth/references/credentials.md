# Credentials

Token format, claims and lifetimes for the three principals defined in
`SKILL.md`, and the roles they hold.

The identity provider is the project's `.bioeksen/identity-provider`, per
`sds-project/SKILL.md`: `entra-id` or `keycloak`. This document holds what
every provider must give; `entra-id.md` and `keycloak.md` beside it say how
each does: its issuer, its claim names, its principal key, and how a role
reaches a token.

## Format

Every credential is a JWT, signed (never `alg: none`, never symmetric
keys shared between services). A JWT is chosen over an opaque token for one
reason that the specs already depend on: `AUTH-4102` requires distinguishing
*expired* from *invalid* without a call to the issuer, which needs a readable
`exp`.

## Issuer

Tokens are issued by the identity provider, from one tenant or realm, for
every principal type. Operator identity, MFA, conditional access and
offboarding then arrive with the directory rather than being built, and
someone who leaves loses their tokens by the same action that removes their
account — the part of an identity system that is hardest to get right and
easiest to forget.

One issuer at a time. A verifier that accepts either of two issuers has twice
the surface and an `iss` check that no longer means anything.

Every app is registered once with the provider, under its software id,
allocated per `sds-logging/references/log-record.md`. A caller asks for a
token for the app it is about to call, so `aud` names the receiving app, as
the claims table requires, without any app arranging it. Naming the
registration after the software id also lets anything that reads the
registrations derive which client id belongs to which software id: the
aggregator needs exactly that mapping to refuse a record submitted under
another app's `id`, per `sds-logging/references/aggregator-api.md`.

Every app's registration MUST refuse a person who holds none of the app's
roles at sign-in, before any of its code runs, so the provider's accounts are
not all the app's users. Each provider's reference says how.

### Principal type

The claims table requires a token to say which principal it carries:

| Token | Principal |
|-------|-----------|
| An app-only token, from the client credentials grant | App |
| A person's token carrying the configured operator scope, with `operator` among its roles | Operator |
| Any other person's token | An employee: a person signed in to the app as themselves. Only the app's own endpoints accept one, per **Company roles** |
| A token that is none of these | Rejected, `AUTH-4101` |

Each provider's reference says which claims tell an app-only token from a
person's, and where the scope is carried.

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
| Employee | An employee holding the company role the endpoint requires, or any employee when it requires none | Proceeds |
| Employee | An employee without that role, or an app | `PERM-4150` |

An app credential MUST NOT satisfy an operator requirement. `operator` is
assignable to people only, per **Roles**, so an app-only token never carries
it, and one that somehow did would still not be a person's token.

## Required claims

| Claim | Meaning | Rule |
|-------|---------|------|
| `iss` | Issuer | MUST match the configured issuer exactly |
| The principal key | The person's or the app's stable id | MUST be present. The one key a principal is stored, compared and logged under, the same in every app: Entra's `oid` with `tid`, Keycloak's `sub` |
| `azp` | The calling client | MUST be present. The client id of the application the token was issued to — for an app principal, the calling app itself |
| `aud` | Intended audience | MUST name the receiving app; a token for one service MUST NOT be accepted by another |
| `exp` | Expiry | MUST be present; see lifetimes |
| `iat` | Issued at | MUST NOT be in the future beyond the skew allowance |
| `roles` | The roles the principal holds | A top-level array of strings: the app roles and company roles the directory assigned, per **Roles** |
| The principal type's claims | Which principal the token carries | Per **Principal type**, in the claims the provider's reference names |

The principal type is what makes "an app credential MUST NOT satisfy an
operator requirement" checkable. Without it, that rule depends on inspecting
the formats of ids, which is guesswork.

A principal is keyed by its principal key and nothing else. A value that
differs from one app to the next, such as Entra's `sub`, makes a person keyed
by it in one app a stranger in the next, and two apps' records of them cannot
be joined. The principal key is what `user=` carries in a log record, per
`sds-logging/references/log-record.md`.

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
| Every credential | The provider's, per its reference |

**A lifetime MUST NOT be assumed.** A provider may vary it, and may change it,
so an app reads `exp` and works from that. Anything that hardcodes a duration
will be wrong for most tokens and catastrophically wrong on the day the
provider changes.

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

Revoking an app credential means rotating its client secret or certificate, or
disabling or unassigning it at the provider. **None of those invalidates a
token already issued.** The revocation window is therefore the token lifetime.
An incident that cannot wait that long needs the receiving app to stop
accepting the principal key itself — a deny list, which is a different
mechanism from a credential rotation and belongs to whoever runs the incident.

- Credentials MUST NOT be committed to a repository, baked into an image, or
  passed on a command line. They arrive as environment configuration; a
  missing one at startup is `CFG-5000`, and an unusable one is `CFG-5001`.
- A certificate or a federated workload identity SHOULD be preferred over a
  client secret. A secret that must be rotated on a calendar is a secret that
  expires in production on a Friday.

## Roles

Roles are a closed list, like error codes, and this table is it, with the
company roles in **Company roles** below:

| Role | Assignable to | Defined on | Grants |
|------|---------------|------------|--------|
| `operator` | Users only | Every app's registration | Every operator endpoint in the estate: the full health report, an app's own `GET /api/admin/logs`, and the aggregator's read endpoints |
| `logs.write` | Applications only | The aggregator's registration | Submitting log records, `POST /api/v1/logs` and `POST /api/v1/logs/batch`, and reading the codes the aggregator accepts, `GET /api/v1/codes` |
| `logs.resolve` | Applications only | The aggregator's registration | Moving an error group along its lifecycle with the issue that tracks it, `PUT /api/v1/groups/{groupId}/issue`, and reading a record to find its group, `GET /api/v1/logs/{recordId}`. Held by the git provider's integration alone |

"Assignable to" is enforced by the provider, as its reference says, so a user
role is unobtainable by an app, and the reverse, without any receiving app
having to check.

An app role that an app grants to its callers is named `<resource>.<action>`,
lowercase, e.g. `logs.write`. `operator` keeps its bare name, being the one
role that means the same thing on every app.

A role is added to this table by a human, in the same commit as the spec of
the endpoint that requires it, and only then created on the owning app's
registration. An app MUST NOT require a role neither table lists: a role
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

### Company roles

A company role says what an employee does in the company, such as
`lab-manager`, and is what an app's own endpoints require of an employee. An
employee is given one once, not once per app:

- **The company roles are a closed list**, the table below, on the same terms
  as the roles above: a human adds one, in the same commit as the
  specification of the first endpoint that requires it. Each is a kebab-case
  noun, matching `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`.
- **Each is a group at the identity provider**, named `bio-role-{role}`. An
  employee holds the role by being a member of its group, and is added once.
  Where the provider cannot give an app role to a group, as Entra ID cannot
  without its P1 licence, the role is assigned to each employee directly, on
  every app that requires it, per the provider's reference.
- **The token carries the role**, in its `roles`, either way. The token is
  the only source an app reads a company role from: a second source would be
  a second answer, and the two disagree the day one of them is not updated.

An app checks role names, and, as with every role, ignores the ones it does
not require.

| Company role | Means |
|--------------|-------|
| None yet | Each is added with the first endpoint that requires it |

## An app's own users

An app that needs to know more about a person than their token carries keeps
a profile table keyed by the principal key, holding only what the app itself
needs: its foreign keys then keep working whoever the person is. The table
holds no password, because people sign in at the identity provider, and no
role, because the token carries the roles.

When a person's data must be erased, the app sets the profile's personal
fields to `null` in place. The key remains, so every log record that names the
person, per `sds-logging/references/log-record.md`, stays exactly as written
and no longer identifies anyone.

## Acting for a person

A tool an operator uses — a dashboard, a CLI — calls operator endpoints for
that person, not as itself. Its own app credential never satisfies an operator
endpoint, so it presents the person's delegated token instead:

- A tool the person signs in to directly, such as a CLI or a single-page app,
  obtains a token for the target app with the authorization code flow and
  PKCE, requesting that app's operator scope.
- A server-side tool that already holds the person's token for itself
  exchanges it for one addressed to the target app, again requesting the
  target's operator scope, by the provider's token exchange: Entra's
  on-behalf-of flow, or Keycloak's token exchange.

Either way the token that arrives carries the person's principal key, scope and
roles, so the receiving app sees an operator — or refuses a person who is not
one — exactly as if the person had called it directly. A tool MUST NOT fall
back to its own credential when the person's is unavailable: an app credential
able to act as an operator is the escalation the principal rule exists to
prevent.

## Configuration

Every value below arrives as environment configuration, under the variable
beside it, except the client id to software id mapping, which is derived. This is the concrete list `CFG-5000` and `CFG-5001` refer to:
a missing one is `CFG-5000` at startup, a present but unusable one is
`CFG-5001`.

| Value | Variable | Required of | Purpose |
|-------|----------|-------------|---------|
| Tenant id | `AUTH_TENANT_ID` | Every app on Entra ID | The tenant, checked against `tid`, per `entra-id.md` |
| Issuer | `AUTH_ISSUER` | Every app | The exact `iss` string to compare against |
| JWKS URI | `AUTH_JWKS_URI` | Every app | Where signing keys are fetched |
| JWKS cache max age | `AUTH_JWKS_MAX_AGE_SECONDS` | Every app | How long keys are held before an unconditional refresh |
| Audience | `AUTH_AUDIENCE` | Every app | This app's identifier at the provider — the value `aud` must equal |
| Client id | `AUTH_CLIENT_ID` | Every app | This app's own identity, used when it calls another app |
| Client credential | `AUTH_CLIENT_CERTIFICATE_PATH`, or `AUTH_CLIENT_SECRET` | Every app | The certificate or secret backing that identity |
| Operator scope | `AUTH_OPERATOR_SCOPE` | Every app | The scope marking a delegated token as an operator's |
| Clock skew | `AUTH_CLOCK_SKEW_SECONDS` | Every app | 60 seconds, per **Validation** |
| Client id to software id | — | The aggregator | Derived from the provider's registrations, which are named after the software ids, per **Issuer**. Never configuration |
| Trusted proxies | `TRUSTED_PROXIES` | Apps behind a proxy | The addresses whose `X-Forwarded-For` entries are believed when finding a request's source, per the rate limiting rule in `SKILL.md` |

These names are fixed for every app and every provider, as `LOG_LEVEL` is, so
an operator finds a setting under the same name everywhere.

A value required of an app that is missing or unusable is handled as every
configuration value is, per **When it is validated** in `sds-config/SKILL.md`,
which is normative for it: the app does not report ready,
`GET /api/health/ready` answers 503 `fail`, and a `FATAL` record carrying
`CFG-5000` or `CFG-5001` names the variable, never its value. An app that
reported ready while it could authenticate nobody would stay in the load
balancer's rotation, and answer every caller with a 401 that blames the
caller's own credential. An app that is not ready leaves the rotation, and its
record says why.
