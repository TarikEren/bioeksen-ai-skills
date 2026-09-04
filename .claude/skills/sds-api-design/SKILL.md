---
name: sds-api-design
description: BioEksen API design conventions. Use when designing, reviewing or implementing an HTTP API endpoint
---

# API Design

Every API contains standard and specialized endpoints.

## Standard API Endpoints

Every app MUST expose:

- Health
- Readiness
- Liveness
- Admin logs

with identical paths and schemas.

- `references/standard-api-endpoints.md` — the conventions and the reasoning
  behind them.
- `references/openapi.yaml` — the normative OpenAPI 3.1 definition, takes precedence over the markdown.

## Specialized Endpoints

App-specific endpoints have no shared schema, but MUST follow the conventions in `references/standard-api-endpoints.md`: the type and unit table, the body `status` vs HTTP status code mapping, and the error envelope.
