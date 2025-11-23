/**
 * Refund Endpoint (C11)
 * POST /api/bookings/:id/refund
 */

import { FastifyInstance } from 'fastify';
import { z } from 'zod';
import Stripe from 'stripe';
import { Pool } from 'pg';
import { ApiError } from '@prep/common';
import { log } from '@prep/logger';

const RefundSchema = z.object({
  amount_cents: z.number().int().positive().optional(),
  reason: z.enum(['requested_by_customer', 'duplicate', 'fraudulent']).optional()
});

export default async function (app: FastifyInstance) {
  const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '', {
    apiVersion: '2023-10-16'
  });

  const db = new Pool({
    connectionString: process.env.DATABASE_URL
  });

  app.post('/api/bookings/:id/refund', async (req, reply) => {
    const { id: bookingId } = req.params as { id: string };
    const parsed = RefundSchema.safeParse(req.body);

    if (!parsed.success) {
      return reply.code(400).send(ApiError('PC-REQ-400', 'Invalid request body'));
    }

    const { amount_cents, reason } = parsed.data;

    try {
      // Get booking with payment intent
      const bookingResult = await db.query(
        'SELECT * FROM bookings WHERE booking_id = $1',
        [bookingId]
      );

      if (bookingResult.rows.length === 0) {
        return reply.code(404).send(ApiError('PC-BOOK-404', 'Booking not found'));
      }

      const booking = bookingResult.rows[0];

      if (!booking.payment_intent_id) {
        return reply.code(400).send(ApiError('PC-PAY-400', 'Booking has no associated payment'));
      }

      if (booking.status === 'cancelled') {
        return reply.code(400).send(ApiError('PC-BOOK-400', 'Booking already cancelled'));
      }

      // Create Stripe refund
      const refund = await stripe.refunds.create({
        payment_intent: booking.payment_intent_id,
        amount: amount_cents, // Undefined = full refund
        reason: reason || 'requested_by_customer'
      });

      // Update booking and payout records
      await db.query('BEGIN');

      // Mark booking as cancelled
      await db.query(
        `UPDATE bookings SET status = 'cancelled', updated_at = NOW() WHERE booking_id = $1`,
        [bookingId]
      );

      // Record refund
      await db.query(
        `INSERT INTO refunds (
          refund_id,
          booking_id,
          payment_intent_id,
          amount_cents,
          reason,
          created_at
        ) VALUES ($1, $2, $3, $4, $5, NOW())`,
        [refund.id, bookingId, booking.payment_intent_id, refund.amount, reason || 'requested_by_customer']
      );

      await db.query('COMMIT');

      log.info('Refund processed', {
        booking_id: bookingId,
        refund_id: refund.id,
        amount_cents: refund.amount
      });

      return reply.code(200).send({
        refund_id: refund.id,
        booking_id: bookingId,
        amount_cents: refund.amount,
        status: refund.status
      });

    } catch (error: any) {
      await db.query('ROLLBACK');
      log.error('Refund failed', { booking_id: bookingId, error });

      if (error.type === 'StripeInvalidRequestError') {
        return reply.code(400).send(ApiError('PC-PAY-400', error.message));
      }

      return reply.code(500).send(ApiError('PC-BOOK-500', 'Unexpected error'));
    }
  });

  app.addHook('onClose', async () => {
    await db.end();
  });
}
