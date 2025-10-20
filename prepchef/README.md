# PrepChef Monorepo (v1.0)

Downtime-only, compliant commercial-kitchen marketplace.

## Quickstart
```bash
# Install deps
npm i -g npm@^10
npm install

# Start a couple of services in dev mode
npm run dev -w services/auth-svc
npm run dev -w services/booking-svc
npm run dev -w services/access-svc

# Generate OpenAPI client/server stubs (placeholder)
npm run codegen
```

## Services
- auth-svc, identity-svc, compliance-svc, listing-svc, availability-svc, pricing-svc, payments-svc, booking-svc, access-svc, notif-svc, reviews-svc, admin-svc, audit-svc

See `contracts/openapi.yaml` and `db/schema.sql`.

## Documentation

- [PrepChef MVP v1.0 Engineering Plan](../docs/prepchef_mvp_engineering_plan.md)
