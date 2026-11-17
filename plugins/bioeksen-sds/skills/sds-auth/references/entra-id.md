# Microsoft Entra ID

How a project whose `.bioeksen/identity-provider` is `entra-id` meets
`credentials.md`, which is normative for every rule here.

## Issuer

| Value | Form |
|-------|------|
| `iss` | `https://login.microsoftonline.com/{tenantId}/v2.0` |
| Discovery | `{iss}/.well-known/openid-configuration` |
| Signing keys | `https://login.microsoftonline.com/{tenantId}/discovery/v2.0/keys` |
| `aud` | The receiving app's Application ID URI, e.g. `api://logs-aggregator` |

Every app is registered once, with the Application ID URI
`api://{software-id}`. A caller asks for a token with the client credentials
grant and the scope `api://{that app}/.default`, so `aud` names the receiving
app.

Every app's registration MUST also set:

- **`requestedAccessTokenVersion: 2`**, in its manifest. A version 1 token
  carries no `azp`, which the aggregator needs to tell which app sent a
  record. It also names its issuer `https://sts.windows.net/{tenantId}/`, so
  it fails the `iss` check and is refused with `AUTH-4101`.
- **Assignment required: Yes**, on its enterprise application. Without it,
  any account in the tenant, guests included, can sign in to the app and get
  a token for it. With it, only the people and the apps assigned one of the
  app's roles can.

## Principal type

Entra does not let an app-only token carry an arbitrary claim, so the type is
**derived from claims Entra does emit**:

| Token | Principal |
|-------|-----------|
| `scp` absent, `roles` present | App |
| `scp` holds `AUTH_OPERATOR_SCOPE`, and `roles` holds `operator` | Operator |
| `scp` present otherwise | Employee |
| Neither present | Rejected, `AUTH-4101` |

This is the distinction the issuer itself draws between a delegated and an
app-only token, so it cannot drift from what the issuer actually does.

`scp` rather than `roles` is the discriminator because a delegated token can
carry both: a person's roles are app roles assigned to them, and they arrive in
the same `roles` claim an app-only token uses.

## Principal key

The principal key is `oid` with `tid`. Entra's `sub` is pairwise: the same
person carries a different one in every app registration, so it is never a
key. `oid` is the same in every app of the tenant.

`tid` and `iss` are redundant in a single-tenant configuration, which is the
point of checking both. `iss` is a string comparison that a copied
configuration survives intact, and `tid`, against `AUTH_TENANT_ID`, is the one
that fails it.

## Roles

- A role is an app role on the registration that defines it. "Assignable to"
  is the app role's allowed member type, which keeps a user role from an app
  and the reverse.
- **Company roles with Entra ID P1:** every app's registration defines the
  company roles its endpoints require as app roles, assignable to users only,
  and each is assigned to its `bio-role-{role}` security group once, when the
  app is created. Tokens then carry the role names in `roles`.
- **Company roles without P1:** a group cannot be assigned to an app role,
  so each employee is assigned the app role directly, on every app that
  requires it, and again whenever an app is added. Tokens carry the role names
  in `roles` the same way; what P1 saves is the assigning.

## Lifetimes and revocation

- Entra randomises an access token's lifetime between 60 and 90 minutes, and
  does not expose it as a policy. The app reads `exp`.
- Revoking an app credential means rotating its client secret or certificate,
  disabling its service principal, or removing its app role assignment. The
  window is the token's lifetime, up to 90 minutes.

## Acting for a person

A server-side tool exchanges the person's token with the on-behalf-of flow,
requesting the target app's operator scope.
