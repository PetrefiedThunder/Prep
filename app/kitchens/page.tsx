import { createClient } from '@/lib/supabase/server'
import SearchFilters from './SearchFilters'
import KitchenSearchCard from './KitchenSearchCard'

interface SearchParams {
  city?: string
  minPrice?: string
  maxPrice?: string
}

interface KitchensPageProps {
  searchParams: Promise<SearchParams>
}

export default async function KitchensPage({ searchParams }: KitchensPageProps) {
  const params = await searchParams
  const supabase = await createClient()

  // Build query
  let query = supabase
    .from('kitchens')
    .select(`
      *,
      kitchen_photos (*)
    `)
    .eq('is_active', true)
    .order('created_at', { ascending: false })

  // Apply filters
  if (params.city) {
    query = query.ilike('city', `%${params.city}%`)
  }

  if (params.minPrice) {
    query = query.gte('price_per_hour', parseFloat(params.minPrice))
  }

  if (params.maxPrice) {
    query = query.lte('price_per_hour', parseFloat(params.maxPrice))
  }

  // Limit results
  query = query.limit(50)

  const { data: kitchens, error } = await query

  if (error) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          Error loading kitchens: {error.message}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">
        Find a Kitchen
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filters Sidebar */}
        <div className="lg:col-span-1">
          <SearchFilters />
        </div>

        {/* Results */}
        <div className="lg:col-span-3">
          {!kitchens || kitchens.length === 0 ? (
            <div className="bg-white p-12 rounded-lg shadow-md text-center">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">
                No kitchens found
              </h2>
              <p className="text-gray-600">
                Try adjusting your search filters or browse all kitchens.
              </p>
            </div>
          ) : (
            <>
              <div className="mb-4 text-gray-600">
                {kitchens.length} {kitchens.length === 1 ? 'kitchen' : 'kitchens'} found
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {kitchens.map((kitchen) => (
                  <KitchenSearchCard key={kitchen.id} kitchen={kitchen} />
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
