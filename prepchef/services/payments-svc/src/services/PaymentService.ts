/**
 * PaymentService (C10)
 * Handles Stripe payment intent creation with idempotency
 */

import Stripe from 'stripe';
import { Pool } from 'pg';
import { randomUUID } from 'crypto';
import { log } from '@prep/logger';

export class PaymentService {
  private stripe: Stripe;

  constructor(
    private db: Pool,
    stripeSecretKey: string
  ) {
    this.stripe = new Stripe(stripeSecretKey, {
      apiVersion: '2025-10-29.clover'
    });
  }

  async createPaymentIntent(bookingId: string, amountCents: number): Promise<Stripe.PaymentIntent> {
    // Generate idempotency key for this booking
    const idempotencyKey = `booking-${bookingId}-${Date.now()}`;

    try {
      // Create Stripe payment intent
      const paymentIntent = await this.stripe.paymentIntents.create(
        {
          amount: amountCents,
          currency: 'usd',
          metadata: {
            booking_id: bookingId
          },
          automatic_payment_methods: {
            enabled: true
          }
        },
        {
          idempotencyKey
        }
      );

      // Persist payment intent to database
      await this.db.query(
        `INSERT INTO payment_intents (
          payment_intent_id,
          booking_id,
          amount_cents,
          currency,
          status,
          idempotency_key,
          created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, NOW())`,
        [
          paymentIntent.id,
          bookingId,
          amountCents,
          'usd',
          paymentIntent.status,
          idempotencyKey
        ]
      );

      log.info('Created payment intent', {
        payment_intent_id: paymentIntent.id,
        booking_id: bookingId,
        amount_cents: amountCents
      });

      return paymentIntent;
    } catch (error) {
      log.error('Failed to create payment intent', { booking_id: bookingId, error });
      throw error;
    }
  }

  async retrievePaymentIntent(paymentIntentId: string): Promise<Stripe.PaymentIntent> {
    return await this.stripe.paymentIntents.retrieve(paymentIntentId);
  }
}
