# HarborHomes Frontend

HarborHomes is a Next.js 14 App Router prototype inspired by familiar travel marketplaces while delivering a distinct brand system and product surface.

## Getting started

```bash
pnpm install
pnpm dev
```

Environment variables:

```
MAPBOX_TOKEN=mock
NEXT_PUBLIC_MAPBOX_TOKEN=mock
```

## Architecture

- **Next.js 14 App Router** with TypeScript and server components for data fetching.
- **Tailwind CSS + shadcn/ui** for the component system with custom brand tokens and dark mode toggle.
- **React Query + Zustand** for light client-side caching and UI state.
- **next-intl** powers i18n with English and Spanish message bundles and locale middleware.
- **Mock API routes** under `/app/api` seed listings, wishlists, reviews, host data, and inbox threads.
- **Dynamic map** integration via Mapbox GL with clustering-ready helpers.
- **Framer Motion** enriches gallery and toast animations respecting prefers-reduced-motion.

## Key journeys

- Discover curated listings on the home page with category rails and promos.
- Split-view search with synchronized cards and map markers, filter dialog, and infinite-ready layout.
- Listing detail with gallery lightbox, booking sidebar, amenity grid, reviews, and embedded map.
- Frontend checkout wizard (review → details → payment → confirmation) validated with zod + react-hook-form.
- Wishlists, trips, inbox, account settings, auth flows, and host dashboards with onboarding wizard.

## Tooling

- **Testing**
  - `pnpm test:unit` runs Vitest + Testing Library specs.
  - `pnpm test:e2e` runs Playwright UI flows.
  - `pnpm test:a11y` runs Playwright + axe against home, search, and listing.
- **Linting** via `pnpm lint` (Next.js config plus accessibility rules).
- **Formatting** via Prettier with lint-staged + Husky ready to wire up.

## Demo walkthrough

1. Visit `/` for the HarborHomes hero, search pill, categories, and featured listings.
2. Click the search pill to open advanced filters, pick dates + guests, and load `/search` with synced map and cards.
3. Choose a listing to explore photos, amenities, reviews, and book via the sticky checkout card.
4. Proceed to `/checkout/[id]` for the multi-step reservation flow.
5. Manage wishlists, trips, inbox, host dashboards, and account preferences from the navigation.

## Future hooks

- Connect the mock API to live services (search inventory, messaging, payments).
- Replace the placeholder auth with a hosted provider (e.g., Clerk, Auth0) and secure server actions.
- Integrate real payment instrumentation and receipt generation, plus SSR caching strategies.
- Expand analytics events into a real telemetry pipeline.

## Non-infringement note

All branding, copy, colors, and layouts are bespoke to HarborHomes and avoid reuse of Airbnb protected assets.
