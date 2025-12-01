'use client'

import { useState } from 'react'
import Link from 'next/link'
import { createCheckoutSession } from '@/lib/actions/bookings'

interface BookKitchenPageProps {
  params: Promise<{ id: string }>
}

export default function BookKitchenPage({ params }: BookKitchenPageProps) {
  const [kitchenId, setKitchenId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Unwrap params
  useState(() => {
    params.then(p => setKitchenId(p.id))
  })

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!kitchenId) return

    setLoading(true)
    setError(null)

    const formData = new FormData(e.currentTarget)
    const date = formData.get('date') as string
    const startTime = formData.get('start_time') as string
    const endTime = formData.get('end_time') as string

    const startDateTime = `${date}T${startTime}:00`
    const endDateTime = `${date}T${endTime}:00`

    const result = await createCheckoutSession(kitchenId, startDateTime, endDateTime)

    if (result.error) {
      setError(result.error)
      setLoading(false)
    } else if (result.url) {
      window.location.href = result.url
    }
  }

  if (!kitchenId) {
    return <div className="max-w-2xl mx-auto">Loading...</div>
  }

  return (
    <div className="max-w-2xl mx-auto">
      <Link
        href={`/kitchens/${kitchenId}`}
        className="inline-block mb-4 text-gray-900 hover:underline"
      >
        ← Back to kitchen
      </Link>

      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">
          Book This Kitchen
        </h1>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="date" className="block text-sm font-medium text-gray-700 mb-1">
              Date *
            </label>
            <input
              id="date"
              name="date"
              type="date"
              required
              min={new Date().toISOString().split('T')[0]}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="start_time" className="block text-sm font-medium text-gray-700 mb-1">
                Start Time *
              </label>
              <input
                id="start_time"
                name="start_time"
                type="time"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900"
              />
            </div>

            <div>
              <label htmlFor="end_time" className="block text-sm font-medium text-gray-700 mb-1">
                End Time *
              </label>
              <input
                id="end_time"
                name="end_time"
                type="time"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900"
              />
            </div>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <p className="text-sm text-gray-600 mb-2">
              Payment will be processed securely through Stripe.
            </p>
            <p className="text-sm text-gray-600">
              You will be able to review the total amount before confirming payment.
            </p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gray-900 text-white py-3 rounded-lg font-semibold hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Processing...' : 'Proceed to Payment'}
          </button>
        </form>
      </div>
    </div>
  )
}
