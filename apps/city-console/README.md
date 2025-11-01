# City Console

City Console is a lightweight Next.js dashboard for operations and policy teams. It surfaces the latest policy decisions, fee updates, and required compliance documents for supported Prep jurisdictions.

## Prerequisites

- Node.js 18.17+
- pnpm 8.14+
- Access to the Prep compliance API (or the API gateway) with permissions for fee and requirements endpoints

## Environment Variables

Copy `.env.example` to `.env.local` and populate the values:

| Variable | Description |
| --- | --- |
| `NEXT_PUBLIC_API_BASE` | Base URL for Prep API (e.g. `https://api.prep.dev`). |
| `COMPLIANCE_API_KEY` | Optional API key forwarded as `x-api-key` for fee endpoints. |
| `PREP_API_KEY` | Optional bearer token forwarded as `Authorization` header. |
| `CITY_CONSOLE_BEARER_TOKEN` | Optional bearer token override for dedicated deployments. |

## Scripts

```bash
pnpm install
pnpm dev       # Run the development server on http://localhost:3000
pnpm build     # Create a production build
pnpm start     # Start the production build
pnpm lint      # Run Next.js lint checks
pnpm typecheck # Run TypeScript in noEmit mode
```

## Deployment Notes

The app ships with a standalone Next.js build (`next.config.mjs` sets `output: 'standalone'`). Provision the environment variables above in your hosting provider (Vercel, Render, etc.) and run `pnpm build` followed by `pnpm start` to serve the dashboard.
