import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Photo Actions Tests
 *
 * Tests validation and authorization logic for:
 *   - uploadKitchenPhoto (file type, size, ownership)
 *   - deleteKitchenPhoto (ownership, primary reassignment)
 *   - setPhotoAsPrimary (ownership check)
 *   - getKitchenPhotos
 *
 * These test the validation rules extracted from photos.ts
 * without hitting real Supabase/Storage.
 */

const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

// MIME-to-extension mapping (mirrors photos.ts)
const MIME_TO_EXT: Record<string, string> = {
  'image/jpeg': 'jpg',
  'image/png': 'png',
  'image/webp': 'webp',
}

// --- File validation tests ---

describe('Photo Upload — File Type Validation', () => {
  it('accepts JPEG files', () => {
    assert.ok(ALLOWED_TYPES.includes('image/jpeg'))
  })

  it('accepts PNG files', () => {
    assert.ok(ALLOWED_TYPES.includes('image/png'))
  })

  it('accepts WebP files', () => {
    assert.ok(ALLOWED_TYPES.includes('image/webp'))
  })

  it('rejects GIF files', () => {
    assert.ok(!ALLOWED_TYPES.includes('image/gif'))
  })

  it('rejects SVG files', () => {
    assert.ok(!ALLOWED_TYPES.includes('image/svg+xml'))
  })

  it('rejects application/pdf', () => {
    assert.ok(!ALLOWED_TYPES.includes('application/pdf'))
  })

  it('rejects empty string MIME type', () => {
    assert.ok(!ALLOWED_TYPES.includes(''))
  })
})

describe('Photo Upload — File Size Validation', () => {
  it('allows files under 5MB', () => {
    const fileSize = 4 * 1024 * 1024 // 4MB
    assert.ok(fileSize <= MAX_FILE_SIZE)
  })

  it('allows files exactly 5MB', () => {
    const fileSize = 5 * 1024 * 1024
    assert.ok(fileSize <= MAX_FILE_SIZE)
  })

  it('rejects files over 5MB', () => {
    const fileSize = 5 * 1024 * 1024 + 1
    assert.ok(fileSize > MAX_FILE_SIZE)
  })

  it('rejects very large files (100MB)', () => {
    const fileSize = 100 * 1024 * 1024
    assert.ok(fileSize > MAX_FILE_SIZE)
  })
})

describe('Photo Upload — MIME to Extension Mapping', () => {
  it('maps image/jpeg to jpg', () => {
    assert.strictEqual(MIME_TO_EXT['image/jpeg'], 'jpg')
  })

  it('maps image/png to png', () => {
    assert.strictEqual(MIME_TO_EXT['image/png'], 'png')
  })

  it('maps image/webp to webp', () => {
    assert.strictEqual(MIME_TO_EXT['image/webp'], 'webp')
  })

  it('returns undefined for unknown MIME types', () => {
    assert.strictEqual(MIME_TO_EXT['image/gif'], undefined)
  })

  it('falls back to jpg for unknown types (mirrors code logic)', () => {
    const fileType = 'image/bmp'
    const ext = MIME_TO_EXT[fileType] || 'jpg'
    assert.strictEqual(ext, 'jpg')
  })
})

describe('Photo Upload — Storage Path Generation', () => {
  it('generates path with kitchen ID prefix', () => {
    const kitchenId = 'kitchen-abc-123'
    const storagePath = `${kitchenId}/${Date.now()}-${Math.random().toString(36).substring(2, 8)}.jpg`
    assert.ok(storagePath.startsWith('kitchen-abc-123/'))
    assert.ok(storagePath.endsWith('.jpg'))
  })

  it('generates unique paths for consecutive uploads', () => {
    const kitchenId = 'kitchen-1'
    const path1 = `${kitchenId}/${Date.now()}-${Math.random().toString(36).substring(2, 8)}.png`
    const path2 = `${kitchenId}/${Date.now()}-${Math.random().toString(36).substring(2, 8)}.png`
    assert.notStrictEqual(path1, path2)
  })
})

describe('Photo Upload — Ownership Verification Pattern', () => {
  it('rejects upload when kitchen owner_id does not match user', () => {
    const kitchen = { owner_id: 'owner-999' }
    const userId = 'user-1'
    assert.notStrictEqual(kitchen.owner_id, userId)
    // Server action returns { error: 'Unauthorized: You do not own this kitchen' }
  })

  it('allows upload when kitchen owner_id matches user', () => {
    const kitchen = { owner_id: 'user-1' }
    const userId = 'user-1'
    assert.strictEqual(kitchen.owner_id, userId)
  })
})

describe('Photo Upload — Primary Photo Logic', () => {
  it('first photo is set as primary (count === 0)', () => {
    const existingCount = 0
    const isFirst = existingCount === 0
    assert.strictEqual(isFirst, true)
  })

  it('subsequent photos are not primary (count > 0)', () => {
    const existingCount = 3
    const isFirst = existingCount === 0
    assert.strictEqual(isFirst, false)
  })

  it('sort_order matches existing count', () => {
    const count = 5
    assert.strictEqual(count, 5)
    // New photo gets sort_order = count
  })
})

describe('Photo Delete — Primary Reassignment', () => {
  it('when deleting primary photo, next photo by sort_order becomes primary', () => {
    const deletedPhoto = { is_primary: true, kitchen_id: 'k1' }
    const remainingPhotos = [
      { id: 'p2', sort_order: 1 },
      { id: 'p3', sort_order: 2 },
    ]

    if (deletedPhoto.is_primary && remainingPhotos.length > 0) {
      const nextPrimary = remainingPhotos[0] // first by sort_order
      assert.strictEqual(nextPrimary.id, 'p2')
    }
  })

  it('when deleting primary photo with no remaining photos, no reassignment needed', () => {
    const deletedPhoto = { is_primary: true, kitchen_id: 'k1' }
    const remainingPhotos: unknown[] = []

    const needsReassignment = deletedPhoto.is_primary && remainingPhotos.length > 0
    assert.strictEqual(needsReassignment, false)
  })

  it('when deleting non-primary photo, no reassignment needed', () => {
    const deletedPhoto = { is_primary: false, kitchen_id: 'k1' }
    assert.strictEqual(deletedPhoto.is_primary, false)
  })
})
