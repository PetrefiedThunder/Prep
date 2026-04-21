import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Tests for Stripe configuration validation logic.
 *
 * We extract and test the pure validation functions rather than importing
 * from lib/stripe.ts directly (which instantiates a Stripe client at
 * module level).
 */

// Extracted validation logic mirrors lib/stripe.ts → validateStripeKey()
function validateStripeKey(env: { STRIPE_SECRET_KEY?: string; NODE_ENV?: string }) {
  if (!env.STRIPE_SECRET_KEY && env.NODE_ENV === 'production') {
    throw new Error('STRIPE_SECRET_KEY is not set in production environment')
  }
}

// Extracted validation logic mirrors route.ts → validateSupabaseConfig()
function validateSupabaseConfig(env: {
  NEXT_PUBLIC_SUPABASE_URL?: string
  SUPABASE_SERVICE_ROLE_KEY?: string
}) {
  if (!env.NEXT_PUBLIC_SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error('Supabase environment variables are not set')
  }
}

describe('validateStripeKey', () => {
  it('throws in production when STRIPE_SECRET_KEY is missing', () => {
    assert.throws(
      () => validateStripeKey({ NODE_ENV: 'production' }),
      { message: 'STRIPE_SECRET_KEY is not set in production environment' }
    )
  })

  it('throws in production when STRIPE_SECRET_KEY is empty string', () => {
    assert.throws(
      () => validateStripeKey({ STRIPE_SECRET_KEY: '', NODE_ENV: 'production' }),
      { message: 'STRIPE_SECRET_KEY is not set in production environment' }
    )
  })

  it('does not throw in development without STRIPE_SECRET_KEY', () => {
    assert.doesNotThrow(() => validateStripeKey({ NODE_ENV: 'development' }))
  })

  it('does not throw in test without STRIPE_SECRET_KEY', () => {
    assert.doesNotThrow(() => validateStripeKey({ NODE_ENV: 'test' }))
  })

  it('does not throw in production when key is present', () => {
    assert.doesNotThrow(
      () => validateStripeKey({ STRIPE_SECRET_KEY: 'sk_test_123', NODE_ENV: 'production' })
    )
  })

  it('does not throw when NODE_ENV is undefined', () => {
    assert.doesNotThrow(() => validateStripeKey({}))
  })
})

describe('validateSupabaseConfig', () => {
  it('throws when both env vars are missing', () => {
    assert.throws(
      () => validateSupabaseConfig({}),
      { message: 'Supabase environment variables are not set' }
    )
  })

  it('throws when SUPABASE_SERVICE_ROLE_KEY is missing', () => {
    assert.throws(
      () => validateSupabaseConfig({ NEXT_PUBLIC_SUPABASE_URL: 'https://x.supabase.co' }),
      { message: 'Supabase environment variables are not set' }
    )
  })

  it('throws when NEXT_PUBLIC_SUPABASE_URL is missing', () => {
    assert.throws(
      () => validateSupabaseConfig({ SUPABASE_SERVICE_ROLE_KEY: 'key123' }),
      { message: 'Supabase environment variables are not set' }
    )
  })

  it('does not throw when both are present', () => {
    assert.doesNotThrow(() =>
      validateSupabaseConfig({
        NEXT_PUBLIC_SUPABASE_URL: 'https://x.supabase.co',
        SUPABASE_SERVICE_ROLE_KEY: 'key123',
      })
    )
  })
})
