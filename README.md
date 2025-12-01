# PrepChef - Commercial Kitchen Rental Marketplace

A lean, modern two-sided marketplace connecting culinary entrepreneurs with commercial kitchen space.

## Overview

PrepChef is a complete rebuild focused on core marketplace functionality. This MVP enables kitchen owners to list their spaces and receive bookings from culinary entrepreneurs, with integrated payments via Stripe Connect.

**Before**: 223,753 lines of over-engineered code with regulatory engines, Python microservices, Kubernetes orchestration, and complex observability stacks.

**After**: ~3,500 lines of focused Next.js code delivering core marketplace value.

**Code Reduction**: 97%+ reduction while delivering production-ready MVP.

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | Next.js 14 (App Router) | Server and client components |
| Language | TypeScript | Type safety throughout |
| Styling | TailwindCSS | Utility-first styling |
| Database | Supabase (PostgreSQL) | Managed Postgres with RLS |
| Authentication | Supabase Auth | Email/password auth |
| Payments | Stripe Connect | Two-sided marketplace payments |
| Hosting | Vercel | Serverless deployment |

## Features

### For Kitchen Owners

- **Onboarding**: Create profile and connect Stripe account for payouts
- **Listings**: Create and manage kitchen listings with photos, pricing, and details
- **Dashboard**: View all listings, toggle active/inactive status
- **Bookings**: See all upcoming and past bookings for owned kitchens
- **Payouts**: Automatic payout tracking with 90% revenue (10% platform fee)

### For Renters

- **Discovery**: Search kitchens by city, price range, and availability
- **Booking**: Reserve kitchen time with secure Stripe Checkout
- **Dashboard**: View all upcoming and past bookings
- **Payments**: Pay with credit card via Stripe

### Platform Features

- **Row Level Security**: Database-enforced access control
- **Server Actions**: Type-safe mutations with `'use server'`
- **Real-time Auth**: Automatic session refresh via middleware
- **Webhook Handling**: Idempotent booking creation from Stripe
- **Responsive Design**: Mobile-friendly TailwindCSS layouts

## Database Schema

Six core tables with comprehensive RLS policies:

1. **profiles** - User accounts (extends Supabase auth)
2. **kitchens** - Kitchen listings with location and pricing
3. **kitchen_photos** - Photo URLs for kitchen listings
4. **stripe_accounts** - Stripe Connect account linking
5. **bookings** - Confirmed reservations with payment info
6. **payouts** - Owner payout tracking

See [SCHEMA.md](./SCHEMA.md) for complete documentation.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser Client                        │
│  Next.js Pages → Server Actions → Supabase Client (Browser) │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       Vercel Edge                            │
│  Middleware (Auth Refresh) → Server Actions → API Routes    │
└─────────────────────────────────────────────────────────────┘
                              ↓
         ┌────────────────────┴────────────────────┐
         ↓                                          ↓
┌──────────────────────┐                 ┌──────────────────────┐
│   Supabase Cloud     │                 │    Stripe API        │
│  - PostgreSQL + RLS  │                 │  - Connect Accounts  │
│  - Auth (JWT)        │                 │  - Checkout Sessions │
│  - Storage (ready)   │                 │  - Webhooks          │
└──────────────────────┘                 └──────────────────────┘
```

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Supabase account
- Stripe account

### Installation

```bash
# Clone repository
git clone https://github.com/PetrefiedThunder/Prep.git
cd Prep

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your Supabase and Stripe keys

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the app.

### Full Setup Guide

See [INSTALL.md](./INSTALL.md) for complete local development setup including:
- Supabase project creation and schema setup
- Stripe Connect configuration
- Webhook testing with Stripe CLI
- Troubleshooting common issues

## Documentation

| Document | Purpose |
|----------|---------|
| [INSTALL.md](./INSTALL.md) | Complete local development setup |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Production deployment to Vercel |
| [API.md](./API.md) | Server actions and API routes |
| [SCHEMA.md](./SCHEMA.md) | Database tables, columns, and RLS policies |

## Deployment

Deploy to Vercel in minutes:

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variables
vercel env add NEXT_PUBLIC_SUPABASE_URL
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY
vercel env add STRIPE_SECRET_KEY
vercel env add STRIPE_WEBHOOK_SECRET

# Deploy to production
vercel --prod
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete production setup.

## Testing

```bash
# Build check (type checking + compilation)
npm run build

# Type checking only
npm run type-check

# Linting
npm run lint
```

## Sprint Progress

- [x] **Sprint 0**: Repository reset and Next.js scaffolding
- [x] **Sprint 1**: Supabase integration and authentication
- [x] **Sprint 2**: Database schema with RLS policies
- [x] **Sprint 3**: Kitchen owner onboarding and CRUD
- [x] **Sprint 4**: Kitchen search and discovery
- [x] **Sprint 5**: Stripe Connect and checkout flow
- [x] **Sprint 6**: Owner and renter dashboards
- [x] **Sprint 7**: Documentation and polish

**Status**: MVP Complete ✅

## Cost Breakdown

### Free Tier (Development)

- **Vercel**: Free hobby plan
- **Supabase**: Free tier (500MB database, 50MB storage)
- **Stripe**: No monthly fees, pay-per-transaction

**Total**: $0/month (pay only Stripe fees on transactions)

### Production (Growth)

- **Vercel Pro**: $20/month (custom domain, analytics)
- **Supabase Pro**: $25/month (8GB database, 100GB storage)
- **Stripe**: 2.9% + $0.30 per transaction

**Total**: ~$45/month + transaction fees

## Security Features

- **Row Level Security**: All tables enforce user-based access control
- **JWT Validation**: Every request validates Supabase auth token
- **Webhook Signatures**: Stripe webhook requests verified via signature
- **Environment Variables**: No secrets committed to repository
- **HTTPS Only**: Supabase and Stripe require HTTPS in production
- **SQL Injection Prevention**: Supabase client uses parameterized queries

## Design Philosophy

### What This MVP Includes

✅ Kitchen listing CRUD
✅ Search and discovery
✅ Stripe Connect onboarding
✅ Booking with Stripe Checkout
✅ Owner/renter dashboards
✅ Webhook-based booking creation
✅ Comprehensive documentation

### What This MVP Excludes

❌ Regulatory compliance engines
❌ Complex ETL pipelines
❌ Kubernetes orchestration
❌ AI integrations
❌ Advanced analytics
❌ Multi-tenant architecture
❌ Complex observability stacks

This lean approach delivers core marketplace value with minimal complexity.

## Roadmap

### Phase 2 (Post-MVP)

- Photo upload to Supabase Storage
- Calendar availability management
- Email notifications
- Reviews and ratings
- Advanced search filters
- Mobile app

### Phase 3 (Scale)

- Multi-city expansion
- Kitchen verification process
- Insurance integration
- Analytics dashboard
- Referral program

## Project Metrics

- **Lines of Code**: ~3,500 (vs 223,753 before)
- **Files**: ~40 (vs hundreds before)
- **Dependencies**: 15 (vs 100+ before)
- **Build Time**: <30 seconds
- **Time to Market**: 1 week (vs months before)

## Contributing

This is a proprietary project. External contributions are not accepted at this time.

## License

Proprietary - All Rights Reserved

## Support

For issues or questions, contact the development team.

---

**Built with**: Next.js 14, TypeScript, Supabase, Stripe Connect, TailwindCSS
**Repository**: https://github.com/PetrefiedThunder/Prep
**Version**: 1.0.0 (MVP)
