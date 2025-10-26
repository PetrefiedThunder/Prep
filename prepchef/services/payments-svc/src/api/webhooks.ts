/**
 * Stripe Webhook Handler (B8)
 * Handles payment_intent.succeeded events
 */

import { FastifyInstance } from 'fastify';
import Stripe from 'stripe';
import { Pool } from 'pg';
import { log } from '@prep/logger';

export default async function (app: FastifyInstance) {
  const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '', {
    apiVersion: '2024-12-18.acacia'
  });

  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET || '';

  const db = new Pool({
    connectionString: process.env.DATABASE_URL
  });

  app.post('/webhooks/stripe', {
    config: {
      rawBody: true // Preserve raw body for signature verification
    }
  }, async (req, reply) => {
    const sig = req.headers['stripe-signature'];

    if (!sig) {
      return reply.code(400).send({ error: 'Missing stripe-signature header' });
    }

    let event: Stripe.Event;

    try {
      // Verify webhook signature
      event = stripe.webhooks.constructEvent(
        req.rawBody as Buffer | string,
        sig,
        webhookSecret
      );
    } catch (err: any) {
      log.error('Webhook signature verification failed', err);
      return reply.code(400).send({ error: `Webhook Error: ${err.message}` });
    }

    // Handle payment_intent.succeeded
    if (event.type === 'payment_intent.succeeded') {
      const paymentIntent = event.data.object as Stripe.PaymentIntent;

      try {
        const bookingId = paymentIntent.metadata.booking_id;

        if (!bookingId) {
          log.warn('PaymentIntent missing booking_id in metadata', {
            payment_intent_id: paymentIntent.id
          });
          return reply.code(200).send({ received: true });
        }

        // Update booking status to confirmed
        const result = await db.query(
          `UPDATE bookings
           SET status = 'confirmed',
               payment_intent_id = $1,
               updated_at = NOW()
           WHERE booking_id = $2
           RETURNING *`,
          [paymentIntent.id, bookingId]
        );

        if (result.rows.length === 0) {
          log.warn('Booking not found for payment intent', {
            booking_id: bookingId,
            payment_intent_id: paymentIntent.id
          });
        } else {
          log.info('Booking confirmed via Stripe webhook', {
            booking_id: bookingId,
            payment_intent_id: paymentIntent.id
          });

          // TODO: Trigger host notification
        }

        return reply.code(200).send({ received: true });
      } catch (error) {
        log.error('Failed to process payment_intent.succeeded', error);
        return reply.code(500).send({ error: 'Internal server error' });
      }
    }

    // Acknowledge other event types
    return reply.code(200).send({ received: true });
  });

  app.addHook('onClose', async () => {
    await db.end();
  });
}
