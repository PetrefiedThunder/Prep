const assert = require('node:assert')
const { describe, it } = require('node:test')
const { sanitizeString, sanitizeKitchenPayload } = require('./request_validation')

describe('sanitizeString – extended edge cases', () => {
  it('returns empty string for non-string input (number)', () => {
    assert.strictEqual(sanitizeString(123), '')
  })

  it('returns empty string for null', () => {
    assert.strictEqual(sanitizeString(null), '')
  })

  it('returns empty string for undefined', () => {
    assert.strictEqual(sanitizeString(undefined), '')
  })

  it('returns empty string for boolean', () => {
    assert.strictEqual(sanitizeString(true), '')
  })

  it('returns empty string for object', () => {
    assert.strictEqual(sanitizeString({}), '')
  })

  it('trims leading and trailing whitespace', () => {
    assert.strictEqual(sanitizeString('  hello  '), 'hello')
  })

  it('preserves internal whitespace', () => {
    assert.strictEqual(sanitizeString('hello  world'), 'hello  world')
  })

  it('handles empty string', () => {
    assert.strictEqual(sanitizeString(''), '')
  })

  it('handles string of only whitespace', () => {
    assert.strictEqual(sanitizeString('   '), '')
  })

  it('escapes ampersands', () => {
    assert.strictEqual(sanitizeString('A & B'), 'A &amp; B')
  })

  it('escapes single quotes', () => {
    assert.strictEqual(sanitizeString("it's"), 'it&#39;s')
  })

  it('escapes double quotes', () => {
    assert.strictEqual(sanitizeString('say "hello"'), 'say &quot;hello&quot;')
  })

  it('handles mixed special characters', () => {
    const input = '<a href="test">&\'</a>'
    const result = sanitizeString(input)
    assert.ok(!result.includes('<'))
    assert.ok(!result.includes('>'))
    assert.ok(!result.includes('"'))
    assert.ok(!result.includes("'"))
    assert.ok(!result.includes('&') || result.includes('&amp;') || result.includes('&lt;') || result.includes('&gt;') || result.includes('&quot;') || result.includes('&#39;'))
  })

  it('handles unicode characters without escaping', () => {
    assert.strictEqual(sanitizeString('café résumé'), 'café résumé')
  })

  it('handles emoji without escaping', () => {
    assert.strictEqual(sanitizeString('Hello 👋'), 'Hello 👋')
  })

  it('handles very long strings without throwing', () => {
    const longStr = 'a'.repeat(100000)
    const result = sanitizeString(longStr)
    assert.strictEqual(result.length, 100000)
  })
})

describe('sanitizeKitchenPayload – extended edge cases', () => {
  const basePayload = {
    title: 'Test Kitchen',
    description: 'A great kitchen',
    address: '123 Main St',
    city: 'Portland',
    state: 'OR',
    zip_code: '97201',
    price_per_hour: 25,
    max_capacity: 4,
    square_feet: 500,
  }

  it('handles missing description gracefully (defaults to empty string)', () => {
    const payload = { ...basePayload, description: undefined }
    const result = sanitizeKitchenPayload(payload)
    assert.strictEqual(result.description, '')
  })

  it('preserves numeric fields unchanged', () => {
    const result = sanitizeKitchenPayload(basePayload)
    assert.strictEqual(result.price_per_hour, 25)
    assert.strictEqual(result.max_capacity, 4)
    assert.strictEqual(result.square_feet, 500)
  })

  it('preserves zero as a valid numeric value', () => {
    const payload = { ...basePayload, price_per_hour: 0, max_capacity: 0 }
    const result = sanitizeKitchenPayload(payload)
    assert.strictEqual(result.price_per_hour, 0)
    assert.strictEqual(result.max_capacity, 0)
  })

  it('sanitizes all string fields simultaneously', () => {
    const payload = {
      title: '<script>',
      description: '<img onerror>',
      address: '1 & 2 <St>',
      city: '"Portland"',
      state: "O'R",
      zip_code: '972<01',
      price_per_hour: 10,
      max_capacity: 2,
    }
    const result = sanitizeKitchenPayload(payload)
    // No raw HTML in any string field
    for (const key of ['title', 'description', 'address', 'city', 'state', 'zip_code']) {
      assert.ok(!result[key].includes('<'), `${key} should not contain <`)
      assert.ok(!result[key].includes('>'), `${key} should not contain >`)
    }
  })

  it('spreads through extra fields from data', () => {
    const payload = { ...basePayload, extra_field: 'bonus' }
    const result = sanitizeKitchenPayload(payload)
    assert.strictEqual(result.extra_field, 'bonus')
  })
})
