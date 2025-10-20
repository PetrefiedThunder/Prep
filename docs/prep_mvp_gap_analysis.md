# Prep MVP Gap Analysis

## Summary
- The current codebase focuses on a lightweight React prototype and a Python-based compliance microservice, leaving most of the outlined MVP platform unimplemented.
- Critical booking, payments, authentication, and data management capabilities described in the MVP outline are absent, and there is no Express/Node API gateway or PostgreSQL/Redis integration in place.
- DevOps, monitoring, and regulatory integrations are largely undocumented or missing, indicating substantial work is required before reaching the stated MVP scope.

## Architecture & Infrastructure
### Current State
- Backend functionality is centered on a FastAPI compliance service that exposes health and report-generation endpoints and instantiates the Food Safety Compliance engine. 【F:apps/compliance_service/main.py†L1-L78】
- The frontend is a small Vite/React application with a single router and four views rendered via client-side routes. 【F:apps/web/src/App.tsx†L1-L24】

### Gaps vs. MVP Outline
- No Express/Node API gateway or modular application services (authentication, booking, payments, notifications) are present; only the compliance FastAPI service exists, diverging from the planned architecture.
- There is no evidence of infrastructure for managed PostgreSQL/Redis, object storage, or third-party integrations such as Stripe, Plaid, Twilio, Google Maps, or Yelp.
- DevOps elements like Dockerfiles, deployment scripts, or monitoring setup are absent, leaving the deployment strategy undefined.

## Frontend (React + TailwindCSS)
### Current State
- Landing, kitchen browser, checkout, and dashboard pages render minimal placeholder UI with basic fetch calls to unimplemented `/api` endpoints. 【F:apps/web/src/pages/LandingPage.tsx†L1-L8】【F:apps/web/src/pages/KitchenBrowser.tsx†L1-L25】【F:apps/web/src/pages/BookingCheckout.tsx†L1-L28】【F:apps/web/src/pages/Dashboard.tsx†L1-L21】
- Project dependencies include React, React Router, and TailwindCSS, but omit state management libraries such as Zustand and any PWA-specific tooling. 【F:apps/web/package.json†L1-L32】

### Gaps vs. MVP Outline
- Required views like the kitchen detail page, full booking checkout flow, user and host dashboards with detailed panels, admin moderation tools, and messaging interfaces are missing or placeholder-only.
- PWA features (service workers, push notifications, add-to-home-screen support) and responsive enhancements are not implemented.
- There is no integration with availability calendars, payments, messaging, or analytics components outlined for the MVP.

## Backend Services (Node.js + Express + PostgreSQL)
### Current State
- The repository lacks any Node.js/Express service; only the Python FastAPI compliance service is implemented. 【F:apps/compliance_service/main.py†L44-L78】
- There are no endpoints for kitchens, bookings, verification, payments, or messaging beyond the compliance report API.

### Gaps vs. MVP Outline
- User, kitchen, booking, notification, and review services are unimplemented, and there is no middleware for JWT auth, RBAC, or input validation as required.
- Payment intent creation, messaging, and certification verification endpoints do not exist, preventing end-to-end booking flows.

## Data & Storage
### Current State
- Python project dependencies cover FastAPI and Pydantic only, with no database drivers or ORMs configured. 【F:pyproject.toml†L1-L27】
- There are no schema migrations or data models for PostgreSQL tables or Redis caching, and no storage integration for files or certificates.

### Gaps vs. MVP Outline
- Core relational tables (`users`, `kitchens`, `bookings`, etc.) and Redis caching strategies are not defined or implemented.
- Health certificate uploads, equipment tagging, and notification storage are missing, limiting compliance and listing functionality.

## Payments, Identity, and Compliance
### Current State
- The codebase does not integrate Stripe, Plaid, SendGrid, or KYC providers; only the internal compliance engine wrapper is present. 【F:apps/compliance_service/main.py†L1-L78】

### Gaps vs. MVP Outline
- Stripe Connect accounts, escrow handling, and automated payouts are absent, along with identity verification and document moderation workflows.
- There is no integration with health department APIs, geolocation services, or insurance verification.

## Authentication & Security
### Current State
- No authentication flows, JWT handling, or password management utilities exist in either frontend or backend code.

### Gaps vs. MVP Outline
- Email verification, admin role gating, GDPR policies, and secure token storage remain to be implemented.

## Testing & Quality
### Current State
- Frontend tests cover only simple UI interactions for the placeholder pages. 【F:apps/web/src/tests/BookingCheckout.test.tsx†L1-L12】

### Gaps vs. MVP Outline
- There are no Jest/Supertest suites for backend routes, nor are there E2E tests (Playwright/Cypress) covering booking flows, payments, or dashboards as specified.

## Next Steps
- Establish the Node.js/Express API gateway with modular services and connect it to PostgreSQL/Redis, implementing the outlined endpoints and data models.
- Expand the React application to include the full set of user, host, and admin experiences with real data flows, state management, and PWA capabilities.
- Integrate Stripe (payments), identity verification, messaging, and compliance document workflows, alongside robust authentication and security measures.
- Introduce infrastructure-as-code or deployment scripts, monitoring, and comprehensive automated testing to support the MVP launch target.
