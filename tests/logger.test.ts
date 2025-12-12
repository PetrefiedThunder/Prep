import assert from 'node:assert'
import { describe, it, mock } from 'node:test'
import { logInfo, logError, maskIdentifier } from '../lib/logger'

describe('logger', () => {
  it('redacts sensitive keys in context', () => {
    const output: string[] = []
    const restore = mock.method(console, 'info', (...args: unknown[]) => {
      output.push(JSON.stringify(args))
    })

    logInfo('Test message', {
      apiKey: 'sk_test_12345abcde',
      secret: 'my-secret-value',
      safe: 'ok',
    })

    restore.mock.restore()

    assert.ok(output.length > 0)
    const logged = output[0]
    assert.ok(logged.includes('[redacted]'))
    assert.ok(logged.includes('ok'))
  })

  it('logs without context when none provided', () => {
    const output: string[] = []
    const restore = mock.method(console, 'info', (...args: unknown[]) => {
      output.push(JSON.stringify(args))
    })

    logInfo('Simple message')

    restore.mock.restore()

    assert.equal(output.length, 1)
    assert.ok(output[0].includes('Simple message'))
  })

  it('masks identifiers correctly', () => {
    assert.equal(maskIdentifier('sk_live_1234567890abcdef'), 'sk_liv…[redacted]')
    assert.equal(maskIdentifier('short'), '[redacted]')
    assert.equal(maskIdentifier(null), '[redacted]')
    assert.equal(maskIdentifier(undefined), '[redacted]')
  })

  it('logs errors with redacted sensitive data', () => {
    const output: string[] = []
    const restore = mock.method(console, 'error', (...args: unknown[]) => {
      output.push(JSON.stringify(args))
    })

    logError('Failed to verify webhook signature', {
      stripeSecretKey: 'rk_test_super_secret',
      requestId: 'req_123',
    })

    restore.mock.restore()

    assert.ok(output.length > 0)
    const logged = output[0]
    assert.ok(logged.includes('[redacted]'))
    assert.ok(logged.includes('req_123'))
  })
})
