import Stripe from 'stripe'

// Allow build to succeed without env vars - use placeholder during build, runtime will validate in production
const stripeSecretKey = process.env.STRIPE_SECRET_KEY || 'sk_test_placeholder_for_build'

// Validate at runtime when actually used (not at build time)
function validateStripeKey() {
  if (
    !process.env.STRIPE_SECRET_KEY &&
    process.env.NODE_ENV === 'production'
  ) {
    throw new Error('STRIPE_SECRET_KEY is not set in production environment')
  }
}

export const stripe = new Stripe(stripeSecretKey, {
  apiVersion: '2023-10-16' as unknown as Stripe.StripeConfig['apiVersion'],
})

// Export validation function so it can be called at runtime
export { validateStripeKey }
