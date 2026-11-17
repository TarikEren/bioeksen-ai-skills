# Keycloak

How a project whose `.bioeksen/identity-provider` is `keycloak` meets
`credentials.md`, which is normative for every rule here. One realm holds the
estate's apps and people, as one Entra tenant would.

## Issuer

| Value | Form |
|-------|------|
| `iss` | `https://{host}/realms/{realm}` |
| Discovery | `{iss}/.well-known/openid-configuration` |
| Signing keys | `{iss}/protocol/openid-connect/certs` |
| `aud` | The receiving app's client id, which is its software id |

Every app is a confidential client whose client id is its software id. A
caller asks for a token with the client credentials grant, and an audience
mapper on the receiving client's scope puts that client's id in `aud`:
Keycloak does not add it by itself.

Keycloak has no switch like Entra's assignment requirement. Every app's
client MUST refuse a person who holds none of its roles: its browser flow
ends with a role condition that denies access, so the realm's accounts are
not all the app's users.

## Principal type

| Token | Principal |
|-------|-----------|
| `principal` is `app` | App |
| `scope` holds `AUTH_OPERATOR_SCOPE`, and `roles` holds `operator` | Operator |
| Any other person's token | Employee |
| A token without `roles` | Rejected, `AUTH-4101` |

Every client's service-account user carries the attribute `principal` = `app`,
and a user-attribute mapper puts it in the token. A person's account never
carries it, so the claim marks an app-only token whatever else the token
holds. The claim is not named `typ`, which Keycloak already uses.

The operator scope is a client scope the operator's tool requests. Keycloak
carries scopes in `scope`, a space-separated string, where Entra uses `scp`.

## Principal key

The principal key is `sub`: a user's id, the same in every client of the
realm. `AUTH_TENANT_ID` is unused; the realm is fixed by `iss`.

## Roles

- A role is a client role of the client that defines it. A client-role mapper
  puts the receiving client's roles in a top-level `roles` claim, where
  `credentials.md` expects them, in place of Keycloak's own
  `resource_access`.
- "Assignable to" is kept by assignment: a user role is granted only to
  people or their groups, and an application role only to service-account
  users.
- **Company roles:** each `bio-role-{role}` group is given the matching client
  role of every app that requires it, so its members' tokens carry the role
  in `roles`. No directory is needed for roles.

## Lifetimes and revocation

- The realm's access token lifespan sets the lifetime. The app reads `exp`.
- Revoking an app credential means regenerating its client secret or
  certificate, disabling the client, or removing its service-account user's
  role. A token already issued stays valid until its `exp`.

## Acting for a person

A server-side tool exchanges the person's token with Keycloak's token
exchange, for the target client, requesting its operator scope.
