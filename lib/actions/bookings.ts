'use server'

import { createClient } from '@/lib/supabase/server'
import { stripe } from '@/lib/stripe'
import { headers } from 'next/headers'
// import { revalidatePath } from 'next/cache'

export async function createCheckoutSession(kitchenId: string, startTime: string, endTime: string) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  // Get kitchen details
  const { data: kitchen, error: kitchenError } = await supabase
    .from('kitchens')
    .select('*, profiles!kitchens_owner_id_fkey(id), stripe_accounts!stripe_accounts_user_id_fkey(stripe_account_id, onboarding_complete)')
    .eq('id', kitchenId)
    .single()

  if (kitchenError || !kitchen) {
    return { error: 'Kitchen not found' }
  }

  // Check that owner has Stripe Connect account
  const ownerStripeAccount = kitchen.stripe_accounts as { stripe_account_id: string; onboarding_complete: boolean } | null
  if (!ownerStripeAccount || !ownerStripeAccount.onboarding_complete) {
    return { error: 'Kitchen owner has not completed Stripe onboarding' }
  }

  // Calculate booking details
  const start = new Date(startTime)
  const end = new Date(endTime)
  const hours = (end.getTime() - start.getTime()) / (1000 * 60 * 60)

  if (hours <= 0) {
    return { error: 'Invalid booking times' }
  }

  const totalAmount = Math.round(hours * kitchen.price_per_hour * 100) // Stripe uses cents
  const platformFeePercent = 0.10 // 10% platform fee
  const platformFee = Math.round(totalAmount * platformFeePercent)

  const headersList = await headers()
  const origin = headersList.get('origin') || process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'

  // Create Stripe Checkout Session
  const session = await stripe.checkout.sessions.create({
    mode: 'payment',
    payment_method_types: ['card'],
    line_items: [
      {
        price_data: {
          currency: 'usd',
          product_data: {
            name: kitchen.title,
            description: `${hours} hour rental from ${start.toLocaleString()} to ${end.toLocaleString()}`,
          },
          unit_amount: totalAmount,
        },
        quantity: 1,
      },
    ],
    payment_intent_data: {
      application_fee_amount: platformFee,
      transfer_data: {
        destination: ownerStripeAccount.stripe_account_id,
      },
    },
    metadata: {
      kitchen_id: kitchenId,
      renter_id: user.id,
      start_time: startTime,
      end_time: endTime,
      total_hours: hours.toString(),
      price_per_hour: kitchen.price_per_hour.toString(),
    },
    success_url: `${origin}/bookings/success?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${origin}/kitchens/${kitchenId}`,
  })

  return { url: session.url }
}

export async function getUserBookings() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  const { data: bookings, error } = await supabase
    .from('bookings')
    .select(`
      *,
      kitchens (
        id,
        title,
        city,
        state,
        address
      )
    `)
    .eq('renter_id', user.id)
    .order('start_time', { ascending: false })

  if (error) {
    return { error: error.message }
  }

  return { data: bookings }
}

export async function getOwnerBookings() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized' }
  }

  const { data: bookings, error } = await supabase
    .from('bookings')
    .select(`
      *,
      kitchens!inner (
        id,
        title,
        owner_id
      ),
      profiles!bookings_renter_id_fkey (
        email,
        full_name
      )
    `)
    .eq('kitchens.owner_id', user.id)
    .order('start_time', { ascending: false })

  if (error) {
    return { error: error.message }
  }

  return { data: bookings }
}
