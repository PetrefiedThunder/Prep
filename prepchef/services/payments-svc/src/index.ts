import Fastify from 'fastify';
import { log } from '@prep/logger';
import { prepSecurityPlugin } from '@prep/common';
import crypto from 'node:crypto';

interface StoredPaymentIntent {
  id: string;
  amount: number;
  currency: string;
  status: string;
  client_secret: string;
  metadata: Record<string, unknown>;
  created: number;
  paid: boolean;
  bookingId?: string;
}

interface BookingPaymentState {
  paid: boolean;
  paymentIntentId?: string;
}

type StripeEvent = {
  id?: string;
  type?: string;
  data?: {
    object?: {
      id?: string;
      metadata?: Record<string, unknown>;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  [key: string]: unknown;
};

type RawStripeBody = {
  raw: string;
  parsed: StripeEvent;
};

declare module 'fastify' {
  interface FastifyInstance {
    paymentIntents: Map<string, StoredPaymentIntent>;
    bookingPayments: Map<string, BookingPaymentState>;
  }
}

function parseStripeSignatureHeader(header: string): { timestamp?: string; signature?: string } {
  const parts = header.split(',');
  let timestamp: string | undefined;
  let signature: string | undefined;

  for (const part of parts) {
    const [key, value] = part.split('=');
    if (key === 't' && value) {
      timestamp = value;
    } else if (key === 'v1' && value) {
      signature = value;
    }
  }

  return { timestamp, signature };
}

function verifyStripeSignature(payload: string, header: string, secret: string): boolean {
  const { timestamp, signature } = parseStripeSignatureHeader(header);
  if (!timestamp || !signature) return false;

  const signedPayload = `${timestamp}.${payload}`;
  const expected = crypto.createHmac('sha256', secret).update(signedPayload, 'utf8').digest('hex');

  let actual: Buffer;
  try {
    actual = Buffer.from(signature, 'hex');
  } catch {
    return false;
  }

  if (actual.length === 0 || actual.length !== expected.length / 2) {
    return false;
  }

  const expectedBuffer = Buffer.from(expected, 'hex');
  if (expectedBuffer.length !== actual.length) {
    return false;
  }

  return crypto.timingSafeEqual(expectedBuffer, actual);
}

export async function createApp() {
  const app = Fastify({ logger: false });
  await app.register(prepSecurityPlugin, {
    serviceName: 'payments-svc'
  });

  app.decorate('paymentIntents', new Map<string, StoredPaymentIntent>());
  app.decorate('bookingPayments', new Map<string, BookingPaymentState>());

  app.get('/healthz', async () => ({ ok: true, svc: 'payments-svc' }));

  app.post('/intents', async (req, reply) => {
    const { amount_cents, metadata } = req.body as any;
    if (!amount_cents || amount_cents <= 0) {
      return reply.code(400).send({
        error: 'Invalid amount',
        message: 'Amount must be positive'
      });
    }
    const sanitizedMetadata = (metadata && typeof metadata === 'object' && !Array.isArray(metadata))
      ? metadata as Record<string, unknown>
      : {};
    const bookingIdFromSnake = typeof sanitizedMetadata['booking_id'] === 'string'
      ? sanitizedMetadata['booking_id'] as string
      : undefined;
    const bookingIdFromCamel = typeof sanitizedMetadata['bookingId'] === 'string'
      ? sanitizedMetadata['bookingId'] as string
      : undefined;
    const bookingId = bookingIdFromSnake ?? bookingIdFromCamel;

    const paymentIntent = {
      id: `pi_${crypto.randomUUID().replace(/-/g, '')}`,
      amount: amount_cents,
      currency: 'usd',
      status: 'requires_payment_method',
      client_secret: `pi_secret_${crypto.randomUUID().replace(/-/g, '')}`,
      metadata: sanitizedMetadata,
      created: Date.now()
    };
    app.paymentIntents.set(paymentIntent.id, {
      ...paymentIntent,
      metadata: paymentIntent.metadata,
      paid: false,
      bookingId
    });

    if (bookingId) {
      app.bookingPayments.set(bookingId, {
        paid: false,
        paymentIntentId: paymentIntent.id
      });
    }

    return reply.code(201).send(paymentIntent);
  });

  app.register(async function routes(instance) {
    instance.get('/', async () => ({ name: 'payments-svc' }));
  });

  await app.register(async function webhookRoutes(instance) {
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
      if (typeof stripeSignature !== 'string') {
        return reply.code(400).send({ error: 'Missing Stripe-Signature header' });
      }

      const secret = process.env.STRIPE_WEBHOOK_SECRET;
      if (!secret) {
        instance.log.error('STRIPE_WEBHOOK_SECRET is not configured');
        return reply.code(500).send({ error: 'Webhook secret not configured' });
      }

      const body = req.body as RawStripeBody;
      if (!body || typeof body.raw !== 'string' || typeof body.parsed !== 'object' || body.parsed === null) {
        return reply.code(400).send({ error: 'Invalid webhook payload' });
      }

      if (!verifyStripeSignature(body.raw, stripeSignature, secret)) {
        return reply.code(400).send({ error: 'Invalid Stripe signature' });
      }

      if (body.parsed.type === 'payment_intent.succeeded' && body.parsed.data?.object) {
        const paymentIntentId = typeof body.parsed.data.object.id === 'string' ? body.parsed.data.object.id : undefined;
        const rawMetadata = body.parsed.data.object.metadata;
        const metadata = (rawMetadata && typeof rawMetadata === 'object' && !Array.isArray(rawMetadata))
          ? (rawMetadata as Record<string, unknown>)
          : {};
        const bookingIdFromSnake = typeof metadata['booking_id'] === 'string' ? metadata['booking_id'] as string : undefined;
        const bookingIdFromCamel = typeof metadata['bookingId'] === 'string' ? metadata['bookingId'] as string : undefined;
        const bookingId = bookingIdFromSnake
          ? bookingIdFromSnake
          : bookingIdFromCamel
            ? bookingIdFromCamel
            : app.paymentIntents.get(paymentIntentId ?? '')?.bookingId;

        if (paymentIntentId) {
          const storedIntent = app.paymentIntents.get(paymentIntentId);
          if (storedIntent) {
            storedIntent.status = 'succeeded';
            storedIntent.paid = true;
            if (bookingId) {
              storedIntent.bookingId = bookingId;
              storedIntent.metadata = {
                ...storedIntent.metadata,
                booking_id: bookingId
              };
            }
            app.paymentIntents.set(paymentIntentId, storedIntent);
          } else {
            app.paymentIntents.set(paymentIntentId, {
              id: paymentIntentId,
              amount: typeof body.parsed.data.object.amount === 'number' ? body.parsed.data.object.amount : 0,
              currency: typeof body.parsed.data.object.currency === 'string' ? body.parsed.data.object.currency : 'usd',
              status: typeof body.parsed.data.object.status === 'string' ? body.parsed.data.object.status : 'succeeded',
              client_secret: typeof body.parsed.data.object.client_secret === 'string' ? body.parsed.data.object.client_secret : '',
              metadata,
              created: typeof body.parsed.data.object.created === 'number' ? body.parsed.data.object.created : Date.now(),
              paid: true,
              bookingId
            });
          }
        }

        if (bookingId) {
          app.bookingPayments.set(bookingId, {
            paid: true,
            paymentIntentId: paymentIntentId
          });
        }
      }

      return reply.code(200).send({ received: true });
    });
  }, { prefix: '/payments' });

  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 0) || Math.floor(Math.random() * 1000) + 3000;
  createApp().then(app => app.listen({ port }).then(() => log.info('payments-svc listening', { port })));
}
