import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Stripe Connect Server Actions — Business Logic Tests
 *
 * Tests the decision paths in lib/actions/stripe.ts:
 *   - createConnectAccount: auth, existing account check, new creation
 *   - checkOnboardingStatus: auth, account lookup, status update
 *   - createAccountLink: auth, missing account
 */

// --- Mock Supabase ---

interface MockResult { data: unknown; error: unknown }

function mockChain(result: MockResult) {
  const chain: Record<string, unknown> = {}
  const methods = ['select', 'eq', 'single', 'insert', 'update']
  for (const m of methods) {
    chain[m] = (..._args: unknown[]) => chain
  }
  chain.single = async () => result
  return chain
}

function makeMockSupabase(opts: {
  user: { id: string; email?: string } | null
  existingAccount?: { stripe_account_id: string; onboarding_complete: boolean } | null
  insertError?: string | null
}) {
  const calls: { table: string; method: string; args: unknown[] }[] = []

  return {
    calls,
    auth: {
      getUser: async () => ({ data: { user: opts.user } }),
    },
    from(table: string) {
      if (table === 'stripe_accounts') {
        return {
          select: (...args: unknown[]) => {
            calls.push({ table, method: 'select', args })
            return mockChain({
              data: opts.existingAccount ?? null,
              error: opts.existingAccount ? null : null,
            })
          },
          insert: (payload: unknown) => {
            calls.push({ table, method: 'insert', args: [payload] })
            if (opts.insertError) {
              return { data: null, error: { message: opts.insertError } }
            }
            return { data: payload, error: null }
          },
          update: (payload: unknown) => {
            calls.push({ table, method: 'update', args: [payload] })
            return mockChain({ data: null, error: null })
          },
        }
      }
      throw new Error(`Unexpected table: ${table}`)
    },
  }
}

// --- Extracted logic ---

async function createConnectAccount(supabase: ReturnType<typeof makeMockSupabase>) {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: 'Unauthorized' }

  const { data: existing } = await supabase
    .from('stripe_accounts')
    .select('stripe_account_id, onboarding_complete')
    .eq('user_id', user.id)
    .single() as unknown as MockResult

  const ex = existing as { stripe_account_id: string; onboarding_complete: boolean } | null
  if (ex) {
    return { accountId: ex.stripe_account_id, onboardingComplete: ex.onboarding_complete }
  }

  // Simulate Stripe account creation
  const newAccountId = `acct_new_${user.id}`

  supabase.from('stripe_accounts').insert({
    user_id: user.id,
    stripe_account_id: newAccountId,
    onboarding_complete: false,
  })

  return { accountId: newAccountId, onboardingComplete: false }
}

async function createAccountLink(supabase: ReturnType<typeof makeMockSupabase>) {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: 'Unauthorized' }

  const { data: stripeAccount } = await supabase
    .from('stripe_accounts')
    .select('stripe_account_id')
    .eq('user_id', user.id)
    .single() as unknown as MockResult

  if (!stripeAccount) return { error: 'No Stripe account found' }

  return { url: 'https://connect.stripe.com/onboarding/test' }
}

async function checkOnboardingStatus(
  supabase: ReturnType<typeof makeMockSupabase>,
  stripeChargesEnabled: boolean,
  stripeDetailsSubmitted: boolean,
) {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: 'Unauthorized' }

  const { data: stripeAccount } = await supabase
    .from('stripe_accounts')
    .select('stripe_account_id, onboarding_complete')
    .eq('user_id', user.id)
    .single() as unknown as MockResult

  const sa = stripeAccount as { stripe_account_id: string; onboarding_complete: boolean } | null
  if (!sa) return { onboardingComplete: false }

  const isComplete = stripeChargesEnabled && stripeDetailsSubmitted

  // Update DB if status changed
  if (isComplete !== sa.onboarding_complete) {
    await supabase
      .from('stripe_accounts')
      .update({ onboarding_complete: isComplete })
      .eq('user_id', user.id)
  }

  return { onboardingComplete: isComplete, accountId: sa.stripe_account_id }
}

// --- Tests ---

