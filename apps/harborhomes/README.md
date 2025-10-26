# HarborHomes Frontend

HarborHomes is a short-stay marketplace demo inspired by familiar travel products while maintaining a distinct brand. This project demonstrates a production-ready Next.js 14 application with mock services, modern UI components, testing, and accessibility workflows.

## Getting Started

```bash
pnpm install
pnpm dev
```

Visit http://localhost:3000 to view the app.

## Scripts
- `pnpm dev` – start the development server
- `pnpm build` – create a production build
- `pnpm start` – run the production server
- `pnpm lint` – lint the codebase
- `pnpm format` – format with Prettier
- `pnpm test:unit` – run Vitest suite
- `pnpm test:e2e` – execute Playwright end-to-end tests
- `pnpm test:a11y` – run accessibility smoke suite with Axe

## Architecture
- **Next.js 14 App Router** with TypeScript and Server Actions for mutations.
- **Tailwind CSS** + shadcn-inspired components with a custom HarborHomes theme.
- **Mock API** routes under `/app/api` providing listings, reviews, wishlists, messages, and host data.
- **Data Layer** using React Query for caching and Zustand for lightweight UI state.
- **Internationalization** powered by `next-intl` with English and Spanish dictionaries.
- **Testing** via Vitest + Testing Library, Playwright E2E, and Axe accessibility scans.
- **Performance** enhancements with dynamic imports (Map, gallery) and optimized images.

## Demo Walkthrough
1. Explore the home page with featured listings and categories.
2. Use the search pill to open advanced filters, then view the map/list split search results.
3. Select a listing to open the detail page with gallery, reviews, and booking card.
4. Add dates and guests, then advance through the checkout wizard to a confirmation number.
5. Save homes to wishlists, review trips, inbox messages, and manage host listings.

## Future Hooks
- Connect real authentication and payments providers.
- Replace mock APIs with real backend services and SSR data fetching.
- Expand analytics instrumentation and integrate experimentation tooling.
