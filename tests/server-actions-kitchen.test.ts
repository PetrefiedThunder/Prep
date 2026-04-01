import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Server Action Integration Tests — Kitchen CRUD
 *
 * These tests verify the business logic of kitchen server actions
 * by simulating the Supabase client interface. The actual server
 * actions (lib/actions/kitchens.ts) use `createClient()` from
 * Next.js server context, so we replicate the logic with a mock
 * Supabase client to test the decision paths.
 */

// --- Mock Supabase builder (chainable query interface) ---

interface MockResult { data: unknown; error: unknown }

function mockChain(result: MockResult) {
  const chain: Record<string, unknown> = {}
  const methods = ['select', 'insert', 'update', 'delete', 'eq', 'order', 'single']
  for (const m of methods) {
    chain[m] = (..._args: unknown[]) => chain
  }
  // Terminal methods return the result
  chain.single = async () => result
  chain.then = (resolve: (v: MockResult) => void) => resolve(result)
  // Make it thenable for non-single queries
  return chain
}

function makeMockSupabase(opts: {
  user: { id: string; email: string } | null
  queryResults?: Record<string, MockResult>
}) {
  const calls: { table: string; method: string; args: unknown[] }[] = []

  return {
    calls,
    auth: {
      getUser: async () => ({ data: { user: opts.user } }),
    },
    from(table: string) {
      const results = opts.queryResults ?? {}
      return {
        select: (...args: unknown[]) => {
          calls.push({ table, method: 'select', args })
          return mockChain(results[`${table}.select`] ?? { data: [], error: null })
        },
        insert: (payload: unknown) => {
          calls.push({ table, method: 'insert', args: [payload] })
          return mockChain(results[`${table}.insert`] ?? { data: payload, error: null })
        },
        update: (payload: unknown) => {
          calls.push({ table, method: 'update', args: [payload] })
          return mockChain(results[`${table}.update`] ?? { data: payload, error: null })
        },
        delete: () => {
          calls.push({ table, method: 'delete', args: [] })
          return mockChain(results[`${table}.delete`] ?? { data: null, error: null })
        },
      }
    },
  }
}

// --- Extracted server action logic ---
// Mirrors lib/actions/kitchens.ts but accepts injected supabase + user

function sanitizeString(input: unknown): string {
  if (typeof input !== 'string') return ''
  const ESCAPE_MAP: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
  let sanitized = ''
  for (const char of input) {
    sanitized += ESCAPE_MAP[char] ?? char
  }
  return sanitized.trim()
}

function sanitizeKitchenPayload(data: Record<string, unknown>) {
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


interface KitchenFormData {
  title: string; description: string; address: string; city: string
  state: string; zip_code: string; price_per_hour: number
  max_capacity: number; square_feet?: number
}

async function createKitchen(supabase: ReturnType<typeof makeMockSupabase>, data: KitchenFormData) {
  const cleanData = sanitizeKitchenPayload(data as unknown as Record<string, unknown>)
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) return { error: 'Unauthorized' }

  const result = await supabase
    .from('kitchens')
    .insert({
      owner_id: user.id,
      title: cleanData.title,
      description: cleanData.description,
      address: cleanData.address,
      city: cleanData.city,
      state: cleanData.state,
      zip_code: cleanData.zip_code,
      price_per_hour: cleanData.price_per_hour,
      max_capacity: cleanData.max_capacity,
      square_feet: (cleanData as Record<string, unknown>).square_feet || null,
      is_active: true,
    })
    .select()
    .single() as unknown as MockResult

  if (result.error) return { error: (result.error as { message: string }).message }
  return { data: result.data }
}

async function updateKitchen(
  supabase: ReturnType<typeof makeMockSupabase>,
  id: string,
  data: KitchenFormData
) {
  const cleanData = sanitizeKitchenPayload(data as unknown as Record<string, unknown>)
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) return { error: 'Unauthorized' }

  const result = await supabase
    .from('kitchens')
    .update({
      title: cleanData.title,
      description: cleanData.description,
    })
    .eq('id', id)
    .eq('owner_id', user.id)
    .select()
    .single() as unknown as MockResult

  if (result.error) return { error: (result.error as { message: string }).message }
  return { data: result.data }
}

async function deleteKitchen(supabase: ReturnType<typeof makeMockSupabase>, id: string) {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: 'Unauthorized' }

  const result = await supabase
    .from('kitchens')
    .delete()
    .eq('id', id)
    .eq('owner_id', user.id) as unknown as MockResult

  if (result.error) return { error: (result.error as { message: string }).message }
  return { success: true }
}

