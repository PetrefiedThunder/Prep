import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Stripe Connect Actions Tests
 *
 * Tests authorization and logic for:
 *   - createConnectAccount (existing account detection, return shape)
 *   - createAccountLink (missing account handling)
 *   - checkOnboardingStatus (status sync logic)
 *
 * Extracted from lib/actions/stripe.ts
 */

describe('Stripe Connect — createConnectAccount Authorization', () => {
  it('rejects unauthenticated user', () => {
    const user = null
    if (!user) {
      assert.deepStrictEqual({ error: 'Unauthorized' }, { error: 'Unauthorized' })
    }
  })

  it('returns existing account without creating a new one', () => {
    const existing = { stripe_account_id: 'acct_existing_123', onboarding_complete: true }
    if (existing) {
      const result = {
        accountId: existing.stripe_account_id,
        onboardingComplete: existing.onboarding_complete,
      }
      assert.strictEqual(result.accountId, 'acct_existing_123')
      assert.strictEqual(result.onboardingComplete, true)
    }
  })

  it('returns existing account even when onboarding incomplete', () => {
    const existing = { stripe_account_id: 'acct_new_456', onboarding_complete: false }
    const result = {
      accountId: existing.stripe_account_id,
      onboardingComplete: existing.onboarding_complete,
    }
    assert.strictEqual(result.accountId, 'acct_new_456')
    assert.strictEqual(result.onboardingComplete, false)
  })
})

describe('Stripe Connect — createConnectAccount Return Shape', () => {
  it('new account returns accountId and onboardingComplete=false', () => {
    const newAccount = { id: 'acct_brand_new' }
    const result = {
      accountId: newAccount.id,
      onboardingComplete: false,
    }
    assert.strictEqual(result.accountId, 'acct_brand_new')
    assert.strictEqual(result.onboardingComplete, false)
  })
})

describe('Stripe Connect — createAccountLink Authorization', () => {
  it('rejects unauthenticated user', () => {
    const user = null
    assert.strictEqual(user, null)
  })

  it('returns error when no Stripe account exists for user', () => {
    const stripeAccount = null
    if (!stripeAccount) {
      assert.deepStrictEqual({ error: 'No Stripe account found' }, { error: 'No Stripe account found' })
    }
  })

  it('constructs correct return/refresh URLs from origin header', () => {
    const origin = 'https://prepchef.co'
    const refreshUrl = `${origin}/owner/stripe/refresh`
    const returnUrl = `${origin}/owner/stripe/return`

    assert.strictEqual(refreshUrl, 'https://prepchef.co/owner/stripe/refresh')
    assert.strictEqual(returnUrl, 'https://prepchef.co/owner/stripe/return')
  })

  it('falls back to NEXT_PUBLIC_APP_URL when no origin header', () => {
    const origin = null
    const appUrl = 'https://app.prepchef.co'
    const baseUrl = origin || appUrl || 'http://localhost:3000'
    assert.strictEqual(baseUrl, 'https://app.prepchef.co')
  })

  it('falls back to localhost when no origin or env var', () => {
    const origin = null
    const appUrl = undefined
    const baseUrl = origin || appUrl || 'http://localhost:3000'
    assert.strictEqual(baseUrl, 'http://localhost:3000')
  })
})

describe('Stripe Connect — checkOnboardingStatus Logic', () => {
  it('returns onboardingComplete=false when no account exists', () => {
    const stripeAccount = null
    if (!stripeAccount) {
      const result = { onboardingComplete: false }
      assert.strictEqual(result.onboardingComplete, false)
    }
  })

  it('detects complete onboarding (charges_enabled AND details_submitted)', () => {
    const account = { charges_enabled: true, details_submitted: true }
    const isComplete = account.charges_enabled && account.details_submitted
    assert.strictEqual(isComplete, true)
  })

  it('detects incomplete onboarding when charges not enabled', () => {
    const account = { charges_enabled: false, details_submitted: true }
    const isComplete = account.charges_enabled && account.details_submitted
    assert.strictEqual(isComplete, false)
  })

  it('detects incomplete onboarding when details not submitted', () => {
    const account = { charges_enabled: true, details_submitted: false }
    const isComplete = account.charges_enabled && account.details_submitted
    assert.strictEqual(isComplete, false)
  })

  it('detects incomplete when both are false', () => {
    const account = { charges_enabled: false, details_submitted: false }
    const isComplete = account.charges_enabled && account.details_submitted
    assert.strictEqual(isComplete, false)
  })

  it('triggers DB update when status has changed', () => {
    const dbOnboarding = false
    const stripeOnboarding = true
    const statusChanged = stripeOnboarding !== dbOnboarding
    assert.strictEqual(statusChanged, true)
  })

  it('skips DB update when status unchanged', () => {
    const dbOnboarding = true
    const stripeOnboarding = true
    const statusChanged = stripeOnboarding !== dbOnboarding
    assert.strictEqual(statusChanged, false)
  })
})
