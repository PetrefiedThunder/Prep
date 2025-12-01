# Deployment Guide - PrepChef

This guide covers deploying PrepChef to production using Vercel and Supabase.

## Overview

PrepChef is optimized for deployment on:
- **Frontend/Backend**: Vercel (Next.js hosting)
- **Database/Auth**: Supabase (PostgreSQL + Auth)
- **Payments**: Stripe (Connect + Checkout)

This stack provides:
- Zero infrastructure management
- Automatic HTTPS
- Global CDN
- Auto-scaling
- Built-in monitoring

## Prerequisites

- Completed local setup (see [INSTALL.md](./INSTALL.md))
- GitHub account
- Vercel account (free tier available)
- Production Supabase project
- Production Stripe account

## Step 1: Prepare Your Repository

### 1.1 Push to GitHub

```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

### 1.2 Verify Build

Before deploying, ensure your app builds successfully:

```bash
npm run build
```

Fix any errors before proceeding.

## Step 2: Set Up Production Supabase

### 2.1 Create Production Project

1. Go to [supabase.com](https://supabase.com)
2. Create a new project (use a strong password)
3. Wait for setup to complete

### 2.2 Apply Database Schema

1. Go to SQL Editor in Supabase Dashboard
2. Copy contents of `supabase/schema.sql`
3. Run the SQL to create all tables and policies

### 2.3 Configure Auth Settings

1. Go to **Authentication** → **URL Configuration**
2. Set **Site URL** to your production domain (e.g., `https://prepchef.com`)
3. Add to **Redirect URLs**:
   - `https://your-domain.com/auth/callback`
   - `https://your-domain.vercel.app/auth/callback`

### 2.4 Enable Email Templates (Optional)

1. Go to **Authentication** → **Email Templates**
2. Customize confirmation and password reset emails
3. Add your branding

### 2.5 Get Production Credentials

From **Settings** → **API**:
- Project URL
- anon/public key
- service_role key (keep secure!)

## Step 3: Set Up Production Stripe

### 3.1 Activate Your Stripe Account

1. Complete Stripe account activation
2. Add business details
3. Add bank account for payouts

### 3.2 Switch to Live Mode

1. In Stripe Dashboard, toggle from Test to **Live mode**
2. Go to **Developers** → **API keys**
3. Copy your **live** keys:
   - Publishable key (starts with `pk_live_`)
   - Secret key (starts with `sk_live_`)

### 3.3 Configure Live Webhook

1. Go to **Developers** → **Webhooks**
2. Add endpoint: `https://your-domain.com/api/webhooks/stripe`
3. Select event: `checkout.session.completed`
4. Copy the **signing secret** (starts with `whsec_`)

### 3.4 Configure Connect Settings

1. Go to **Connect** → **Settings**
2. Add your branding
3. Set business details
4. Configure payout schedule (optional)

## Step 4: Deploy to Vercel

### 4.1 Create Vercel Account

