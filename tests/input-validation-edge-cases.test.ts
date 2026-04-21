import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Input Validation Edge Cases
 *
 * Tests sanitizeString and sanitizeKitchenPayload with edge cases:
 *   - Unicode characters
 *   - Very long strings
 *   - Null / undefined / non-string inputs
 *   - Empty strings and whitespace-only
 *   - Nested XSS vectors
 *   - SQL injection-like patterns
 */

// Import CJS module using createRequire for ESM compatibility
import { createRequire } from 'node:module'
const require = createRequire(import.meta.url)
const { sanitizeString, sanitizeKitchenPayload } = require('../middleware/request_validation')

describe('sanitizeString edge cases', () => {
  it('returns empty string for null input', () => {
    assert.strictEqual(sanitizeString(null), '')
  })

  it('returns empty string for undefined input', () => {
    assert.strictEqual(sanitizeString(undefined), '')
  })

  it('returns empty string for numeric input', () => {
    assert.strictEqual(sanitizeString(42), '')
  })

  it('returns empty string for boolean input', () => {
    assert.strictEqual(sanitizeString(true), '')
  })

  it('returns empty string for object input', () => {
    assert.strictEqual(sanitizeString({}), '')
  })

  it('returns empty string for array input', () => {
    assert.strictEqual(sanitizeString([]), '')
  })

  it('trims whitespace-only string', () => {
    assert.strictEqual(sanitizeString('   '), '')
  })

  it('trims leading and trailing whitespace', () => {
    assert.strictEqual(sanitizeString('  hello  '), 'hello')
  })

  it('preserves unicode characters (Chinese)', () => {
    assert.strictEqual(sanitizeString('商业厨房'), '商业厨房')
  })

  it('preserves unicode characters (emoji)', () => {
    assert.strictEqual(sanitizeString('Kitchen 🍳'), 'Kitchen 🍳')
  })

  it('preserves accented characters', () => {
    assert.strictEqual(sanitizeString('Café René'), 'Café René')
  })

  it('escapes all five HTML special characters', () => {
    assert.strictEqual(sanitizeString('&<>"\' '), '&amp;&lt;&gt;&quot;&#39;')
  })

  it('handles double-encoded attempts', () => {
    const input = '&amp;lt;script&amp;gt;'
    const result = sanitizeString(input)
    assert.strictEqual(result, '&amp;amp;lt;script&amp;amp;gt;')
  })

  it('handles very long string (10k chars) without crashing', () => {
    const longInput = 'a'.repeat(10000)
    const result = sanitizeString(longInput)
    assert.strictEqual(result.length, 10000)
  })

  it('handles string with only special characters', () => {
    assert.strictEqual(sanitizeString('<>&"\''), '&lt;&gt;&amp;&quot;&#39;')
  })

  it('handles SQL injection pattern (does not break)', () => {
    const input = "'; DROP TABLE kitchens; --"
    const result = sanitizeString(input)
    assert.strictEqual(result, "&#39;; DROP TABLE kitchens; --")
  })

  it('handles null byte character', () => {
    const input = 'hello\x00world'
    const result = sanitizeString(input)
    assert.ok(typeof result === 'string')
  })
})

describe('sanitizeKitchenPayload edge cases', () => {
  it('preserves numeric fields untouched', () => {
    const payload = {
      title: 'Test',
      description: 'Desc',
      address: '123 St',
      city: 'Portland',
      state: 'OR',
      zip_code: '97201',
      price_per_hour: 25.50,
      max_capacity: 10,
      square_feet: 1500,
    }
    const result = sanitizeKitchenPayload(payload)
    assert.strictEqual(result.price_per_hour, 25.50)
    assert.strictEqual(result.max_capacity, 10)
    assert.strictEqual(result.square_feet, 1500)
  })

  it('handles missing description (null → empty string)', () => {
    const payload = {
      title: 'Test',
      description: null,
      address: '123 St',
      city: 'Portland',
      state: 'OR',
      zip_code: '97201',
      price_per_hour: 25,
      max_capacity: 4,
    }
    const result = sanitizeKitchenPayload(payload)
    assert.strictEqual(result.description, '')
  })

  it('sanitizes all string fields simultaneously', () => {
    const payload = {
      title: '<b>Bold</b>',
      description: '<script>alert("xss")</script>',
      address: '123 "Main" St',
      city: "O'Brien",
      state: 'CA&OR',
      zip_code: '<97201>',
      price_per_hour: 25,
      max_capacity: 4,
    }
    const result = sanitizeKitchenPayload(payload)
    assert.strictEqual(result.title, '&lt;b&gt;Bold&lt;/b&gt;')
    assert.strictEqual(result.description, '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;')
    assert.strictEqual(result.address, '123 &quot;Main&quot; St')
    assert.strictEqual(result.city, 'O&#39;Brien')
    assert.strictEqual(result.state, 'CA&amp;OR')
    assert.strictEqual(result.zip_code, '&lt;97201&gt;')
  })

  it('preserves extra fields passed through spread', () => {
    const payload = {
      title: 'Test',
      description: 'Desc',
      address: '123 St',
      city: 'Portland',
      state: 'OR',
      zip_code: '97201',
      price_per_hour: 25,
      max_capacity: 4,
      extra_field: 'should persist',
    }
    const result = sanitizeKitchenPayload(payload)
    assert.strictEqual(result.extra_field, 'should persist')
  })
})
