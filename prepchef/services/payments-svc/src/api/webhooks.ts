/**
 * Stripe Webhook Handler (B8)
 * Handles payment_intent.succeeded events with proper validation and error handling
 */

import { FastifyInstance } from 'fastify';
import Stripe from 'stripe';
import { Pool } from 'pg';
import { log } from '@prep/logger';

// Validation schema types
interface PaymentIntentMetadata {
  booking_id: string;
  user_id?: string;
  amount_cents?: string;
}

function isValidUUID(str: string): boolean {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
}

function validateMetadata(metadata: Stripe.Metadata): PaymentIntentMetadata | null {
  const bookingId = metadata.booking_id;

  if (!bookingId || typeof bookingId !== 'string') {
    return null;
  }

  if (!isValidUUID(bookingId)) {
    log.warn('Invalid booking_id format in metadata', { booking_id: bookingId });
    return null;
  }

  return {
    booking_id: bookingId,
    user_id: metadata.user_id as string | undefined,
    amount_cents: metadata.amount_cents as string | undefined,
  };
}

export default async function (app: FastifyInstance) {
  const stripeSecretKey = process.env.STRIPE_SECRET_KEY;
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  const databaseUrl = process.env.DATABASE_URL;

  // Validate required environment variables
  if (!stripeSecretKey) {
    log.error('STRIPE_SECRET_KEY environment variable is required');
    throw new Error('Missing STRIPE_SECRET_KEY');
  }
  if (!webhookSecret) {
    log.error('STRIPE_WEBHOOK_SECRET environment variable is required');
    throw new Error('Missing STRIPE_WEBHOOK_SECRET');
  }
  if (!databaseUrl) {
    log.error('DATABASE_URL environment variable is required');
    throw new Error('Missing DATABASE_URL');
  }

  const stripe = new Stripe(stripeSecretKey, {
    apiVersion: '2023-10-16'
  });

  const db = new Pool({
    connectionString: databaseUrl,
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000,
  });

  app.post('/webhooks/stripe', {
    config: {
      rawBody: true // Preserve raw body for signature verification
    }
  }, async (req, reply) => {
    const sig = req.headers['stripe-signature'];

    if (!sig) {
      log.warn('Missing stripe-signature header');
      return reply.code(400).send({ error: 'Missing stripe-signature header' });
    }

    let event: Stripe.Event;

    try {
      // Verify webhook signature
      const rawBody = (req.body as any).raw || JSON.stringify(req.body);
      event = stripe.webhooks.constructEvent(
        rawBody,
        sig,
        webhookSecret
      );
    } catch (err) {
      const error = err as Error;
      log.error('Webhook signature verification failed', error);
      return reply.code(400).send({ error: `Webhook Error: ${error.message}` });
    }

    // Handle payment_intent.succeeded
    if (event.type === 'payment_intent.succeeded') {
      const paymentIntent = event.data.object as Stripe.PaymentIntent;

      try {
        const metadata = validateMetadata(paymentIntent.metadata);

        if (!metadata) {
          log.warn('PaymentIntent missing or invalid booking_id in metadata', {
            payment_intent_id: paymentIntent.id,
            metadata: paymentIntent.metadata,
          });
          // Return 200 to acknowledge webhook, but log for investigation
          return reply.code(200).send({ received: true, warning: 'invalid_metadata' });
        }

        const { booking_id: bookingId } = metadata;

        // Update booking status to confirmed with idempotency check
        const result = await db.query(
          `UPDATE bookings
           SET status = 'confirmed',
               payment_intent_id = $1,
               updated_at = NOW()
           WHERE booking_id = $2
             AND status IN ('pending', 'hold')
           RETURNING booking_id, status, kitchen_id, user_id, amount_cents`,
          [paymentIntent.id, bookingId]
        );

        if (result.rows.length === 0) {
          // Critical: payment succeeded but booking not found or already processed
          log.error('PAYMENT_BOOKING_MISMATCH', {
            payment_intent_id: paymentIntent.id,
            booking_id: bookingId,
            amount: paymentIntent.amount,
            status: 'booking_not_found_or_already_processed',
          });

          // In production, send to dead letter queue for manual review
          // await dlq.send({
          //   event_type: 'payment_booking_mismatch',
          //   payment_intent_id: paymentIntent.id,
          //   booking_id: bookingId,
          //   timestamp: new Date().toISOString(),
          // });

          // Return 500 to trigger Stripe retry (they will retry failed webhooks)
          return reply.code(500).send({
            received: false,
            error: 'booking_not_found_or_already_processed'
          });
        }

        const booking = result.rows[0];

        log.info('Booking confirmed via Stripe webhook', {
          booking_id: bookingId,
          payment_intent_id: paymentIntent.id,
          amount: paymentIntent.amount,
          kitchen_id: booking.kitchen_id,
          user_id: booking.user_id,
        });

        // TODO: Trigger host notification asynchronously
        // await notificationService.notifyHost({
        //   booking_id: bookingId,
        //   event: 'booking_confirmed',
        //   amount: booking.amount_cents,
        // });

        return reply.code(200).send({ received: true, booking_id: bookingId });

      } catch (error) {
        log.error('Failed to process payment_intent.succeeded', error as Error, {
          payment_intent_id: paymentIntent.id,
        });
        return reply.code(500).send({ error: 'Internal server error' });
      }
    }

    // Acknowledge other event types
    log.debug('Received Stripe webhook event', {
      event_type: event.type,
      event_id: event.id,
    });
    return reply.code(200).send({ received: true });
  });

  app.addHook('onClose', async () => {
    await db.end();
    log.info('Database connection pool closed');
  });
}
