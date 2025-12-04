import { maskIdentifier, logError, logInfo } from '@/lib/logger'
import { stripe } from '@/lib/stripe'
import { logger } from '@/lib/logger'
import { createClient } from '@/lib/supabase/server'
import { headers } from 'next/headers'
import { NextResponse } from 'next/server'
import Stripe from 'stripe'

export async function POST(req: Request) {
  const body = await req.text()
  const headersList = await headers()
  const signature = headersList.get('stripe-signature')

  if (!signature) {
    return NextResponse.json({ error: 'No signature' }, { status: 400 })
  }

  let event: Stripe.Event

  try {
    event = stripe.webhooks.constructEvent(
      body,
      signature,
      process.env.STRIPE_WEBHOOK_SECRET!,
    )
  } catch (err) {
    const error = err as Error
    logError('Webhook signature verification failed', { error: error.message })
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 })
  }

  // Handle the event
  if (event.type === 'checkout.session.completed') {
    const session = event.data.object as Stripe.Checkout.Session

    const metadata = session.metadata
    if (!metadata) {
      logError('Stripe session metadata missing', { sessionId: session.id })
      return NextResponse.json({ error: 'No metadata' }, { status: 400 })
    }

    const {
      kitchen_id,
      renter_id,
      start_time,
      end_time,
      total_hours,
      price_per_hour,
    } = metadata

    const totalAmount = session.amount_total! / 100 // Convert from cents

    // Create booking in database
    const supabase = await createClient()

    // Check for existing booking with this payment intent to prevent duplicates
    const paymentIntentId = session.payment_intent as string

    const { data: existing } = await supabase
      .from('bookings')
      .select('id')
      .eq('stripe_payment_intent_id', paymentIntentId)
      .single()

    if (existing) {
      logInfo('Booking already exists for payment intent', {
        paymentIntentId: maskIdentifier(paymentIntentId),
      })
      return NextResponse.json({ received: true })
    }

    const { data: booking, error } = await supabase
      .from('bookings')
      .insert({
        kitchen_id,
        renter_id,
        start_time,
        end_time,
        total_hours: parseFloat(total_hours),
        price_per_hour: parseFloat(price_per_hour),
        total_amount: totalAmount,
        status: 'confirmed',
        stripe_payment_intent_id: paymentIntentId,
      })
      .select()
      .single()

    if (error) {
      logError('Error creating booking', {
        error: error.message,
        paymentIntentId: maskIdentifier(paymentIntentId),
      })
      return NextResponse.json({ error: error.message }, { status: 500 })
    }

    logInfo('Booking created', {
      bookingId: booking.id,
      paymentIntentId: maskIdentifier(paymentIntentId),
    })

    // Create payout record
    const platformFeePercent = 0.10
    const platformFee = totalAmount * platformFeePercent
    const netAmount = totalAmount - platformFee

    // Get kitchen owner
    const { data: kitchen } = await supabase
      .from('kitchens')
      .select('owner_id')
      .eq('id', kitchen_id)
      .single()

    if (kitchen) {
      await supabase
        .from('payouts')
        .insert({
          booking_id: booking.id,
          owner_id: kitchen.owner_id,
          amount: totalAmount,
          platform_fee: platformFee,
          net_amount: netAmount,
          status: 'pending',
        })

      logInfo('Payout record created for booking', {
        bookingId: booking.id,
        ownerId: kitchen.owner_id,
      })
    }
  }

  return NextResponse.json({ received: true })
}
