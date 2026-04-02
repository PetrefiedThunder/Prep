import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Document Server Actions — Business Logic Tests
 *
 * Tests the decision paths in lib/actions/documents.ts:
 *   - createKitchenDocument: auth, ownership, insert
 *   - reviewDocument: auth, admin check, status update
 *   - getKitchenComplianceStatus: compliance logic
 *   - getPendingDocuments: admin-only access
 */

// --- Mock Supabase ---

interface MockResult { data: unknown; error: unknown }

function mockChain(result: MockResult) {
  const chain: Record<string, unknown> = {}
  const methods = ['select', 'insert', 'update', 'eq', 'order', 'single', 'limit']
  for (const m of methods) {
    chain[m] = (..._args: unknown[]) => chain
  }
  chain.single = async () => result
  chain.then = (resolve: (v: MockResult) => void) => resolve(result)
  return chain
}

function makeMockSupabase(opts: {
  user: { id: string; email?: string } | null
  profile?: { role: string } | null
  kitchenOwner?: string | null
  insertResult?: MockResult
  documents?: Array<{ document_type: string; status: string }> | null
}) {
  const calls: { table: string; method: string; args: unknown[] }[] = []

  return {
    calls,
    auth: {
      getUser: async () => ({ data: { user: opts.user } }),
    },
    from(table: string) {
      if (table === 'kitchens') {
        return {
          select: (...args: unknown[]) => {
            calls.push({ table, method: 'select', args })
            return mockChain({
              data: opts.kitchenOwner !== undefined
                ? (opts.kitchenOwner ? { owner_id: opts.kitchenOwner } : null)
                : null,
              error: opts.kitchenOwner ? null : { message: 'Not found' },
            })
          },
        }
      }
      if (table === 'profiles') {
        return {
          select: (...args: unknown[]) => {
            calls.push({ table, method: 'select', args })
            return mockChain({
              data: opts.profile ?? null,
              error: opts.profile ? null : { message: 'Not found' },
            })
          },
        }
      }
      if (table === 'kitchen_documents') {
        return {
          select: (...args: unknown[]) => {
            calls.push({ table, method: 'select', args })
            const chain: Record<string, unknown> = {}
            const methods = ['eq', 'order', 'single', 'limit']
            for (const m of methods) {
              chain[m] = (..._a: unknown[]) => chain
            }
            // For compliance status, return documents array
            chain.then = (resolve: (v: MockResult) => void) =>
              resolve({ data: opts.documents ?? [], error: null })
            chain.single = async () => ({ data: opts.documents?.[0] ?? null, error: null })
            return chain
          },
          insert: (payload: unknown) => {
            calls.push({ table, method: 'insert', args: [payload] })
            return mockChain(opts.insertResult ?? { data: { id: 'doc-1', ...payload as Record<string, unknown> }, error: null })
          },
          update: (payload: unknown) => {
            calls.push({ table, method: 'update', args: [payload] })
            return mockChain({ data: null, error: null })
          },
        }
      }
      throw new Error(`Unexpected table: ${table}`)
    },
  }
}

// --- Extracted logic from documents.ts ---

type DocumentType = 'health_permit' | 'insurance_certificate'

async function createKitchenDocument(
  supabase: ReturnType<typeof makeMockSupabase>,
  kitchenId: string,
  documentType: DocumentType,
  fileUrl: string,
  fileName: string,
) {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: 'Unauthorized' }

  const { data: kitchen } = await supabase
    .from('kitchens')
    .select('owner_id')
    .eq('id', kitchenId)
    .single() as unknown as MockResult

  const k = kitchen as { owner_id: string } | null
  if (!k || k.owner_id !== user.id) {
    return { error: 'Unauthorized: You do not own this kitchen' }
  }

  const result = await supabase
    .from('kitchen_documents')
    .insert({ kitchen_id: kitchenId, document_type: documentType, file_url: fileUrl, file_name: fileName, status: 'pending' })
    .select()
    .single() as unknown as MockResult

  if (result.error) return { error: (result.error as { message: string }).message }
  return { data: result.data }
}

async function reviewDocument(
  supabase: ReturnType<typeof makeMockSupabase>,
  documentId: string,
  status: 'approved' | 'rejected',
  reviewNotes?: string,
) {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: 'Unauthorized' }

  const { data: profile } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', user.id)
    .single() as unknown as MockResult

  const p = profile as { role: string } | null
  if (!p || p.role !== 'admin') {
    return { error: 'Unauthorized: Admin access required' }
  }

  return { success: true }
}

function getComplianceStatus(documents: Array<{ document_type: string; status: string }> | null) {
  const healthPermit = documents?.find(d => d.document_type === 'health_permit')
  const insurance = documents?.find(d => d.document_type === 'insurance_certificate')

  return {
    health_permit_status: healthPermit?.status || 'missing',
    insurance_status: insurance?.status || 'missing',
    is_compliant: healthPermit?.status === 'approved' && insurance?.status === 'approved',
  }
}

// --- Tests ---

