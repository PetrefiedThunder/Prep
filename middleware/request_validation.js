const ESCAPE_MAP = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
}

function sanitizeString(input) {
  if (typeof input !== 'string') return ''
  let sanitized = ''
  for (const char of input) {
    sanitized += ESCAPE_MAP[char] ?? char
  }
  return sanitized.trim()
}

function sanitizeKitchenPayload(data) {
  return {
    ...data,
    title: sanitizeString(data.title),
    description: sanitizeString(data.description ?? ''),
    address: sanitizeString(data.address),
    city: sanitizeString(data.city),
    state: sanitizeString(data.state),
    zip_code: sanitizeString(data.zip_code),
  }
}

module.exports = {
  sanitizeString,
  sanitizeKitchenPayload,
}
