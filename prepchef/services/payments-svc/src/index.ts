import Fastify from 'fastify';
import Stripe from 'stripe';
import { getPrismaClient } from '@prep/database';
import { log } from '@prep/logger';
import { prepSecurityPlugin } from '@prep/common';
import { z } from 'zod';

const CreatePaymentIntentSchema = z.object({
  booking_id: z.string().uuid(),
  amount_cents: z.number().int().positive()
});

type RawStripeBody = {
  raw: string;
  parsed: Stripe.Event;
};

// Initialize Stripe with API key from env
const stripeSecretKey = process.env.STRIPE_SECRET_KEY || '';
if (!stripeSecretKey) {
  log.warn('[payments-svc] STRIPE_SECRET_KEY not configured, payments will fail');
}

const stripe = new Stripe(stripeSecretKey, {
  apiVersion: '2024-11-20.acacia',
  typescript: true
});

const prisma = getPrismaClient();

export async function createApp() {
  const app = Fastify({ logger: false });
  await app.register(prepSecurityPlugin, {
    serviceName: 'payments-svc'
  });

  app.get('/healthz', async () => ({ ok: true, svc: 'payments-svc' }));

  // Create payment intent for booking
  app.post('/intents', async (req, reply) => {
    const parsed = CreatePaymentIntentSchema.safeParse(req.body);

    if (!parsed.success) {
      return reply.code(400).send({
        error: 'Invalid request body',
        details: parsed.error.flatten().fieldErrors
      });
    }

    const { booking_id, amount_cents } = parsed.data;

    if (!stripeSecretKey) {
      return reply.code(503).send({ error: 'Stripe not configured' });
    }

    try {
      // Atomically check and reserve booking for payment (prevents double-charge race)
      // Uses optimistic locking: only update if status is still 'requested'
      const booking = await prisma.booking.update({
        where: {
          id: booking_id,
          status: 'requested',
          stripePaymentIntentId: null // Only if no payment intent exists yet
        },
        data: {
          paymentStatus: 'pending' // Reserve for payment creation
        }
      }).catch((error) => {
        // If update fails, booking doesn't exist or is in wrong state
        return null;
      });

      if (!booking) {
        // Check if booking exists to provide better error message
        const existingBooking = await prisma.booking.findUnique({
          where: { id: booking_id }
        });

        if (!existingBooking) {
          return reply.code(404).send({ error: 'Booking not found' });
        }

        if (existingBooking.stripePaymentIntentId) {
          return reply.code(409).send({
            error: 'Payment intent already exists for this booking',
            payment_intent_id: existingBooking.stripePaymentIntentId
          });
        }

        return reply.code(400).send({ error: 'Booking not in valid state for payment' });
      }

      // Create Stripe PaymentIntent (booking is now locked to this request)
      const paymentIntent = await stripe.paymentIntents.create({
        amount: amount_cents,
        currency: 'usd',
        metadata: {
          booking_id,
          renter_id: booking.renterId,
          listing_id: booking.listingId
        },
        automatic_payment_methods: {
          enabled: true
        }
      });

      // Update booking with payment intent ID
      await prisma.booking.update({
        where: { id: booking_id },
        data: {
          stripePaymentIntentId: paymentIntent.id
        }
      });

      log.info('[payments-svc] Created PaymentIntent', {
        booking_id,
        payment_intent_id: paymentIntent.id,
        amount_cents
      });

      return reply.code(201).send({
        payment_intent_id: paymentIntent.id,
        client_secret: paymentIntent.client_secret,
        status: paymentIntent.status
      });

    } catch (error: any) {
      log.error('[payments-svc] Failed to create payment intent', { error: error.message, booking_id });
      return reply.code(500).send({ error: 'Failed to create payment intent' });
    }
  });

  // Stripe webhook handler
  app.register(async function webhookRoutes(instance) {
    // Custom content type parser for webhooks (need raw body)
    instance.addContentTypeParser('application/json', { parseAs: 'string' }, (req, body, done) => {
      try {
        const bodyStr = typeof body === 'string' ? body : body.toString();
        const parsed = bodyStr.length > 0 ? JSON.parse(bodyStr) : {};
        done(null, { raw: bodyStr, parsed } satisfies RawStripeBody);
      } catch (err) {
        const error = err as Error;
        error.message = 'Invalid JSON payload';
        (error as any).statusCode = 400;
        done(error, undefined);
      }
    });

    instance.post('/webhook', async (req, reply) => {
      const stripeSignature = req.headers['stripe-signature'];
      const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

      if (typeof stripeSignature !== 'string') {
        return reply.code(400).send({ error: 'Missing Stripe-Signature header' });
      }

      if (!webhookSecret) {
        instance.log.error('[payments-svc] STRIPE_WEBHOOK_SECRET not configured');
        return reply.code(500).send({ error: 'Webhook secret not configured' });
      }

      const body = req.body as RawStripeBody;
      if (!body || typeof body.raw !== 'string') {
        return reply.code(400).send({ error: 'Invalid webhook payload' });
      }

      let event: Stripe.Event;

      try {
        // Verify webhook signature
        event = stripe.webhooks.constructEvent(body.raw, stripeSignature, webhookSecret);
      } catch (err: any) {
        instance.log.error('[payments-svc] Webhook signature verification failed', { error: err.message });
        return reply.code(400).send({ error: 'Invalid signature' });
      }

      // Idempotency: Try to insert event atomically
      // On conflict (duplicate event_id), the event was already processed
      try {
        await prisma.$executeRaw`
          INSERT INTO stripe_webhook_events (event_id, type, data, created_at)
          VALUES (${event.id}, ${event.type}, ${JSON.stringify(event.data.object)}::jsonb, NOW())
        `;
      } catch (error: any) {
        // Check if this is a unique constraint violation
        if (error.code === '23505' || error.message?.includes('unique constraint')) {
          log.info('[payments-svc] Webhook event already processed (duplicate delivery)', {
            event_id: event.id
          });
          return reply.code(200).send({ received: true });
        }
        // Other database errors should fail
        throw error;
      }

      // Handle payment_intent.succeeded
      if (event.type === 'payment_intent.succeeded') {
        const paymentIntent = event.data.object as Stripe.PaymentIntent;
        const bookingId = paymentIntent.metadata.booking_id;

        if (bookingId) {
          try {
            await prisma.booking.update({
              where: { id: bookingId },
              data: {
                paymentStatus: 'captured',
                status: 'confirmed',
                paidAt: new Date()
              }
            });

            log.info('[payments-svc] Booking confirmed after payment', {
              booking_id: bookingId,
              payment_intent_id: paymentIntent.id
            });

            // TODO: Trigger notification service
          } catch (error: any) {
            log.error('[payments-svc] Failed to update booking after payment', {
              booking_id: bookingId,
              error: error.message
            });
          }
        }
      }

      // Handle payment_intent.payment_failed
      if (event.type === 'payment_intent.payment_failed') {
        const paymentIntent = event.data.object as Stripe.PaymentIntent;
        const bookingId = paymentIntent.metadata.booking_id;

        if (bookingId) {
          try {
            await prisma.booking.update({
              where: { id: bookingId },
              data: {
                paymentStatus: 'failed'
              }
            });

            log.warn('[payments-svc] Payment failed for booking', {
              booking_id: bookingId,
              payment_intent_id: paymentIntent.id
            });
          } catch (error: any) {
            log.error('[payments-svc] Failed to update booking after payment failure', {
              booking_id: bookingId,
              error: error.message
            });
          }
        }
      }

      return reply.code(200).send({ received: true });
    });
  }, { prefix: '/payments' });

  app.addHook('onClose', async () => {
    await prisma.$disconnect();
  });

  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 0) || Math.floor(Math.random() * 1000) + 3000;
  createApp().then(app => app.listen({ port }).then(() => log.info('payments-svc listening', { port })));
}
