import assert from 'node:assert'
import { describe, it, mock } from 'node:test'
import { createLogEntry, logger } from '../lib/logger'

describe('logger', () => {
  it('redacts known secret keys and patterns', () => {
    const entry = createLogEntry('error', 'Webhook failed', {
      metadata: {
        apiKey: 'sk_test_12345abcde',
        nested: { token: 'Bearer secret-token-value' },
        safe: 'ok',
      },
      error: new Error('Failed with client_secret_98765'),
    })

    assert.equal(entry.metadata?.apiKey, '[REDACTED]')
    assert.equal((entry.metadata as any).nested.token, '[REDACTED]')
    assert.equal(entry.metadata?.safe, 'ok')
    assert.deepStrictEqual(entry.error, {
      name: 'Error',
      message: '[REDACTED]',
    })
  })

  it('keeps whitelisted fields untouched', () => {
    const entry = createLogEntry('info', 'Booking exists', {
      metadata: {
        paymentIntentId: 'pi_123',
        eventType: 'checkout.session.completed',
        status: 'confirmed',
      },
    })

    assert.equal(entry.metadata?.paymentIntentId, 'pi_123')
    assert.equal(entry.metadata?.eventType, 'checkout.session.completed')
    assert.equal(entry.metadata?.status, 'confirmed')
  })

  it('logs structured output without leaking secrets on error path', async () => {
    const output: string[] = []
    const restore = mock.method(console, 'error', (value: string) => {
      output.push(value)
    })

    logger.error('Failed to verify webhook signature', {
      metadata: {
        stripeSecretKey: 'rk_test_super_secret',
        requestId: 'req_123',
      },
      error: new Error('token sk_live_very_secret leaked'),
    })

    restore.mock.restore()

    assert.equal(output.length, 1)
    const parsed = JSON.parse(output[0])
    assert.equal(parsed.message, 'Failed to verify webhook signature')
    assert.equal(parsed.metadata.stripeSecretKey, '[REDACTED]')
    assert.equal(parsed.metadata.requestId, 'req_123')
    assert.deepStrictEqual(parsed.error, { name: 'Error', message: '[REDACTED]' })
  })
})
