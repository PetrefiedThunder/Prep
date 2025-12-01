import Stripe from 'stripe'

// Allow build to succeed without env vars (runtime will fail if actually used without proper keys)
const stripeSecretKey = process.env.STRIPE_SECRET_KEY || 'sk_test_placeholder'

export const stripe = new Stripe(stripeSecretKey, {
  apiVersion: '2025-11-17.clover',
  typescript: true,
})
