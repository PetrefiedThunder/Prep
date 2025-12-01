import { redirect } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/server'
import { getOwnerKitchens } from '@/lib/actions/kitchens'
import KitchenCard from './KitchenCard'

export default async function OwnerKitchensPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  const result = await getOwnerKitchens()

  if (result.error) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          Error loading kitchens: {result.error}
        </div>
      </div>
    )
  }

  const kitchens = result.data || []

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-gray-900">My Kitchens</h1>
        <Link
          href="/owner/kitchens/new"
          className="bg-gray-900 text-white px-6 py-3 rounded-lg font-semibold hover:bg-gray-800 transition"
        >
          + Add Kitchen
        </Link>
      </div>

      {kitchens.length === 0 ? (
        <div className="bg-white p-12 rounded-lg shadow-md text-center">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">
            No kitchens yet
          </h2>
          <p className="text-gray-600 mb-6">
            Start earning by listing your commercial kitchen space.
          </p>
          <Link
            href="/owner/kitchens/new"
            className="inline-block bg-gray-900 text-white px-8 py-3 rounded-lg font-semibold hover:bg-gray-800 transition"
          >
            List Your Kitchen
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {kitchens.map((kitchen) => (
            <KitchenCard key={kitchen.id} kitchen={kitchen} />
          ))}
        </div>
      )}
    </div>
  )
}
