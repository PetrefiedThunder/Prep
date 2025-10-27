import { test, expect } from '@playwright/test';
import crypto from 'node:crypto';
import { createApp } from '../../prepchef/services/payments-svc/src/index';

const STRIPE_SECRET_KEY = 'sk_test_e2e_secret_key';
const STRIPE_WEBHOOK_SECRET = 'whsec_e2e_test_secret';

type PaymentsApp = Awaited<ReturnType<typeof createApp>>;

let app: PaymentsApp;

function createSignedWebhookPayload(bookingId: string, paymentIntentId: string, amount: number, currency: string) {
  const event = {
    id: `evt_${crypto.randomUUID()}`,
    type: 'payment_intent.succeeded',
    data: {
      object: {
        id: paymentIntentId,
        metadata: {
          booking_id: bookingId
        },
        amount,
        currency,
        status: 'succeeded',
        client_secret: `pi_secret_${crypto.randomUUID()}`,
        created: Math.floor(Date.now() / 1000)
      }
    }
  };

  const payload = JSON.stringify(event);
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const signature = crypto
    .createHmac('sha256', STRIPE_WEBHOOK_SECRET)
    .update(`${timestamp}.${payload}`, 'utf8')
    .digest('hex');

  return {
    payload,
    headers: {
      'content-type': 'application/json',
      'stripe-signature': `t=${timestamp},v1=${signature}`
    }
  } as const;
}

function resetInMemoryState(instance: PaymentsApp) {
  instance.paymentIntents.clear();
  instance.bookingPayments.clear();
}

test.describe('Booking payment intent lifecycle', () => {
  test.beforeAll(async () => {
    process.env.STRIPE_SECRET_KEY = STRIPE_SECRET_KEY;
    process.env.STRIPE_API_KEY = STRIPE_SECRET_KEY;
    process.env.STRIPE_WEBHOOK_SECRET = STRIPE_WEBHOOK_SECRET;

    app = await createApp();
    await app.ready();
  });

  test.afterAll(async () => {
    await app.close();
    delete process.env.STRIPE_SECRET_KEY;
    delete process.env.STRIPE_API_KEY;
    delete process.env.STRIPE_WEBHOOK_SECRET;
  });

  test.beforeEach(() => {
    resetInMemoryState(app);
  });

  test('marks booking as paid once Stripe webhook succeeds', async () => {
    test.slow();

    const bookingId = `booking-${crypto.randomUUID()}`;
    const amountCents = 12500;

    const intentResponse = await app.inject({
      method: 'POST',
      url: '/intents',
      payload: {
        amount_cents: amountCents,
        metadata: {
          booking_id: bookingId
        }
      }
    });

    expect(intentResponse.statusCode).toBe(201);
    const intentBody = intentResponse.json() as {
      id: string;
      amount: number;
      currency: string;
      status: string;
      client_secret: string;
    };

    const bookingStateBefore = app.bookingPayments.get(bookingId);
    expect(bookingStateBefore).toBeDefined();
    expect(bookingStateBefore?.paid).toBe(false);
    expect(bookingStateBefore?.paymentIntentId).toBe(intentBody.id);

    const { payload, headers } = createSignedWebhookPayload(
      bookingId,
      intentBody.id,
      intentBody.amount,
      intentBody.currency
    );

    const webhookResponse = await app.inject({
      method: 'POST',
      url: '/payments/webhook',
      payload,
      headers
    });

    expect(webhookResponse.statusCode).toBe(200);
    expect(webhookResponse.json()).toEqual({ received: true });

    const bookingStateAfter = app.bookingPayments.get(bookingId);
    expect(bookingStateAfter).toBeDefined();
    expect(bookingStateAfter?.paid).toBe(true);
    expect(bookingStateAfter?.paymentIntentId).toBe(intentBody.id);

    const storedIntent = app.paymentIntents.get(intentBody.id);
    expect(storedIntent).toBeDefined();
    expect(storedIntent?.paid).toBe(true);
    expect(storedIntent?.status).toBe('succeeded');
    expect(storedIntent?.metadata).toMatchObject({ booking_id: bookingId });
  });
});
