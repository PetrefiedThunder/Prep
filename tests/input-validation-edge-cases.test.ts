import assert from 'node:assert'
import { describe, it } from 'node:test'
import { createRequire } from 'node:module'

// Import CJS module in ESM context
const require = createRequire(import.meta.url)
const { sanitizeString, sanitizeKitchenPayload } = require('../middleware/request_validation')

/**
 * Input Validation — Extended Edge Cases
 *
 * Extends request_validation.test.js with edge cases:
 *   - Unicode handling
 *   - Empty/null/undefined inputs
 *   - Very long strings
 *   - Nested XSS attempts
 *   - Kitchen payload boundary values
 */

describe('sanitizeString — Edge Cases', () => {
  it('returns empty string for non-string input (number)', () => {
    const result = sanitizeString(123 as unknown as string)
    assert.strictEqual(result, '')
  })

  it('returns empty string for null input', () => {
    const result = sanitizeString(null as unknown as string)
    assert.strictEqual(result, '')
  })

  it('returns empty string for undefined input', () => {
    const result = sanitizeString(undefined as unknown as string)
    assert.strictEqual(result, '')
  })

  it('returns empty string for boolean input', () => {
    const result = sanitizeString(true as unknown as string)
    assert.strictEqual(result, '')
  })

  it('trims leading and trailing whitespace', () => {
    const result = sanitizeString('  hello  ')
    assert.strictEqual(result, 'hello')
  })

  it('trims tabs and newlines', () => {
    const result = sanitizeString('\thello\n')
    assert.strictEqual(result, 'hello')
  })

  it('handles empty string', () => {
    const result = sanitizeString('')
    assert.strictEqual(result, '')
  })

  it('handles string with only whitespace', () => {
    const result = sanitizeString('   ')
    assert.strictEqual(result, '')
  })

  it('preserves Unicode characters (Chinese)', () => {
    const result = sanitizeString('厨房 Kitchen')
    assert.strictEqual(result, '厨房 Kitchen')
  })

  it('preserves Unicode characters (emoji)', () => {
    const result = sanitizeString('My Kitchen 🍳')
    assert.strictEqual(result, 'My Kitchen 🍳')
  })

  it('preserves accented characters', () => {
    const result = sanitizeString('Café résumé')
    assert.strictEqual(result, 'Café résumé')
  })

  it('escapes all five special characters', () => {
    const result = sanitizeString('&<>"\' all special')
    assert.strictEqual(result, '&amp;&lt;&gt;&quot;&#39; all special')
  })

  it('handles nested XSS attempt', () => {
    const result = sanitizeString('<scr<script>ipt>alert(1)</scr</script>ipt>')
    // All < and > should be escaped regardless of nesting
    assert.ok(!result.includes('<'))
    assert.ok(!result.includes('>'))
  })

  it('escapes javascript: protocol in attribute', () => {
    const result = sanitizeString('<a href="javascript:alert(1)">click</a>')
    assert.ok(!result.includes('<a'))
    assert.ok(result.includes('&lt;a'))
  })

  it('handles very long strings without error', () => {
    const longString = 'A'.repeat(10000)
    const result = sanitizeString(longString)
    assert.strictEqual(result.length, 10000)
  })

  it('handles string with only special characters', () => {
    const result = sanitizeString('<>&"\'')
    assert.strictEqual(result, '&lt;&gt;&amp;&quot;&#39;')
  })
})

describe('sanitizeKitchenPayload — Boundary Values', () => {
  it('preserves numeric zero for price_per_hour', () => {
    const payload = {
      title: 'Free Kitchen',
      description: '',
      address: '123 Main',
      city: 'Austin',
      state: 'TX',
      zip_code: '78701',
      price_per_hour: 0,
      max_capacity: 1,
    }
    const result = sanitizeKitchenPayload(payload)
    assert.strictEqual(result.price_per_hour, 0)
  })

  it('preserves negative price (validation should be at app layer)', () => {
    const payload = {
      title: 'Test',
      description: '',
      address: '123 Main',
      city: 'Austin',
      state: 'TX',
      zip_code: '78701',
      price_per_hour: -10,
      max_capacity: 5,
    }
    const result = sanitizeKitchenPayload(payload)
    // sanitizeKitchenPayload only sanitizes strings, not numeric validation
    assert.strictEqual(result.price_per_hour, -10)
  })

  it('handles undefined description gracefully', () => {
    const payload = {
      title: 'Test',
      description: undefined,
      address: '123 Main',
      city: 'Austin',
      state: 'TX',
      zip_code: '78701',
      price_per_hour: 50,
      max_capacity: 5,
    }
    const result = sanitizeKitchenPayload(payload)
    // description: sanitizeString(data.description ?? '')
    assert.strictEqual(result.description, '')
  })

  it('handles null description gracefully', () => {
    const payload = {
      title: 'Test',
      description: null,
      address: '123 Main',
      city: 'Austin',
      state: 'TX',
      zip_code: '78701',
      price_per_hour: 50,
      max_capacity: 5,
    }
    const result = sanitizeKitchenPayload(payload)
    assert.strictEqual(result.description, '')
  })

  it('sanitizes all string fields simultaneously', () => {
    const payload = {
      title: '<script>',
      description: '<img onerror=alert(1)>',
      address: '<b>bold</b>',
      city: 'O\'Fallon',
      state: 'TX & OK',
      zip_code: '"78701"',
      price_per_hour: 50,
      max_capacity: 5,
    }
    const result = sanitizeKitchenPayload(payload)
    assert.ok(!result.title.includes('<'))
    assert.ok(!result.description.includes('<'))
    assert.ok(!result.address.includes('<'))
    assert.ok(result.city.includes('&#39;'))
    assert.ok(result.state.includes('&amp;'))
    assert.ok(result.zip_code.includes('&quot;'))
  })

  it('preserves square_feet as undefined when not provided', () => {
    const payload = {
      title: 'Test',
      description: '',
      address: '123 Main',
      city: 'Austin',
      state: 'TX',
      zip_code: '78701',
      price_per_hour: 50,
      max_capacity: 5,
    }
    const result = sanitizeKitchenPayload(payload)
    assert.strictEqual(result.square_feet, undefined)
  })
})
