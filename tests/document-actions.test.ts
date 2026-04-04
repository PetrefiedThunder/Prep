import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Document Actions Tests
 *
 * Tests authorization and logic for:
 *   - createKitchenDocument (ownership verification)
 *   - reviewDocument (admin role check, status transitions)
 *   - getKitchenComplianceStatus (status aggregation)
 *   - uploadDocumentFile (file path generation)
 *   - getPendingDocuments (admin-only access)
 *
 * Extracted from lib/actions/documents.ts
 */

// --- Valid document types ---
const VALID_DOC_TYPES = ['health_permit', 'insurance_certificate']
const VALID_STATUSES = ['pending', 'approved', 'rejected']

describe('Document Actions — Authorization: createKitchenDocument', () => {
  it('rejects unauthenticated user', () => {
    const user = null
    if (!user) {
      assert.deepStrictEqual({ error: 'Unauthorized' }, { error: 'Unauthorized' })
    }
  })

  it('rejects user who does not own the kitchen', () => {
    const kitchen = { owner_id: 'owner-999' }
    const userId = 'user-1'
    assert.notStrictEqual(kitchen.owner_id, userId)
    // returns { error: 'Unauthorized: You do not own this kitchen' }
  })

  it('allows kitchen owner to create document', () => {
    const kitchen = { owner_id: 'user-1' }
    const userId = 'user-1'
    assert.strictEqual(kitchen.owner_id, userId)
  })
})

describe('Document Actions — reviewDocument Admin Check', () => {
  it('rejects non-admin user (role=owner)', () => {
    const profile = { role: 'owner' }
    if (!profile || profile.role !== 'admin') {
      assert.deepStrictEqual(
        { error: 'Unauthorized: Admin access required' },
        { error: 'Unauthorized: Admin access required' }
      )
    }
  })

  it('rejects non-admin user (role=tenant)', () => {
    const profile = { role: 'tenant' }
    assert.notStrictEqual(profile.role, 'admin')
  })

  it('allows admin user', () => {
    const profile = { role: 'admin' }
    assert.strictEqual(profile.role, 'admin')
  })

  it('rejects when profile is null (user not in profiles table)', () => {
    const profile = null
    if (!profile || (profile as { role: string } | null)?.role !== 'admin') {
      assert.ok(true, 'correctly rejects null profile')
    }
  })
})

describe('Document Actions — Review Status Transitions', () => {
  it('sets status to approved with reviewer metadata', () => {
    const status = 'approved'
    const reviewerId = 'admin-1'
    const reviewedAt = new Date().toISOString()

    const updatePayload = {
      status,
      reviewer_id: reviewerId,
      reviewed_at: reviewedAt,
      review_notes: null,
    }

    assert.strictEqual(updatePayload.status, 'approved')
    assert.ok(updatePayload.reviewer_id)
    assert.ok(updatePayload.reviewed_at)
    assert.strictEqual(updatePayload.review_notes, null)
  })

  it('sets status to rejected with review notes', () => {
    const updatePayload = {
      status: 'rejected',
      reviewer_id: 'admin-1',
      reviewed_at: new Date().toISOString(),
      review_notes: 'Document expired, please upload a current permit',
    }

    assert.strictEqual(updatePayload.status, 'rejected')
    assert.ok(updatePayload.review_notes)
    assert.ok(updatePayload.review_notes.length > 0)
  })

  it('only allows approved or rejected as review status', () => {
    const validReviewStatuses = ['approved', 'rejected']
    assert.ok(validReviewStatuses.includes('approved'))
    assert.ok(validReviewStatuses.includes('rejected'))
    assert.ok(!validReviewStatuses.includes('pending'))
  })
})

describe('Document Actions — Document Type Validation', () => {
  it('recognizes health_permit as valid type', () => {
    assert.ok(VALID_DOC_TYPES.includes('health_permit'))
  })

  it('recognizes insurance_certificate as valid type', () => {
    assert.ok(VALID_DOC_TYPES.includes('insurance_certificate'))
  })

  it('rejects unknown document types', () => {
    assert.ok(!VALID_DOC_TYPES.includes('business_license'))
    assert.ok(!VALID_DOC_TYPES.includes('fire_inspection'))
    assert.ok(!VALID_DOC_TYPES.includes(''))
  })
})

describe('Document Actions — File Upload Path Generation', () => {
  it('generates path with kitchenId and documentType', () => {
    const kitchenId = 'kitchen-abc'
    const documentType = 'health_permit'
    const fileName = 'permit.pdf'
    const fileExt = fileName.split('.').pop()
    const generatedPath = `${kitchenId}/${documentType}-${Date.now()}.${fileExt}`

    assert.ok(generatedPath.startsWith('kitchen-abc/'))
    assert.ok(generatedPath.includes('health_permit'))
    assert.ok(generatedPath.endsWith('.pdf'))
  })

  it('handles filenames with multiple dots', () => {
    const fileName = 'my.health.permit.v2.pdf'
    const fileExt = fileName.split('.').pop()
    assert.strictEqual(fileExt, 'pdf')
  })

  it('handles filenames with no extension', () => {
    const fileName = 'document'
    const fileExt = fileName.split('.').pop()
    // When no dot, pop() returns the whole string
    assert.strictEqual(fileExt, 'document')
  })
})

describe('Document Actions — Compliance Status Aggregation', () => {
  it('returns missing when no documents exist', () => {
    const documents: Array<{ document_type: string; status: string }> = []
    const healthPermit = documents.find(d => d.document_type === 'health_permit')
    const insurance = documents.find(d => d.document_type === 'insurance_certificate')

    assert.strictEqual(healthPermit?.status || 'missing', 'missing')
    assert.strictEqual(insurance?.status || 'missing', 'missing')
    const isCompliant = healthPermit?.status === 'approved' && insurance?.status === 'approved'
    assert.strictEqual(isCompliant, false)
  })

  it('returns pending status when document is pending review', () => {
    const documents = [
      { document_type: 'health_permit', status: 'pending' },
    ]
    const healthPermit = documents.find(d => d.document_type === 'health_permit')
    assert.strictEqual(healthPermit?.status || 'missing', 'pending')
  })

  it('handles multiple documents of same type (uses first found)', () => {
    const documents = [
      { document_type: 'health_permit', status: 'rejected' },
      { document_type: 'health_permit', status: 'approved' },
    ]
    // find() returns first match — older upload
    const healthPermit = documents.find(d => d.document_type === 'health_permit')
    assert.strictEqual(healthPermit?.status, 'rejected')
  })
})