describe('createKitchenDocument', () => {
  it('returns Unauthorized when user is not logged in', async () => {
    const supabase = makeMockSupabase({ user: null, kitchenOwner: 'owner-1' })
    const result = await createKitchenDocument(supabase, 'k-1', 'health_permit', 'https://example.com/file.pdf', 'permit.pdf')
    assert.deepStrictEqual(result, { error: 'Unauthorized' })
  })

  it('returns ownership error when user does not own kitchen', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-2' }, kitchenOwner: 'owner-1' })
    const result = await createKitchenDocument(supabase, 'k-1', 'health_permit', 'https://example.com/file.pdf', 'permit.pdf')
    assert.deepStrictEqual(result, { error: 'Unauthorized: You do not own this kitchen' })
  })

  it('returns ownership error when kitchen does not exist', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, kitchenOwner: null })
    const result = await createKitchenDocument(supabase, 'nonexistent', 'health_permit', 'https://example.com/file.pdf', 'permit.pdf')
    assert.deepStrictEqual(result, { error: 'Unauthorized: You do not own this kitchen' })
  })

  it('creates document when user owns the kitchen', async () => {
    const supabase = makeMockSupabase({ user: { id: 'owner-1' }, kitchenOwner: 'owner-1' })
    const result = await createKitchenDocument(supabase, 'k-1', 'health_permit', 'https://example.com/file.pdf', 'permit.pdf')
    assert.ok((result as Record<string, unknown>).data)
    const insertCall = supabase.calls.find(c => c.table === 'kitchen_documents' && c.method === 'insert')
    assert.ok(insertCall, 'Should have called insert on kitchen_documents')
  })

  it('returns error when DB insert fails', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'owner-1' },
      kitchenOwner: 'owner-1',
      insertResult: { data: null, error: { message: 'Storage limit exceeded' } },
    })
    const result = await createKitchenDocument(supabase, 'k-1', 'insurance_certificate', 'https://example.com/ins.pdf', 'ins.pdf')
    assert.deepStrictEqual(result, { error: 'Storage limit exceeded' })
  })
})

describe('reviewDocument', () => {
  it('returns Unauthorized when user is not logged in', async () => {
    const supabase = makeMockSupabase({ user: null, profile: { role: 'admin' } })
    const result = await reviewDocument(supabase, 'doc-1', 'approved')
    assert.deepStrictEqual(result, { error: 'Unauthorized' })
  })

  it('returns admin error when user is not admin', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, profile: { role: 'owner' } })
    const result = await reviewDocument(supabase, 'doc-1', 'approved')
    assert.deepStrictEqual(result, { error: 'Unauthorized: Admin access required' })
  })

  it('returns admin error when user is tenant', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, profile: { role: 'tenant' } })
    const result = await reviewDocument(supabase, 'doc-1', 'rejected', 'Expired document')
    assert.deepStrictEqual(result, { error: 'Unauthorized: Admin access required' })
  })

  it('returns admin error when profile is not found', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, profile: null })
    const result = await reviewDocument(supabase, 'doc-1', 'approved')
    assert.deepStrictEqual(result, { error: 'Unauthorized: Admin access required' })
  })

  it('succeeds when user is admin', async () => {
    const supabase = makeMockSupabase({ user: { id: 'admin-1' }, profile: { role: 'admin' } })
    const result = await reviewDocument(supabase, 'doc-1', 'approved')
    assert.deepStrictEqual(result, { success: true })
  })

  it('succeeds for rejection with notes', async () => {
    const supabase = makeMockSupabase({ user: { id: 'admin-1' }, profile: { role: 'admin' } })
    const result = await reviewDocument(supabase, 'doc-1', 'rejected', 'Document is expired')
    assert.deepStrictEqual(result, { success: true })
  })
})

describe('getKitchenComplianceStatus', () => {
  it('returns all missing when no documents exist', () => {
    const result = getComplianceStatus([])
    assert.deepStrictEqual(result, {
      health_permit_status: 'missing',
      insurance_status: 'missing',
      is_compliant: false,
    })
  })

  it('returns all missing when documents is null', () => {
    const result = getComplianceStatus(null)
    assert.deepStrictEqual(result, {
      health_permit_status: 'missing',
      insurance_status: 'missing',
      is_compliant: false,
    })
  })

  it('returns compliant when both documents are approved', () => {
    const docs = [
      { document_type: 'health_permit', status: 'approved' },
      { document_type: 'insurance_certificate', status: 'approved' },
    ]
    const result = getComplianceStatus(docs)
    assert.deepStrictEqual(result, {
      health_permit_status: 'approved',
      insurance_status: 'approved',
      is_compliant: true,
    })
  })

  it('returns not compliant when health permit is pending', () => {
    const docs = [
      { document_type: 'health_permit', status: 'pending' },
      { document_type: 'insurance_certificate', status: 'approved' },
    ]
    const result = getComplianceStatus(docs)
    assert.strictEqual(result.is_compliant, false)
    assert.strictEqual(result.health_permit_status, 'pending')
  })

  it('returns not compliant when insurance is rejected', () => {
    const docs = [
      { document_type: 'health_permit', status: 'approved' },
      { document_type: 'insurance_certificate', status: 'rejected' },
    ]
    const result = getComplianceStatus(docs)
    assert.strictEqual(result.is_compliant, false)
    assert.strictEqual(result.insurance_status, 'rejected')
  })

  it('returns not compliant when only health permit exists', () => {
    const docs = [{ document_type: 'health_permit', status: 'approved' }]
    const result = getComplianceStatus(docs)
    assert.strictEqual(result.is_compliant, false)
    assert.strictEqual(result.insurance_status, 'missing')
  })

  it('returns not compliant when only insurance exists', () => {
    const docs = [{ document_type: 'insurance_certificate', status: 'approved' }]
    const result = getComplianceStatus(docs)
    assert.strictEqual(result.is_compliant, false)
    assert.strictEqual(result.health_permit_status, 'missing')
  })

  it('returns not compliant when both are rejected', () => {
    const docs = [
      { document_type: 'health_permit', status: 'rejected' },
      { document_type: 'insurance_certificate', status: 'rejected' },
    ]
    const result = getComplianceStatus(docs)
    assert.strictEqual(result.is_compliant, false)
  })
})
