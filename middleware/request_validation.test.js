const assert = require('node:assert')
const { describe, it } = require('node:test')
const { sanitizeString, sanitizeKitchenPayload } = require('./request_validation')

describe('sanitizeString', () => {
  it('escapes script tags', () => {
    const input = '<script>alert(1)</script>'
    const result = sanitizeString(input)
    assert.strictEqual(result, '&lt;script&gt;alert(1)&lt;/script&gt;')
  })

  it('neutralizes inline event handlers', () => {
    const input = '<div onclick="alert(1)">click</div>'
    const result = sanitizeString(input)
    assert.strictEqual(result, '&lt;div onclick=&quot;alert(1)&quot;&gt;click&lt;/div&gt;')
  })

  it('handles malformed html gracefully', () => {
    const input = '<<img src=x onerror=alert(1)>'
    const result = sanitizeString(input)
    assert.strictEqual(result, '&lt;&lt;img src=x onerror=alert(1)&gt;')
  })
})

describe('sanitizeKitchenPayload', () => {
  it('sanitizes risky user-provided fields while keeping numeric values intact', () => {
    const payload = {
      title: 'Test <b>Kitchen</b>',
      description: 'Nice spot <script>alert(1)</script>',
      address: '123 Main <street>',
      city: 'New <York>',
      state: 'CA',
      zip_code: '94102',
      price_per_hour: 10,
      max_capacity: 2,
      square_feet: 100,
    }

    const sanitized = sanitizeKitchenPayload(payload)

    assert.strictEqual(sanitized.title, 'Test &lt;b&gt;Kitchen&lt;/b&gt;')
    assert.strictEqual(
      sanitized.description,
      'Nice spot &lt;script&gt;alert(1)&lt;/script&gt;'
    )
    assert.strictEqual(sanitized.address, '123 Main &lt;street&gt;')
    assert.strictEqual(sanitized.city, 'New &lt;York&gt;')
    assert.strictEqual(sanitized.state, 'CA')
    assert.strictEqual(sanitized.zip_code, '94102')
    assert.strictEqual(sanitized.price_per_hour, 10)
    assert.strictEqual(sanitized.max_capacity, 2)
    assert.strictEqual(sanitized.square_feet, 100)
  })
})