// --- Tests ---

const VALID_KITCHEN: KitchenFormData = {
  title: 'Test Kitchen',
  description: 'A great place to cook',
  address: '123 Main St',
  city: 'Portland',
  state: 'OR',
  zip_code: '97201',
  price_per_hour: 25,
  max_capacity: 4,
  square_feet: 500,
}

describe('createKitchen server action', () => {
  it('returns Unauthorized when user is not logged in', async () => {
    const supabase = makeMockSupabase({ user: null })
    const result = await createKitchen(supabase, VALID_KITCHEN)
    assert.deepStrictEqual(result, { error: 'Unauthorized' })
    assert.strictEqual(supabase.calls.length, 0)
  })

  it('sanitizes input before inserting', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1', email: 'test@test.com' },
      queryResults: {
        'kitchens.insert': { data: { id: 'k-1', title: '&lt;script&gt;' }, error: null },
      },
    })
    const xssKitchen = { ...VALID_KITCHEN, title: '<script>alert(1)</script>' }
    await createKitchen(supabase, xssKitchen)

    assert.strictEqual(supabase.calls.length, 1)
    const insertPayload = supabase.calls[0].args[0] as Record<string, unknown>
    assert.ok(!(insertPayload.title as string).includes('<script>'))
    assert.ok((insertPayload.title as string).includes('&lt;script&gt;'))
  })

  it('sets owner_id to current user', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-42', email: 'owner@test.com' },
    })
    await createKitchen(supabase, VALID_KITCHEN)

    const insertPayload = supabase.calls[0].args[0] as Record<string, unknown>
    assert.strictEqual(insertPayload.owner_id, 'user-42')
  })

  it('sets is_active to true by default', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1', email: 'test@test.com' },
    })
    await createKitchen(supabase, VALID_KITCHEN)

    const insertPayload = supabase.calls[0].args[0] as Record<string, unknown>
    assert.strictEqual(insertPayload.is_active, true)
  })

  it('returns error when DB insert fails', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1', email: 'test@test.com' },
      queryResults: {
        'kitchens.insert': { data: null, error: { message: 'Duplicate title' } },
      },
    })
    const result = await createKitchen(supabase, VALID_KITCHEN)
    assert.deepStrictEqual(result, { error: 'Duplicate title' })
  })

  it('sets square_feet to null when not provided', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1', email: 'test@test.com' },
    })
    const kitchenNoSqft = { ...VALID_KITCHEN, square_feet: undefined }
    await createKitchen(supabase, kitchenNoSqft)

    const insertPayload = supabase.calls[0].args[0] as Record<string, unknown>
    assert.strictEqual(insertPayload.square_feet, null)
  })
})

describe('updateKitchen server action', () => {
  it('returns Unauthorized when user is not logged in', async () => {
    const supabase = makeMockSupabase({ user: null })
    const result = await updateKitchen(supabase, 'k-1', VALID_KITCHEN)
    assert.deepStrictEqual(result, { error: 'Unauthorized' })
  })

  it('sanitizes input on update', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1', email: 'test@test.com' },
    })
    const xssKitchen = { ...VALID_KITCHEN, title: '"><img onerror=alert(1)>' }
    await updateKitchen(supabase, 'k-1', xssKitchen)

    const updatePayload = supabase.calls[0].args[0] as Record<string, unknown>
    assert.ok(!(updatePayload.title as string).includes('<'))
  })
})

describe('deleteKitchen server action', () => {
  it('returns Unauthorized when user is not logged in', async () => {
    const supabase = makeMockSupabase({ user: null })
    const result = await deleteKitchen(supabase, 'k-1')
    assert.deepStrictEqual(result, { error: 'Unauthorized' })
  })

  it('calls delete on kitchens table', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1', email: 'test@test.com' },
    })
    const result = await deleteKitchen(supabase, 'k-1')
    assert.deepStrictEqual(result, { success: true })
    assert.strictEqual(supabase.calls[0].method, 'delete')
    assert.strictEqual(supabase.calls[0].table, 'kitchens')
  })

  it('returns error when DB delete fails', async () => {
    const supabase = makeMockSupabase({
      user: { id: 'user-1', email: 'test@test.com' },
      queryResults: {
        'kitchens.delete': { data: null, error: { message: 'FK constraint' } },
      },
    })
    const result = await deleteKitchen(supabase, 'k-1')
    assert.deepStrictEqual(result, { error: 'FK constraint' })
  })
})
