# Security

## Secrets
- Never commit tokens/passwords
- Use .env for dev, secret manager for prod

## Network
- Postgres/Redis should not be exposed publicly
- Restrict inbound access to bot/API endpoints

## RBAC
- Enforce role checks on every admin action
- Enforce territory/ds scope checks

## Audit
- Record who did what and when (assets, decisions, config changes)
- Keep immutable logs for critical actions

## Data access
- Superset DB read-only credentials (least privilege)
