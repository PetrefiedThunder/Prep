'use server'

import { createClient } from '@/lib/supabase/server'
import { stripe, validateStripeKey } from '@/lib/stripe'
import { headers } from 'next/headers'

export async function createConnectAccount() {
  // Validate Stripe configuration at runtime
  validateStripeKey()

  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  // Check if account already exists
  const { data: existing } = await supabase
    .from('stripe_accounts')
    .select('stripe_account_id, onboarding_complete')
    .eq('user_id', user.id)
    .single()

  if (existing) {
    return {
      accountId: existing.stripe_account_id,
      onboardingComplete: existing.onboarding_complete
    }
  }

  // Create new Stripe Connect account
  const account = await stripe.accounts.create({
    type: 'standard',
    email: user.email,
  })

  // Store in database
  await supabase
    .from('stripe_accounts')
    .insert({
      user_id: user.id,
      stripe_account_id: account.id,
      onboarding_complete: false,
    })

  return {
    accountId: account.id,
    onboardingComplete: false
  }
}

export async function createAccountLink() {
  // Validate Stripe configuration at runtime
  validateStripeKey()

  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  const { data: stripeAccount } = await supabase
    .from('stripe_accounts')
    .select('stripe_account_id')
    .eq('user_id', user.id)
    .single()

  if (!stripeAccount) {
    return { error: 'No Stripe account found' }
  }

  const headersList = await headers()
  const origin = headersList.get('origin') || process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'

  const accountLink = await stripe.accountLinks.create({
    account: stripeAccount.stripe_account_id,
    refresh_url: `${origin}/owner/stripe/refresh`,
    return_url: `${origin}/owner/stripe/return`,
    type: 'account_onboarding',
  })

  return { url: accountLink.url }
}

export async function checkOnboardingStatus() {
  // Validate Stripe configuration at runtime
  validateStripeKey()

  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  const { data: stripeAccount } = await supabase
    .from('stripe_accounts')
    .select('stripe_account_id, onboarding_complete')
    .eq('user_id', user.id)
    .single()

  if (!stripeAccount) {
    return { onboardingComplete: false }
  }

  // Check with Stripe API
  const account = await stripe.accounts.retrieve(stripeAccount.stripe_account_id)

  const isComplete = account.charges_enabled && account.details_submitted

  // Update database if status changed
  if (isComplete !== stripeAccount.onboarding_complete) {
    await supabase
      .from('stripe_accounts')
      .update({ onboarding_complete: isComplete })
      .eq('user_id', user.id)
  }

  return {
    onboardingComplete: isComplete,
    accountId: stripeAccount.stripe_account_id
  }
}
