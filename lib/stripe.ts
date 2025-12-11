import Stripe from 'stripe'

// Allow build to succeed without env vars in development (runtime will fail in prod without proper keys)
const stripeSecretKey =
  process.env.STRIPE_SECRET_KEY ??
  (process.env.NODE_ENV === 'development'
    ? 'sk_test_placeholder'
    : (() => {
        throw new Error('STRIPE_SECRET_KEY is not set')
      })())

export const stripe = new Stripe(stripeSecretKey, {
  apiVersion: '2023-10-16' as unknown as Stripe.StripeConfig['apiVersion'],
})
