# PrepChef - Commercial Kitchen Rental Marketplace

A lean, modern two-sided marketplace connecting culinary entrepreneurs with commercial kitchen space.

## Tech Stack

- **Frontend & Backend**: Next.js 14 (App Router) with TypeScript
- **Styling**: TailwindCSS
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **Payments**: Stripe Connect
- **Hosting**: Vercel (frontend) + Supabase (database/auth)

## Development Status

This is a lean MVP rebuild focused on core marketplace functionality only. No over-engineered regulatory systems, no complex infrastructure.

### Core Features

- Kitchen owner onboarding and listing creation
- Kitchen search and discovery for renters
- Booking flow with Stripe Checkout
- Owner and renter dashboards
- Stripe Connect payouts to kitchen owners

## Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Project Structure

```
/app              # Next.js App Router pages and layouts
  /globals.css    # Global styles with Tailwind directives
  layout.tsx      # Root layout with header and footer
  page.tsx        # Home page
/public           # Static assets
next.config.js    # Next.js configuration
tailwind.config.ts # Tailwind configuration
tsconfig.json     # TypeScript configuration
```

## Environment Variables

See `.env.example` for required environment variables.

## Documentation

- **INSTALL.md** - Detailed setup instructions (coming soon)
- **DEPLOYMENT.md** - Deployment guide (coming soon)
- **API.md** - API documentation (coming soon)
- **SCHEMA.md** - Database schema documentation (coming soon)

## Sprint Progress

- [x] Sprint 0: Repo reset and scaffolding
- [ ] Sprint 1: Supabase integration and auth
- [ ] Sprint 2: Database schema and migrations
- [ ] Sprint 3: Kitchen owner onboarding
- [ ] Sprint 4: Search and discovery
- [ ] Sprint 5: Booking and payments
- [ ] Sprint 6: Dashboards
- [ ] Sprint 7: Polish and documentation

## License

Proprietary