1. Go to [vercel.com](https://vercel.com)
2. Sign up with GitHub

### 4.2 Import Project

1. Click **Add New** → **Project**
2. Import your GitHub repository
3. Vercel will auto-detect Next.js

### 4.3 Configure Build Settings

Framework Preset: **Next.js** (auto-detected)
- Build Command: `next build`
- Output Directory: `.next` (auto-configured)
- Install Command: `npm install`

### 4.4 Add Environment Variables

In the Vercel project settings, add all environment variables:

```env
# Supabase (Production)
NEXT_PUBLIC_SUPABASE_URL=https://your-prod-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-prod-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-prod-service-role-key

# Stripe (Live Mode)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Application
NEXT_PUBLIC_APP_URL=https://your-domain.vercel.app
```

**Important:**
- Use your production Supabase credentials
- Use Stripe **live mode** keys
- Set `NEXT_PUBLIC_APP_URL` to your Vercel deployment URL

### 4.5 Deploy

Click **Deploy**

Vercel will:
1. Clone your repository
2. Install dependencies
3. Build the application
4. Deploy to global CDN

Deployment usually takes 1-2 minutes.

## Step 5: Configure Custom Domain (Optional)

### 5.1 Add Domain in Vercel

1. Go to your project → **Settings** → **Domains**
2. Add your custom domain (e.g., `prepchef.com`)
3. Follow Vercel's DNS configuration instructions

### 5.2 Update Environment Variables

After adding a custom domain:

```env
NEXT_PUBLIC_APP_URL=https://prepchef.com
```

Redeploy for changes to take effect.

### 5.3 Update Supabase Redirect URLs

In Supabase Dashboard:
- Add `https://prepchef.com/auth/callback` to allowed redirect URLs

### 5.4 Update Stripe Webhook

In Stripe Dashboard:
- Update webhook endpoint to `https://prepchef.com/api/webhooks/stripe`

## Step 6: Post-Deployment Verification

### 6.1 Test Authentication

1. Visit your deployed site
2. Sign up with a real email
3. Confirm email
4. Log in

### 6.2 Test Kitchen Creation

1. Create a kitchen listing
2. Upload photos (if using Supabase Storage)
3. Verify listing appears in search

### 6.3 Test Stripe Connect

1. Go through Stripe onboarding as a kitchen owner
2. Use real business information
3. Verify account activation

### 6.4 Test Booking Flow

**For initial testing, use Stripe test cards:**
- Card: `4242 4242 4242 4242`
- Any future expiry, any CVC

For production testing:
- Create a test booking
- Verify booking appears in dashboards
- Check Stripe dashboard for payment

### 6.5 Verify Webhooks

1. Make a test booking
2. Check Vercel logs for webhook calls
3. Verify booking created in database
4. Check Stripe Dashboard → **Webhooks** for delivery status

## Step 7: Monitoring and Maintenance

### 7.1 Vercel Monitoring

Access via Vercel Dashboard:
- Real-time logs
- Build logs
- Function execution logs
- Error tracking

### 7.2 Supabase Monitoring

Access via Supabase Dashboard:
- Database health
- Query performance
- Auth logs
- Storage usage

### 7.3 Stripe Monitoring

Monitor in Stripe Dashboard:
- Payment success rates
- Failed payments
- Webhook delivery
- Payout status

## Scaling Considerations

### Database

Supabase free tier includes:
- 500MB database
- 50MB file storage
- 2GB bandwidth

For growth:
- Upgrade to Pro tier ($25/mo)
- Add database indexes as needed
- Monitor query performance

### Vercel

Free tier includes:
- 100GB bandwidth
- Unlimited deployments
- Automatic scaling

For growth:
- Upgrade to Pro tier ($20/mo)
- Add team members
- Custom domain SSL included

### Stripe

No monthly fees, just transaction fees:
- 2.9% + $0.30 per successful charge
- Plus Connect fees for platform

## Security Checklist

Before going live:

- [ ] Environment variables are set correctly
- [ ] Service role key is kept secret
- [ ] Stripe webhook signature verification is enabled
- [ ] HTTPS is enforced (automatic with Vercel)
- [ ] Row Level Security is enabled on all Supabase tables
- [ ] Email confirmation is required for signups
- [ ] Stripe is in live mode with real keys
- [ ] Custom domain has SSL (automatic with Vercel)
- [ ] Database backups are configured (Supabase automatic)

## Rollback Procedure

If you need to rollback a deployment:

### In Vercel:
1. Go to **Deployments**
2. Find previous working deployment
3. Click **⋯** → **Promote to Production**

### Database Schema:
- Supabase maintains automatic backups
- Download a backup before major schema changes
- Test schema migrations in development first

## Continuous Deployment

Vercel automatically deploys when you push to GitHub:

```bash
git add .
git commit -m "Feature: Add new functionality"
git push origin main
```

Vercel will:
1. Detect the push
2. Build the new version
3. Run tests (if configured)
4. Deploy if successful

## Troubleshooting Production Issues

### 500 Errors

Check Vercel logs:
```
https://vercel.com/your-team/your-project/logs
```

Common causes:
- Missing environment variables
- Database connection issues
- Stripe key mismatch

### Webhook Failures

In Stripe Dashboard → **Webhooks**:
- Check delivery attempts
- View request/response
- Retry failed events

### Authentication Issues

Check Supabase logs and verify:
- Redirect URLs are correct
- Email templates are working
- SMTP is configured (if custom)

### Database Errors

In Supabase Dashboard:
- Check query logs
- Verify RLS policies
- Monitor connection pool

## Performance Optimization

### Next.js

- Static pages are automatically cached by Vercel CDN
- API routes run at the edge
- Images are automatically optimized

### Database

- Add indexes for frequently queried fields
- Use Supabase connection pooling
- Monitor slow queries in dashboard

### Caching

Vercel automatically caches:
- Static assets (CSS, JS, images)
- Static pages
- API responses (with headers)

## Cost Estimation

For a small marketplace (< 1000 users):

| Service | Tier | Cost |
|---------|------|------|
| Vercel | Free | $0/mo |
| Supabase | Free | $0/mo |
| Stripe | Pay-as-you-go | 2.9% + $0.30 per transaction |

For growth (1000+ users):

| Service | Tier | Cost |
|---------|------|------|
| Vercel | Pro | $20/mo |
| Supabase | Pro | $25/mo |
| Stripe | Pay-as-you-go | 2.9% + $0.30 per transaction |

**Total fixed costs:** $45/mo + transaction fees

## Support Resources

- **Vercel**: [vercel.com/docs](https://vercel.com/docs)
- **Supabase**: [supabase.com/docs](https://supabase.com/docs)
- **Stripe**: [stripe.com/docs](https://stripe.com/docs)
- **Next.js**: [nextjs.org/docs](https://nextjs.org/docs)

---

**Your PrepChef marketplace is now live!** 🚀
