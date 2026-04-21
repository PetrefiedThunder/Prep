import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Tests for photo upload validation logic extracted from lib/actions/photos.ts.
 *
 * The server action uploadKitchenPhoto validates file type, file size,
 * and maps MIME types to safe extensions. We test that logic here.
 */

const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const MIME_TO_EXT: Record<string, string> = {
  'image/jpeg': 'jpg',
  'image/png': 'png',
  'image/webp': 'webp',
}

function validateFileType(mimeType: string): { valid: boolean; error?: string } {
  if (!ALLOWED_TYPES.includes(mimeType)) {
    return { valid: false, error: 'Invalid file type. Allowed: JPEG, PNG, WebP' }
  }
  return { valid: true }
}

function validateFileSize(size: number): { valid: boolean; error?: string } {
  if (size > MAX_FILE_SIZE) {
    return { valid: false, error: 'File too large. Maximum size is 5MB' }
  }
  return { valid: true }
}

function getFileExtension(mimeType: string): string {
  return MIME_TO_EXT[mimeType] || 'jpg'
}

describe('Photo file type validation', () => {
  it('accepts image/jpeg', () => {
    assert.strictEqual(validateFileType('image/jpeg').valid, true)
  })

  it('accepts image/png', () => {
    assert.strictEqual(validateFileType('image/png').valid, true)
  })

  it('accepts image/webp', () => {
    assert.strictEqual(validateFileType('image/webp').valid, true)
  })

  it('rejects image/gif', () => {
    const result = validateFileType('image/gif')
    assert.strictEqual(result.valid, false)
    assert.ok(result.error?.includes('Invalid file type'))
  })

  it('rejects application/pdf', () => {
    assert.strictEqual(validateFileType('application/pdf').valid, false)
  })

  it('rejects image/svg+xml (XSS risk)', () => {
    assert.strictEqual(validateFileType('image/svg+xml').valid, false)
  })

  it('rejects text/html', () => {
    assert.strictEqual(validateFileType('text/html').valid, false)
  })

  it('rejects empty string', () => {
    assert.strictEqual(validateFileType('').valid, false)
  })
})

describe('Photo file size validation', () => {
  it('accepts file exactly at limit (5MB)', () => {
    assert.strictEqual(validateFileSize(MAX_FILE_SIZE).valid, true)
  })

  it('accepts file under limit', () => {
    assert.strictEqual(validateFileSize(1024 * 1024).valid, true) // 1MB
  })

  it('rejects file over limit', () => {
    const result = validateFileSize(MAX_FILE_SIZE + 1)
    assert.strictEqual(result.valid, false)
    assert.ok(result.error?.includes('5MB'))
  })

  it('accepts zero-size file', () => {
    assert.strictEqual(validateFileSize(0).valid, true)
  })

  it('rejects 10MB file', () => {
    assert.strictEqual(validateFileSize(10 * 1024 * 1024).valid, false)
  })
})

describe('MIME to extension mapping', () => {
  it('maps image/jpeg to jpg', () => {
    assert.strictEqual(getFileExtension('image/jpeg'), 'jpg')
  })

  it('maps image/png to png', () => {
    assert.strictEqual(getFileExtension('image/png'), 'png')
  })

  it('maps image/webp to webp', () => {
    assert.strictEqual(getFileExtension('image/webp'), 'webp')
  })

  it('defaults to jpg for unknown MIME type', () => {
    assert.strictEqual(getFileExtension('image/bmp'), 'jpg')
  })

  it('defaults to jpg for empty string', () => {
    assert.strictEqual(getFileExtension(''), 'jpg')
  })
})