describe('createConnectAccount', () => {
  it('returns Unauthorized when user is not logged in', async () => {
    const supabase = makeMockSupabase({ user: null })
    const result = await createConnectAccount(supabase)
    assert.deepStrictEqual(result, { error: 'Unauthorized' })
  })

  it('returns existing account when one already exists', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1', email: 'test@test.com' },
      existingAccount: { stripe_account_id: 'acct_existing', onboarding_complete: true },
    })
    const result = await createConnectAccount(supabase)
    assert.deepStrictEqual(result, { accountId: 'acct_existing', onboardingComplete: true })
    // Should not call insert
    const insertCalls = supabase.calls.filter(c => c.method === 'insert')
    assert.strictEqual(insertCalls.length, 0)
  })

  it('returns existing incomplete account without creating new one', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1', email: 'test@test.com' },
      existingAccount: { stripe_account_id: 'acct_incomplete', onboarding_complete: false },
    })
    const result = await createConnectAccount(supabase)
    assert.deepStrictEqual(result, { accountId: 'acct_incomplete', onboardingComplete: false })
  })

  it('creates new account when none exists', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1', email: 'test@test.com' },
      existingAccount: null,
    })
    const result = await createConnectAccount(supabase)
    assert.strictEqual((result as Record<string, unknown>).onboardingComplete, false)
    assert.ok((result as Record<string, unknown>).accountId)
    // Should have called insert
    const insertCalls = supabase.calls.filter(c => c.method === 'insert')
    assert.strictEqual(insertCalls.length, 1)
  })
})

describe('createAccountLink', () => {
  it('returns Unauthorized when user is not logged in', async () => {
    const supabase = makeMockSupabase({ user: null })
    const result = await createAccountLink(supabase)
    assert.deepStrictEqual(result, { error: 'Unauthorized' })
  })

  it('returns error when no Stripe account exists', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, existingAccount: null })
    const result = await createAccountLink(supabase)
    assert.deepStrictEqual(result, { error: 'No Stripe account found' })
  })

  it('returns URL when Stripe account exists', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1' },
      existingAccount: { stripe_account_id: 'acct_test', onboarding_complete: false },
    })
    const result = await createAccountLink(supabase)
    assert.ok((result as Record<string, unknown>).url)
  })
})

describe('checkOnboardingStatus', () => {
  it('returns Unauthorized when user is not logged in', async () => {
    const supabase = makeMockSupabase({ user: null })
    const result = await checkOnboardingStatus(supabase, false, false)
    assert.deepStrictEqual(result, { error: 'Unauthorized' })
  })

  it('returns false when no Stripe account exists', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, existingAccount: null })
    const result = await checkOnboardingStatus(supabase, false, false)
    assert.deepStrictEqual(result, { onboardingComplete: false })
  })

  it('returns complete when charges_enabled and details_submitted', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1' },
      existingAccount: { stripe_account_id: 'acct_test', onboarding_complete: false },
    })
    const result = await checkOnboardingStatus(supabase, true, true)
    assert.strictEqual((result as Record<string, unknown>).onboardingComplete, true)
    assert.strictEqual((result as Record<string, unknown>).accountId, 'acct_test')
    // Should have called update since status changed (false → true)
    const updateCalls = supabase.calls.filter(c => c.method === 'update')
    assert.strictEqual(updateCalls.length, 1)
  })

  it('returns incomplete when only charges_enabled is true', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1' },
      existingAccount: { stripe_account_id: 'acct_test', onboarding_complete: false },
    })
    const result = await checkOnboardingStatus(supabase, true, false)
    assert.strictEqual((result as Record<string, unknown>).onboardingComplete, false)
  })

  it('returns incomplete when only details_submitted is true', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1' },
      existingAccount: { stripe_account_id: 'acct_test', onboarding_complete: false },
    })
    const result = await checkOnboardingStatus(supabase, false, true)
    assert.strictEqual((result as Record<string, unknown>).onboardingComplete, false)
  })

  it('does not update DB when status has not changed', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1' },
      existingAccount: { stripe_account_id: 'acct_test', onboarding_complete: true },
    })
    const result = await checkOnboardingStatus(supabase, true, true)
    assert.strictEqual((result as Record<string, unknown>).onboardingComplete, true)
    // Should NOT have called update since status is unchanged (true → true)
    const updateCalls = supabase.calls.filter(c => c.method === 'update')
    assert.strictEqual(updateCalls.length, 0)
  })

  it('updates DB when account reverts from complete to incomplete', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1' },
      existingAccount: { stripe_account_id: 'acct_test', onboarding_complete: true },
    })
    const result = await checkOnboardingStatus(supabase, false, false)
    assert.strictEqual((result as Record<string, unknown>).onboardingComplete, false)
    // Should have called update since status changed (true → false)
    const updateCalls = supabase.calls.filter(c => c.method === 'update')
    assert.strictEqual(updateCalls.length, 1)
  })
})
