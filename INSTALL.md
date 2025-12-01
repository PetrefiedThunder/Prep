# Installation Guide - PrepChef

This guide will walk you through setting up PrepChef for local development.

## Prerequisites

- **Node.js** 18.x or later
- **npm** or **yarn**
- **Supabase account** (free tier available at [supabase.com](https://supabase.com))
- **Stripe account** (free test mode available at [stripe.com](https://stripe.com))

## Step 1: Clone the Repository

```bash
git clone https://github.com/PetrefiedThunder/Prep.git
cd Prep
```

## Step 2: Install Dependencies

```bash
npm install
```

This will install all required packages including:
- Next.js 14
- Supabase client libraries
- Stripe SDK
- TypeScript and TailwindCSS

## Step 3: Set Up Supabase

### 3.1 Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a free account
2. Create a new project
3. Wait for the project to finish setting up (usually takes 2-3 minutes)

### 3.2 Run the Database Schema

1. Open the Supabase Dashboard
2. Navigate to the SQL Editor
3. Copy the entire contents of `supabase/schema.sql`
4. Paste into the SQL Editor and click "Run"

This will create:
- All database tables (profiles, kitchens, kitchen_photos, bookings, payouts, stripe_accounts)
- Row Level Security policies
- Indexes for performance
- Triggers for auto-updating timestamps
- Auto-profile creation on user signup

### 3.3 Get Your Supabase Credentials

From your Supabase project dashboard:

1. Go to **Settings** → **API**
2. Copy the following values:
   - **Project URL** (starts with `https://`)
   - **anon/public key** (starts with `eyJ`)
   - **service_role key** (starts with `eyJ`, keep this secret!)

## Step 4: Set Up Stripe

### 4.1 Create a Stripe Account

1. Go to [stripe.com](https://stripe.com) and create an account
2. Activate your account (you can use test mode immediately)

### 4.2 Enable Stripe Connect

1. In Stripe Dashboard, go to **Connect** → **Settings**
2. Enable Standard accounts
3. Configure your branding (optional)

### 4.3 Get Your Stripe Keys

From Stripe Dashboard:

1. Go to **Developers** → **API keys**
2. Toggle to **Test mode** (recommended for development)
3. Copy:
   - **Publishable key** (starts with `pk_test_`)
   - **Secret key** (starts with `sk_test_`)

### 4.4 Set Up Webhook Endpoint

1. Go to **Developers** → **Webhooks**
2. Click **Add endpoint**
3. Endpoint URL: `http://localhost:3000/api/webhooks/stripe` (for local development)
4. Select events to listen for:
   - `checkout.session.completed`
5. Copy the **Signing secret** (starts with `whsec_`)

**Note:** For production, you'll need to update this to your deployed URL.

## Step 5: Configure Environment Variables

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and fill in your credentials:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...your-anon-key
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...your-service-role-key

# Stripe Configuration
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...your-publishable-key
STRIPE_SECRET_KEY=sk_test_...your-secret-key
STRIPE_WEBHOOK_SECRET=whsec_...your-webhook-secret

# Application Configuration
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

**Important:**
- Never commit `.env` to version control
- The `.env` file is already in `.gitignore`
- Use test mode keys for development

## Step 6: Run the Development Server

```bash
npm run dev
```

The application will start at [http://localhost:3000](http://localhost:3000)

## Step 7: Test the Setup

### 7.1 Test Authentication

1. Navigate to [http://localhost:3000](http://localhost:3000)
2. Click "Sign Up"
3. Create an account with your email
4. Check your email for the confirmation link
5. Confirm your email
6. Log in

### 7.2 Test Kitchen Creation

1. Log in to your account
2. Go to `/owner/kitchens`
3. Click "Add Kitchen"
4. Fill out the kitchen listing form
5. Submit

### 7.3 Test Stripe Connect (Optional)

1. Go to `/owner/stripe/onboard`
2. Click "Connect Stripe Account"
3. Follow the Stripe onboarding flow
4. Use Stripe test data:
   - Routing number: `110000000`
   - Account number: `000123456789`
   - SSN: `000-00-0000`

### 7.4 Test Booking Flow

1. Browse kitchens at `/kitchens`
2. Click on a kitchen
3. Click "Book This Kitchen"
4. Select a date and time
5. Use Stripe test card: `4242 4242 4242 4242`
   - Expiry: any future date
   - CVC: any 3 digits
   - ZIP: any 5 digits

## Troubleshooting

### "Module not found" errors

```bash
rm -rf node_modules .next
npm install
npm run dev
```

### "Database connection failed"

- Check that your Supabase URL and keys are correct
- Verify your Supabase project is running
- Check that the schema was applied successfully

### "Stripe webhook verification failed"

- Make sure `STRIPE_WEBHOOK_SECRET` is set correctly
- For local development, use Stripe CLI to forward webhooks:

```bash
stripe listen --forward-to localhost:3000/api/webhooks/stripe
# Copy the webhook signing secret and update STRIPE_WEBHOOK_SECRET
```

### Type checking fails

```bash
npm run type-check
```

Fix any reported issues before running the dev server.

### Database RLS issues

If you can't access data:
- Check that you're logged in
- Verify RLS policies in Supabase Dashboard
- Check browser console for errors

## Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run type checking
npm run type-check

# Run linter
npm run lint
```

## Next Steps

- Read [DEPLOYMENT.md](./DEPLOYMENT.md) for production deployment
- Read [API.md](./API.md) for API documentation
- Read [SCHEMA.md](./SCHEMA.md) for database schema details

## Getting Help

If you encounter issues:
1. Check this guide first
2. Review the error messages carefully
3. Check Supabase and Stripe dashboards for errors
4. Review the console logs in your browser and terminal

## Security Notes

- Never commit `.env` files
- Use test mode for development
- Keep your service role key secure
- Only use real payment information in production
- Enable Stripe webhook signature verification in production

---

**Happy building!** 🎉
